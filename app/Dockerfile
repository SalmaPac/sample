FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt /app

# Install git, highlight, and certificates
RUN apt-get update && \
    apt-get install -y git highlight ca-certificates && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies ignoring SSL verification
RUN pip install --trusted-host pypi.org \
                --trusted-host files.pythonhosted.org \
                --trusted-host pypi.python.org \
                --no-cache-dir -r requirements.txt gunicorn

COPY . /app

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "greenCode:app", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "--workers", "1"]
