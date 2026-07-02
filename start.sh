#!/bin/bash
set -e

# Backend stays internal (127.0.0.1); Spaces only exposes the frontend's port.
uvicorn backend.main:app --host 127.0.0.1 --port 8000 &

exec streamlit run frontend/app.py \
    --server.port 7860 \
    --server.address 0.0.0.0 \
    --server.headless true
