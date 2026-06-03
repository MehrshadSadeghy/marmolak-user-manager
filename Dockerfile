FROM python:3.12-slim-bookworm

WORKDIR /app

COPY pyproject.toml .
COPY backend ./backend

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/backend/src
ENV PYTHONUNBUFFERED=1
ENV RAYA_TRADE_ENVIRONMENT=docker

EXPOSE 8080

CMD ["python", "-m", "vpn_core"]
