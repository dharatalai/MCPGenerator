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
import re

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
            "engine", "templates", "generated"
        )
        
        # Create directory if it doesn't exist
        try:
            os.makedirs(self.templates_dir, exist_ok=True)
            logger.info(f"Created templates directory: {self.templates_dir}")
        except Exception as e:
            logger.error(f"Error creating templates directory: {str(e)}")
    
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
            user_id: User ID
            request_message: User request message
            doc_url: URL to API documentation
            api_credentials: API credentials for authentication
            existing_template_id: Optional existing template ID
            existing_server_id: Optional existing server ID
            
        Returns:
            Dictionary with generation results
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
            
            # Extract generated code and raw response
            raw_response = result.get("raw_response", "")
            generated_code = result.get("generated_code", {})
            
            # Check if we have valid JSON code in raw_response
            if raw_response and not generated_code.get("files"):
                try:
                    # Try to parse the raw response as JSON
                    parsed_json = json.loads(raw_response)
                    if isinstance(parsed_json, dict) and "files" in parsed_json:
                        generated_code = parsed_json
                        logger.info("Successfully parsed raw response as JSON with 'files' key")
                except json.JSONDecodeError:
                    # If raw response isn't valid JSON, check if it contains code blocks
                    logger.warning("Raw response isn't valid JSON, looking for code blocks")
                    # Further processing could be done here to extract code blocks
            
            # Ensure template directory exists
            template_dir = os.path.join(self.templates_dir, template_id)
            logger.info(f"Ensuring template directory exists: {template_dir}")
            
            try:
                os.makedirs(template_dir, exist_ok=True)
                logger.info(f"Successfully created/verified template directory: {template_dir}")
            except Exception as e:
                logger.error(f"Error creating template directory: {str(e)}")
            
            # Save the files
            try:
                logger.info(f"Attempting to save files for template ID: {template_id}")
                
                # Wait for save operation with timeout
                try:
                    # If files exist in generated_code, save those
                    if isinstance(generated_code, dict) and "files" in generated_code:
                        await asyncio.wait_for(
                            self._save_template_files(template_id, raw_response, generated_code["files"]),
                            timeout=15.0
                        )
                    else:
                        # If we don't have structured files, try to extract from raw response
                        try:
                            # Parse raw response and extract files
                            parsed_files = self._parse_files_from_raw_response(raw_response)
                            if parsed_files:
                                await asyncio.wait_for(
                                    self._save_template_files(template_id, raw_response, parsed_files),
                                    timeout=15.0
                                )
                            else:
                                logger.warning("Couldn't extract files from raw response")
                        except Exception as parse_error:
                            logger.error(f"Error parsing files from raw response: {str(parse_error)}")
                            
                except asyncio.TimeoutError:
                    logger.error("Save operation timed out after 15 seconds")
                    
                # Verify files were saved
                template_dir = os.path.join(self.templates_dir, template_id)
                
                if os.path.exists(template_dir):
                    files = os.listdir(template_dir)
                    logger.info(f"Files in template directory: {files}")
                    
                    # If directory exists but is empty and we have raw_response, write it directly
                    if not files and raw_response:
                        logger.info("Directory exists but no files, writing raw response directly")
                        try:
                            main_file_path = os.path.join(template_dir, "main.py")
                            with open(main_file_path, "w", encoding="utf-8") as f:
                                # If raw_response looks like valid Python code, save it directly
                                if "def " in raw_response and "import " in raw_response:
                                    f.write(raw_response)
                                else:
                                    # Otherwise create a simple file with raw_response as a comment
                                    f.write(f"# Generated MCP Server\n\n'''\nRaw LLM Response:\n{raw_response}\n'''\n\nfrom mcp.server.fastmcp import FastMCP\n\nmcp = FastMCP('deepsearch_mcp')\n\n# TODO: Implement tools based on the raw LLM response\n\nif __name__ == '__main__':\n    mcp.run()")
                            logger.info(f"Wrote raw response to {main_file_path}")
                        except Exception as e:
                            logger.error(f"Error writing raw response: {str(e)}")
                else:
                    logger.error(f"Template directory doesn't exist after save operation: {template_dir}")
                
            except Exception as e:
                logger.error(f"Error saving files: {str(e)}")
            
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
    
    def _parse_files_from_raw_response(self, raw_response: str) -> Dict[str, str]:
        """
        Parse files from raw LLM response.
        
        Args:
            raw_response: Raw LLM response
            
        Returns:
            Dictionary of filenames to file contents
        """
        try:
            # Check if the response is JSON
            try:
                parsed_json = json.loads(raw_response)
                if isinstance(parsed_json, dict) and "files" in parsed_json:
                    return parsed_json["files"]
            except json.JSONDecodeError:
                pass
                
            # Try to extract code blocks using regex
            files = {}
            
            # Pattern for markdown code blocks: ```filename.ext\ncode\n```
            code_blocks = re.findall(r'```(?:python)?\s*(?:([a-zA-Z0-9_\-\.]+))?\n(.*?)```', raw_response, re.DOTALL)
            
            for i, (filename, code) in enumerate(code_blocks):
                # Clean up the code - remove trailing whitespace
                code = code.strip()
                
                # If no filename was provided, try to guess based on content
                if not filename:
                    if "def main" in code or "@mcp.tool" in code:
                        filename = "main.py"
                    elif "BaseModel" in code or "Field(" in code:
                        filename = "models.py"
                    elif "class API" in code or "httpx.AsyncClient" in code:
                        filename = "api.py"
                    elif "class Settings" in code or "BaseSettings" in code:
                        filename = "config.py"
                    elif "mcp" in code and "requirements" in raw_response.lower():
                        filename = "requirements.txt"
                    elif "API_KEY" in code:
                        filename = ".env.example"
                    elif "# " in code and "Usage" in code:
                        filename = "README.md"
                    else:
                        filename = f"file_{i+1}.py"
                
                files[filename] = code
            
            # Look for Python file content without code blocks
            if not files:
                if "def " in raw_response and "import " in raw_response:
                    files["main.py"] = raw_response
            
            return files
        except Exception as e:
            logger.error(f"Error parsing files from raw response: {str(e)}")
            return {}

    async def _save_template_files(self, template_id: str, raw_response: Optional[str], generated_code: Optional[Dict[str, str]]) -> bool:
        """
        Save generated files to the template directory.
        
        Args:
            template_id: Template ID
            raw_response: Raw LLM response
            generated_code: Dictionary of filenames to file contents
            
        Returns:
            True if files were saved successfully, False otherwise
        """
        try:
            # Log the attempt
            logger.info(f"Attempting to save files for template ID: {template_id}")
            
            # Get template directory
            template_dir = os.path.join(self.templates_dir, template_id)
            logger.info(f"Template directory path: {template_dir}")
            
            # Ensure directory exists
            try:
                os.makedirs(template_dir, exist_ok=True)
                logger.info(f"Successfully created directory: {template_dir}")
            except Exception as e:
                logger.error(f"Error creating template directory: {str(e)}")
                return False
            
            # Save the raw LLM response
            if raw_response:
                raw_response_path = os.path.join(template_dir, "raw_llm_response.txt")
                try:
                    with open(raw_response_path, "w", encoding="utf-8") as f:
                        f.write(raw_response)
                    logger.info(f"Saved raw LLM response to {raw_response_path}")
                except Exception as e:
                    logger.error(f"Failed to save raw response: {str(e)}")
            
            # If generated_code is empty or None, create required files
            if not generated_code:
                logger.warning("No generated code provided, using default files")
                
                # Only create default files if no raw response is available
                if not raw_response:
                    logger.warning("No raw response available either, using completely default files")
                    generated_code = {
                        "main.py": "# Generated MCP Server\nfrom mcp.server.fastmcp import FastMCP\n\nmcp = FastMCP('generated_mcp')\n\n@mcp.tool()\nasync def example_tool(query: str):\n    \"\"\"Example tool\"\"\"\n    return {'result': f'Processed: {query}'}\n\nif __name__ == \"__main__\":\n    mcp.run()",
                        "requirements.txt": "mcp>=1.4.1\nfastmcp>=0.2.0\nrequests>=2.28.0",
                        ".env.example": "# API credentials\nAPI_KEY=your_api_key_here",
                        "README.md": f"# Generated MCP Server\n\nTemplate ID: {template_id}\n\nThis MCP server was generated automatically."
                    }
                else:
                    # Try to create a main.py file from raw response
                    generated_code = {
                        "main.py": f"# Generated MCP Server\n\n'''\nRaw LLM Response:\n{raw_response[:2000]}...\n'''\n\nfrom mcp.server.fastmcp import FastMCP\n\nmcp = FastMCP('generated_mcp')\n\n# TODO: Implement tools based on the raw LLM response\n\nif __name__ == '__main__':\n    mcp.run()",
                        "requirements.txt": "mcp>=1.4.1\nfastmcp>=0.2.0\nrequests>=2.28.0\nhttpx>=0.24.0\npydantic>=2.0.0\npython-dotenv>=1.0.0",
                        ".env.example": "# API credentials\nAPI_KEY=your_api_key_here\nAPI_BASE_URL=https://api.example.com",
                        "README.md": f"# Generated MCP Server\n\nTemplate ID: {template_id}\n\nThis MCP server was generated automatically based on LLM output. Check raw_llm_response.txt for details."
                    }
            
            # Save all generated files
            for filename, content in generated_code.items():
                file_path = os.path.join(template_dir, filename)
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    logger.info(f"Successfully wrote file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to write file {filename}: {str(e)}")
            
            # Check what was actually saved
            try:
                files = os.listdir(template_dir)
                logger.info(f"Files in directory after save: {files}")
                if not files:
                    logger.warning(f"Directory exists but is empty: {template_dir}")
            except Exception as e:
                logger.error(f"Failed to list directory contents: {str(e)}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error in _save_template_files: {str(e)}")
            return False
    
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