from typing import Dict, Any, Optional
import httpx
import yaml
import json
from bs4 import BeautifulSoup
import markdown
import logging
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

class DocProcessor:
    """Class for processing API documentation from URLs."""
    
    def __init__(self):
        """Initialize the documentation processor with HTTP client."""
        self.client = httpx.AsyncClient()
    
    async def process_url(self, url: str) -> Dict[str, Any]:
        """
        Process documentation from a URL.
        
        Args:
            url: The URL to the API documentation
            
        Returns:
            Processed documentation structure
        """
        try:
            logger.info(f"Processing documentation from URL: {url}")
            response = await self.client.get(url)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '')
            
            if 'json' in content_type:
                return await self._process_openapi(response.text)
            elif 'yaml' in content_type or url.endswith('.yaml') or url.endswith('.yml'):
                return await self._process_openapi(response.text, is_yaml=True)
            else:
                return await self._process_markdown(response.text)
        except Exception as e:
            logger.error(f"Failed to process documentation: {str(e)}")
            raise ValueError(f"Failed to process documentation: {str(e)}")
    
    async def _process_openapi(self, content: str, is_yaml: bool = False) -> Dict[str, Any]:
        """Process OpenAPI documentation."""
        try:
            if is_yaml:
                spec = yaml.safe_load(content)
            else:
                spec = json.loads(content)
            
            # Extract relevant information
            processed = {
                "info": spec.get("info", {}),
                "servers": spec.get("servers", []),
                "paths": {},
                "components": spec.get("components", {})
            }
            
            # Process paths
            for path, methods in spec.get("paths", {}).items():
                processed["paths"][path] = {}
                for method, details in methods.items():
                    if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                        continue
                        
                    processed["paths"][path][method] = {
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "parameters": details.get("parameters", []),
                        "requestBody": details.get("requestBody", {}),
                        "responses": details.get("responses", {})
                    }
            
            return processed
        except Exception as e:
            logger.error(f"Failed to process OpenAPI documentation: {str(e)}")
            raise ValueError(f"Failed to process OpenAPI documentation: {str(e)}")
    
    async def _process_markdown(self, content: str) -> Dict[str, Any]:
        """Process Markdown documentation."""
        try:
            # Convert markdown to HTML
            html = markdown.markdown(content)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract structure
            processed = {
                "title": self._get_title(soup),
                "sections": self._get_sections(soup),
                "endpoints": self._extract_endpoints(soup),
                "code_samples": self._extract_code_samples(soup)
            }
            
            return processed
        except Exception as e:
            logger.error(f"Failed to process Markdown documentation: {str(e)}")
            raise ValueError(f"Failed to process Markdown documentation: {str(e)}")
    
    def _get_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML."""
        h1 = soup.find('h1')
        return h1.text if h1 else ""
    
    def _get_sections(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract sections from HTML."""
        sections = {}
        current_section = None
        current_content = []
        
        for elem in soup.find_all(['h2', 'p']):
            if elem.name == 'h2':
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = elem.text
                current_content = []
            else:
                if current_section:
                    current_content.append(elem.text)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _extract_endpoints(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract API endpoints from HTML."""
        endpoints = {}
        
        # Look for code blocks that might contain endpoint information
        for code in soup.find_all('code'):
            text = code.text.strip()
            if text.startswith(('GET', 'POST', 'PUT', 'DELETE', 'PATCH')):
                parts = text.split(' ', 1)
                if len(parts) >= 2:
                    method, path = parts
                    endpoints[path] = {"method": method}
        
        return endpoints
    
    def _extract_code_samples(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract code samples from HTML."""
        samples = {}
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                lang_class = code.get('class', [''])
                lang = lang_class[0].replace('language-', '') if lang_class else 'generic'
                samples[lang] = code.text
        return samples
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

class JinaDocumentProcessor:
    """Class to read and process documentation using Jina AI."""
    
    def __init__(self):
        """Initialize the Jina documentation processor."""
        # Use provided API key or from environment
        self.jina_api_key = os.getenv("JINA_API_KEY", "jina_acd51f2ce2414643b43119b62567f7dbFlYZe9DLybjxNkUut28Y4kQIG-Hn")
    
    async def process_url(self, url: str) -> str:
        """
        Extract and process documentation from the given URL using Jina AI.
        
        Args:
            url: The URL to process
            
        Returns:
            Processed documentation as text
        """
        try:
            # Use the Jina Reader API format
            jina_url = f"https://r.jina.ai/{url}"
            headers = {
                "Authorization": f"Bearer {self.jina_api_key}",
                "X-Return-Format": "markdown"
            }
            
            logger.info(f"Fetching documentation from Jina Reader: {url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    jina_url,
                    headers=headers,
                    timeout=60.0  # Longer timeout for document processing
                )
                response.raise_for_status()
                content = response.text
                
                logger.info(f"Retrieved {len(content)} characters of documentation from {url}")
                return content
                
        except Exception as e:
            logger.error(f"Error processing documentation from {url}: {str(e)}")
            raise ValueError(f"Error retrieving documentation: {str(e)}") 