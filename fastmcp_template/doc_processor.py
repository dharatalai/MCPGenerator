from typing import Dict, Any, Optional
import httpx
import yaml
import json
from bs4 import BeautifulSoup
import markdown

class DocProcessor:
    def __init__(self):
        self.client = httpx.AsyncClient()
    
    async def process_url(self, url: str) -> Dict[str, Any]:
        """Process documentation from a URL."""
        try:
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
                    processed["paths"][path][method] = {
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "parameters": details.get("parameters", []),
                        "requestBody": details.get("requestBody", {}),
                        "responses": details.get("responses", {})
                    }
            
            return processed
        except Exception as e:
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
                method, path = text.split(' ', 1)
                endpoints[path] = {"method": method}
        
        return endpoints
    
    def _extract_code_samples(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract code samples from HTML."""
        samples = {}
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                lang = code.get('class', [''])[0].replace('language-', '')
                samples[lang] = code.text
        return samples
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose() 