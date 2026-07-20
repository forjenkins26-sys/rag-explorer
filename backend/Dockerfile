FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# HF Spaces run containers as a non-root user; give that user a writable
# home so huggingface_hub can cache the embedding model, and writable data
# dirs for the watched-folder + persistent Chroma store.
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/data/pdf /app/chroma_db \
    && chown -R appuser:appuser /app
ENV HOME=/home/appuser
USER appuser

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
