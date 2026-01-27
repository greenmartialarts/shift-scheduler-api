package main

import (
	"log"
	"net/http"
	"os"

	"github.com/arnavshah/scheduler-api-go/pkg/auth"
	"github.com/arnavshah/scheduler-api-go/pkg/database"
	"github.com/arnavshah/scheduler-api-go/pkg/handlers"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// Load .env if it exists
	// Try root and parent directories for flexibility
	envPaths := []string{".env", "../.env", "../../.env"}
	for _, p := range envPaths {
		if _, err := os.Stat(p); err == nil {
			_ = godotenv.Load(p)
			break
		}
	}

	if os.Getenv("GIN_MODE") == "" {
		gin.SetMode(gin.ReleaseMode)
	}

	db := database.InitDB()
	_ = auth.EnsureAdminExists(db)
	h := &handlers.Handler{DB: db}

	r := gin.Default()

	// Admin interface - serve static files from embedded FS
	r.StaticFS("/static", h.GetStaticFS())

	// Routes
	r.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"message": "Shift Scheduler API (Go Version)",
			"version": "2.1.0",
		})
	})

	r.GET("/admin", h.AdminInterface)
	r.POST("/admin/login", h.Login)

	// Admin Endpoints
	admin := r.Group("/admin")
	admin.Use(h.AuthMiddleware())
	{
		admin.POST("/keys", h.GenerateKey)
		admin.GET("/keys", h.ListKeys)
		admin.PUT("/keys/:id", h.UpdateKeyLimit)
		admin.DELETE("/keys/:id", h.RevokeKey)
		admin.GET("/usage/:id", h.GetUsage)
	}

	// Scheduler Endpoints
	api := r.Group("/api")
	api.Use(h.APIKeyMiddleware())
	{
		api.POST("/schedule", h.ScheduleJSON)
		api.POST("/schedule/csv", h.ScheduleCSV)
		api.POST("/validate", h.ValidateInput)
		api.GET("/usage", h.GetMyUsage)
	}

	// Python Parity Routes
	r.POST("/schedule/json", h.APIKeyMiddleware(), h.ScheduleJSON)
	r.POST("/schedule/csv", h.APIKeyMiddleware(), h.ScheduleCSV)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	log.Printf("Server starting on port %s", port)
	if err := r.Run(":" + port); err != nil {
		log.Fatalf("could not run server: %v", err)
	}
}
