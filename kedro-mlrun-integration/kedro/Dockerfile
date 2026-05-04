# Use MLRun 1.10 base image
FROM mlrun/mlrun:1.10.0

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install additional Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
