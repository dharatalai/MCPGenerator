import os
import uuid
import logging
import asyncio
import json
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("Missing Supabase credentials. Please check your .env file.")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Create admin client with service key for admin operations
supabase_admin = None
if SUPABASE_SERVICE_KEY:
    supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Current authenticated user ID (set during sign-in)
current_auth_user_id = None

# Authentication methods
class AuthOperations:
    async def sign_up(self, email: str, password: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sign up a new user.
        
        Args:
            email: User's email
            password: User's password
            metadata: Optional metadata
            
        Returns:
            Sign-up response
        """
        try:
            metadata = metadata or {}
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": metadata
                }
            })
            
            if response.user:
                logger.info(f"User signed up: {response.user.id}")
                global current_auth_user_id
                current_auth_user_id = response.user.id
            
            return {
                "user_id": response.user.id if response.user else None,
                "email": email,
                "session": response.session.access_token if response.session else None
            }
        except Exception as e:
            logger.error(f"Sign-up error: {str(e)}")
            raise
    
    async def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Sign in an existing user.
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            Sign-in response
        """
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                logger.info(f"User signed in: {response.user.id}")
                global current_auth_user_id
                current_auth_user_id = response.user.id
            
            return {
                "user_id": response.user.id if response.user else None,
                "email": email,
                "session": response.session.access_token if response.session else None
            }
        except Exception as e:
            logger.error(f"Sign-in error: {str(e)}")
            raise
    
    async def get_current_user(self) -> Dict[str, Any]:
        """
        Get the currently authenticated user.
        
        Returns:
            Current user information
        """
        try:
            response = supabase.auth.get_user()
            
            if response.user:
                global current_auth_user_id
                current_auth_user_id = response.user.id
                
                return {
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "metadata": response.user.user_metadata
                }
            return None
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            return None
    
    async def sign_out(self) -> bool:
        """
        Sign out the current user.
        
        Returns:
            True if successful
        """
        try:
            supabase.auth.sign_out()
            global current_auth_user_id
            current_auth_user_id = None
            return True
        except Exception as e:
            logger.error(f"Sign-out error: {str(e)}")
            return False

# Helper to validate UUID
def validate_uuid(id_value):
    """Validate and format a UUID, returning a default if invalid."""
    if not id_value:
        # Return a default UUID if None
        return str(uuid.uuid4())
    
    try:
        # Try to parse as UUID
        return str(uuid.UUID(str(id_value)))
    except (ValueError, AttributeError, TypeError):
        logger.warning(f"Invalid UUID: {id_value}. Using default.")
        return str(uuid.uuid4())

# Template table operations
class TemplateOperations:
    async def createTemplate(self, template_data):
        # Ensure created_by is a valid UUID - use the authenticated user if available
        if "created_by" in template_data:
            template_data["created_by"] = validate_uuid(template_data["created_by"])
        elif current_auth_user_id:
            template_data["created_by"] = current_auth_user_id
            logger.info(f"Using authenticated user ID: {current_auth_user_id}")
        
        logger.info(f"Creating template with validated data: {template_data}")
        
        try:
            # Use a timeout for the Supabase operation
            async def _do_insert():
                return supabase.table('templates').insert(template_data).execute()
            
            # Create task and run with timeout
            try:
                response = await asyncio.wait_for(_do_insert(), timeout=5.0)
                if hasattr(response, 'error') and response.error:
                    error_message = response.error
                    # Check for RLS violation
                    if "violates row-level security policy" in str(error_message):
                        logger.error(f"Row Level Security violation: {error_message}")
                        logger.error(f"This is likely because the user ID ({template_data.get('created_by')}) is not authenticated properly.")
                        logger.error(f"Make sure you're passing a valid authentication token and using a valid user ID.")
                    else:
                        logger.error(f"Supabase error: {error_message}")
                    
                    raise ValueError(f"Error creating template: {error_message}")
                
                logger.info(f"Template created successfully: {response.data[0]['id'] if response.data else None}")
                # Return object with proper id attribute
                if response.data and len(response.data) > 0:
                    template = response.data[0]
                    return type('Template', (), template)  # Convert dict to object with attributes
                return None
            except asyncio.TimeoutError:
                logger.error("Supabase template creation timed out after 5 seconds")
                # Return a mock template so the flow can continue
                mock_id = str(uuid.uuid4())
                mock_template = {
                    "id": mock_id,
                    "name": template_data.get("name", "Generated Template"),
                    "description": template_data.get("description", "Timeout occurred during template creation"),
                    "created_at": "",
                    "is_mock": True
                }
                logger.info(f"Created mock template with ID: {mock_id}")
                # Convert dict to object with attributes
                return type('Template', (), mock_template)
        except Exception as e:
            logger.error(f"Error in createTemplate: {str(e)}")
            # Return a mock template in case of error
            mock_id = str(uuid.uuid4())
            mock_template = {
                "id": mock_id,
                "name": template_data.get("name", "Generated Template"),
                "description": template_data.get("description", "Error during template creation"),
                "created_at": "",
                "is_mock": True
            }
            logger.info(f"Using mock template due to error: {mock_id}")
            # Convert dict to object with attributes
            return type('Template', (), mock_template)
    
    async def getTemplateById(self, id):
        id = validate_uuid(id)
        response = supabase.table('templates').select('*').eq('id', id).execute()
        if hasattr(response, 'error') and response.error:
            raise ValueError(f"Error getting template: {response.error}")
        return response.data[0] if response.data else None

    async def getAllTemplates(self):
        response = supabase.table('templates').select('*').execute()
        if hasattr(response, 'error') and response.error:
            raise ValueError(f"Error getting templates: {response.error}")
        return response.data

# Server table operations
class ServerOperations:
    async def createServer(self, server_data):
        # Ensure user_id is a valid UUID - use the authenticated user if available
        if "user_id" in server_data:
            server_data["user_id"] = validate_uuid(server_data["user_id"])
        elif current_auth_user_id:
            server_data["user_id"] = current_auth_user_id
            logger.info(f"Using authenticated user ID: {current_auth_user_id}")
        
        # Ensure template_id is a valid UUID if provided
        if "template_id" in server_data and server_data["template_id"]:
            server_data["template_id"] = validate_uuid(server_data["template_id"])
        
        response = supabase.table('mcp_servers').insert(server_data).execute()
        if hasattr(response, 'error') and response.error:
            raise ValueError(f"Error creating server: {response.error}")
        return response.data[0] if response.data else None
    
    async def getServerById(self, id):
        id = validate_uuid(id)
        response = supabase.table('mcp_servers').select('*').eq('id', id).execute()
        if hasattr(response, 'error') and response.error:
            raise ValueError(f"Error getting server: {response.error}")
        return response.data[0] if response.data else None
    
    async def updateServer(self, id, updates):
        id = validate_uuid(id)
        response = supabase.table('mcp_servers').update(updates).eq('id', id).execute()
        if hasattr(response, 'error') and response.error:
            raise ValueError(f"Error updating server: {response.error}")
        return response.data[0] if response.data else None

# User operations
class UserOperations:
    async def getUserById(self, id):
        if not supabase_admin:
            raise ValueError("Service role key is required for admin operations")
        
        id = validate_uuid(id)
        user = supabase_admin.auth.admin.get_user_by_id(id)
        return user
    
    async def createUser(self, user_data):
        if not supabase_admin:
            raise ValueError("Service role key is required for admin operations")
        
        new_user = supabase_admin.auth.admin.create_user(user_data)
        return new_user

# Chat session operations
class ChatSessionOperations:
    async def createChatSession(self, session_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new chat session.
        
        Args:
            session_data: Dictionary with chat session data
            
        Returns:
            Created chat session or None if error
        """
        try:
            # Generate a unique ID for the chat session if not provided
            if "id" not in session_data:
                session_data["id"] = str(uuid.uuid4())
            
            # Ensure required fields exist
            if "user_id" not in session_data:
                logger.error("Missing required field 'user_id' in chat session data")
                return None
                
            if "title" not in session_data:
                session_data["title"] = "MCP Generation Session"
                
            if "messages" not in session_data and not isinstance(session_data["messages"], str):
                session_data["messages"] = json.dumps([])
            
            # Insert data using admin client with service role
            if not supabase_admin:
                logger.error("Service role client not initialized. Check SUPABASE_SERVICE_KEY.")
                return None
                
            async def _do_insert():
                return supabase_admin.table('chat_sessions').insert(session_data).execute()
                
            response = await asyncio.wait_for(_do_insert(), timeout=5.0)
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error creating chat session: {response.error}")
                return None
                
            logger.info(f"Chat session created successfully: {response.data[0]['id'] if response.data else None}")
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Error in createChatSession: {str(e)}")
            return None
    
    async def saveChatSessionResponse(self, session_id: str, raw_response: str) -> bool:
        """
        Save raw response to an existing chat session.
        
        Args:
            session_id: ID of the chat session
            raw_response: Raw LLM response to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if admin client is available
            if not supabase_admin:
                logger.error("Service role client not initialized. Check SUPABASE_SERVICE_KEY.")
                return False
                
            # Update the chat session with raw response
            async def _do_update():
                return supabase_admin.table('chat_sessions').update({
                    "raw_response": raw_response,
                    "has_response": True,
                    "updated_at": "now()"
                }).eq("id", session_id).execute()
                
            response = await asyncio.wait_for(_do_update(), timeout=5.0)
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error updating chat session with response: {response.error}")
                return False
                
            logger.info(f"Chat session response saved successfully for ID: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in saveChatSessionResponse: {str(e)}")
            return False
    
    async def getChatSession(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a chat session by ID.
        
        Args:
            session_id: ID of the chat session
            
        Returns:
            Chat session data or None if not found
        """
        try:
            # Check if admin client is available
            if not supabase_admin:
                logger.error("Service role client not initialized. Check SUPABASE_SERVICE_KEY.")
                return None
                
            response = supabase_admin.table('chat_sessions').select('*').eq('id', session_id).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error getting chat session: {response.error}")
                return None
                
            return response.data[0] if response.data and len(response.data) > 0 else None
            
        except Exception as e:
            logger.error(f"Error in getChatSession: {str(e)}")
            return None

# Initialize operations
authOperations = AuthOperations()
templateOperations = TemplateOperations()
serverOperations = ServerOperations()
chatSessionOperations = ChatSessionOperations() 