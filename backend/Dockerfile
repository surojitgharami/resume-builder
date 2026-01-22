FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and system dependencies
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8000

# Use shell form to allow variable expansion for PORT (Render sets this)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
