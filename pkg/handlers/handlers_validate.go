package handlers

import (
	"net/http"

	"github.com/arnavshah/scheduler-api-go/pkg/models"
	"github.com/gin-gonic/gin"
)

// ValidateInput handles the JSON-based validation request
func (h *Handler) ValidateInput(c *gin.Context) {
	var input models.ScheduleInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"valid": false,
			"error": err.Error(),
		})
		return
	}

	// Basic validation of data structures
	if len(input.Volunteers) == 0 {
		c.JSON(http.StatusOK, gin.H{
			"valid": false,
			"error": "At least one volunteer is required",
		})
		return
	}

	if len(input.UnassignedShifts) == 0 {
		c.JSON(http.StatusOK, gin.H{
			"valid": false,
			"error": "At least one unassigned shift is required",
		})
		return
	}

	// Check for duplicate IDs
	volIDs := make(map[string]bool)
	for _, v := range input.Volunteers {
		if volIDs[v.ID] {
			c.JSON(http.StatusOK, gin.H{"valid": false, "error": "Duplicate volunteer ID: " + v.ID})
			return
		}
		volIDs[v.ID] = true
	}

	shiftIDs := make(map[string]bool)
	for _, s := range input.UnassignedShifts {
		if shiftIDs[s.ID] {
			c.JSON(http.StatusOK, gin.H{"valid": false, "error": "Duplicate shift ID: " + s.ID})
			return
		}
		shiftIDs[s.ID] = true
	}

	c.JSON(http.StatusOK, gin.H{
		"valid": true,
		"stats": gin.H{
			"volunteer_count": len(input.Volunteers),
			"shift_count":     len(input.UnassignedShifts),
		},
	})
}
