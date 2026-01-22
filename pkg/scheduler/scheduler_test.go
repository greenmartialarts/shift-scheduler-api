package scheduler

import (
	"testing"
	"time"

	"github.com/arnavshah/scheduler-api-go/pkg/models"
)

func TestAssignSimple(t *testing.T) {
	volunteers := map[string]*models.Volunteer{
		"v1": {ID: "v1", Name: "Alice", Group: "A", MaxHours: 10},
		"v2": {ID: "v2", Name: "Bob", Group: "A", MaxHours: 10},
	}

	start := time.Now()
	end := start.Add(2 * time.Hour)

	shifts := map[string]*models.Shift{
		"s1": {
			ID:             "s1",
			Start:          start,
			End:            end,
			RequiredGroups: map[string]int{"A": 1},
		},
	}

	s := NewScheduler(volunteers, shifts)
	s.AssignSimple(false)

	if len(shifts["s1"].Assigned) != 1 {
		t.Errorf("Expected 1 volunteer assigned to s1, got %d", len(shifts["s1"].Assigned))
	}

	assignedVolID := shifts["s1"].Assigned[0]
	if volunteers[assignedVolID].AssignedHours != 2.0 {
		t.Errorf("Expected assigned volunteer to have 2.0 hours, got %f", volunteers[assignedVolID].AssignedHours)
	}
}

func TestAssignSimple_Overlap(t *testing.T) {
	volunteers := map[string]*models.Volunteer{
		"v1": {ID: "v1", Name: "Alice", Group: "A", MaxHours: 10},
	}

	start1 := time.Now()
	end1 := start1.Add(2 * time.Hour)

	start2 := start1.Add(1 * time.Hour)
	end2 := start2.Add(2 * time.Hour)

	shifts := map[string]*models.Shift{
		"s1": {
			ID:             "s1",
			Start:          start1,
			End:            end1,
			RequiredGroups: map[string]int{"A": 1},
		},
		"s2": {
			ID:             "s2",
			Start:          start2,
			End:            end2,
			RequiredGroups: map[string]int{"A": 1},
		},
	}

	s := NewScheduler(volunteers, shifts)
	s.AssignSimple(false)

	assignedCount := 0
	for _, sh := range shifts {
		assignedCount += len(sh.Assigned)
	}

	if assignedCount != 1 {
		t.Errorf("Expected only 1 shift to be assigned due to overlap, got %d", assignedCount)
	}
}
