# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the frontend
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /build

# Install dependencies from the lockfile first so this layer caches.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# vite.config.ts writes to ../backend/static; override it to a local directory
# so the output is easy to copy in the next stage.
RUN npm run build -- --outDir dist --emptyOutDir


# ---------------------------------------------------------------------------
# Stage 2 — runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    # Cloud Run defaults: Firestore, no dev affordances, SPA served here.
    # AUTH_MODE is deliberately not set: ENVIRONMENT=production already forces
    # Firebase authentication in app/core/config.py.
    ENVIRONMENT=production \
    DATA_BACKEND=firestore \
    SERVE_FRONTEND=true \
    FRONTEND_DIST_DIR=static

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /build/dist ./static

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 teampulse \
    && chown -R teampulse:teampulse /app
USER teampulse

EXPOSE 8080

# Cloud Run sets $PORT; uvicorn binds to it. One worker keeps the in-process
# request working set coherent; scale out with Cloud Run instances instead.
# Exec form via sh so ${PORT} is expanded and uvicorn still receives signals.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
