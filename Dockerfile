# Currently supported Python runtime (3.9 is end-of-life).
FROM python:3.12-slim

# Don't buffer stdout/stderr; no .pyc files.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/instance /app/uploads \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Basic liveness check against the catalogue page.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/').status==200 else 1)"

# The entrypoint applies migrations once, then starts Gunicorn. Debug mode is
# never enabled here.
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--access-logfile", "-", "app:app"]
