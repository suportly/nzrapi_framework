# Contributing to nzrRest Framework

Thank you for your interest in contributing to nzrRest! We welcome contributions from developers of all skill levels. This guide will help you get started with contributing to the project.

## 🤝 How to Contribute

### Reporting Issues

Before creating an issue, please:

1. **Search existing issues** to avoid duplicates
2. **Use a clear and descriptive title**
3. **Provide detailed information** about the bug or feature request
4. **Include steps to reproduce** for bugs
5. **Specify your environment** (OS, Python version, nzrRest version)

### Feature Requests

We welcome feature requests! Please:

1. **Check existing issues** and discussions first
2. **Describe the use case** and why it would be valuable
3. **Provide examples** of how the feature would be used
4. **Consider the scope** - start with smaller, focused features

## 🚀 Development Setup

### Prerequisites

- Python 3.8 or higher
- Git

### Getting Started

1. **Fork the repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/nzrrest.git
   cd nzrrest
   ```

2. **Set up development environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install in development mode with all dependencies
   pip install -e ".[dev,ai,monitoring,redis]"
   
   # Install pre-commit hooks
   pre-commit install
   ```

3. **Verify installation**
   ```bash
   # Run tests to ensure everything is working
   pytest
   
   # Run examples
   python examples/basic_api.py
   ```

### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. **Make your changes**
   - Write clean, readable code
   - Follow existing code style and patterns
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Run all tests
   pytest
   
   # Run specific test file
   pytest tests/test_your_feature.py
   
   # Run with coverage
   pytest --cov=nzrrest
   
   # Run linting and formatting
   black .
   isort .
   flake8
   mypy nzrrest
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add description of your feature"
   # or
   git commit -m "fix: description of the bug fix"
   ```

5. **Push and create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📝 Code Style Guidelines

### Python Code Style

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 88 characters (Black default)
- **Imports**: Use `isort` for import sorting
- **Type hints**: Required for all public functions and methods
- **Docstrings**: Use Google-style docstrings

### Code Formatting

We use automated tools to maintain consistent code style:

```bash
# Format code
black .

# Sort imports
isort .

# Check style
flake8

# Type checking
mypy nzrrest
```

### Example Code Style

```python
"""
Module docstring describing the purpose.
"""

from typing import Dict, List, Optional

from nzrrest import NzrRestApp
from nzrrest.ai.models import AIModel


class ExampleModel(AIModel):
    """Example AI model implementation.
    
    Args:
        config: Model configuration dictionary
        
    Attributes:
        name: Model name
        is_loaded: Whether model is loaded
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.custom_param = config.get('custom_param', 'default')
    
    async def load_model(self) -> None:
        """Load the AI model asynchronously."""
        # Implementation here
        self.is_loaded = True
    
    async def predict(
        self, 
        payload: Dict[str, Any], 
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make prediction with the model.
        
        Args:
            payload: Input data for prediction
            context: Optional conversation context
            
        Returns:
            Prediction results dictionary
            
        Raises:
            RuntimeError: If model is not loaded
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")
        
        # Implementation here
        return {"response": "Example response"}
```

## 🧪 Testing Guidelines

### Writing Tests

- **Test coverage**: Aim for >90% test coverage
- **Test types**: Write unit tests, integration tests, and examples
- **Test naming**: Use descriptive test names
- **Fixtures**: Use pytest fixtures for common setup
- **Async tests**: Mark async tests with `@pytest.mark.asyncio`

### Test Structure

```python
"""Tests for example module."""

import pytest
from nzrrest import NzrRestApp
from nzrrest.ai.models import MockAIModel


class TestExampleModel:
    """Test suite for ExampleModel."""
    
    @pytest.fixture
    async def model(self):
        """Create test model instance."""
        config = {"name": "test_model", "provider": "test"}
        model = MockAIModel(config)
        await model.load_model()
        return model
    
    @pytest.mark.asyncio
    async def test_predict_success(self, model):
        """Test successful prediction."""
        payload = {"message": "test"}
        result = await model.predict(payload)
        
        assert "response" in result
        assert isinstance(result["response"], str)
    
    @pytest.mark.asyncio
    async def test_predict_without_loading(self):
        """Test prediction fails when model not loaded."""
        config = {"name": "test_model"}
        model = MockAIModel(config)
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            await model.predict({"message": "test"})
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ai_models.py

# Run with coverage
pytest --cov=nzrrest --cov-report=html

# Run integration tests only
pytest -m integration

# Run tests in parallel
pytest -n auto
```

## 📚 Documentation

### Docstring Guidelines

Use Google-style docstrings:

```python
def example_function(param1: str, param2: int = 10) -> bool:
    """Example function with documented parameters.
    
    Args:
        param1: Description of param1
        param2: Description of param2. Defaults to 10.
        
    Returns:
        True if successful, False otherwise.
        
    Raises:
        ValueError: If param1 is empty.
        
    Example:
        >>> example_function("hello", 5)
        True
    """
```

### Documentation Updates

When adding new features:

1. **Update docstrings** for all new functions/classes
2. **Add examples** showing how to use the feature
3. **Update README.md** if it affects the main API
4. **Consider adding** to the examples directory

## 🎯 Areas for Contribution

### High Priority

- **AI Model Integrations**: Additional AI provider support
- **Performance Optimizations**: Async improvements, caching
- **Documentation**: Examples, tutorials, API documentation
- **Testing**: Increase test coverage, integration tests

### Medium Priority

- **CLI Enhancements**: Additional commands and utilities
- **Middleware**: Rate limiting improvements, auth systems
- **Database**: Additional database backends, migrations
- **Monitoring**: Better logging, metrics, health checks

### Good First Issues

Look for issues labeled with:
- `good-first-issue`
- `help-wanted`
- `documentation`
- `tests`

## 🔍 Code Review Process

### Pull Request Guidelines

1. **Clear description**: Explain what and why
2. **Link issues**: Reference related issues
3. **Small PRs**: Keep changes focused and reviewable
4. **Tests included**: All new code should have tests
5. **Documentation**: Update docs for user-facing changes

### Review Criteria

Reviewers will check for:

- **Functionality**: Does it work as intended?
- **Tests**: Are there adequate tests?
- **Code quality**: Is it readable and maintainable?
- **Performance**: Does it introduce performance issues?
- **Breaking changes**: Are they necessary and documented?

## 🏷️ Commit Message Guidelines

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(ai): add Anthropic Claude model support

fix(serializers): handle null values in validation

docs(readme): update installation instructions

test(ai): add tests for model registry
```

## 🐛 Debugging Tips

### Common Issues

1. **Import errors**: Check virtual environment activation
2. **Test failures**: Run tests individually to isolate issues
3. **Type errors**: Use `mypy` to catch type issues early
4. **Async issues**: Remember to use `await` with async functions

### Debug Mode

Enable debug mode for better error messages:

```python
app = NzrRestApp(debug=True)
```

### Logging

Use structured logging for debugging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
```

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Discord**: Join our community chat (link in README)
- **Email**: Contact maintainers at team@nzrrest.dev

## 📄 License

By contributing to nzrRest, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

All contributors will be:

- Listed in the contributors section
- Mentioned in release notes for significant contributions
- Invited to join the core contributor team for sustained contributions

Thank you for contributing to nzrRest! Your efforts help make AI API development better for everyone. 🚀