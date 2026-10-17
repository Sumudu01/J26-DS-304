FROM python:3.10-slim

WORKDIR /app

# Install the Tesseract executable used by TopJobs advert OCR.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Hugging Face Spaces exposes port 7860 by default
EXPOSE 7860

# Set environment variables for the app to listen on the correct host and port
ENV HOST=0.0.0.0
ENV PORT=7860
ENV ENVIRONMENT=production

# Command to run the application
CMD ["python", "run.py"]
