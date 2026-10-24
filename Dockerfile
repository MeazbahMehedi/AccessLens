FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/accesscheck
COPY pyproject.toml README.md ./
COPY app ./app
COPY cli ./cli
COPY scripts ./scripts
RUN pip install --no-cache-dir . && python -m playwright install --with-deps chromium
RUN mkdir -p /data/screenshots
ENV DATABASE_URL=sqlite+aiosqlite:////data/accesscheck.db SCREENSHOT_DIR=/data/screenshots
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
