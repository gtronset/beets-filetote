FROM python:3.11.0-alpine

WORKDIR /src

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /src
