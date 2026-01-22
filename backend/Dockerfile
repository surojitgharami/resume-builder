FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Install system dependencies for OCR (pytesseract) and PDF conversion (pdf2image)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# chromium is usually included in the base image, but installing it explicitly 
# ensures it's available and registered for the playwright python package.
RUN playwright install chromium

COPY . .

EXPOSE 8000

# Use shell form to allow variable expansion for PORT (Render sets this)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
