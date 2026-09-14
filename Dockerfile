FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODELNEST_STORAGE_DIR=/data/artifacts

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 modelnest \
    && mkdir -p /data/artifacts \
    && chown -R modelnest:modelnest /data

USER modelnest
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
