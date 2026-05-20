# syntax=docker/dockerfile:1.7

# ---------------------------------------------------------------------------
# Zendesk MCP Server — containerised stdio MCP server for Claude clients
#
# Build:
#     docker build -t artifax/zendesk-mcp .
#
# Run (interactive stdio for an MCP client):
#     docker run --rm -i \
#         -e ZENDESK_EMAIL="you@artifax.com" \
#         -e ZENDESK_TOKEN="$ZENDESK_TOKEN" \
#         -e ZENDESK_SUBDOMAIN="artifax" \
#         artifax/zendesk-mcp
#
# Intended to be wired into Claude Code or Claude Desktop's MCP config; see
# ARTIFAX-READ-INSTALL-GUIDE.md for the JSON snippet.
# ---------------------------------------------------------------------------

# Stage 1 — build a self-contained virtualenv with the package and its deps.
FROM python:3.12-slim AS builder

# uv from the official Astral image is faster and avoids a curl-pipe install.
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /build

# Copy only the files needed to resolve and build the wheel. Source files
# come last so dep-only layers cache across source-only changes.
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install into a venv at /opt/venv so we can copy just the venv to the
# runtime stage (no build tooling, no source tree, no caches).
RUN uv venv /opt/venv \
 && uv pip install --python /opt/venv/bin/python --no-cache .

# ---------------------------------------------------------------------------
# Stage 2 — minimal runtime: Python + jq + the venv + a non-root user.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# jq powers the `zd-cli query` sub-command. The MCP server itself doesn't
# strictly need it, but exposing it costs ~1.5 MB and matches the CLI.
RUN apt-get update \
 && apt-get install -y --no-install-recommends jq \
 && rm -rf /var/lib/apt/lists/*

# Non-root user for defence in depth — the MCP server only needs to read
# env vars, write to /tmp, and make outbound HTTPS calls.
RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 mcp

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER mcp
WORKDIR /home/mcp

# FastMCP listens on stdio by default; the container expects `docker run -i`.
ENTRYPOINT ["zendesk-mcp"]

LABEL org.opencontainers.image.title="Artifax Zendesk MCP Server" \
      org.opencontainers.image.description="MCP server exposing Zendesk Support operations to Claude clients." \
      org.opencontainers.image.source="https://github.com/ArtifaxSoftware/zendesk-skill" \
      org.opencontainers.image.licenses="MIT"
