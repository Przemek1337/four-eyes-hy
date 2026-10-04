FROM node:22-bookworm-slim AS ui
WORKDIR /build/ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml ./
COPY src/ ./src/
COPY --from=ui /build/src/foureyes/ui_dist/ ./src/foureyes/ui_dist/
RUN pip install --no-cache-dir '.[harness]'
COPY policy.yaml ./
COPY feeds/ ./feeds/
EXPOSE 8080
CMD ["python", "-m", "foureyes.cli", "serve", "--policy", "/app/policy.yaml", "--harness", "kyc", "--host", "0.0.0.0", "--port", "8080"]
