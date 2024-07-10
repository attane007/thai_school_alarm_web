# Dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y \
        libsdl1.2-dev \
        libsdl-image1.2-dev \
        libsdl-mixer1.2-dev \
        libsdl-ttf2.0-dev \
        libsmpeg-dev \
        libportmidi-dev \
        libavformat-dev \
        libswscale-dev \
        libjpeg-dev \
        libfreetype6-dev \
        libglib2.0-0

WORKDIR /app

COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY . /app/
