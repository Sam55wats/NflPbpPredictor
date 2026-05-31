FROM node:20-bookworm-slim AS frontend

WORKDIR /app/nflpredictor

COPY nflpredictor/package*.json ./
RUN npm ci

COPY nflpredictor/.babelrc ./
COPY nflpredictor/webpack.config.js ./
COPY nflpredictor/assets ./assets
RUN npm run build

FROM python:3.11-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBUG=False \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-render.txt ./
RUN pip install --no-cache-dir -r requirements-render.txt

COPY nflpredictor ./nflpredictor
COPY --from=frontend /app/nflpredictor/static ./nflpredictor/static

WORKDIR /app/nflpredictor
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python -m gunicorn nflpredictor.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}"]
