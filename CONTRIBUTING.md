# Contributing to Wave Client for Emacs

Thank you for your interest in contributing to Wave Client for Emacs!

## Development Setup

### Prerequisites

- Python 3.11+
- uv (Python package manager)
- Emacs 29.4+
- Git
- GNU Make (gmake on FreeBSD)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/aygp-dr/wave-client-for-emacs.git
cd wave-client-for-emacs

# Check dependencies
gmake deps-check

# Install Python dependencies
gmake install

# Run tests to verify setup
gmake test
```

## Development Workflow

### Running the Server

```bash
# Development server with auto-reload
gmake dev

# Production server
gmake server
```

### Running Tests

```bash
# All tests
gmake test

# Python tests only
gmake test-python

# Elisp tests only
gmake test-elisp
```

### Code Quality

```bash
# Run linters
gmake lint

# Format code
gmake format
```

## Code Style

### Python

- Follow PEP 8 guidelines
- Use type hints where possible
- Format with `ruff` and `black`
- Maximum line length: 88 characters

### Emacs Lisp

- Follow Emacs Lisp conventions
- Use `wave-` prefix for all public functions
- Document functions with docstrings
- Ensure byte-compilation without warnings

## Commit Guidelines

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature
fix: correct bug
docs: update documentation
test: add or update tests
refactor: restructure code without behavior change
style: formatting changes
chore: maintenance tasks
```

### Commit Message Format

```
<type>: <description>

[optional body]

[optional footer]
```

### Co-authorship

For AI-assisted commits, include:

```
--trailer "Co-authored-by: Claude <noreply@anthropic.com>"
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with appropriate tests
3. Ensure CI passes (`gmake lint && gmake test`)
4. Submit a PR with a clear description
5. Address review feedback

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventions
- [ ] No secrets or credentials committed

## Project Structure

```
wave-client-for-emacs/
├── src/wave_client_server/  # Python FastAPI server
├── lisp/                    # Emacs Lisp client
├── tests/                   # Test suites
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── broken/             # Tests awaiting fixes
├── experiments/            # Research and prototypes
├── scripts/                # Utility scripts
├── specs/                  # OpenAPI specifications
└── seeds/                  # Test data generators
```

## Issue Tracking

We use `bd` (beads) for issue tracking. Common commands:

```bash
# Find available work
bd ready

# View issue details
bd show <id>

# Create new issue
bd create --title="..." --type=task --priority=2
```

## Testing Experimental Features

Experimental code lives in `experiments/`:

```bash
# List experiments
ls experiments/

# Run specific experiment
gmake gastown-demo
```

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Join discussions in relevant issues

## License

By contributing, you agree that your contributions will be licensed under the project's license.
