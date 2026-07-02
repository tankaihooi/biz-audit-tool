FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Build the Chroma index into the image - Spaces disk is non-persistent,
# and this doesn't need GEMINI_API_KEY (no LLM calls, just embeddings).
RUN python -m scripts.ingest

RUN chmod +x start.sh

ENV BACKEND_URL=http://127.0.0.1:8000
EXPOSE 7860

CMD ["./start.sh"]
