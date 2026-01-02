FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Expose port (Railway will override with $PORT env var)
EXPOSE 8080

# Run the setup and start the application
CMD ["./start.sh"]
