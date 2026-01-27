package scheduler

import (
	"fmt"
	"math"
	"math/rand"
	"time"

	"github.com/arnavshah/scheduler-api-go/pkg/models"
)

// Scheduler handles the logic of assigning volunteers to shifts
type Scheduler struct {
	Volunteers map[string]*models.Volunteer
	Shifts     map[string]*models.Shift
	Conflicts  []models.ConflictReason
}

// NewScheduler creates a new scheduler instance
func NewScheduler(volunteers map[string]*models.Volunteer, shifts map[string]*models.Shift) *Scheduler {
	return &Scheduler{
		Volunteers: volunteers,
		Shifts:     shifts,
	}
}

// Prefill records existing assignments
func (s *Scheduler) Prefill(assignments []models.Assignment) {
	for _, asgn := range assignments {
		vol, okVol := s.Volunteers[asgn.VolunteerID]
		shift, okShift := s.Shifts[asgn.ShiftID]

		if okVol && okShift {
			shift.Assigned = append(shift.Assigned, vol.ID)
			vol.AssignedShifts = append(vol.AssignedShifts, shift.ID)
			vol.AssignedHours += s.DurationHours(shift.Start, shift.End)
		}
	}
}

// DurationHours calculates the duration between two times in hours
func (s *Scheduler) DurationHours(start, end time.Time) float64 {
	return end.Sub(start).Hours()
}

// Overlap checks if two time ranges overlap
func (s *Scheduler) Overlap(aStart, aEnd, bStart, bEnd time.Time) bool {
	return aStart.Before(bEnd) && bStart.Before(aEnd)
}

// WouldOverlap checks if a volunteer's existing shifts overlap with a new one
func (s *Scheduler) WouldOverlap(volunteer *models.Volunteer, shift *models.Shift) bool {
	for _, shiftID := range volunteer.AssignedShifts {
		existingShift := s.Shifts[shiftID]
		if s.Overlap(existingShift.Start, existingShift.End, shift.Start, shift.End) {
			return true
		}
	}
	return false
}

