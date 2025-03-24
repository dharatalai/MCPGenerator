from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Import routers
from api.generators.router import router as generators_router
# from api.auth import router as auth_router
# from api.servers import router as servers_router
# from api.templates import router as templates_router

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="MCP SaaS API",
    description="API for creating and managing MCP servers",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to MCP SaaS API"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include routers
app.include_router(generators_router, prefix="/generators", tags=["MCP Generators"])
# app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# app.include_router(servers_router, prefix="/servers", tags=["MCP Servers"])
# app.include_router(templates_router, prefix="/templates", tags=["Server Templates"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 