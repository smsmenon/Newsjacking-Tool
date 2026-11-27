FROM python:3.12-slim

WORKDIR /app
COPY . /app

ENV PYTHONPATH=/app/src
EXPOSE 8787

CMD ["python", "-m", "tada_ci.api.server", "--root", "/app", "--host", "0.0.0.0", "--port", "8787"]

