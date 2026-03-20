# pdf-exam-parser - FastAPI app for parsing exam questions from any file type
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for OCR (tesseract) and image processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .
COPY parsers/ parsers/

# Expose FastAPI default port
EXPOSE 8000

# Run with uvicorn (host 0.0.0.0 for container access)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
