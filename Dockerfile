FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port (Railway will override with $PORT env var)
EXPOSE 8080
RUN python railway_setup.py

# Run the application with shell to expand environment variables
CMD ["sh", "-c", "uvicorn api_scheduler:app --host 0.0.0.0 --port ${PORT:-8080}"]
