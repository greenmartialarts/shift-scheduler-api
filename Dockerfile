FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port (Railway will set PORT env var)
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api_scheduler:app", "--host", "0.0.0.0", "--port", "8000"]
