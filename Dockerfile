FROM python:3.15.0-alpine@sha256:2699b90f4d562a22e2dd076c82f964032f64814204bff36d271a54ba4cc2c7e2

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
