# /wealth-advisor/Dockerfile
# Use an official lightweight Python base image
FROM python:3.11-slim

# Set up a non-root user for security
RUN useradd --create-home appuser
WORKDIR /home/appuser/app
USER appuser

# Copy and install dependencies
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Expose the port the app runs on (used by Cloud Run)
EXPOSE 8080

# Run the application with Gunicorn
CMD ["gunicorn", "--workers", "1", "--threads", "8", "--timeout", "0", "main:app"]