from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
import uuid

# Import generator service
from engine.generator.mcp_generator_service import MCPGeneratorService
from db.supabase_client import supabase, current_auth_user_id, serverOperations

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Initialize generator service
generator_service = MCPGeneratorService()

# Request models
class ApiCredentials(BaseModel):
    api_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class GenerateRequest(BaseModel):
    """Request model for generating an MCP server."""
    doc_url: str = Field(..., description="URL to the API documentation")
    request_message: str = Field(..., description="User request for the MCP server")
    api_credentials: Optional[ApiCredentials] = Field(default=None, description="API credentials for authentication")
    existing_template_id: Optional[str] = Field(default=None, description="Existing template ID to use")
    existing_server_id: Optional[str] = Field(default=None, description="Existing server ID to update")

class DeployRequest(BaseModel):
    """Request model for deploying an MCP server."""
    template_id: str = Field(..., description="ID of the template to deploy")
    server_name: str = Field(..., description="Name for the deployed server")
    server_description: Optional[str] = Field(None, description="Description for the server")
    config: Dict[str, Any] = Field(default_factory=dict, description="Configuration for the server")

# Response models
class GenerateResponse(BaseModel):
    """Response model for generation requests."""
    success: bool = Field(..., description="Whether the generation was successful")
    message: str = Field(..., description="Human-readable message about the result")
    template_id: Optional[str] = Field(default=None, description="ID of the generated/updated template")
    server_id: Optional[str] = Field(default=None, description="ID of the generated/updated server")
    error: Optional[str] = Field(default=None, description="Error message, if any")

class DeployResponse(BaseModel):
    """Response model for deployment requests."""
    success: bool = Field(..., description="Whether the operation was successful")
    server_id: Optional[str] = Field(None, description="ID of the deployed server")
    deployment_url: Optional[str] = Field(None, description="URL for accessing the deployed server")
    message: str = Field(..., description="Status message")
    error: Optional[str] = Field(None, description="Error message if any")

async def get_authenticated_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Get the authenticated user's ID from the token, or return a default ID."""
    try:
        # If we already have a user ID from the global state, use it
        if current_auth_user_id:
            logger.info(f"Using authenticated user ID from global state: {current_auth_user_id}")
            return current_auth_user_id
        
        # Try to get user from token
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            
            try:
                # For Supabase, we need to call get_user directly without setting session
                # This works with just the access token
                user_response = supabase.auth.get_user(token)
                
                if user_response and user_response.user:
                    logger.info(f"Authenticated user from token: {user_response.user.id}")
                    return user_response.user.id
            except Exception as e:
                logger.error(f"Error getting user from token: {str(e)}")
        
        # If we couldn't get a valid user ID, return a default
        default_id = str(uuid.uuid4())
        logger.warning(f"No authenticated user found. Using generated ID: {default_id}")
        return default_id
    except Exception as e:
        logger.error(f"Error in get_authenticated_user_id: {str(e)}")
        default_id = str(uuid.uuid4())
        logger.warning(f"Exception occurred. Using generated ID: {default_id}")
        return default_id

@router.post("/generate", response_model=GenerateResponse)
async def generate_mcp_server_route(request: GenerateRequest, user_id: str = Depends(get_authenticated_user_id)):
    """Generate a new MCP server from API documentation."""
    try:
        # Log generation request
        logger.info(f"Generate request from user {user_id} for doc URL: {request.doc_url}")
        
        # Call generator service
        result = await generator_service.generate_mcp_server(
            user_id=user_id,
            request_message=request.request_message,
            doc_url=request.doc_url,
            api_credentials=request.api_credentials.dict() if request.api_credentials else {},
            existing_template_id=request.existing_template_id,
            existing_server_id=request.existing_server_id
        )
        
        # Return the result directly, as we're always returning a valid structure now
        return result
        
    except Exception as e:
        # Log the error
        logger.error(f"Error generating MCP server: {str(e)}")
        
        # Return a response that indicates an error but has a success status
        # This allows the client to continue processing
        return {
            "success": True,  # Success means the request was processed
            "message": f"Processed with error: {str(e)}",
            "template_id": None,
            "server_id": None,
            "error": str(e)
        }

@router.post("/deploy", response_model=DeployResponse, status_code=status.HTTP_200_OK)
async def deploy_mcp_server(
    request: DeployRequest,
    user_id: str = Depends(get_authenticated_user_id)
):
    """
    Deploy an MCP server from a template.
    
    This endpoint deploys a previously generated MCP server template.
    """
    try:
        logger.info(f"Deploy request from user {user_id} for template ID: {request.template_id}")
        
        result = await generator_service.deploy_mcp_server(
            user_id=user_id,
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

@router.get("/list-templates", response_model=List[Dict[str, Any]])
async def list_templates(user_id: str = Depends(get_authenticated_user_id)):
    """List all templates."""
    try:
        # Import Supabase operations
        from db.supabase_client import templateOperations
        
        # Get all templates
        templates = await templateOperations.getAllTemplates()
        return templates
    except Exception as e:
        # Log the error
        logger.error(f"Error listing templates: {str(e)}")
        
        # Return an empty list rather than error
        return []

@router.get("/list-servers", response_model=List[Dict[str, Any]])
async def list_servers(user_id: str = Depends(get_authenticated_user_id)):
    """List all servers for the current user."""
    try:
        # Get all servers for the current user
        response = supabase.table('mcp_servers').select('*').eq('user_id', user_id).execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error getting servers: {response.error}")
            return []
        return response.data or []
    except Exception as e:
        # Log the error
        logger.error(f"Error listing servers: {str(e)}")
        
        # Return an empty list rather than error
        return [] 