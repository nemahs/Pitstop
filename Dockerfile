# syntax=docker/dockerfile:1.7-labs
FROM python AS builder


RUN apt update && apt install -y nodejs npm 
WORKDIR /app
COPY . /app/
RUN --mount=type=secret,id=.env,dst=/app/.env pip install --no-cache-dir -r /app/requirements.txt && flask vite install
RUN --mount=type=secret,id=.env,dst=/app/.env flask vite build


FROM python:slim as production

EXPOSE 80/tcp

COPY --exclude=**/vite . /app
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY --from=builder /app/vite/dist /app/vite/dist

WORKDIR /app
CMD [ "flask", "run", "--port", "80", "--host", "0.0.0.0"]