# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the project definition file
COPY pyproject.toml .

# We copy the source code here because `pip install .` needs it to install the project.
COPY src ./src

# Install any needed packages specified in pyproject.toml
RUN pip install --no-cache-dir . uvicorn[standard] gunicorn

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Set environment variables for production
ENV PYTHONPATH=/app/src
ENV HOST=0.0.0.0
ENV PORT=8000

# Define required environment variables to ensure they're documented
ENV DATABASE_URL=""
ENV GOOGLE_CLIENT_ID=""
ENV GOOGLE_CLIENT_SECRET=""
# Optional environment variables
ENV GOOGLE_API_KEY=""
ENV AZURE_INFERENCE_CREDENTIAL=""
ENV AZURE_INFERENCE_ENDPOINT=""

# Run the FastAPI application with production server (gunicorn + uvicorn workers)
CMD ["gunicorn", "app.api.main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]