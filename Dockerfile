FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir $(python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(' '.join(d['project']['dependencies']))")

ENV TERM=xterm-256color

CMD ["python", "-m", "dockmeister"]
