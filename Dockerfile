FROM python:3.11.3-alpine

# Add dependencies for the reflink python module
RUN apk update && apk add python3-dev \
    gcc \
    gdal \
    libc-dev \
    libffi-dev

WORKDIR /src

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /src
