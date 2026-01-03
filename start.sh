#!/bin/bash
# Run server setup (creates admin if needed)
python server_setup.py

# Start the server
uvicorn api_scheduler:app --host 0.0.0.0 --port ${PORT:-8000}
