from typing import Dict, Any, Optional, List
import os
import logging
import json
import tempfile
import shutil
from pathlib import Path
import asyncio
import sys

# Add parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from db.database import get_db
from db.models.server import MCPServer
from db.models.template import Template

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
            
            # Check for errors
            if result.get("error"):
                logger.error(f"Workflow failed: {result['error']}")
                return {"success": False, "error": result["error"]}
            
            # Save generated files
            template_id = result.get("template_id", existing_template_id)
            if template_id and result.get("generated_code"):
                await self._save_template_files(template_id, result["generated_code"])
                
            return {
                "success": True,
                "template_id": template_id,
                "server_id": result.get("server_id", existing_server_id),
                "message": "MCP server generated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate MCP server: {str(e)}")
            return {"success": False, "error": f"Failed to generate MCP server: {str(e)}"}
    
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
            # Get DB session
            db = next(get_db())
            
            # Get template
            template = db.query(Template).filter(Template.id == template_id).first()
            if not template:
                raise ValueError(f"Template not found: {template_id}")
            
            # Create server instance
            server = MCPServer(
                name=server_name,
                description=server_description or template.description,
                template_id=template_id,
                user_id=user_id,
                status="created",
                config=config or {},
                credentials=config.get("credentials", {}) if config else {}
            )
            
            db.add(server)
            db.commit()
            db.refresh(server)
            
            # In a real implementation, this would trigger a deployment process
            # For now, we'll just mark it as deployed
            server.status = "deployed"
            server.deployment_url = f"https://example.com/mcp/{server.id}"
            db.commit()
            
            return {
                "success": True,
                "server_id": server.id,
                "deployment_url": server.deployment_url,
                "message": "MCP server deployed successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy MCP server: {str(e)}")
            return {"success": False, "error": f"Failed to deploy MCP server: {str(e)}"}
    
    async def _save_template_files(self, template_id: str, files: Dict[str, str]) -> None:
        """
        Save generated files for a template.
        
        Args:
            template_id: ID of the template
            files: Dictionary of filenames to file contents
        """
        template_dir = os.path.join(self.templates_dir, template_id)
        os.makedirs(template_dir, exist_ok=True)
        
        for filename, content in files.items():
            filepath = os.path.join(template_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)
                
        logger.info(f"Saved template files to {template_dir}") 