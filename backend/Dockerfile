FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        docker-cli \
        curl \
        ca-certificates \
    && docker --version \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock.txt /app/requirements.lock.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install \
        --no-cache-dir \
        -r /app/requirements.lock.txt

COPY app /app/app

RUN mkdir -p /app/data

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]