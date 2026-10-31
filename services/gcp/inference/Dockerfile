FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# git is only needed for the CLIP package that YOLO-World depends on.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libglib2.0-0 \
    libgl1 \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libsm6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && pip install "git+https://github.com/ultralytics/CLIP.git"

COPY app ./app
COPY config ./config

# Cloud Run supplies $PORT.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
