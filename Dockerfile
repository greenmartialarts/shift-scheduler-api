FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Copy and make start script executable
COPY start.sh .
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Run the start script
CMD ["./start.sh"]
