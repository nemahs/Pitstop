# syntax=docker/dockerfile:1.7-labs
FROM python AS builder


RUN apt update && apt install -y nodejs npm 
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY . .
ENV FLASK_DEBUG=0
RUN uv sync --no-cache-dir && uv run flask vite install
RUN uv run flask vite build


FROM python:slim as production
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
EXPOSE 80/tcp

COPY --exclude=**/vite . /app
WORKDIR /app
RUN uv sync --no-cache-dir
COPY --from=builder /app/vite/dist /app/vite/dist

WORKDIR /app
CMD [ "uv", "run", "flask", "run", "--port", "80", "--host", "0.0.0.0"]