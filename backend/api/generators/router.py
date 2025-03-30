from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
import uuid
import os
import json

# Import generator service
from engine.generator.mcp_generator_service import MCPGeneratorService
from db.supabase_client import supabase, current_auth_user_id, serverOperations
from engine.generator.llm_workflow import ProgressTracker

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Initialize generator service
generator_service = MCPGeneratorService()

# Initialize progress tracker
progress_tracker = ProgressTracker()

# Request models
class ApiCredentials(BaseModel):
    api_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class GenerateRequest(BaseModel):
    """Request model for generating an MCP server."""
    doc_url: List[str] = Field(..., description="URLs to the API documentation")
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
    chat_session_id: Optional[str] = Field(default=None, description="ID of the chat session with the raw response")

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

@router.get("/template-files/{template_id}", response_model=List[Dict[str, Any]])
async def get_template_files(template_id: str):
    """Get all files for a template."""
    try:
        # Build the path to the template directory
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "engine", "templates", "generated", template_id
        )
        
        # Check if directory exists
        if not os.path.exists(template_dir):
            logger.warning(f"Template directory not found: {template_dir}")
            
            # Double check if old path exists (for backward compatibility)
            old_template_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "templates", "generated", template_id
            )
            
            if os.path.exists(old_template_dir):
                logger.info(f"Found template in old location: {old_template_dir}")
                template_dir = old_template_dir
            else:
                return []
        
        result = []
        
        # Walk the directory and get all files and directories
        for root, dirs, files in os.walk(template_dir):
            # Add directories
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                rel_path = os.path.relpath(dir_path, template_dir)
                result.append({
                    "name": dir_name,
                    "path": rel_path,
                    "is_dir": True
                })
            
            # Add files
            for file_name in files:
                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, template_dir)
                result.append({
                    "name": file_name,
                    "path": rel_path,
                    "is_dir": False
                })
        
        return result
    except Exception as e:
        logging.error(f"Error getting template files: {str(e)}")
        return []

@router.get("/file-content/{template_id}")
async def get_file_content(template_id: str, file_path: str):
    """Get content of a specific file."""
    try:
        # Build the full path to the file
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "engine", "templates", "generated", template_id
        )
        
        # If directory doesn't exist, check old location
        if not os.path.exists(template_dir):
            logger.warning(f"Template directory not found: {template_dir}")
            old_template_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "templates", "generated", template_id
            )
            
            if os.path.exists(old_template_dir):
                logger.info(f"Found template in old location: {old_template_dir}")
                template_dir = old_template_dir
        
        # Check if file_path is a complex object or a string
        actual_file_path = file_path
        try:
            # If it's passed as query parameters in complex form like file_path[name]=x&file_path[path]=y
            # this would come through as a JSON string in some frameworks
            file_obj = json.loads(file_path)
            if isinstance(file_obj, dict) and 'path' in file_obj:
                actual_file_path = file_obj['path']
                logger.info(f"Extracted file path from JSON object: {actual_file_path}")
        except (json.JSONDecodeError, TypeError):
            # If it's passed as separate query parameters like file_path.name=x
            # FastAPI will parse this as a string, so we need to handle both cases
            pass
            
        full_path = os.path.join(template_dir, actual_file_path)
        
        # Special case for raw_response.txt - always return it if it exists
        if actual_file_path.endswith("raw_response.txt") or "raw_response" in actual_file_path:
            raw_response_path = os.path.join(template_dir, "raw_response.txt")
            if os.path.exists(raw_response_path):
                logger.info(f"Directly serving raw_response.txt file")
                with open(raw_response_path, "r") as f:
                    content = f.read()
                return {"content": content}
        
        # Security check - make sure the file is actually within the template directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(template_dir)):
            logging.warning(f"Attempted to access file outside template directory: {full_path}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if file exists
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            logging.warning(f"File not found: {full_path}")
            raise HTTPException(status_code=404, detail="File not found")
        
        # Read file content
        try:
            with open(full_path, "r") as f:
                content = f.read()
            
            return {"content": content}
        except UnicodeDecodeError:
            # If it's a binary file, return an error
            logging.warning(f"Cannot read binary file: {full_path}")
            raise HTTPException(status_code=400, detail="Cannot read binary file")
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting file content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

@router.get("/generation-progress/{template_id}", response_model=Dict[str, Any])
async def get_generation_progress(template_id: str):
    """Get the progress of an ongoing generation process."""
    try:
        # Get progress from tracker
        progress = progress_tracker.get_progress(template_id)
        
        if not progress:
            # If no progress record exists, check if template exists in database
            try:
                template = await templateOperations.getTemplateById(template_id)
                
                if template:
                    # Template exists but no progress record, so generation is complete
                    return {
                        "status": "completed",
                        "progress": 100,
                        "message": "Generation completed",
                        "template_id": template_id,
                        "template_exists": True
                    }
                else:
                    # Template doesn't exist in database
                    # Check if files exist on disk as a fallback
                    template_dir = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "engine", "templates", "generated", template_id
                    )
                    
                    if os.path.exists(template_dir):
                        files = os.listdir(template_dir)
                        if files:
                            return {
                                "status": "completed",
                                "progress": 100,
                                "message": "Generation completed (files exist)",
                                "template_id": template_id,
                                "template_exists": False,
                                "files_exist": True,
                                "file_count": len(files)
                            }
            except Exception as e:
                logger.warning(f"Error checking template status: {str(e)}")
            
            # No progress record and no template exists
            return {
                "status": "not_found",
                "progress": 0,
                "message": "No generation process found with this ID",
                "template_id": template_id,
                "template_exists": False
            }
        
        # Return the progress data
        return {
            **progress,
            "template_id": template_id
        }
    except Exception as e:
        logger.error(f"Error getting generation progress: {str(e)}")
        return {
            "status": "error",
            "progress": 0,
            "message": f"Error retrieving progress: {str(e)}",
            "template_id": template_id,
            "error": str(e)
        }

