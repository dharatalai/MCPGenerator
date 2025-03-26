from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Request model
class TestGenerateRequest(BaseModel):
    """Test request model for generating an MCP server."""
    doc_url: str = Field(..., description="URL to the API documentation")
    request_message: str = Field(..., description="Description of the MCP server to generate")
    api_credentials: Dict[str, Any] = Field(default_factory=dict, description="Credentials for accessing the API")

# Response model
class TestGenerateResponse(BaseModel):
    """Test response model for generation requests."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")

@router.post("/generate", response_model=TestGenerateResponse, status_code=status.HTTP_200_OK)
async def test_generate_mcp_server(request: TestGenerateRequest):
    """
    Test endpoint for MCP server generation (no authentication required).
    """
    try:
        logger.info(f"Test generate request for doc URL: {request.doc_url}")
        
        # This is just a test endpoint that always returns success
        return {
            "success": True,
            "message": f"Successfully received request for {request.doc_url}. This is a test endpoint that doesn't perform actual generation."
        }
    except Exception as e:
        logger.error(f"Test endpoint error: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        } 