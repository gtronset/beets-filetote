FROM python:3.12-alpine

# Add dependencies for the reflink python module
RUN apk update && apk add python3-dev \
    cargo \
    gcc \
    gdal \
    libc-dev \
    libffi-dev

WORKDIR /src

COPY requirements.txt dev-requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt -r dev-requirements.txt

COPY . /src
