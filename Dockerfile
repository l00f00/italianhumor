# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install system dependencies (fonts)
RUN apt-get update && apt-get install -y \
    fonts-dejavu \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000 for Flask API
EXPOSE 5000

# Define environment variable
ENV PYTHONUNBUFFERED=1

# Run app.py when the container launches
CMD ["python", "main.py"]
