# syntax=docker/dockerfile:1.7-labs
FROM python AS builder


RUN apt update && apt install -y nodejs npm 
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /contracting
COPY . .
ENV FLASK_DEBUG=0
RUN ls
RUN uv sync --no-dev && uv run flask vite install
RUN uv run flask vite build


FROM python:slim as production
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
EXPOSE 80/tcp

COPY --exclude=**/vite . /contracting
WORKDIR /contracting
RUN uv sync --no-dev && uv lock
COPY --from=builder /contracting/vite/dist /contracting/vite/dist

WORKDIR /contracting
CMD [ "uv", "run", "--no-sync", "flask", "run", "--port", "80", "--host", "0.0.0.0"]