@router.get("/raw-response/{template_id}")
async def get_raw_response(template_id: str):
    """Get the raw LLM response for a template."""
    try:
        # Build the path to the template directory
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "engine", "templates", "generated", template_id
        )
        
        # If directory doesn't exist, check old location
        if not os.path.exists(template_dir):
            logger.warning(f"Template directory not found: {template_dir}")
            old_template_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "templates", "generated", template_id
            )
            
            if os.path.exists(old_template_dir):
                logger.info(f"Found template in old location: {old_template_dir}")
                template_dir = old_template_dir
        
        # Check for raw_response.txt file
        raw_response_path = os.path.join(template_dir, "raw_response.txt")
        
        if os.path.exists(raw_response_path):
            try:
                with open(raw_response_path, "r") as f:
                    content = f.read()
                
                logger.info(f"Successfully read raw response file of {len(content)} chars")
                return {
                    "success": True,
                    "content": content,
                    "template_id": template_id
                }
            except Exception as read_error:
                logger.error(f"Error reading raw response file: {str(read_error)}")
                raise HTTPException(status_code=500, detail=f"Failed to read raw response: {str(read_error)}")
        else:
            logger.warning(f"Raw response file not found: {raw_response_path}")
            
            # Try to find any files that might contain the raw response
            debug_file_path = os.path.join(template_dir, "debug_raw_response.txt")
            if os.path.exists(debug_file_path):
                with open(debug_file_path, "r") as f:
                    content = f.read()
                logger.info(f"Found debug raw response file instead")
                return {
                    "success": True,
                    "content": content,
                    "template_id": template_id, 
                    "note": "Using debug_raw_response.txt instead of raw_response.txt"
                }
            
            # If no raw response file found, return 404
            raise HTTPException(status_code=404, detail="Raw response file not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting raw response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get raw response: {str(e)}")

@router.get("/chat-session/{session_id}")
async def get_chat_session(session_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Get a chat session by ID with its raw response."""
    try:
        # Import chat session operations
        from db.supabase_client import chatSessionOperations
        
        # Get the chat session
        chat_session = await chatSessionOperations.getChatSession(session_id)
        
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session not found: {session_id}"
            )
        
        # Check if the user has access to this chat session
        if chat_session.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this chat session"
            )
        
        return chat_session
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting chat session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting chat session: {str(e)}"
        ) 