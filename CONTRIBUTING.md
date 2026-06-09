# Contributing to LAAP

We love your input! We want to make contributing to LAAP as easy and transparent as possible.

## Development Process

1. Fork the repo and create your branch from `main`
2. If you've added code, add tests
3. Ensure the test suite passes
4. Make sure your code lints
5. Issue that pull request!

## Development Setup

```bash
# Clone the repo
git clone https://github.com/laap-agi/laap.git
cd laap

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

# Install in development mode
pip install -e ".[dev,all]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

## Code Style

- **Python**: We use `ruff` for linting and formatting
- **Rust**: We use `rustfmt` and `clippy`
- **TypeScript**: We use `eslint` and `prettier`

Run linting before committing:

```bash
ruff check laap/ tests/
mypy laap/
```

## Testing

Write tests for any new functionality:

```bash
pytest -v
pytest --cov=laap
```

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the CHANGELOG.md with any new features or fixes
3. The PR will be merged once you have the sign-off of maintainers

## Any contributions you make will be under the MIT Software License

When you submit code changes, your submissions are understood to be under the
same [MIT License](LICENSE) that covers the project.
