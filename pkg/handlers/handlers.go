package handlers

import (
	"embed"
	"encoding/csv"
	"fmt"
	"io"
	"io/fs"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/arnavshah/scheduler-api-go/pkg/auth"
	"github.com/arnavshah/scheduler-api-go/pkg/database"
	"github.com/arnavshah/scheduler-api-go/pkg/models"
	"github.com/arnavshah/scheduler-api-go/pkg/scheduler"
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

//go:embed static/*
var staticEmbed embed.FS

// Handler contains dependencies for the route handlers
type Handler struct {
	DB *gorm.DB
}

// AuthMiddleware verifies the JWT token for admin routes
func (h *Handler) AuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		token := c.GetHeader("Authorization")
		if token == "" {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Authorization header required"})
			c.Abort()
			return
		}

		// Strip "Bearer " if present
		if len(token) > 7 && token[:7] == "Bearer " {
			token = token[7:]
		}

		claims, err := auth.VerifyToken(token)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid token"})
			c.Abort()
			return
		}

		c.Set("username", claims.Username)
		c.Next()
	}
}

// APIKeyMiddleware verifies the API key for scheduler routes using HMAC
func (h *Handler) APIKeyMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		key := c.GetHeader("Authorization")
		if key == "" {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "API Key required"})
			c.Abort()
			return
		}

		if len(key) > 7 && key[:7] == "Bearer " {
			key = key[7:]
		}

		userID, err := auth.VerifyHMACKey(key)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid API Key signature"})
			c.Abort()
			return
		}

		// Fetch or create API key record to track usage
		var apiKey database.APIKey
		h.DB.Where(database.APIKey{Key: key}).FirstOrCreate(&apiKey, database.APIKey{
			Key:       key,
			Name:      userID,
			RateLimit: 10000,
		})

		c.Set("apiKey", &apiKey)
		c.Set("userID", userID)
		c.Next()
	}
}

// ScheduleJSON handles the JSON-based scheduling request
func (h *Handler) ScheduleJSON(c *gin.Context) {
	var input models.ScheduleInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	volMap := make(map[string]*models.Volunteer)
	for i := range input.Volunteers {
		volMap[input.Volunteers[i].ID] = &input.Volunteers[i]
	}

	shiftMap := make(map[string]*models.Shift)
	for i := range input.UnassignedShifts {
		shiftMap[input.UnassignedShifts[i].ID] = &input.UnassignedShifts[i]
	}

	s := scheduler.NewScheduler(volMap, shiftMap)
	s.Prefill(input.CurrentAssignments)
	s.AssignSimple(true)

	// Record usage
	h.RecordUsage(c, len(shiftMap), len(volMap))

	// Format response for parity with Python version
	assignedShifts := make(map[string][]string)
	unfilledShifts := make(map[string]bool)
	for id, sh := range shiftMap {
		assignedShifts[id] = sh.Assigned

		// Determine which shifts have unfilled slots
		totalNeeded := 0
		for _, count := range sh.RequiredGroups {
			totalNeeded += count
		}
		if len(sh.Assigned) < totalNeeded {
			unfilledShifts[id] = true
		}
	}

	unfilledList := make([]string, 0, len(unfilledShifts))
	for id := range unfilledShifts {
		unfilledList = append(unfilledList, id)
	}

	volStats := make(map[string]any)
	for id, v := range volMap {
		volStats[id] = gin.H{
			"assigned_hours":  v.AssignedHours,
			"assigned_shifts": v.AssignedShifts,
		}
	}

	c.JSON(http.StatusOK, models.ScheduleResponse{
		AssignedShifts: assignedShifts,
		UnfilledShifts: unfilledList,
		Conflicts:      s.Conflicts,
		FairnessScore:  s.CalculateFairnessScore(),
		Volunteers:     volStats,
	})
}

// RecordUsage records API usage in the database using an efficient upsert
func (h *Handler) RecordUsage(c *gin.Context, shiftCount, volunteerCount int) {
	apiKeyRaw, exists := c.Get("apiKey")
	if !exists {
		return
	}
	apiKey := apiKeyRaw.(*database.APIKey)

	today := time.Now().Format("2006-01-02")

	// Use OnConflict for a single-query upsert (supported by both Postgres and SQLite)
	h.DB.Clauses(clause.OnConflict{
		Columns: []clause.Column{{Name: "key_id"}, {Name: "date"}},
		DoUpdates: clause.Assignments(map[string]interface{}{
			"request_count":    gorm.Expr("request_count + ?", 1),
			"total_shifts":     gorm.Expr("total_shifts + ?", shiftCount),
			"total_volunteers": gorm.Expr("total_volunteers + ?", volunteerCount),
		}),
	}).Create(&database.APIUsage{
		KeyID:           apiKey.ID,
		Date:            today,
		RequestCount:    1,
		TotalShifts:     shiftCount,
		TotalVolunteers: volunteerCount,
	})
}

