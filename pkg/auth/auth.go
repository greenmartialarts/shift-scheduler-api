package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"os"
	"strings"
	"time"

	"github.com/arnavshah/scheduler-api-go/pkg/database"
	"github.com/golang-jwt/jwt/v4"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

var jwtSecret = []byte(os.Getenv("JWT_SECRET"))
var jwtAlgorithm = jwt.SigningMethodHS256

// Claims represents the JWT claims
type Claims struct {
	Username string `json:"username"`
	jwt.RegisteredClaims
}

// HashPassword hashes a password using bcrypt
func HashPassword(password string) (string, error) {
	bytes, err := bcrypt.GenerateFromPassword([]byte(password), 14)
	return string(bytes), err
}

// CheckPasswordHash compares a password with its hash
func CheckPasswordHash(password, hash string) bool {
	err := bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
	return err == nil
}

// CreateToken creates a new JWT token for a user
func CreateToken(username string) (string, error) {
	expirationTime := time.Now().Add(24 * time.Hour)
	claims := &Claims{
		Username: username,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(expirationTime),
		},
	}

	token := jwt.NewWithClaims(jwtAlgorithm, claims)
	return token.SignedString(jwtSecret)
}

// VerifyToken verifies a JWT token
func VerifyToken(tokenString string) (*Claims, error) {
	claims := &Claims{}
	token, err := jwt.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (interface{}, error) {
		return jwtSecret, nil
	})

	if err != nil {
		return nil, err
	}

	if !token.Valid {
		return nil, errors.New("invalid token")
	}

	return claims, nil
}

// VerifyAPIKey checks if an API key is valid and records usage
func VerifyAPIKey(db *gorm.DB, key string) (*database.APIKey, error) {
	var apiKey database.APIKey
	if err := db.Where("key = ?", key).First(&apiKey).Error; err != nil {
		return nil, err
	}

	now := time.Now()
	apiKey.LastUsed = &now
	db.Save(&apiKey)

	return &apiKey, nil
}

// EnsureAdminExists checks if any admin exists, if not create one from environment variables.
func EnsureAdminExists(db *gorm.DB) error {
	var count int64
	db.Model(&database.MasterUser{}).Count(&count)

	if count == 0 {
		username := os.Getenv("ADMIN_USERNAME")
		if username == "" {
			username = "admin"
		}
		password := os.Getenv("ADMIN_PASSWORD")
		if password == "" {
			password = "admin123"
		}

		hash, err := HashPassword(password)
		if err != nil {
			return err
		}

		user := database.MasterUser{
			Username:     username,
			PasswordHash: hash,
		}

		err = db.Create(&user).Error
		if err == nil {
			println("Default admin user created: " + username)
		}
		return err
	}
	return nil
}

// GenerateHMACKey creates a signed API key using HMAC-SHA256
func GenerateHMACKey(userID string) string {
	secret := os.Getenv("API_MASTER_SECRET")
	h := hmac.New(sha256.New, []byte(secret))
	h.Write([]byte(userID))
	signature := hex.EncodeToString(h.Sum(nil))
	return userID + "." + signature
}

// VerifyHMACKey validates an HMAC-signed API key
func VerifyHMACKey(key string) (string, error) {
	parts := strings.Split(key, ".")
	if len(parts) != 2 {
		return "", errors.New("invalid key format")
	}

	userID := parts[0]
	providedSignature := parts[1]

	secret := os.Getenv("API_MASTER_SECRET")
	h := hmac.New(sha256.New, []byte(secret))
	h.Write([]byte(userID))
	expectedSignature := hex.EncodeToString(h.Sum(nil))

	// Use constant-time comparison to prevent timing attacks
	if !hmac.Equal([]byte(providedSignature), []byte(expectedSignature)) {
		return "", errors.New("invalid signature")
	}

	return userID, nil
}
