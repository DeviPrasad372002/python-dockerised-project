FROM python:3.13-slim

# Set the working directory.
WORKDIR /app

# Copy everything into the container
COPY . .

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["python", "myapp.py"]