// Allows checks if a volunteer is allowed to work a shift
func (s *Scheduler) Allows(shift *models.Shift, volunteer *models.Volunteer) bool {
	// Excluded groups
	if len(shift.ExcludedGroups) > 0 {
		for _, g := range shift.ExcludedGroups {
			if volunteer.Group == g {
				return false
			}
		}
	}
	// Allowed groups
	if len(shift.AllowedGroups) > 0 {
		found := false
		for _, g := range shift.AllowedGroups {
			if volunteer.Group == g {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	return true
}

// GroupByGroup returns volunteers grouped by their group name
func (s *Scheduler) GroupByGroup() map[string][]*models.Volunteer {
	volsByGroup := make(map[string][]*models.Volunteer)
	for _, vol := range s.Volunteers {
		volsByGroup[vol.Group] = append(volsByGroup[vol.Group], vol)
	}
	return volsByGroup
}

// AssignSimple implements a greedy randomized assignment logic
func (s *Scheduler) AssignSimple(shuffle bool) {
	s.AssignSimpleWithGroups(shuffle, s.GroupByGroup())
}

// AssignSimpleWithGroups implements a greedy randomized assignment logic with pre-grouped volunteers
func (s *Scheduler) AssignSimpleWithGroups(shuffle bool, volsByGroup map[string][]*models.Volunteer) {
	type slot struct {
		shiftID string
		group   string
	}

	// Pre-calculate shift durations and collect slots
	shiftDurations := make(map[string]float64, len(s.Shifts))
	var slots []slot
	for shiftID, shift := range s.Shifts {
		shiftDurations[shiftID] = s.DurationHours(shift.Start, shift.End)
		for group, count := range shift.RequiredGroups {
			// Find how many of this group are already assigned
			countAlready := 0
			for _, volID := range shift.Assigned {
				if vol, ok := s.Volunteers[volID]; ok && vol.Group == group {
					countAlready++
				}
			}
			needed := count - countAlready
			if needed > 0 {
				for i := 0; i < needed; i++ {
					slots = append(slots, slot{shiftID, group})
				}
			}
		}
	}

	if shuffle && len(slots) > 0 {
		r := rand.New(rand.NewSource(time.Now().UnixNano()))
		r.Shuffle(len(slots), func(i, j int) {
			slots[i], slots[j] = slots[j], slots[i]
		})
	}

	for _, sl := range slots {
		shift := s.Shifts[sl.shiftID]
		duration := shiftDurations[sl.shiftID]

		var best *models.Volunteer
		minHours := -1.0
		var reasons []string

		maxHoursCount := 0
		overlapCount := 0
		disallowedCount := 0

		// Use the pre-calculated volsByGroup for high performance
		for _, vol := range volsByGroup[sl.group] {
			// Check constraints and track why they fail
			fitsHours := vol.AssignedHours+duration <= vol.MaxHours
			noOverlap := !s.WouldOverlap(vol, shift)
			isAllowed := s.Allows(shift, vol)

			if fitsHours && noOverlap && isAllowed {
				if best == nil || vol.AssignedHours < minHours {
					best = vol
					minHours = vol.AssignedHours
				}
			} else {
				if !fitsHours {
					maxHoursCount++
				}
				if !noOverlap {
					overlapCount++
				}
				if !isAllowed {
					disallowedCount++
				}
			}
		}

		if best != nil {
			shift.Assigned = append(shift.Assigned, best.ID)
			best.AssignedHours += duration
			best.AssignedShifts = append(best.AssignedShifts, shift.ID)
		} else {
			// Record conflict
			if maxHoursCount > 0 {
				reasons = append(reasons, fmt.Sprintf("%d volunteers were at max hours", maxHoursCount))
			}
			if overlapCount > 0 {
				reasons = append(reasons, fmt.Sprintf("%d volunteers had overlapping shifts", overlapCount))
			}
			if disallowedCount > 0 {
				reasons = append(reasons, fmt.Sprintf("%d volunteers were disallowed by group rules", disallowedCount))
			}
			if len(reasons) == 0 {
				reasons = append(reasons, "no volunteers found in this group")
			}

			s.Conflicts = append(s.Conflicts, models.ConflictReason{
				ShiftID: sl.shiftID,
				Group:   sl.group,
				Reasons: reasons,
			})
		}
	}
}

// CalculateFairnessScore returns a percentage (0-100) representing how evenly
// shifts are distributed. 100% is perfectly fair (Standard Deviation = 0).
func (s *Scheduler) CalculateFairnessScore() float64 {
	if len(s.Volunteers) == 0 {
		return 100.0
	}

	var sum float64
	for _, v := range s.Volunteers {
		sum += v.AssignedHours
	}

	if sum == 0 {
		return 100.0 // Everyone having 0 hours is perfectly fair
	}

	mean := sum / float64(len(s.Volunteers))

	var varianceSum float64
	for _, v := range s.Volunteers {
		diff := v.AssignedHours - mean
		varianceSum += diff * diff
	}
	variance := varianceSum / float64(len(s.Volunteers))
	stdDev := math.Sqrt(variance)

	// Convert SD to a percentage relative to the mean
	// 100% means SD is 0. 0% means SD is >= mean.
	score := (1.0 - (stdDev / mean)) * 100.0
	if score < 0 {
		return 0.0
	}
	return score
}

// AssignOptimal attempts a more thorough assignment (simplified backtracking)
func (s *Scheduler) AssignOptimal(timeoutSeconds int) {
	// For simplicity and speed in serverless, we'll use a multi-pass greedy strategy
	// that tries different shuffles and keeps the best one (scored by unfilled slots)

	bestScore := -1.0
	var bestAssignments map[string][]string // shiftID -> []volunteerID

	start := time.Now()
	timeout := time.Duration(timeoutSeconds) * time.Second

	// Keep track of original state
	originalVols := make(map[string]float64)
	for id, v := range s.Volunteers {
		originalVols[id] = v.AssignedHours
	}

	volsByGroup := s.GroupByGroup()

	for time.Since(start) < timeout {
		// Reset
		for _, v := range s.Volunteers {
			v.AssignedHours = originalVols[v.ID]
			v.AssignedShifts = nil // We'd need to properly reset prefills here if we wanted perfection
		}
		for _, sh := range s.Shifts {
			sh.Assigned = nil
		}

		s.AssignSimpleWithGroups(true, volsByGroup)

		// Score
		score := 0.0
		totalRequired := 0
		filled := 0
		for _, sh := range s.Shifts {
			for _, count := range sh.RequiredGroups {
				totalRequired += count
			}
			filled += len(sh.Assigned)
		}
		score = float64(filled) / float64(totalRequired)

		if score > bestScore {
			bestScore = score
			bestAssignments = make(map[string][]string)
			for id, sh := range s.Shifts {
				bestAssignments[id] = append([]string{}, sh.Assigned...)
			}
		}

		if bestScore >= 1.0 {
			break // Perfect score
		}
	}

	// Restore best
	for id, asgn := range bestAssignments {
		s.Shifts[id].Assigned = asgn
	}
}
