FROM python:3.14-alpine

# Add dependencies for the reflink python module
RUN apk update && apk add python3-dev \
    cargo \
    ffmpeg \
    gcc \
    gdal \
    libc-dev \
    libffi-dev \
    && rm -rf /var/cache/apk/*

WORKDIR /src

RUN mkdir -p /beets/library && mkdir -p /beets/inbox

COPY . /src
COPY example.config.yaml /root/.config/beets/config.yaml

RUN pip install --upgrade pip \
    && pip install beets poetry pre-commit tox \
    && poetry install
