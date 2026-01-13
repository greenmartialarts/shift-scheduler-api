package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"

	"github.com/joho/godotenv"
)

func main() {
	// Load .env from project root
	_ = godotenv.Load("../.env")

	if len(os.Args) < 2 {
		fmt.Println("Usage: go run keygen.go <userID>")
		os.Exit(1)
	}

	userID := os.Args[1]
	secret := os.Getenv("API_MASTER_SECRET")
	if secret == "" {
		fmt.Println("Error: API_MASTER_SECRET not found in .env")
		os.Exit(1)
	}

	h := hmac.New(sha256.New, []byte(secret))
	h.Write([]byte(userID))
	signature := hex.EncodeToString(h.Sum(nil))
	
	apiKey := userID + "." + signature
	fmt.Printf("Generated Key for %s:\n%s\n", userID, apiKey)
}
