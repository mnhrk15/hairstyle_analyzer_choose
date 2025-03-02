# Development Guide

This document provides detailed information about developing for the Hairstyle Analyzer project.

## Setting Up Development Environment

### Prerequisites

- Python 3.9 or higher
- Git
- Code editor (VSCode recommended)

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/hairstyle-analyzer.git
   cd hairstyle-analyzer
   ```

2. Set up the virtual environment:
   - **Windows:** Run `setup_env.bat`
   - **macOS/Linux:** Run `chmod +x setup_env.sh && ./setup_env.sh`

3. Activate the virtual environment:
   - **Windows:** `venv\Scripts\activate`
   - **macOS/Linux:** `source venv/bin/activate`

4. Install the package in development mode:
   ```bash
   pip install -e .
   ```

### Environment Variables

Create a `.env` file in the project root with the following variables:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

## Project Structure

### Directory Layout

- `hairstyle_analyzer/` - Main package
  - `core/` - Core analysis and processing functionality
  - `data/` - Data models and management
  - `services/` - External service integrations (Gemini API, web scraping)
  - `ui/` - User interface components
  - `utils/` - Utility functions and helpers
- `tests/` - Unit and integration tests
- `docs/` - Documentation
- `assets/` - Static assets
  - `templates/` - Template CSV files
  - `samples/` - Sample images

### Module Responsibilities

#### Core

- `image_analyzer.py` - Handles image analysis using Gemini API
- `template_matcher.py` - Matches analysis results with templates
- `main_processor.py` - Controls the overall processing flow

#### Data

- `models.py` - Data models for the application
- `config_manager.py` - Configuration management
- `template_manager.py` - Template loading and management
- `cache_manager.py` - Cache management

#### Services

- `gemini_service.py` - Gemini API integration
- `scraper_service.py` - Web scraping functionality

#### UI

- `streamlit_app.py` - Main Streamlit application
- `gui_components.py` - Reusable UI components

## Development Workflow

### Code Style

This project follows PEP 8 style guidelines. We recommend using:

- `black` for code formatting
- `flake8` for linting
- `mypy` for static type checking

### Testing

- Write unit tests for all new functionality
- Run tests with pytest: `pytest tests/`
- Aim for at least 80% test coverage

### Git Workflow

1. Create a new branch for each feature or bug fix
2. Make small, focused commits
3. Write descriptive commit messages
4. Open a pull request for review
5. Merge to main branch after approval

### Documentation

- Document all public functions, classes, and methods
- Update README.md and other documentation when adding new features
- Use clear, concise docstrings following Google style format

## Working with Gemini API

### Structured Output

When working with the Gemini API for structured outputs:

1. Define clear JSON schema in your prompts
2. Use the response_mime_type parameter to request JSON:
   ```python
   response = model.generate_content(
       prompt,
       generation_config={
           "response_mime_type": "application/json"
       }
   )
   ```
3. Handle parsing errors gracefully

## Troubleshooting

### Common Issues

1. **Gemini API connection issues**
   - Check your API key
   - Verify internet connection
   - Check for rate limiting

2. **Web scraping errors**
   - HotPepper Beauty may change their HTML structure
   - Check selector patterns in `scraper_service.py`

3. **Image processing errors**
   - Verify image format compatibility
   - Check file permissions

For additional help, please open an issue on the GitHub repository.
