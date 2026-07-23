FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Expose port for webhook
EXPOSE 10000

# Health check — bot process should be alive
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
  CMD python -c "import os; exit(0 if os.path.exists('/proc/1') else 1)"

# Run bot
CMD ["python", "bot.py"]
