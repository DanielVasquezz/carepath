# Dockerfile
# ===========
# CarePath API — Container definition
#
# This file describes how to build a Docker image
# for the CarePath FastAPI server.
#
# Build stages:
#   FROM    → start from an official Python image
#   WORKDIR → set the working directory inside the container
#   COPY    → copy files into the container
#   RUN     → execute commands during build
#   CMD     → what to run when the container starts

FROM python:3.12-slim
# python:3.12-slim = Python 3.12 on Debian Linux, minimal installation
# 'slim' means no unnecessary packages — smaller image, faster builds
# Smaller images = faster deployments to AWS

WORKDIR /app
# All subsequent commands run from /app inside the container
# When you COPY files, they go to /app
# When the server starts, it starts from /app

COPY requirements.txt .
# Copy requirements BEFORE the rest of the code
# Why? Docker caches layers. If requirements.txt hasn't changed,
# Docker skips the pip install step and uses the cached layer.
# This makes rebuilds after code changes very fast.

RUN pip install --no-cache-dir -r requirements.txt
# Install all Python dependencies
# --no-cache-dir = don't cache the pip download cache
# Saves disk space in the image

COPY . .
# Copy the rest of the code
# This is done AFTER pip install so code changes don't
# invalidate the pip cache layer

EXPOSE 8000
# Documents that this container listens on port 8000
# Doesn't actually open the port — that's done in docker-compose.yml

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# What runs when the container starts
# --host 0.0.0.0 = accept connections from outside the container
# Without this, uvicorn only accepts connections from inside
# the container itself — you couldn't reach it from your browser