// ScheduleCSV handles CSV file uploads for scheduling
func (h *Handler) ScheduleCSV(c *gin.Context) {
	// 1. Get files
	volsFile, _ := c.FormFile("volunteers_file")
	shiftsFile, _ := c.FormFile("shifts_file")
	assignmentsFile, _ := c.FormFile("assignments_file")

	if volsFile == nil || shiftsFile == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "volunteers_file and shifts_file are required"})
		return
	}

	// Parse volunteers
	vFile, err := volsFile.Open()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to open volunteers file"})
		return
	}
	defer vFile.Close()
	vReader := csv.NewReader(vFile)
	vHeader, err := vReader.Read()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Failed to read volunteers header"})
		return
	}
	vCols := make(map[string]int)
	for i, h := range vHeader {
		vCols[h] = i
	}

	volMap := make(map[string]*models.Volunteer)
	for {
		record, err := vReader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		id := record[vCols["id"]]
		maxHours, _ := strconv.ParseFloat(record[vCols["max_hours"]], 64)
		volMap[id] = &models.Volunteer{
			ID:       id,
			Name:     record[vCols["name"]],
			Group:    record[vCols["group"]],
			MaxHours: maxHours,
		}
	}

	// Parse shifts
	sFile, err := shiftsFile.Open()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to open shifts file"})
		return
	}
	defer sFile.Close()
	sReader := csv.NewReader(sFile)
	sHeader, err := sReader.Read()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Failed to read shifts header"})
		return
	}
	sCols := make(map[string]int)
	for i, h := range sHeader {
		sCols[h] = i
	}

	shiftMap := make(map[string]*models.Shift)
	for {
		record, err := sReader.Read()
		if err == io.EOF {
			break
		}
		id := record[sCols["id"]]
		start, _ := time.Parse("2006-01-02T15:04:05Z", record[sCols["start"]])
		if start.IsZero() {
			start, _ = time.Parse("2006-01-02T15:04", record[sCols["start"]])
		}
		end, _ := time.Parse("2006-01-02T15:04:05Z", record[sCols["end"]])
		if end.IsZero() {
			end, _ = time.Parse("2006-01-02T15:04", record[sCols["end"]])
		}

		reqGroups := make(map[string]int)
		for _, part := range strings.Split(record[sCols["required_groups"]], "|") {
			if strings.Contains(part, ":") {
				gp := strings.Split(part, ":")
				count, _ := strconv.Atoi(strings.TrimSpace(gp[1]))
				reqGroups[strings.TrimSpace(gp[0])] = count
			}
		}

		var allowed, excluded []string
		if val, ok := sCols["allowed_groups"]; ok && record[val] != "" {
			allowed = strings.Split(record[val], "|")
		}
		if val, ok := sCols["excluded_groups"]; ok && record[val] != "" {
			excluded = strings.Split(record[val], "|")
		}

		shiftMap[id] = &models.Shift{
			ID:             id,
			Start:          start,
			End:            end,
			RequiredGroups: reqGroups,
			AllowedGroups:  allowed,
			ExcludedGroups: excluded,
		}
	}

	s := scheduler.NewScheduler(volMap, shiftMap)

	// Prefill if assignments provided
	if assignmentsFile != nil {
		aFile, _ := assignmentsFile.Open()
		defer aFile.Close()
		aReader := csv.NewReader(aFile)
		aHeader, _ := aReader.Read()
		aCols := make(map[string]int)
		for i, h := range aHeader {
			aCols[h] = i
		}
		var asgns []models.Assignment
		for {
			record, err := aReader.Read()
			if err == io.EOF {
				break
			}
			asgns = append(asgns, models.Assignment{
				ShiftID:     record[aCols["shift_id"]],
				VolunteerID: record[aCols["volunteer_id"]],
			})
		}
		s.Prefill(asgns)
	}

	s.AssignSimple(true)

	// Record usage
	assignedVols := 0
	assignedShifts := 0
	for _, sh := range shiftMap {
		if len(sh.Assigned) > 0 {
			assignedShifts++
			assignedVols += len(sh.Assigned)
		}
	}
	h.RecordUsage(c, assignedShifts, assignedVols)

	// Export CSV
	var outCSV strings.Builder
	writer := csv.NewWriter(&outCSV)
	writer.Write([]string{"shift_id", "volunteer_id", "volunteer_name", "start", "end", "duration_hours"})

	for _, sh := range shiftMap {
		for _, vid := range sh.Assigned {
			v := volMap[vid]
			duration := sh.End.Sub(sh.Start).Hours()
			writer.Write([]string{
				sh.ID,
				v.ID,
				v.Name,
				sh.Start.Format(time.RFC3339),
				sh.End.Format(time.RFC3339),
				fmt.Sprintf("%.2f", duration),
			})
		}
	}
	writer.Flush()

	c.JSON(http.StatusOK, gin.H{"csv": outCSV.String()})
}

