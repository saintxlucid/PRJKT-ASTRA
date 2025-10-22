# Contributing Guide

This guide outlines the process for contributing to the RAG system project.

## Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/your-org/rag-system.git
   cd rag-system
   ```

2. Create virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   .\venv\Scripts\activate   # Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

## Code Style

We follow these conventions:

1. Python Style
   - PEP 8 guidelines
   - Type hints for all functions
   - Docstrings for classes and functions
   - Maximum line length: 88 characters

2. Documentation
   - Clear module documentation
   - Updated README.md
   - Example usage
   - Architecture notes

3. Testing
   - Unit tests required
   - Integration tests where applicable
   - Performance benchmarks for critical paths

## Git Workflow

1. Create Feature Branch:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make Changes:
   - Write code
   - Add tests
   - Update documentation

3. Commit Changes:

   ```bash
   git add .
   git commit -m "feat: your detailed commit message"
   ```

4. Push Changes:

   ```bash
   git push origin feature/your-feature-name
   ```

5. Create Pull Request:
   - Clear description
   - Link related issues
   - List testing steps

## Commit Messages

Follow Conventional Commits:

```
feat: add neural query router
^--^  ^--------------------^
|     |
|     +-> Summary in present tense
|
+-------> Type: feat, fix, docs, style, refactor, test, chore
```

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- style: Formatting
- refactor: Code restructuring
- test: Adding tests
- chore: Maintenance

## Testing

1. Run Tests:

   ```bash
   # Run all tests
   pytest tests/

   # Run specific test file
   pytest tests/test_router.py

   # Run with coverage
   pytest --cov=astra tests/
   ```

2. Performance Tests:

   ```bash
   # Run benchmarks
   python -m pytest tests/benchmarks/
   ```

## Documentation

1. Update Docs:
   - Component documentation
   - API reference
   - Example usage
   - Architecture diagrams

2. Build Docs:

   ```bash
   # Generate documentation
   cd docs
   make html
   ```

## Code Review

Pull requests require:

1. Code Quality
   - Passing tests
   - Style compliance
   - Type checking
   - Documentation

2. Review Process
   - 2 approving reviews
   - All comments addressed
   - CI checks passing

3. Testing
   - Unit tests
   - Integration tests
   - Performance validation

## Release Process

1. Version Update:
   - Update version.py
   - Update CHANGELOG.md
   - Tag release

2. Release Steps:

   ```bash
   # Update version
   bump2version patch  # or minor, major

   # Create tag
   git tag -a v1.0.0 -m "Release version 1.0.0"

   # Push changes
   git push origin main --tags
   ```

## Support

Need help?

1. Check documentation
2. Search existing issues
3. Open new issue with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior

## Best Practices

1. Code Quality:
   - Write clear, maintainable code
   - Follow project style guide
   - Add comprehensive tests
   - Document your changes

2. Communication:
   - Clear commit messages
   - Detailed PR descriptions
   - Responsive to feedback
   - Update relevant docs

3. Testing:
   - Write tests first
   - Cover edge cases
   - Check performance
   - Verify integrations