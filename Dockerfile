FROM python:3.14.5-alpine@sha256:5a824eb82cc75361f98611f3cfc5091ea33f10a6ccea4d4ebdabbc523b9a1614

# Add dependencies for the reflink python module
RUN apk update && apk add python3-dev \
    cargo \
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
    && pip install beets poetry prek tox \
    && poetry install
