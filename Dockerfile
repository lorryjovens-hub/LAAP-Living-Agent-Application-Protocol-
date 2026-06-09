# Multi-stage build for LAAP
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Rust for core extension
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy and install dependencies
COPY pyproject.toml setup.py ./
COPY core/ ./core/
COPY laap/ ./laap/

RUN pip install --upgrade pip && \
    pip install -e ".[all]" && \
    cd core && cargo build --release && cd ..

EXPOSE 8080

ENTRYPOINT ["laap"]
CMD ["--help"]

# Development image with hot-reload
FROM base AS dev
RUN pip install watchdog pytest ipython
ENV LAAP_ENV=development
CMD ["laap", "repl"]
