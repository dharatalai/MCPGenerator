# Supabase Setup Instructions

This document outlines how to set up Supabase for the MCP SaaS backend.

## 1. Create a Supabase Project

1. Sign up for Supabase at [https://supabase.com](https://supabase.com)
2. Create a new project with a name of your choice
3. Note your project URL and API keys (found in Project Settings > API)

## 2. Create Database Tables

1. Navigate to the SQL Editor in your Supabase dashboard
2. Copy and paste the SQL from `db/supabase_schema.sql` 
3. Run the SQL to create the necessary tables and policies

## 3. Configure Environment Variables

1. Create a `.env` file in the backend directory (copy from `.env.example`)
2. Add your Supabase credentials:
   ```
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_ANON_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_KEY=your-supabase-service-key
   ```

3. Update your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your-openrouter-api-key
   ```

## 4. Install Dependencies

```bash
pip install -r requirements.txt
pip install email-validator  # Required for Pydantic email validation
```

## 5. Run the Application

```bash
uvicorn main:app --reload --port 8000
```

## 6. Testing Supabase Connection

After starting the server, visit `http://localhost:8000/health` to check if the Supabase connection is working properly.

## 7. Authentication

This backend uses Supabase Authentication for user management:

1. Creating a new user:
   ```bash
   curl -X POST http://localhost:8000/auth/signup \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.com", "password":"password123", "full_name":"Test User"}'
   ```

2. Signing in:
   ```bash
   curl -X POST http://localhost:8000/auth/signin \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.com", "password":"password123"}'
   ```

3. Using the `generate_mcp.py` script with authentication:
   ```bash
   python generate_mcp.py --email=user@example.com --password=password123 --doc-url=https://example.com/api-docs
   ```

4. The authentication flow handles:
   - Auto sign-up if a user doesn't exist
   - Setting an authentication token for API requests
   - Associating templates and servers with the authenticated user
   - Respecting Row Level Security policies in Supabase

## 8. Row Level Security

The SQL schema includes Row Level Security (RLS) policies to ensure data is properly protected:

- Templates are accessible publicly only if marked as public
- Users can only access their own templates and servers
- Authentication is required for most operations

When using the API without authentication, a temporary UUID is generated as the user ID, but this won't have RLS permissions to save to Supabase. 