FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_ROOT=/app/data \
    STAGING_ROOT=/app/staging \
    INBOX_ROOT=/app/inbox \
    LEDGER_ROOT=/app/ledger \
    DATABASE_PATH=/app/data/nodepanel.db \
    SSH_KNOWN_HOSTS_PATH=/app/data/known_hosts \
    BIND_HOST=0.0.0.0 \
    BIND_PORT=420

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system nodepanel \
    && useradd --system --gid nodepanel --create-home --home-dir /home/nodepanel nodepanel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY templates ./templates
COPY static ./static
COPY third_party ./third_party
COPY frontend/dist ./frontend/dist
COPY README.md ./
COPY docs ./docs
COPY pytest.ini ./

RUN mkdir -p /app/data /app/staging /app/inbox /app/ledger /app/events \
    && chown -R nodepanel:nodepanel /app /home/nodepanel

USER nodepanel

EXPOSE 420

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('BIND_PORT', '420') + '/healthz', timeout=3).read()" || exit 1

CMD ["sh", "-c", "exec uvicorn backend.main:app --host \"$BIND_HOST\" --port \"$BIND_PORT\""]
