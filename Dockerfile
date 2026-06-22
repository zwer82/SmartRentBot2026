FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create photos directory (for uploaded images)
RUN mkdir -p photos

# Expose port for webhook
EXPOSE 8080

CMD ["python", "main.py"]
