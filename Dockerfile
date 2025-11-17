ARG PYTHON_VER=3.13-slim

FROM python:${PYTHON_VER} AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Build-time env for uv
# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy
# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Prime dependency cache
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable --no-group dev

# Copy project and install it into the venv
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-group dev

FROM python:${PYTHON_VER} AS final

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --chmod=0755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

ENV PATH=/app/.venv/bin:$PATH
# Set HOME so xdg_config_home() returns /home/appuser/.config
ENV HOME=/home/appuser

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["cdtui"]
