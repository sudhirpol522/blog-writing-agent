# Blog Writing Agent

AI-powered blog writing agent built with LangGraph, OpenAI, and Streamlit. Generates high-quality technical blog posts with automated research, structured planning, and image generation.

## Demo

![Demo Video](assets/demo.mp4)

## Features

- Automated web research using Tavily API
- Structured blog planning with LangGraph workflow
- Parallel section writing for efficiency
- Automatic image generation with DALL-E 3 or Google Imagen
- Real-time progress tracking with SSE
- Interactive Streamlit web interface
- LaTeX formula rendering support
- Load and manage previously generated blogs

## Prerequisites

- Python 3.9 or higher
- OpenAI API key (required)
- Tavily API key (optional, for research)
- Google API key (optional, for Imagen)

## Quick Start

### Windows

```powershell
# Install dependencies
.\setup.ps1

# Run application
.\run.ps1
```

### Linux/Mac

```bash
# Install dependencies
make setup

# Run application
make run
```

## Configuration

Create .env file in project root:

```env
OPENAI_API_KEY=your_openai_key
TAVILY_API_KEY=your_tavily_key
GOOGLE_API_KEY=your_google_key

IMAGE_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
MODEL_TEMPERATURE=0.7
```

## Project Structure

```
blog-writing-agent/
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ models/          # Pydantic schemas
â”‚   â”œâ”€â”€ services/        # LLM, research, image services
â”‚   â”œâ”€â”€ workflow/        # LangGraph workflow nodes
â”‚   â””â”€â”€ ui/              # Streamlit interface
â”œâ”€â”€ outputs/             # Generated blogs
â”œâ”€â”€ images/              # Generated images
â”œâ”€â”€ app.py               # Application entry point
â”œâ”€â”€ config.py            # Configuration management
â”œâ”€â”€ requirements.txt     # Python dependencies
â”œâ”€â”€ Dockerfile           # Container configuration
â””â”€â”€ docker-compose.yml   # Multi-service setup
```

## Usage

### Generate Blog

1. Open application at http://localhost:8501
2. Enter blog topic in sidebar
3. Click "Generate Blog"
4. Monitor progress in real-time
5. View results in tabs

### Load Previous Blogs

1. Navigate to sidebar "Past blogs" section
2. Select blog from list
3. Click "Load selected blog"
4. View in Markdown Preview tab

## Docker Deployment

```bash
# Build and run
docker-compose up -d

# Access application
# http://localhost:8501
```

## API Keys

### OpenAI (Required)
Get key at https://platform.openai.com/api-keys

### Tavily (Optional)
Get key at https://tavily.com

### Google (Optional)
Get key at https://console.cloud.google.com

## Output

Generated blogs are saved to:
- outputs/ directory (markdown files)
- images/ directory (PNG images)

## Technology Stack

- LangGraph: Workflow orchestration
- OpenAI GPT-4o-mini: Content generation
- DALL-E 3: Image generation
- Streamlit: Web interface
- Tavily: Web research
- Pydantic: Data validation
- Docker: Containerization

## Development

```bash
# Install in development mode
pip install -r requirements.txt

# Run tests
python -m pytest

# Format code
black src/

# Type check
mypy src/
```

## Troubleshooting

### Application won't start
```powershell
.\clean.ps1
.\setup.ps1
.\run.ps1
```

### Images not generating
- Verify IMAGE_PROVIDER setting in .env
- Check API key is valid
- Ensure sufficient API credits

### No past blogs showing
- Generate a blog first
- Check outputs/ folder exists
- Verify file permissions

## License

MIT License

## Support

For issues and questions, please open an issue on the repository.
