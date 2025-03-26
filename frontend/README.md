# MCP Generator UI

A React-based user interface for the MCP Generator, allowing users to create MCP servers from API documentation.

## Features

- User authentication (login/register)
- Generate MCP servers from API documentation URLs
- View and manage your generated templates
- Browse and download generated code files
- Syntax highlighting for code files

## Setup

### Prerequisites

- Node.js 16+ and npm

### Installation

1. Clone the repository
2. Navigate to the frontend directory:
   ```
   cd frontend
   ```
3. Install dependencies:
   ```
   npm install
   ```

### Configuration

Create a `.env` file in the frontend directory with the following variables:

```
REACT_APP_API_URL=http://localhost:8000
```

Adjust the URL to match your backend server address.

## Development

To run the development server:

```
npm start
```

This will start the React development server at [http://localhost:3000](http://localhost:3000).

## Building for Production

To create a production build:

```
npm run build
```

This will create optimized files in the `build` directory that can be served by any static file server.

## Connecting to Backend

The frontend expects the backend API to be running at the URL specified in the `REACT_APP_API_URL` environment variable. Make sure the backend server is running before using the frontend.

## API Endpoints Used

The frontend interacts with the following backend endpoints:

- `/auth/signin` - User login
- `/auth/signup` - User registration
- `/generators/generate` - Generate MCP server
- `/generators/list-templates` - List user's templates
- `/generators/template-files/{templateId}` - Get files for a template
- `/generators/file-content/{templateId}` - Get content of a specific file
- `/health` - Check backend health

## Folder Structure

- `/src` - Source code
  - `/api` - API service functions
  - `/components` - Reusable UI components
  - `/pages` - Application pages
- `/public` - Static assets 