# Hairstyle Analyzer

AI-powered hairstyle image analysis and title generation system. This tool analyzes hairstyle images using Google Gemini AI, matches them with templates, and generates optimal Excel output including stylist and coupon information from HotPepper Beauty.

## Features

- Automated image analysis with Google Gemini AI
- Hairstyle categorization and feature extraction
- Gender and hair length detection
- Stylist and coupon matching from HotPepper Beauty
- Template-based title and hashtag generation
- Excel output with standardized format
- User-friendly Streamlit GUI

## System Requirements

- Python 3.9 or higher
- Internet connection for Gemini API and web scraping
- Gemini API key

## Getting Started

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/hairstyle-analyzer.git
   cd hairstyle-analyzer
   ```

2. Set up the virtual environment:

   **Windows:**
   ```
   setup_env.bat
   ```

   **macOS/Linux:**
   ```
   chmod +x setup_env.sh
   ./setup_env.sh
   ```

3. Activate the virtual environment:

   **Windows:**
   ```
   venv\Scripts\activate
   ```

   **macOS/Linux:**
   ```
   source venv/bin/activate
   ```

### API Key Setup

This application requires a Google Gemini API key to run.

1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/).
2. Create a `.env` file in the project root directory with your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
   You can also copy and edit the provided `.env.example` file.

### Configuration

1. Configure the application settings in `config/config.yaml` (sample configuration file provided).
2. Prepare the template CSV file in `assets/templates/` directory (sample template file provided).

### Running the Application

1. Start the Streamlit application:
   ```
   streamlit run hairstyle_analyzer/ui/streamlit_app.py
   ```

2. Open your web browser and navigate to the displayed URL (usually http://localhost:8501).

## Project Structure

```
hairstyle_analyzer/
├── hairstyle_analyzer/       # Main package
│   ├── core/                 # Core functionality
│   ├── data/                 # Data models and management
│   ├── services/             # External service integrations
│   ├── ui/                   # UI components
│   └── utils/                # Utility functions
├── tests/                    # Unit and integration tests
├── docs/                     # Documentation
├── assets/                   # Static assets
│   ├── templates/            # Template files
│   └── samples/              # Sample images
├── setup.py                  # Package setup script
├── requirements.txt          # Dependencies
├── setup_env.bat             # Windows setup script
├── setup_env.sh              # macOS/Linux setup script
└── README.md                 # This file
```

## Development

### Setting Up Development Environment

1. Install development dependencies:
   ```
   pip install -e ".[dev]"
   ```

2. Install pre-commit hooks:
   ```
   pre-commit install
   ```

### Running Tests

Run unit tests:
```
pytest tests/
```

### Running Examples

Try the example scripts to see the functionality in action:

```
# Template and cache management demo
python examples/demo_template_cache.py

# Gemini API integration demo (requires API key)
python examples/demo_gemini_service.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
