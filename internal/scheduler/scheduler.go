package scheduler

import (
	"math/rand"
	"time"

	"github.com/arnavshah/scheduler-api-go/internal/models"
)

// Scheduler handles the logic of assigning volunteers to shifts
type Scheduler struct {
	Volunteers map[string]*models.Volunteer
	Shifts     map[string]*models.Shift
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

// AssignSimple implements a greedy randomized assignment logic
func (s *Scheduler) AssignSimple(shuffle bool) {
	type slot struct {
		shiftID string
		group   string
	}

	var slots []slot
	for shiftID, shift := range s.Shifts {
		for group, count := range shift.RequiredGroups {
			// Find how many of this group are already assigned
			countAlready := 0
			for _, volID := range shift.Assigned {
				if s.Volunteers[volID].Group == group {
					countAlready++
				}
			}
			needed := count - countAlready
			for i := 0; i < needed; i++ {
				slots = append(slots, slot{shiftID, group})
			}
		}
	}

	if shuffle {
		rand.Seed(time.Now().UnixNano())
		rand.Shuffle(len(slots), func(i, j int) {
			slots[i], slots[j] = slots[j], slots[i]
		})
	}

	for _, sl := range slots {
		shift := s.Shifts[sl.shiftID]
		duration := s.DurationHours(shift.Start, shift.End)

		var candidates []*models.Volunteer
		for _, vol := range s.Volunteers {
			if vol.Group == sl.group &&
				vol.AssignedHours+duration <= vol.MaxHours &&
				!s.WouldOverlap(vol, shift) &&
				s.Allows(shift, vol) {
				candidates = append(candidates, vol)
			}
		}

		if len(candidates) > 0 {
			// Pick one with least hours to balance load
			best := candidates[0]
			for _, cand := range candidates {
				if cand.AssignedHours < best.AssignedHours {
					best = cand
				}
			}
			
			shift.Assigned = append(shift.Assigned, best.ID)
			best.AssignedHours += duration
			best.AssignedShifts = append(best.AssignedShifts, shift.ID)
		}
	}
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

	for time.Since(start) < timeout {
		// Reset
		for _, v := range s.Volunteers {
			v.AssignedHours = originalVols[v.ID]
			v.AssignedShifts = nil // We'd need to properly reset prefills here if we wanted perfection
		}
		for _, sh := range s.Shifts {
			sh.Assigned = nil
		}
		
		s.AssignSimple(true)
		
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
