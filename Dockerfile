FROM python:3.10
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
COPY static /app/static
COPY webhook.py /app/webhook.py
RUN pip install --no-cache-dir -r /app/requirements.txt

# Add the application source code into the Docker image


# Start application
CMD ["python", "webhook.py"]

