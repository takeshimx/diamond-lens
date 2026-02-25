FROM python:3.9-slim

WORKDIR /app

# layer caching for faster builds
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./backend

ENV PYTHONPATH=/app

# Create a non-root user for security
RUN adduser --disabled-password appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

USER appuser

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]