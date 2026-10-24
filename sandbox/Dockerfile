FROM python:3.11-slim
RUN pip install --no-cache-dir pytest
RUN useradd -m runner
USER runner
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1