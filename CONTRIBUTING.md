# Contributing Guide

## Getting Started

### Prerequisites
- Python 3.8 or higher
- pip for package management
- git for version control

### Setting Up Development Environment
1. Clone the repository
```bash
git clone <repository-url>
cd astra-core
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
pip install -e ".[dev]"  # Install dev dependencies
```

## Development Workflow

### Branching Strategy
- `main`: Production-ready code
- `develop`: Development branch
- `feature/*`: New features
- `fix/*`: Bug fixes
- `release/*`: Release preparation

### Making Changes
1. Create a new branch
```bash
git checkout -b feature/your-feature
```

2. Make your changes
3. Run tests
```bash
pytest tests/
```

4. Update documentation if needed
5. Commit your changes
```bash
git add .
git commit -m "feat: your feature description"
```

### Commit Message Guidelines
Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `style:` Code style
- `chore:` Maintenance

### Pull Request Process
1. Push your changes
```bash
git push origin feature/your-feature
```

2. Create a pull request
3. Ensure tests pass
4. Get code review
5. Address feedback
6. Merge when approved

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_surgeon.py

# Run with coverage
pytest --cov=evolution tests/
```

### Writing Tests
- Place tests in `tests/` directory
- Follow test naming convention: `test_*.py`
- Use fixtures from `conftest.py`
- Include docstrings and comments

## Documentation

### Building Docs
1. Install documentation dependencies
```bash
pip install -r docs/requirements.txt
```

2. Build documentation
```bash
cd docs
make html
```

### Documentation Style
- Use clear, concise language
- Include code examples
- Add docstrings to all public APIs
- Keep README.md up to date

## Release Process

### Preparing Release
1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release branch
```bash
git checkout -b release/vX.Y.Z
```

### Release Checklist
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped
- [ ] Release notes prepared

### Publishing Release
1. Merge to main
2. Tag release
```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

3. Build and publish
```bash
python -m build
twine upload dist/*
```