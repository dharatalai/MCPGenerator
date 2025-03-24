from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
import sys
import os

# Add parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from db.database import get_db
from db.models.user import User
from engine.generator.mcp_generator_service import MCPGeneratorService
from core.security.auth import get_current_active_user

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Initialize generator service
generator_service = MCPGeneratorService()

# Request models
class GenerateRequest(BaseModel):
    """Request model for generating an MCP server."""
    doc_url: str = Field(..., description="URL to the API documentation")
    request_message: str = Field(..., description="Description of the MCP server to generate")
    api_credentials: Dict[str, Any] = Field(default_factory=dict, description="Credentials for accessing the API")
    template_id: Optional[str] = Field(None, description="Optional ID of an existing template to update")
    server_id: Optional[str] = Field(None, description="Optional ID of an existing server to update")

class DeployRequest(BaseModel):
    """Request model for deploying an MCP server."""
    template_id: str = Field(..., description="ID of the template to deploy")
    server_name: str = Field(..., description="Name for the deployed server")
    server_description: Optional[str] = Field(None, description="Description for the server")
    config: Dict[str, Any] = Field(default_factory=dict, description="Configuration for the server")

# Response models
class GenerateResponse(BaseModel):
    """Response model for generation requests."""
    success: bool = Field(..., description="Whether the operation was successful")
    template_id: Optional[str] = Field(None, description="ID of the generated template")
    server_id: Optional[str] = Field(None, description="ID of the generated server")
    message: str = Field(..., description="Status message")
    error: Optional[str] = Field(None, description="Error message if any")

class DeployResponse(BaseModel):
    """Response model for deployment requests."""
    success: bool = Field(..., description="Whether the operation was successful")
    server_id: Optional[str] = Field(None, description="ID of the deployed server")
    deployment_url: Optional[str] = Field(None, description="URL for accessing the deployed server")
    message: str = Field(..., description="Status message")
    error: Optional[str] = Field(None, description="Error message if any")

@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_200_OK)
async def generate_mcp_server(
    request: GenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate an MCP server from API documentation.
    
    This endpoint processes API documentation and generates a custom MCP server template.
    """
    try:
        logger.info(f"Generate request from user {current_user.id} for doc URL: {request.doc_url}")
        
        result = await generator_service.generate_mcp_server(
            user_id=current_user.id,
            request_message=request.request_message,
            doc_url=request.doc_url,
            api_credentials=request.api_credentials,
            existing_template_id=request.template_id,
            existing_server_id=request.server_id
        )
        
        return result
    except Exception as e:
        logger.error(f"Failed to generate MCP server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate MCP server: {str(e)}"
        )

@router.post("/deploy", response_model=DeployResponse, status_code=status.HTTP_200_OK)
async def deploy_mcp_server(
    request: DeployRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Deploy an MCP server from a template.
    
    This endpoint deploys a previously generated MCP server template.
    """
    try:
        logger.info(f"Deploy request from user {current_user.id} for template ID: {request.template_id}")
        
        result = await generator_service.deploy_mcp_server(
            user_id=current_user.id,
            template_id=request.template_id,
            server_name=request.server_name,
            server_description=request.server_description,
            config=request.config
        )
        
        return result
    except Exception as e:
        logger.error(f"Failed to deploy MCP server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy MCP server: {str(e)}"
        ) 