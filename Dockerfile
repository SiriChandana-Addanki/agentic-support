FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SUPPORT_HOST=0.0.0.0 \
    SUPPORT_PORT=8000

WORKDIR /app

RUN groupadd --system --gid 10001 agentic \
    && useradd --system --uid 10001 --gid agentic --home-dir /app agentic

# requirements.txt currently declares no third-party dependencies.
COPY --chown=agentic:agentic support_agent ./support_agent
COPY --chown=agentic:agentic data ./data
COPY --chown=agentic:agentic tests ./tests

USER agentic
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1

CMD ["python", "-m", "support_agent", "serve"]
