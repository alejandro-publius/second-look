FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY apps ./apps
COPY core ./core
COPY content ./content
COPY photos ./photos
COPY scripts ./scripts
COPY results ./results
COPY fhir/golden ./fhir/golden
COPY fhir/ig.lock ./fhir/ig.lock
RUN mkdir -p /app/data
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app
EXPOSE 8000
CMD ["sh", "-c", "alembic -c apps/api/alembic.ini upgrade head && uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --no-access-log --proxy-headers"]
