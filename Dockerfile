FROM python:3.11-slim

# Install system dependencies required by cairosvg and image libraries
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       pkg-config \
       libcairo2 \
       libcairo2-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
       libffi-dev \
       wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

# Create output dir
RUN mkdir -p /output

# Default command: generate sheet and keep container alive briefly
CMD ["python","generate_qr_sheet.py","--out-svg","/output/test_qr.svg","--out-pdf","/output/test_qr.pdf"]
