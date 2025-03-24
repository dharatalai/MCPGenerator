import os
import json
import shutil
import tempfile
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import logging
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPServerGenerator:
    """Generator for MCP servers from templates."""
    
    def __init__(self, templates_base_path: str):
        """
        Initialize the MCP server generator.
        
        Args:
            templates_base_path: Base path where templates are stored
        """
        self.templates_base_path = templates_base_path
        
    def _validate_config(self, template_path: str, config: Dict[str, Any]) -> bool:
        """
        Validate the provided configuration against the template's schema.
        
        Args:
            template_path: Path to the template
            config: Configuration to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Load schema from template
        schema_path = os.path.join(template_path, "config_schema.json")
        if not os.path.exists(schema_path):
            logger.warning(f"No schema found at {schema_path}")
            return True
            
        # In a real implementation, use jsonschema library to validate
        # For now, just check if required fields are present
        try:
            with open(schema_path, "r") as f:
                schema = json.load(f)
                
            # Check required fields at top level
            for required_field in schema.get("required", []):
                if required_field not in config:
                    logger.error(f"Missing required field: {required_field}")
                    return False
                    
            # Check required fields in credentials
            creds_schema = schema.get("properties", {}).get("credentials", {})
            for required_cred in creds_schema.get("required", []):
                if required_cred not in config.get("credentials", {}):
                    logger.error(f"Missing required credential: {required_cred}")
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Error validating config: {e}")
            return False
    
    def generate_server(
        self, 
        template_name: str, 
        config: Dict[str, Any], 
        output_dir: Optional[str] = None
    ) -> str:
        """
        Generate an MCP server from a template.
        
        Args:
            template_name: Name of the template (e.g., 'google_drive')
            config: Configuration for the server
            output_dir: Directory to output the generated server (optional)
            
        Returns:
            Path to the generated server
        """
        # Resolve template path
        template_path = os.path.join(self.templates_base_path, template_name)
        if not os.path.exists(template_path):
            raise ValueError(f"Template not found: {template_name}")
            
        # Validate config against schema
        if not self._validate_config(template_path, config):
            raise ValueError("Invalid configuration for template")
            
        # Create output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix=f"mcp_server_{template_name}_")
        else:
            os.makedirs(output_dir, exist_ok=True)
            
        # Copy template files
        for item in os.listdir(template_path):
            # Skip schema and other template-specific files
            if item in ["config_schema.json", "__pycache__"]:
                continue
                
            source = os.path.join(template_path, item)
            dest = os.path.join(output_dir, item)
            
            if os.path.isdir(source):
                shutil.copytree(source, dest)
            else:
                # For Python files, use Jinja2 to render templates
                if item.endswith(".py"):
                    self._render_template(source, dest, config)
                else:
                    shutil.copy2(source, dest)
                    
        # Generate environment file for credentials
        self._generate_env_file(output_dir, config)
                    
        logger.info(f"Generated MCP server at {output_dir}")
        return output_dir
    
    def _render_template(self, source_path: str, dest_path: str, config: Dict[str, Any]):
        """
        Render a template file with the given configuration.
        
        Args:
            source_path: Path to the template file
            dest_path: Path to the output file
            config: Configuration data
        """
        # Set up Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(os.path.dirname(source_path)),
            autoescape=False
        )
        
        # Get template filename
        template_filename = os.path.basename(source_path)
        
        # Render template
        template = env.get_template(template_filename)
        rendered = template.render(**config)
        
        # Write to destination
        with open(dest_path, "w") as f:
            f.write(rendered)
    
    def _generate_env_file(self, output_dir: str, config: Dict[str, Any]):
        """
        Generate an environment file for the server.
        
        Args:
            output_dir: Output directory
            config: Configuration data
        """
        env_path = os.path.join(output_dir, ".env")
        
        with open(env_path, "w") as f:
            # Add credentials
            if "credentials" in config:
                for key, value in config["credentials"].items():
                    # Convert nested credentials to JSON
                    if isinstance(value, dict):
                        value = json.dumps(value)
                    f.write(f"{key.upper()}={value}\n")
                    
            # Add Google Drive specific credentials
            if "credentials" in config and "google_drive" in config.get("type", ""):
                creds_json = json.dumps(config["credentials"])
                f.write(f"GOOGLE_CREDENTIALS='{creds_json}'\n")
                
            # Add other settings
            if "settings" in config:
                for key, value in config["settings"].items():
                    if isinstance(value, dict) or isinstance(value, list):
                        value = json.dumps(value)
                    f.write(f"{key.upper()}={value}\n") 