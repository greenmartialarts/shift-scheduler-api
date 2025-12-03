#!/bin/sh
# Start the uvicorn server with PORT from environment variable
exec uvicorn api_scheduler:app --host 0.0.0.0 --port ${PORT:-8000}