// Login handles admin login
func (h *Handler) Login(c *gin.Context) {
	var req struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var user database.MasterUser
	if err := h.DB.Where("username = ?", req.Username).First(&user).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid credentials"})
		return
	}

	if !auth.CheckPasswordHash(req.Password, user.PasswordHash) {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid credentials"})
		return
	}

	token, err := auth.CreateToken(user.Username)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not create token"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"access_token": token, "token_type": "bearer"})
}

// GenerateKey creates a new API key using the HMAC strategy
func (h *Handler) GenerateKey(c *gin.Context) {
	var req struct {
		Name      string `json:"name"`
		RateLimit int    `json:"rate_limit"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Name == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "name is required"})
		return
	}

	if req.RateLimit == 0 {
		req.RateLimit = 10000
	}

	// Generate key using HMAC
	key := auth.GenerateHMACKey(req.Name)

	// Create preview (e.g., sk_...****)
	preview := ""
	if len(key) > 8 {
		preview = key[:3] + "..." + key[len(key)-4:]
	} else {
		preview = "****"
	}

	apiKey := database.APIKey{
		Key:        key,
		Name:       req.Name,
		KeyPreview: preview,
		RateLimit:  req.RateLimit,
	}

	if err := h.DB.Create(&apiKey).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not create key record"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"name": req.Name,
		"key":  key,
	})
}

// ListKeys returns all API keys
func (h *Handler) ListKeys(c *gin.Context) {
	var keys []database.APIKey
	h.DB.Find(&keys)
	c.JSON(http.StatusOK, gin.H{"keys": keys})
}

// RevokeKey deletes an API key
func (h *Handler) RevokeKey(c *gin.Context) {
	id := c.Param("id")
	if err := h.DB.Delete(&database.APIKey{}, id).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not delete key"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Key revoked"})
}

// UpdateKeyLimit updates the rate limit for a key
func (h *Handler) UpdateKeyLimit(c *gin.Context) {
	id := c.Param("id")
	var req struct {
		RateLimit int `json:"rate_limit" form:"rate_limit"`
	}

	// Try JSON first, then Form/Query
	if err := c.ShouldBindJSON(&req); err != nil {
		if err := c.ShouldBindQuery(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "rate_limit is required"})
			return
		}
	}

	if req.RateLimit == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid rate limit"})
		return
	}

	if err := h.DB.Model(&database.APIKey{}).Where("id = ?", id).Update("rate_limit", req.RateLimit).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not update key limit"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Rate limit updated successfully"})
}

// GetUsage returns usage stats for a key
func (h *Handler) GetUsage(c *gin.Context) {
	id := c.Param("id")
	var usage []database.APIUsage
	h.DB.Where("key_id = ?", id).Order("date desc").Limit(30).Find(&usage)
	c.JSON(http.StatusOK, gin.H{"usage": usage})
}

// AdminInterface serves the admin web interface from embedded files
func (h *Handler) AdminInterface(c *gin.Context) {
	_ = auth.EnsureAdminExists(h.DB)

	data, err := staticEmbed.ReadFile("static/index.html")
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "static/index.html not found in embedded FS"})
		return
	}

	c.Data(http.StatusOK, "text/html; charset=utf-8", data)
}

// GetStaticFS returns the embedded filesystem for static assets
func (h *Handler) GetStaticFS() http.FileSystem {
	sub, err := fs.Sub(staticEmbed, "static")
	if err != nil {
		panic(err)
	}
	return http.FS(sub)
}
