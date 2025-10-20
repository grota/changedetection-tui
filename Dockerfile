ARG PYTHON_VER=3.13-slim
ARG NEW_UID=10001
ARG NEW_GID=10001

FROM python:${PYTHON_VER} AS builder

ARG NEW_UID
ARG NEW_GID

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN groupadd -g "${NEW_GID}" appuser \
 && useradd -u "${NEW_UID}" -g appuser --system --shell /usr/sbin/nologin appuser --no-log-init --create-home

USER appuser
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
RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=${NEW_UID},gid=${NEW_GID} \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

# Copy project and install it into the venv
COPY --chown=${NEW_UID}:${NEW_GID} . /app
RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=${NEW_UID},gid=${NEW_GID} \
    uv sync --locked --no-editable

FROM python:${PYTHON_VER} AS final

ARG NEW_UID
ARG NEW_GID

# Recreate the same user
RUN groupadd -g "${NEW_GID}" appuser \
 && useradd -u "${NEW_UID}" -g appuser --system --shell /usr/sbin/nologin appuser --no-log-init --create-home

USER appuser
WORKDIR /app

COPY --from=builder --chown=${NEW_UID}:${NEW_GID} /app/.venv /app/.venv

ENV PATH=/app/.venv/bin:$PATH

CMD ["cdtui"]
