FROM python:3.13 AS builder

# TODO: Use pure vite instead of flask-vite
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
     apt-get update && apt-get install --no-install-recommends -y nodejs npm 
WORKDIR /app
COPY vite/ /app/
RUN npm install --global vite@latest && npm install 
RUN vite build


FROM python:slim AS production
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

EXPOSE 80/tcp
WORKDIR /app

COPY pyproject.toml *.py *.ini templates/ static/ data/ contract_endpoints/ alembic/ /app/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev --compile-bytecode
COPY --from=builder /app/dist /app/vite/dist

#HEALTHCHECK CMD [ "wget", "-q", "localhost" ]
# TODO: Switch to gunicorn
CMD [ "uv", "run", "flask", "run", "--port", "80", "--host", "0.0.0.0"]