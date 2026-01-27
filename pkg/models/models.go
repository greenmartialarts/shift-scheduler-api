package models

import "time"

// Volunteer represents a person available for shifts
type Volunteer struct {
	ID            string  `json:"id"`
	Name          string  `json:"name"`
	Group         string  `json:"group,omitempty"`
	MaxHours      float64 `json:"max_hours"`
	AssignedHours float64 `json:"assigned_hours"`
	AssignedShifts []string `json:"assigned_shifts"`
}

// Shift represents a time slot that needs filling
type Shift struct {
	ID             string         `json:"id"`
	Start          time.Time      `json:"start"`
	End            time.Time      `json:"end"`
	RequiredGroups map[string]int `json:"required_groups"`
	AllowedGroups  []string       `json:"allowed_groups,omitempty"`
	ExcludedGroups []string       `json:"excluded_groups,omitempty"`
	Assigned       []string       `json:"assigned"`
}

// Assignment represents a volunteer-shift pairing
type Assignment struct {
	ShiftID     string `json:"shift_id"`
	VolunteerID string `json:"volunteer_id"`
}

// ConflictReason represents why a shift could not be filled
type ConflictReason struct {
	ShiftID string   `json:"shift_id"`
	Group   string   `json:"group"`
	Reasons []string `json:"reasons"`
}

// ScheduleResponse is the data structure for the scheduling result
type ScheduleResponse struct {
	AssignedShifts map[string][]string `json:"assigned_shifts"`
	UnfilledShifts []string            `json:"unfilled_shifts"` // shift IDs that have ANY unfilled slots
	Conflicts      []ConflictReason    `json:"conflicts,omitempty"`
	FairnessScore  float64             `json:"fairness_score"`
	Volunteers     map[string]any       `json:"volunteers"` // ID -> {assigned_hours, assigned_shifts}
}

// ScheduleInput is the data structure for the scheduling endpoint
type ScheduleInput struct {
	Volunteers         []Volunteer  `json:"volunteers"`
	UnassignedShifts   []Shift      `json:"unassigned_shifts"`
	CurrentAssignments []Assignment `json:"current_assignments"`
}
