FROM python:3.11.0-alpine

RUN apk update && apk add python3-dev \
    gcc \
    gdal \
    libc-dev \
    libffi-dev

WORKDIR /src

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /src
