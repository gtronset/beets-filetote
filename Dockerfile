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

RUN mkdir -p /beets/library /beets/inbox

COPY . /src
COPY example.config.yaml /root/.config/beets/config.yaml

RUN python -m venv /opt/venv
ENV VIRTUAL_ENV="/opt/venv"
ENV PATH="/opt/venv/bin:${PATH}"

RUN pip install --upgrade pip \
    && pip install uv prek tox \
    && uv sync --active --frozen --group dev --group lint --group test
