FROM python:3.10-alpine

WORKDIR /src

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /src