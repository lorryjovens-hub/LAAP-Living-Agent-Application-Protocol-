# LAAP Quickstart Guide

## Installation

### Prerequisites

- Python 3.10+
- Rust (optional, for core performance module)
- Node.js 18+ (optional, for web UI)

### Install from source

```bash
git clone https://github.com/laap-agi/laap.git
cd laap
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[all]"
```

### Install with Docker

```bash
docker compose up -d
```

## Configuration

### Set your API key

```bash
export LAAP_PROVIDER=anthropic
export LAAP_API_KEY=sk-ant-...
export LAAP_MODEL=claude-sonnet-4-6
```

Or use the config wizard:

```bash
laap config
```

## Usage

### Start the REPL

```bash
laap repl
```

### Run a single command

```bash
laap run "Analyze this project's code structure"
```

### Start the API server

```bash
laap serve --port 8080
```

## Web Dashboard

```bash
cd ui && npm install && npm run dev
```

Then open http://localhost:3000

## Next Steps

- Read the [Architecture Overview](architecture-overview.md)
- Explore [CLI Commands](cli-commands.md)
- Configure [Message Gateways](gateway-setup.md)
