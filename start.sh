#!/bin/bash
set -e

# Backend stays internal (127.0.0.1); Spaces only exposes the frontend's port.
uvicorn backend.main:app --host 127.0.0.1 --port 8000 &

# Backend import chain pulls in chromadb/sentence-transformers/torch, which is
# much slower than Streamlit's startup - wait for it so the frontend doesn't
# come up and accept requests before the backend is actually listening.
echo "Waiting for backend..."
for i in $(seq 1 60); do
    if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" 2>/dev/null; then
        echo "Backend ready."
        break
    fi
    sleep 1
done

exec streamlit run frontend/app.py \
    --server.port 7860 \
    --server.address 0.0.0.0 \
    --server.headless true
