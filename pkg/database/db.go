package database

import (
	"log"
	"os"
	"time"

	"gorm.io/driver/postgres"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// APIKey represents the api_keys table
type APIKey struct {
	ID        uint           `gorm:"primaryKey" json:"id"`
	Key       string         `gorm:"unique;not null" json:"key"`
	Name      string         `gorm:"not null" json:"name"`
	RateLimit int            `gorm:"default:10000" json:"rate_limit"`
	CreatedAt time.Time      `json:"created_at"`
	LastUsed  *time.Time     `json:"last_used"`
}

// APIUsage represents the api_usage table
type APIUsage struct {
	ID              uint   `gorm:"primaryKey" json:"id"`
	KeyID           uint   `gorm:"uniqueIndex:idx_key_date;not null" json:"key_id"`
	Date            string `gorm:"uniqueIndex:idx_key_date;not null" json:"date"`
	RequestCount    int    `gorm:"default:0" json:"request_count"`
	TotalShifts     int    `gorm:"default:0" json:"total_shifts"`
	TotalVolunteers int    `gorm:"default:0" json:"total_volunteers"`
}

// MasterUser represents the master_users table
type MasterUser struct {
	ID           uint      `gorm:"primaryKey" json:"id"`
	Username     string    `gorm:"unique;not null" json:"username"`
	PasswordHash string    `gorm:"not null" json:"password_hash"`
	CreatedAt    time.Time `json:"created_at"`
}

// InitDB initializes the database connection and migrates the schema
func InitDB() *gorm.DB {
	var db *gorm.DB
	var err error

	dsn := os.Getenv("DATABASE_URL")
	if dsn != "" {
		db, err = gorm.Open(postgres.New(postgres.Config{
			DSN:                  dsn,
			PreferSimpleProtocol: true,
		}), &gorm.Config{
			PrepareStmt: false,
		})
	} else {
		dbPath := os.Getenv("DATA_PATH")
		if dbPath == "" {
			dbPath = "api_keys.db"
		}
		db, err = gorm.Open(sqlite.Open(dbPath), &gorm.Config{})
	}

	if err != nil {
		log.Fatalf("failed to connect database: %v", err)
	}

	// Auto Migration
	db.AutoMigrate(&APIKey{}, &APIUsage{}, &MasterUser{})

	return db
}
