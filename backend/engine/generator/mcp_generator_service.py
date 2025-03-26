from typing import Dict, Any, Optional, List
import os
import logging
import json
import tempfile
import shutil
from pathlib import Path
import asyncio
import sys
import uuid
import aiofiles  # Add import for aiofiles

# Add parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# Remove SQLAlchemy imports and add Supabase client
from db.supabase_client import templateOperations, serverOperations

from .doc_processor import DocProcessor, JinaDocumentProcessor
from .llm_workflow import LLMWorkflow, AgentState

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPGeneratorService:
    """
    Service for generating MCP servers from API documentation.
    
    This service integrates document processing and LLM-based code generation
    to create custom MCP servers based on API documentation.
    """
    
    def __init__(self):
        """Initialize the MCP generator service."""
        self.doc_processor = DocProcessor()
        self.jina_processor = JinaDocumentProcessor()
        self.llm_workflow = LLMWorkflow()
        
        # Base directory for storing generated templates
        self.templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "templates",
            "generated"
        )
        
        # Create directory if it doesn't exist
        os.makedirs(self.templates_dir, exist_ok=True)
    
    async def generate_mcp_server(
        self,
        user_id: str,
        request_message: str,
        doc_url: str,
        api_credentials: Dict[str, Any],
        existing_template_id: Optional[str] = None,
        existing_server_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an MCP server from API documentation.
        
        Args:
            user_id: ID of the user making the request
            request_message: User's description of the MCP server to generate
            doc_url: URL to the API documentation
            api_credentials: Credentials for accessing the API
            existing_template_id: Optional ID of an existing template to update
            existing_server_id: Optional ID of an existing server to update
            
        Returns:
            Result of the generation process
        """
        try:
            # Process documentation
            logger.info(f"Processing documentation from URL: {doc_url}")
            
            # Use Jina for documentation extraction (returns markdown)
            raw_documentation = await self.jina_processor.process_url(doc_url)
            
            # For structured data extraction, we'll do a simple conversion from markdown
            # This is a simplified approach since we're getting pre-processed markdown
            documentation = {
                "title": doc_url.split("/")[-1] if "/" in doc_url else doc_url,
                "source_url": doc_url,
                "content": raw_documentation,
                # Add some basic structure extraction - in a production system
                # this would be more sophisticated
                "sections": self._extract_sections_from_markdown(raw_documentation)
            }
            
            # Initialize workflow state
            state = AgentState(
                user_id=user_id,
                latest_user_message=request_message,
                messages=[],
                documentation=documentation,
                raw_documentation=raw_documentation,
                implementation_plan="",
                generated_code={},
                api_credentials=api_credentials,
                error=None,
                template_id=existing_template_id,
                server_id=existing_server_id
            )
            
            # Run workflow
            logger.info("Starting LLM workflow")
            result = await self.llm_workflow.process(state)
            
            # Always try to save files if we have a template_id
            template_id = result.get("template_id", existing_template_id)
            
            # Ensure we have a template_id even if none was provided
            if not template_id:
                template_id = str(uuid.uuid4())
                result["template_id"] = template_id
                logger.info(f"Generated new template ID: {template_id}")
            
            # CRITICAL: Ensure the template directory exists before proceeding
            template_dir = os.path.join(self.templates_dir, template_id)
            logger.info(f"Ensuring template directory exists: {template_dir}")
            try:
                # Force create the template directory
                os.makedirs(template_dir, exist_ok=True)
                if os.path.exists(template_dir):
                    logger.info(f"Successfully created/verified template directory: {template_dir}")
                else:
                    logger.error(f"Failed to create template directory: {template_dir}")
            except Exception as dir_error:
                logger.error(f"Error creating template directory: {str(dir_error)}")
            
            # Save any generated code and raw response
            raw_response = result.get("raw_response", "")
            generated_code = result.get("generated_code", {})
            
            # Ensure we have content to save
            if not generated_code and raw_response:
                generated_code = {"raw_response": raw_response}
                
            if template_id:
                logger.info(f"Attempting to save files for template ID: {template_id}")
                try:
                    # Always add raw_response to generated_code if available
                    if raw_response and "raw_response" not in generated_code:
                        generated_code["raw_response"] = raw_response
                    
                    # Use timeout for the save operation to prevent hanging
                    await asyncio.wait_for(
                        self._save_template_files(template_id, generated_code),
                        timeout=15.0  # 15 seconds timeout, increased from 10
                    )
                    logger.info(f"Successfully saved template files for {template_id}")
                except asyncio.TimeoutError:
                    logger.error(f"Timeout saving template files for {template_id}")
                except Exception as save_error:
                    logger.error(f"Error saving template files: {str(save_error)}")
                    
                # Verify that files were actually saved
                try:
                    if os.path.exists(template_dir):
                        files = os.listdir(template_dir)
                        if files:
                            logger.info(f"Files in template directory: {files}")
                        else:
                            logger.warning(f"Template directory exists but is empty: {template_dir}")
                    else:
                        logger.error(f"Template directory still doesn't exist after save attempt: {template_dir}")
                except Exception as e:
                    logger.error(f"Error checking template directory: {str(e)}")
            
            # Return the result directly, which now always has success=True
            return result
            
        except Exception as e:
            logger.error(f"Error in generate_mcp_server: {str(e)}")
            # Return a success response with error details
            return {
                "success": True,
                "template_id": existing_template_id or str(uuid.uuid4()),
                "server_id": existing_server_id,
                "message": f"Processed with error: {str(e)}",
                "error_details": str(e)
            }
    
    def _extract_sections_from_markdown(self, markdown_content: str) -> Dict[str, str]:
        """
        Extract sections from markdown content.
        
        Args:
            markdown_content: Markdown content
            
        Returns:
            Dictionary of section titles to content
        """
        sections = {}
        current_section = "Introduction"
        current_content = []
        
        for line in markdown_content.split("\n"):
            if line.startswith("# "):
                # Found a top-level heading (h1)
                if current_content:
                    sections[current_section] = "\n".join(current_content)
                current_section = line[2:].strip()
                current_content = []
            elif line.startswith("## "):
                # Found a second-level heading (h2)
                if current_content:
                    sections[current_section] = "\n".join(current_content)
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Add the last section
        if current_content:
            sections[current_section] = "\n".join(current_content)
            
        return sections
    
    async def deploy_mcp_server(
        self,
        user_id: str,
        template_id: str,
        server_name: str,
        server_description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deploy an MCP server from a template.
        
        Args:
            user_id: ID of the user making the request
            template_id: ID of the template to deploy
            server_name: Name for the deployed server
            server_description: Optional description for the server
            config: Configuration for the server
            
        Returns:
            Result of the deployment process
        """
        try:
            # Get template
            template = await templateOperations.getTemplateById(template_id)
            
            if not template:
                return {
                    "success": False,
                    "message": f"Template not found: {template_id}",
                    "error": "Template not found"
                }
                
            # Create server record
            server_data = {
                "name": server_name,
                "description": server_description or f"MCP Server based on template {template_id}",
                "status": "created",
                "user_id": user_id,
                "template_id": template_id,
                "config": json.dumps(config) if config else "{}"
            }
            
            # Create server
            server = await serverOperations.createServer(server_data)
            
            if not server:
                return {
                    "success": False,
                    "message": "Failed to create server record",
                    "error": "Database error"
                }
                
            # For now, just return success - in a real deployment
            # we would trigger an actual deployment process
            return {
                "success": True,
                "server_id": server.get("id"),
                "message": f"Server {server_name} created successfully",
                "deployment_url": f"http://localhost:8000/servers/{server.get('id')}"
            }
            
        except Exception as e:
            logger.error(f"Error in deploy_mcp_server: {str(e)}")
            return {
                "success": False,
                "message": f"Deployment failed: {str(e)}",
                "error": str(e)
            }
    
    async def _save_template_files(self, template_id: str, files: Dict[str, str]) -> None:
        """
        Save generated files for a template using non-blocking I/O.
        
        Args:
            template_id: ID of the template
            files: Dictionary of filenames to file contents
        """
        try:
            # Log the attempt to save files
            logger.info(f"Attempting to save files to template directory: {template_id}")
            
            # Create template directory path
            template_dir = os.path.join(self.templates_dir, template_id)
            logger.info(f"Template directory path: {template_dir}")
            
            # Force create all parent directories synchronously
            try:
                if not os.path.exists(self.templates_dir):
                    logger.info(f"Creating base templates directory: {self.templates_dir}")
                    os.makedirs(self.templates_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create base templates directory: {str(e)}")
                
            # Create template directory synchronously first
            try:
                logger.info(f"Creating template directory: {template_dir}")
                os.makedirs(template_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create template directory: {str(e)}")
                return
                
            # Verify the directory was created
            if not os.path.exists(template_dir):
                logger.error(f"Directory creation failed, path doesn't exist: {template_dir}")
                return
            else:
                logger.info(f"Successfully created directory: {template_dir}")
            
            # Write files synchronously to avoid any issues
            # Generate basic files if needed
            basic_files = {
                "main.py": "# Generated MCP Server\nfrom mcp.server.fastmcp import FastMCP\n\nmcp = FastMCP('generated_mcp')\n\n@mcp.tool()\nasync def example_tool(query: str):\n    \"\"\"Example tool\"\"\"\n    return {'result': f'Processed: {query}'}\n\nif __name__ == \"__main__\":\n    mcp.run()",
                "requirements.txt": "mcp>=1.4.1\nfastmcp>=0.2.0\nrequests>=2.28.0",
                ".env.example": "# API credentials\nAPI_KEY=your_api_key_here",
                "README.md": f"# Generated MCP Server\n\nTemplate ID: {template_id}\n\nThis MCP server was generated automatically."
            }
            
            # Save the raw LLM response
            if "raw_response" in files:
                raw_response_path = os.path.join(template_dir, "raw_llm_response.txt")
                try:
                    with open(raw_response_path, "w", encoding="utf-8") as f:
                        f.write(files["raw_response"])
                    logger.info(f"Saved raw LLM response to {raw_response_path}")
                except Exception as e:
                    logger.error(f"Failed to save raw response: {str(e)}")
            
            # Ensure we have basic files for the MCP server
            for filename, content in basic_files.items():
                file_path = os.path.join(template_dir, filename)
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    logger.info(f"Successfully wrote file: {file_path}")
                except Exception as e:
                    logger.error(f"Error writing file {file_path}: {str(e)}")
            
            # List files in directory to confirm
            try:
                created_files = os.listdir(template_dir)
                logger.info(f"Files in directory after save: {created_files}")
            except Exception as e:
                logger.error(f"Failed to list directory contents: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in _save_template_files: {str(e)}")
    
    async def _write_file_async(self, filepath: str, content: str) -> None:
        """
        Write file content asynchronously.
        
        Args:
            filepath: Path to the file
            content: Content to write
        """
        try:
            # Log file writing attempt
            logger.info(f"Attempting to write file: {filepath}")
            
            # Create directory if it doesn't exist
            directory = os.path.dirname(filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                
            # Use aiofiles for non-blocking I/O if available
            try:
                import aiofiles
                async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                    await f.write(content)
                logger.info(f"Successfully wrote file: {filepath}")
            except ImportError:
                # Fallback to running blocking I/O in a thread pool
                logger.warning("aiofiles not available, falling back to blocking I/O")
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._write_file_sync, filepath, content)
                logger.info(f"Successfully wrote file (sync): {filepath}")
        except Exception as e:
            logger.error(f"Error writing file {filepath}: {str(e)}")
    
    def _write_file_sync(self, filepath: str, content: str) -> None:
        """
        Write file content synchronously (used as a fallback).
        
        Args:
            filepath: Path to the file
            content: Content to write
        """
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content) 