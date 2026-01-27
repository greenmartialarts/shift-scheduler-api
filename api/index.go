package handler

import (
	"net/http"

	"github.com/arnavshah/scheduler-api-go/pkg/auth"
	"github.com/arnavshah/scheduler-api-go/pkg/database"
	"github.com/arnavshah/scheduler-api-go/pkg/handlers"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

var r *gin.Engine

func init() {
	// Load .env if it exists (for local testing with vercel dev)
	_ = godotenv.Load(".env")
	_ = godotenv.Load("../.env")

	// Initialize DB
	db := database.InitDB()
	_ = auth.EnsureAdminExists(db)
	h := &handlers.Handler{DB: db}

	// Initialize Gin
	gin.SetMode(gin.ReleaseMode)
	r = gin.New()
	r.Use(gin.Logger(), gin.Recovery())

	// Static files served from embedded FS
	r.StaticFS("/static", h.GetStaticFS())

	// Routes
	r.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"message": "Shift Scheduler API (Go Version on Vercel)",
			"version": "2.2.0",
		})
	})

	r.GET("/admin", h.AdminInterface)
	r.POST("/admin/login", h.Login)

	admin := r.Group("/admin")
	admin.Use(h.AuthMiddleware())
	{
		admin.POST("/keys", h.GenerateKey)
		admin.GET("/keys", h.ListKeys)
		admin.PUT("/keys/:id", h.UpdateKeyLimit)
		admin.DELETE("/keys/:id", h.RevokeKey)
		admin.GET("/usage/:id", h.GetUsage)
	}

	api := r.Group("/api")
	api.Use(h.APIKeyMiddleware())
	{
		api.POST("/schedule", h.ScheduleJSON)
		api.POST("/schedule/csv", h.ScheduleCSV)
	}

	// Python Parity Routes
	r.POST("/schedule/json", h.APIKeyMiddleware(), h.ScheduleJSON)
	r.POST("/schedule/csv", h.APIKeyMiddleware(), h.ScheduleCSV)
}

// Handler is the entry point for Vercel Go Runtime
func Handler(w http.ResponseWriter, r_req *http.Request) {
	r.ServeHTTP(w, r_req)
}
