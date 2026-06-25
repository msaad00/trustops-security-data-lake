# Multi-stage Dockerfile: builds the Next.js workbench, installs the Python
# package with the workbench bundled in, ships a slim runtime image.
#
# Three stages:
#   1. web-build  — Node 22 builds the static React export into
#                   src/security_lakehouse/web/dist/
#   2. py-build   — Python 3.12 installs the package + analytics extras into a
#                   virtualenv that runtime mounts read-only
#   3. runtime    — Python 3.12 slim, copies the venv + lake mount points,
#                   runs `security-lakehouse serve` as a non-root user
#
# Build:  docker build -t trustops:dev .
# Run:    docker run --rm -p 8787:8787 -v $PWD/build/lakehouse:/lake trustops:dev

ARG NODE_VERSION=22
ARG PYTHON_VERSION=3.12

# --- 1. React workbench ----------------------------------------------------
FROM node:${NODE_VERSION}-slim AS web-build
WORKDIR /workbench
COPY app/web/package*.json ./
RUN npm ci --no-audit --no-fund
COPY app/web/ ./
RUN npm run build

# --- 2. Python package + analytics venv -----------------------------------
FROM python:${PYTHON_VERSION}-slim AS py-build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY connectors/ ./connectors/
COPY controls/ ./controls/
COPY frameworks/ ./frameworks/
COPY mappings/ ./mappings/
COPY programs/ ./programs/
# Bring the static export into the package tree before install so wheel
# package-data picks it up.
COPY --from=web-build /src/security_lakehouse/web/dist/ ./src/security_lakehouse/web/dist/
RUN python -m venv /opt/trustops-venv \
  && /opt/trustops-venv/bin/pip install --upgrade pip \
  && /opt/trustops-venv/bin/pip install ".[analytics]"

# --- 3. Slim runtime ------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime
LABEL org.opencontainers.image.title="TrustOps Security Data Lake"
LABEL org.opencontainers.image.source="https://github.com/msaad00/trustops-security-data-lake"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV PATH="/opt/trustops-venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRUSTOPS_LAKE=/lake \
    TRUSTOPS_DATA_DIR=/opt/trustops-data

RUN apt-get update \
  && apt-get install --no-install-recommends -y tini \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd --gid 1100 trustops \
  && useradd --uid 1100 --gid 1100 --home /home/trustops --create-home --shell /bin/bash trustops \
  && mkdir -p /lake \
  && chown -R trustops:trustops /lake

COPY --from=py-build /opt/trustops-venv /opt/trustops-venv
# Ship the framework / control / connector / mapping catalogs inside the
# image so the wheel-installed Python package can find them. The env var
# TRUSTOPS_DATA_DIR (set above) tells security_lakehouse where to look.
COPY frameworks/ /opt/trustops-data/frameworks/
COPY controls/ /opt/trustops-data/controls/
COPY connectors/ /opt/trustops-data/connectors/
COPY mappings/ /opt/trustops-data/mappings/
COPY programs/ /opt/trustops-data/programs/

USER trustops
WORKDIR /home/trustops
EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/api/healthz', timeout=2)"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["security-lakehouse", "serve", "--lake", "/lake", "--host", "0.0.0.0", "--port", "8787"]
