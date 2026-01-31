#!/bin/bash
# Script to correctly start the backend server
cd backend
echo "Starting backend server on port 8000..."
uvicorn app.main:app --reload --port 8000
