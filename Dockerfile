FROM node:24-bookworm-slim AS web-build
WORKDIR /app/apps/carbon_research_web
COPY apps/carbon_research_web/package.json apps/carbon_research_web/package-lock.json ./
RUN npm ci
COPY apps/carbon_research_web/ ./
RUN VITE_PUBLIC_BROWSER_PROJECTS=1 npm run build

FROM python:3.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/packages \
    CIVIL_CARBON_PUBLIC_MODE=1 \
    CIVIL_CARBON_PDF_FONT=/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf
WORKDIR /app
COPY requirements.lock ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-core \
    && test -f "$CIVIL_CARBON_PDF_FONT" \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.lock \
    && useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser apps/ ./apps/
COPY --chown=appuser:appuser packages/ ./packages/
COPY --from=web-build --chown=appuser:appuser /app/apps/carbon_research_web/dist ./apps/carbon_research_web/dist
USER appuser
CMD ["sh", "-c", "exec uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
