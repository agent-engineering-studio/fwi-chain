# The fire danger diary: the API and its page, Bootstrap Italia served by the
# page itself (no CDN). Built from the root of the repository, because the app
# runs on the library of this repository:
#
#   docker compose up ui       http://localhost:3007
FROM node:22-slim AS vendor
WORKDIR /vendor
COPY app/package.json ./
RUN npm install --no-audit --no-fund --silent \
    && mkdir -p bootstrap-italia \
    && cp -R node_modules/bootstrap-italia/dist/css node_modules/bootstrap-italia/dist/fonts bootstrap-italia/

FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    FWI_CHAIN_DATI=/srv/app/data/esempio_gioia_del_colle_2025.csv \
    FWI_CHAIN_STATIC=/srv/app/static

# The library first, then the app on top of it.
WORKDIR /srv
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src src
COPY app/pyproject.toml app/uv.lock app/
COPY app/src app/src
WORKDIR /srv/app
RUN uv sync --locked --no-dev --no-editable

COPY app/data data
COPY app/static static
COPY --from=vendor /vendor/bootstrap-italia static/vendor/bootstrap-italia

RUN python -c "from diario.api import esempio, leggi_righe; assert len(leggi_righe(esempio()).osservazioni) == 48"
EXPOSE 8000
USER nobody
CMD ["uvicorn", "diario.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
