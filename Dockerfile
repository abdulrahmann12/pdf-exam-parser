# pdf-exam-parser - FastAPI app for parsing PDF/CSV exam questions
FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Expose FastAPI default port
EXPOSE 8000

# Run with uvicorn (host 0.0.0.0 for container access)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
