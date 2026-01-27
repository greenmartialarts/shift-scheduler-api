package handlers

import (
	"net/http"

	"github.com/arnavshah/scheduler-api-go/pkg/database"
	"github.com/gin-gonic/gin"
)

// GetMyUsage returns usage stats for the authenticated API key
func (h *Handler) GetMyUsage(c *gin.Context) {
	apiKeyRaw, exists := c.Get("apiKey")
	if !exists {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "API Key context missing"})
		return
	}
	apiKey := apiKeyRaw.(*database.APIKey)

	var usage []database.APIUsage
	if err := h.DB.Where("key_id = ?", apiKey.ID).Order("date desc").Limit(30).Find(&usage).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not fetch usage details"})
		return
	}

	// Calculate totals
	var totalRequests, totalShifts, totalVolunteers int64
	for _, u := range usage {
		totalRequests += int64(u.RequestCount)
		totalShifts += int64(u.TotalShifts)
		totalVolunteers += int64(u.TotalVolunteers)
	}

	c.JSON(http.StatusOK, gin.H{
		"key_name":      apiKey.Name,
		"rate_limit":    apiKey.RateLimit,
		"usage_history": usage,
		"totals": gin.H{
			"requests":   totalRequests,
			"shifts":     totalShifts,
			"volunteers": totalVolunteers,
		},
	})
}
