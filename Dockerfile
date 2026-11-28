# fwi-chain with the example notebooks, the benchmark and the MCP server.
# The page for a public body is another image, built from app/Dockerfile.
#
#   docker compose up notebooks            the notebooks, on http://localhost:8885
#   docker compose --profile mcp up mcp    the MCP server, on http://localhost:8772/mcp
#   docker compose run --rm bench          the benchmark
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /app

# The dependencies first: this layer is rebuilt only when they change.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --extra mcp --group examples --no-install-project

COPY README.md LICENSE ./
COPY src src
RUN uv sync --locked --no-dev --extra mcp --group examples --no-editable

# What the notebooks and the benchmark read, at the same relative paths.
COPY benchmarks benchmarks
COPY examples examples
COPY notebooks notebooks

# Fail the build, not the first run.
RUN python -c "import fwi_chain, fwi_chain.mcp_server, matplotlib, jupyterlab; print(fwi_chain.__version__)" \
    && python -m benchmarks.run --check > /dev/null

RUN useradd --create-home fwi && chown -R fwi /app/notebooks
USER fwi

EXPOSE 8888 8772
WORKDIR /app/notebooks
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", \
     "--ServerApp.token=", "--ServerApp.password=", "--ServerApp.root_dir=/app"]
