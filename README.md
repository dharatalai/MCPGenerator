# MCP SaaS Platform

A software-as-a-service platform for creating and managing Model Context Protocol (MCP) servers.

## Overview

This platform allows users to easily create custom MCP servers by selecting templates and providing API keys and credentials. The service handles the generation, deployment, and management of MCP servers, making it easy for developers to integrate AI capabilities into their applications.

## Features

- User-friendly web interface for creating MCP servers
- Documentation-driven MCP server generation
- LLM-powered code generation for custom APIs
- Secure API key management
- Multiple deployment options
- Monitoring and management tools

## Architecture

The platform uses a sophisticated architecture:

1. **Documentation Processing**:
   - Handles various documentation formats (OpenAPI, Markdown)
   - Extracts API structure and requirements
   - Uses Jina AI for comprehensive document understanding

2. **LLM Workflow**:
   - Planning LLM (GPT-4) analyzes docs and creates implementation plan
   - Coding LLM (GPT-3.5) generates high-quality MCP code
   - Validation ensures generated code meets requirements

3. **FastMCP Integration**:
   - Templates follow FastMCP best practices
   - Proper tool definition and implementation
   - Error handling and security built-in

## Project Structure

```
mcp-saas/
├── frontend/                 # React/Next.js frontend application
├── backend/                  # FastAPI backend application
│   ├── api/                  # API routes and controllers
│   │   ├── auth/             # Authentication endpoints
│   │   ├── servers/          # Server management endpoints
│   │   ├── templates/        # Template management endpoints
│   │   └── generators/       # LLM generation endpoints
│   ├── core/                 # Core application logic
│   │   ├── security/         # Authentication and security
│   │   ├── config/           # Configuration management
│   │   └── utils/            # Utility functions
│   ├── db/                   # Database models and connections
│   │   ├── models/           # SQLAlchemy models
│   │   └── migrations/       # Alembic migrations
│   ├── engine/               # Server generation engine
│   │   ├── generator/        # Code generation logic
│   │   │   ├── doc_processor.py  # Documentation processing
│   │   │   ├── llm_workflow.py   # LLM workflow
│   │   │   └── mcp_generator_service.py # Generator service
│   │   ├── validator/        # Validation logic
│   │   └── deployer/         # Deployment logic
│   └── templates/            # MCP server templates
│       ├── fastmcp_base/     # Base FastMCP template
│       └── generated/        # Generated MCP server templates
├── shared/                   # Shared code/types between frontend and backend
├── docs/                     # Documentation
└── deployment/               # Deployment configuration
```

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+
- API keys for OpenAI/OpenRouter and Jina AI
- PostgreSQL database (optional, SQLite for development)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/mcp-saas.git
   cd mcp-saas
   ```

2. Install backend dependencies:
   ```
   cd backend
   pip install -r requirements.txt
   ```

3. Install frontend dependencies:
   ```
   cd ../frontend
   npm install
   ```

4. Configure environment variables:
   ```
   cd ../backend
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```
   alembic upgrade head
   ```

### Running the Application

1. Start the backend:
   ```
   cd backend
   uvicorn main:app --reload
   ```

2. Start the frontend:
   ```
   cd frontend
   npm run dev
   ```

## API Documentation

Once the application is running, you can access the API documentation at `http://localhost:8000/docs`.

## License

MIT 