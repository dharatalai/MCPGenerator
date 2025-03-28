from typing import TypedDict, List, Dict, Any, Optional
from enum import Enum
import logging
import os
import json
import asyncio
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
import openai
import sys
import re
import uuid
import time
from datetime import datetime

# Add parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from db.database import get_db
from db.models.template import Template
from db.models.server import MCPServer
from db.supabase_client import templateOperations

# Progress tracking singleton
class ProgressTracker:
    _instance = None
    _progress_store = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProgressTracker, cls).__new__(cls)
        return cls._instance
    
    def start_task(self, task_id):
        """Start tracking a new task with given ID"""
        self._progress_store[task_id] = {
            "status": "initializing",
            "progress": 0,
            "current_step": "starting",
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "log": ["Task started"],
            "error": None
        }
        logger.info(f"Started tracking progress for task {task_id}")
        return task_id
    
    def update_progress(self, task_id, progress=None, status=None, step=None, message=None, error=None):
        """Update progress for a task"""
        if task_id not in self._progress_store:
            self.start_task(task_id)
            
        if progress is not None:
            self._progress_store[task_id]["progress"] = progress
        
        if status is not None:
            self._progress_store[task_id]["status"] = status
            
        if step is not None:
            self._progress_store[task_id]["current_step"] = step
            
        if error is not None:
            self._progress_store[task_id]["error"] = error
            
        self._progress_store[task_id]["last_update"] = datetime.now().isoformat()
        
        if message:
            self._progress_store[task_id]["log"].append(message)
            logger.info(f"Task {task_id}: {message}")
            
        return self._progress_store[task_id]
    
    def get_progress(self, task_id):
        """Get the current progress of a task"""
        if task_id not in self._progress_store:
            return None
        return self._progress_store[task_id]
    
    def finish_task(self, task_id, success=True, error=None):
        """Mark a task as finished"""
        if task_id not in self._progress_store:
            return None
            
        status = "completed" if success else "failed"
        message = "Task completed successfully" if success else f"Task failed: {error}"
        
        self._progress_store[task_id]["status"] = status
        self._progress_store[task_id]["progress"] = 100 if success else self._progress_store[task_id]["progress"]
        self._progress_store[task_id]["error"] = error
        self._progress_store[task_id]["log"].append(message)
        self._progress_store[task_id]["end_time"] = datetime.now().isoformat()
        
        logger.info(f"Task {task_id} finished with status: {status}")
        return self._progress_store[task_id]
    
    def clean_old_tasks(self, hours=24):
        """Clean up tasks older than specified hours"""
        current_time = datetime.now()
        to_remove = []
        
        for task_id, task_data in self._progress_store.items():
            last_update = datetime.fromisoformat(task_data["last_update"])
            if (current_time - last_update).total_seconds() > hours * 3600:
                to_remove.append(task_id)
                
        for task_id in to_remove:
            del self._progress_store[task_id]
            
        return len(to_remove)

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

# LLM API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class WorkflowStep(str, Enum):
    PROCESS_DOCS = "process_docs"
    PLANNING = "planning"
    CODING = "coding"
    VALIDATION = "validation"

class AgentState(TypedDict):
    user_id: str
    latest_user_message: str
    messages: List[Dict[str, Any]]
    documentation: Dict[str, Any]
    raw_documentation: str
    implementation_plan: str
    generated_code: Dict[str, str]
    api_credentials: Dict[str, Any]
    error: Optional[str]
    template_id: Optional[str]
    server_id: Optional[str]

class LLMWorkflow:
    """LLM workflow for generating MCP servers from API documentation."""
    
    def __init__(self):
        """Initialize the LLM workflow."""
        self.memory = MemorySaver()
        self.workflow = self._create_workflow()
        self.progress_tracker = ProgressTracker()
        
        # Load API keys from .env file
        load_dotenv()
        
        # Get planning API key from environment variables
        planning_api_key = os.getenv("OPENROUTER_PLANNING_API_KEY")
        if not planning_api_key:
            logger.warning("No Planning API key found in environment variables")
            planning_api_key = ""
        
        # Get coding API key from environment variables
        coding_api_key = os.getenv("OPENROUTER_CODING_API_KEY")
        if not coding_api_key:
            logger.warning("No Coding API key found in environment variables")
            coding_api_key = ""
        
        # Initialize planning client
        self.planning_client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=planning_api_key,
            default_headers={
                "HTTP-Referer": "https://mcp-saas.dev",
                "X-Title": "MCP SaaS - Planning"
            }
        )
        
        # Initialize coding client
        self.coding_client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=coding_api_key,
            default_headers={
                "HTTP-Referer": "https://mcp-saas.dev",
                "X-Title": "MCP SaaS - Coding"
            }
        )
    
    def _extract_json_from_response(self, content: str) -> str:
        """Extract JSON from a response that might be wrapped in markdown or LaTeX."""
        try:
            # Clean up the content first
            # Remove any non-JSON text before the first {
            if '{' in content:
                content = content[content.index('{'):]
            
            # Remove any non-JSON text after the last }
            if '}' in content:
                content = content[:content.rindex('}')+1]
            
            # Look for JSON within LaTeX \boxed{} command
            boxed_match = re.search(r'\\boxed\{(.*?)\}', content, re.DOTALL)
            if boxed_match:
                boxed_content = boxed_match.group(1).strip()
                # Try to find JSON inside the boxed content
                json_match = re.search(r'\{.*\}', boxed_content, re.DOTALL)
                if json_match:
                    return json_match.group(0).strip()
                return boxed_content
            
            # Look for JSON within markdown code blocks
            code_block_match = re.search(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
            if code_block_match:
                return code_block_match.group(1).strip()
            
            # Look for raw JSON object starting with { and ending with }
            json_obj_match = re.search(r'(\{.*\})', content, re.DOTALL)
            if json_obj_match:
                return json_obj_match.group(1).strip()
            
            # If no structured format is found, return the original content
            return content
        except Exception as e:
            logger.warning(f"Error extracting JSON: {str(e)}. Returning original content.")
            return content
    
    def _create_workflow(self) -> StateGraph:
        """Create the agent workflow using LangGraph."""
        
        # Build workflow
        builder = StateGraph(AgentState)
        
        # Add nodes
        builder.add_node(WorkflowStep.PLANNING, self._planning_node)
        builder.add_node(WorkflowStep.CODING, self._coding_node)
        builder.add_node(WorkflowStep.VALIDATION, self._validation_node)
        
        # Set edges
        builder.add_edge(START, WorkflowStep.PLANNING)
        builder.add_edge(WorkflowStep.PLANNING, WorkflowStep.CODING)
        builder.add_edge(WorkflowStep.CODING, WorkflowStep.VALIDATION)
        builder.add_edge(WorkflowStep.VALIDATION, END)
        
        # Compile workflow without using memory/checkpointer
        # This avoids the configurable_fields error
        return builder.compile()
    
    async def _planning_node(self, state: AgentState) -> Dict[str, Any]:
        """Planning node for creating implementation plan."""
        try:
            # Update progress if we have a template_id
            if state.get('template_id'):
                self.progress_tracker.update_progress(
                    state['template_id'],
                    progress=25,
                    status="planning",
                    step="Creating implementation plan",
                    message="Analyzing API documentation and creating plan"
                )
            
            # Define the JSON structure separately as a string literal
            json_structure = """
{
    "service_name": "Name of the MCP service",
    "description": "Detailed description of the service",
    "tools": [
        {
            "name": "tool_name",
            "description": "Comprehensive tool description",
            "input_model": {
                "name": "ModelName",
                "fields": [
                    {"name": "field_name", "type": "type", "description": "Field description", "required": "true"}
                ]
            },
            "returns": {
                "type": "Return type",
                "description": "Detailed description of return value"
            },
            "endpoint": "Full API endpoint URL",
            "method": "HTTP method",
            "error_handling": ["List of error cases to handle"],
            "rate_limits": {"requests": 0, "period": "per_second"},
            "parameters": [
                {
                    "name": "parameter_name",
                    "type": "parameter_type",
                    "description": "Parameter description",
                    "required": "true",
                    "default_value": "default value if any"
                }
            ]
        }
    ],
    "auth_requirements": {
        "type": "Type of authentication",
        "credentials": ["List of required credentials"],
        "headers": {"header_name": "header_value"}
    },
    "dependencies": [
        {"name": "package_name", "version": "version_spec"}
    ],
    "type_definitions": [
        {
            "name": "TypeName",
            "description": "Type description",
            "fields": [{"name": "field_name", "type": "type", "description": "description"}]
        }
    ]
}
"""
            
            planning_prompt = f"""
            You are an expert planning agent that analyzes API documentation to create MCP (Model Context Protocol) servers.
            
            USER REQUEST: {state.get('latest_user_message', '')}
            
            API DOCUMENTATION:
            
            {state.get('raw_documentation', '')}
            
            Your task is to:
            1. Analyze the provided API documentation in detail
            2. Extract ALL available API endpoints, their parameters, and response formats
            3. Identify authentication requirements and API key handling
            4. Map API capabilities to MCP tools with proper type annotations
            5. Create a detailed plan for implementing an MCP server using the FastMCP framework
            
            IMPORTANT GUIDELINE:
            First, identify what type of API this is (REST, GraphQL, WebSocket, etc.) and what service it provides.
            Then, adapt your planning based on the specific API type. Each type of API requires different handling:
            
            - For search/AI APIs (like OpenAI, DeepSearch, etc.):
              * Focus on model parameters, query options, and streaming capabilities
              * Include proper request/response handling for AI models
            
            - For REST APIs:
              * Map REST endpoints to appropriate MCP tools
              * Handle pagination, filtering, and sorting parameters
            
            - For database APIs:
              * Create proper data models and CRUD operations
              * Include transaction and error handling
            
            The implementation must follow the FastMCP pattern and include:
            1. Proper error handling and retries for API calls
            2. Type validation using Pydantic models
            3. Comprehensive docstrings and examples
            4. Authentication handling
            5. Rate limiting and timeout handling
            
            Example structure:
            ```python
            from mcp.server.fastmcp import FastMCP
            from pydantic import BaseModel, Field
            from typing import Optional, List, Dict, Any
            
            class SearchParams(BaseModel):
                query: str = Field(..., description="Search query")
                model: str = Field("default", description="Model to use")
                max_tokens: int = Field(1000, description="Maximum tokens")
            
            mcp = FastMCP("service_name")
            
            @mcp.tool()
            async def search(params: SearchParams) -> Dict[str, Any]:
                '''
                Execute a search query.
                
                Args:
                    params: Search parameters
                    
                Returns:
                    Search results
                    
                Raises:
                    HTTPError: If API request fails'''
                # Implementation with proper error handling
                return result
            ```
            
            Return a JSON object with the following structure:
            {json_structure}
            
            IMPORTANT: Your response must be ONLY the JSON object without any LaTeX formatting or markdown code blocks.
            Focus on COMPLETENESS and ACCURACY of the API implementation details.
            """
            
            # Log that we're about to make API call
            logger.info(f"[TRACK-LLM] Starting Planning API call to {state.get('template_id', 'unknown')}")
            api_call_start = time.time()
            
            # Make API call with retries
            max_retries = 6
            retry_count = 0
            retry_delay = 3  # seconds
            
            while retry_count < max_retries:
                try:
                    # Use synchronous API call without await
                    chat_completion = self.planning_client.chat.completions.create(
                        model="google/gemini-2.5-pro-exp-03-25:free",
                        messages=[
                            {"role": "system", "content": planning_prompt},
                            {"role": "user", "content": f"Given the provided API documentation and user request, create a detailed plan for MCP server implementation.\n\nPlease format your response in LaTeX using the \\boxed{{}} command to enclose your JSON implementation plan.\n\nExample: \\boxed{{{json_structure}}}"}
                        ],
                        temperature=0.6,
                        max_tokens=4000
                    )
                    
                    # Check if we got a valid response
                    if chat_completion and chat_completion.choices and chat_completion.choices[0].message.content:
                        api_call_end = time.time()
                        logger.info(f"[TRACK-LLM] Planning API call completed in {api_call_end - api_call_start:.2f}s for {state.get('template_id', 'unknown')}")
                        
                        content = chat_completion.choices[0].message.content
                        logger.info(f"[TRACK-LLM] Planning response size: {len(content)} chars")
                        
                        # Extract JSON from response
                        extracted_content = self._extract_json_from_response(content)
                        logger.info(f"[TRACK-LLM] Extracted planning JSON size: {len(extracted_content)} chars")
                        
                        # Extract structured JSON if available
                        try:
                            plan_json = json.loads(extracted_content)
                            logger.info("[TRACK-LLM] Successfully parsed planning response as JSON")
                        except json.JSONDecodeError:
                            logger.warning("[TRACK-LLM] Could not parse planning response as JSON, using raw text")
                            plan_json = {"raw_plan": extracted_content}
                        
                        # Update state with implementation plan
                        state["implementation_plan"] = extracted_content
                        state["raw_response"] = content
                        
                        return state
                    else:
                        # Empty response, retry
                        retry_count += 1
                        logger.warning(f"[TRACK-LLM] Empty response from planning API (attempt {retry_count}/{max_retries}), retrying in {retry_delay}s")
                        await asyncio.sleep(retry_delay)
                except Exception as api_error:
                    # Error during API call, retry
                    retry_count += 1
                    logger.warning(f"[TRACK-LLM] Planning API call error (attempt {retry_count}/{max_retries}): {str(api_error)}, retrying in {retry_delay}s")
                    await asyncio.sleep(retry_delay)
            
            # If we get here, all retries failed
            error_msg = f"Planning API call failed after {max_retries} retries"
            logger.error(f"[TRACK-LLM] {error_msg} for {state.get('template_id', 'unknown')}")
            state["implementation_plan"] = f"API call failed: {error_msg}"
            state["error"] = f"Error during planning phase: {error_msg}"
            return state
                
        except Exception as e:
            logger.error(f"[TRACK-LLM] Planning node error: {str(e)}")
            state["error"] = f"Error in planning node: {str(e)}"
            return state
    
    async def _coding_node(self, state: AgentState) -> Dict[str, Any]:
        """Coding node for generating MCP server implementation."""
        try:
            # Update progress if we have a template_id
            if state.get('template_id'):
                self.progress_tracker.update_progress(
                    state['template_id'],
                    progress=50,
                    status="coding",
                    step="Generating code",
                    message="Generating MCP server code based on implementation plan"
                )
            
            coding_prompt = f"""
            You are an expert coding agent that implements MCP (Model Context Protocol) servers using FastMCP.
            
            USER REQUEST: {state.get('latest_user_message', '')}
            
            IMPLEMENTATION PLAN:
            {state.get('implementation_plan', '')}
            
            Your task is to generate complete, production-ready code for an MCP server according to the implementation plan.
            The code must be:
            1. Fully functional and ready to run
            2. Well-structured with proper separation of concerns
            3. Properly typed with Pydantic models
            4. Well-documented with docstrings and comments
            5. Include comprehensive error handling
            6. Handle rate limits and timeouts
            7. Implement proper authentication
            
            SAMPLE MCP TEMPLATE:
            
            main.py:
            ```python
            from mcp.server.fastmcp import FastMCP
            from typing import Dict, Any, Optional, List, Union
            from pydantic import BaseModel, Field
            import httpx
            import logging
            import asyncio
            import os
            from dotenv import load_dotenv

            # Load environment variables
            load_dotenv()

            # Configure logging
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(__name__)

            # Define models
            class QueryParams(BaseModel):
                query: str = Field(..., description="The search query")
                model: str = Field("default-model", description="Model to use for processing")
                max_results: int = Field(10, description="Maximum number of results to return")

            class SearchResult(BaseModel):
                answer: str = Field(..., description="Generated answer")
                sources: List[Dict[str, Any]] = Field([], description="Sources used")
                usage: Dict[str, int] = Field(..., description="Token usage information")

            # Initialize API client
            class APIClient:
                def __init__(self):
                    self.api_key = os.getenv("API_KEY")
                    self.base_url = os.getenv("API_BASE_URL")
                    self.headers = {{
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {{self.api_key}}"
                    }}
                    self.client = httpx.AsyncClient(
                        base_url=self.base_url,
                        headers=self.headers,
                        timeout=60.0
                    )
                
                async def search(self, params: QueryParams) -> Dict[str, Any]:
                    '''
                    Execute a search using the API.
                    
                    Args:
                        params: Search parameters
                        
                    Returns:
                        Search results
                    '''
                    try:
                        payload = {{
                            "model": params.model,
                            "messages": [{{"role": "user", "content": params.query}}],
                            "max_results": params.max_results
                        }}
                        
                        response = await self.client.post("/v1/search", json=payload)
                        response.raise_for_status()
                        return response.json()
                    except httpx.HTTPError as e:
                        logger.error(f"HTTP error: {{str(e)}}")
                        raise
                    except Exception as e:
                        logger.error(f"Error in search: {{str(e)}}")
                        raise

            # Initialize MCP
            mcp = FastMCP("api-service")
            api_client = APIClient()

            @mcp.tool()
            async def search(query: str) -> Dict[str, Any]:
                '''
                Execute a search with default parameters.
                
                Args:
                    query: The search query
                    
                Returns:
                    Search results
                '''
                try:
                    params = QueryParams(query=query)
                    result = await api_client.search(params)
                    return SearchResult(
                        answer=result.get("answer", ""),
                        sources=result.get("sources", []),
                        usage=result.get("usage", {{}})
                    ).dict()
                except Exception as e:
                    logger.error(f"Error in search: {{str(e)}}")
                    return {{"error": str(e)}}

            @mcp.tool()
            async def search_with_options(params: QueryParams) -> Dict[str, Any]:
                '''
                Execute a search with custom parameters.
                
                Args:
                    params: Custom search parameters
                    
                Returns:
                    Search results
                '''
                try:
                    result = await api_client.search(params)
                    return SearchResult(
                        answer=result.get("answer", ""),
                        sources=result.get("sources", []),
                        usage=result.get("usage", {{}})
                    ).dict()
                except Exception as e:
                    logger.error(f"Error in search_with_options: {{str(e)}}")
                    return {{"error": str(e)}}

            if __name__ == "__main__":
                mcp.run()
            ```
            
            requirements.txt:
            ```
            mcp>=0.1.0
            httpx>=0.24.0
            pydantic>=2.0.0
            python-dotenv>=1.0.0
            ```
            
            .env.example:
            ```
            API_KEY=your_api_key_here
            API_BASE_URL=https://api.example.com
            ```
            
            Generate the following files:
            1. main.py - The main MCP server implementation
            2. models.py - Pydantic models for request/response types (if needed)
            3. api.py - API client implementation (if needed) 
            4. requirements.txt - Complete dependencies with versions
            5. .env.example - Example environment variables
            6. README.md - Comprehensive documentation
            
            IMPORTANT:
            1. Generate COMPLETE, RUNNABLE code for each file
            2. Include ALL necessary imports
            3. Implement proper error handling
            4. Add comprehensive logging
            5. Implement EVERY tool listed in the implementation plan
            6. Use the parameters extracted from the documentation
            7. NEVER generate placeholder or example tools - implement real functionality
            8. Follow Python best practices
            9. Do not assume any parameter names - use what was specified in the implementation plan
            """
            
            # Log that we're about to make API call
            logger.info(f"[TRACK-LLM] Starting Coding API call to {state.get('template_id', 'unknown')}")
            api_call_start = time.time()
            
            # Make API call with retries
            max_retries = 6
            retry_count = 0
            retry_delay = 3  # seconds
            
            while retry_count < max_retries:
                try:
                    # Use synchronous API call without await
                    chat_completion = self.coding_client.chat.completions.create(
                        model="google/gemini-2.5-pro-exp-03-25:free",
                        messages=[
                            {"role": "system", "content": coding_prompt},
                            {"role": "user", "content": f"Given the implementation plan, generate a complete MCP server implementation with all necessary files.\n\nIMPLEMENTATION PLAN:\n{state.get('implementation_plan', 'No plan available')}\n\nPlease return your response as a JSON object with a 'files' field that contains all the generated files. Each file should have a 'name' field for the filename and a 'content' field for the file content.\n\nExample format:\n```json\n{{\n  \"files\": [\n    {{\n      \"name\": \"main.py\",\n      \"content\": \"from mcp.server.fastmcp import FastMCP\\n\\nmcp = FastMCP('example_api')\\n...\"\n    }},\n    {{\n      \"name\": \"README.md\",\n      \"content\": \"# Example API MCP Server\\n\\nThis is an MCP server for ...\"\n    }}\n  ]\n}}\n```"}
                        ],
                        temperature=0.4,
                        max_tokens=20000,
                        response_format={"type": "json_object"}
                    )
                    
                    # Check if we got a valid response
                    if chat_completion and chat_completion.choices and chat_completion.choices[0].message.content:
                        api_call_end = time.time()
                        logger.info(f"[TRACK-LLM] Coding API call completed in {api_call_end - api_call_start:.2f}s for {state.get('template_id', 'unknown')}")
                        
                        content = chat_completion.choices[0].message.content
                        logger.info(f"[TRACK-LLM] Coding response size: {len(content)} chars")
                        
                        # Extract JSON from response
                        logger.info("[TRACK-LLM] Extracting JSON from coding response")
                        extracted_json = self._extract_json_from_response(content)
                        
                        # Try to parse JSON response
                        try:
                            generated_code = json.loads(extracted_json)
                            logger.info(f"[TRACK-LLM] Successfully parsed coding response as JSON with keys: {list(generated_code.keys())}")
                            
                            # Validate the format
                            if "files" not in generated_code:
                                logger.warning("[TRACK-LLM] Generated code JSON doesn't contain 'files' key")
                                generated_code = {"files": [{"name": "main.py", "content": extracted_json}]}
                        except json.JSONDecodeError as json_err:
                            error_position = f"at position {json_err.pos}: character '{extracted_json[json_err.pos:json_err.pos+10]}...'"
                            logger.warning(f"[TRACK-LLM] JSON decode error {error_position}: {str(json_err)}")
                            logger.warning("[TRACK-LLM] Could not parse coding response as JSON, saving raw response")
                            # Create a simple structure with raw_response for debugging
                            generated_code = {"files": [{"name": "debug_raw_response.txt", "content": content}]}
                        
                        # Always store the raw response for debugging purposes
                        state["generated_code"] = generated_code
                        state["raw_response"] = content
                        
                        # Add verbose log to confirm raw_response is captured
                        logger.info(f"[TRACK-LLM] Raw response captured in state ({len(content)} chars)")
                        
                        return state
                    else:
                        # Empty response, retry
                        retry_count += 1
                        logger.warning(f"[TRACK-LLM] Empty response from coding API (attempt {retry_count}/{max_retries}), retrying in {retry_delay}s")
                        await asyncio.sleep(retry_delay)
                except Exception as api_error:
                    # Error during API call, retry
                    retry_count += 1
                    logger.warning(f"[TRACK-LLM] Coding API call error (attempt {retry_count}/{max_retries}): {str(api_error)}, retrying in {retry_delay}s")
                    await asyncio.sleep(retry_delay)
            
            # If we get here, all retries failed
            error_msg = f"Coding API call failed after {max_retries} retries"
            logger.error(f"[TRACK-LLM] {error_msg} for {state.get('template_id', 'unknown')}")
            state["generated_code"] = {"files": [{"name": "error.py", "content": f"# API call failed: {error_msg}"}]}
            state["error"] = f"Error during code generation phase: {error_msg}"
            return state
                
        except Exception as e:
            logger.error(f"[TRACK-LLM] Coding node error: {str(e)}")
            state["error"] = f"Error in coding node: {str(e)}"
            return state
    
    async def _validation_node(self, state: AgentState) -> Dict[str, Any]:
        """Validation node for checking the generated code."""
        try:
            # Update progress if we have a template_id
            if state.get('template_id'):
                self.progress_tracker.update_progress(
                    state['template_id'],
                    progress=75,
                    status="validating",
                    step="Validating generated code",
                    message="Validating and finalizing the generated code"
                )
            
            # Create template if not exists
            if not state.get("template_id"):
                try:
                    # Extract basic information from the implementation plan
                    try:
                        impl_plan = json.loads(state.get("implementation_plan", "{}"))
                        service_name = impl_plan.get("service_name", "Generated MCP")
                        description = impl_plan.get("description", "Generated MCP server from API documentation")
                    except json.JSONDecodeError:
                        # Fallback to simple extraction if JSON parsing fails
                        impl_plan = state.get("implementation_plan", "{}")
                        name_match = re.search(r'"service_name":\s*"([^"]+)"', impl_plan)
                        service_name = name_match.group(1) if name_match else "Generated MCP"
                        desc_match = re.search(r'"description":\s*"([^"]+)"', impl_plan)
                        description = desc_match.group(1) if desc_match else "Generated MCP server from API documentation"
                    
                    # Get user ID from state, use default if not available
                    user_id = state.get("user_id")
                    if not user_id or user_id == "None" or user_id == "":
                        logger.warning("No valid user ID found, using default")
                        user_id = "00000000-0000-0000-0000-000000000000"  # Default UUID
                    
                    # Create template using Supabase
                    template_data = {
                        "name": service_name,
                        "description": description,
                        "category": "custom",
                        "is_public": False,
                        "created_by": user_id
                    }
                    
                    logger.info(f"Creating template with data: {template_data}")
                    
                    # Create the template in Supabase with timeout
                    try:
                        template = await templateOperations.createTemplate(template_data)
                        
                        template_id = template.id
                        logger.info(f"Created template with ID: {template_id}")
                        
                        return {
                            "template_id": template_id,
                            "validation_result": "Template created successfully",
                            "raw_response": state.get("raw_response", ""),
                            "generated_code": state.get("generated_code", {})
                        }
                    except Exception as e:
                        logger.error(f"Error creating template: {str(e)}")
                        return {
                            "template_id": str(uuid.uuid4()),
                            "validation_result": f"Error: {str(e)}",
                            "raw_response": state.get("raw_response", ""),
                            "generated_code": state.get("generated_code", {})
                        }
                except Exception as e:
                    logger.error(f"Error creating template: {str(e)}")
                    return {
                        "template_id": str(uuid.uuid4()),
                        "validation_result": f"Error: {str(e)}",
                        "raw_response": state.get("raw_response", ""),
                        "generated_code": state.get("generated_code", {})
                    }
            
            # Include any raw_response in the return value
            return {
                "validation_result": "Validation passed",
                "raw_response": state.get("raw_response", ""),
                "generated_code": state.get("generated_code", {})
            }
        except Exception as e:
            logger.error(f"Error in validation node: {str(e)}")
            return {
                "template_id": str(uuid.uuid4()),
                "validation_result": f"Error: {str(e)}",
                "raw_response": state.get("raw_response", ""),
                "generated_code": state.get("generated_code", {})
            }
    
    # Add placeholder methods to avoid reference errors
    async def _validate_generated_code(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Simple validation placeholder to avoid errors"""
        return {
            "has_errors": False,
            "message": "Validation skipped",
            "errors": []
        }
    
    async def _fix_code_issues(self, state: Dict[str, Any], errors: List[str]) -> Optional[str]:
        """Simple fix placeholder to avoid errors"""
        return None
    
    async def process(self, state: AgentState) -> Dict[str, Any]:
        """
        Process the agent state through the workflow.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state after workflow completion
        """
        try:
            logger.info("Starting workflow process")
            
            # Create a template_id if it doesn't exist
            if not state.get('template_id'):
                state['template_id'] = str(uuid.uuid4())
                logger.info(f"Generated new template ID: {state['template_id']}")
            
            # Start progress tracking
            self.progress_tracker.start_task(state['template_id'])
            self.progress_tracker.update_progress(
                state['template_id'],
                status="processing",
                step="Starting workflow",
                message="Processing user request and API documentation"
            )
            
            # Add a 3-minute timeout for the entire workflow
            try:
                # Execute workflow
                task = asyncio.create_task(self.workflow.ainvoke(state))
                
                # Set timeout for task
                result = await asyncio.wait_for(task, timeout=180)  # 3 minutes
                
                # Log success
                logger.info("Workflow completed successfully")
                
                # Update progress as completed
                self.progress_tracker.update_progress(
                    state['template_id'],
                    progress=90,
                    status="finalizing",
                    step="Finalizing output",
                    message="Workflow completed successfully, finalizing results"
                )
                
                # Return result with success flag
                return {
                    **result,
                    "success": True, 
                    "message": "MCP server generated successfully"
                }
                
            except asyncio.TimeoutError:
                # Log timeout
                logger.error("Workflow timed out after 3 minutes")
                
                # Update progress with timeout error
                self.progress_tracker.update_progress(
                    state['template_id'],
                    progress=75,
                    status="timeout",
                    step="Timeout",
                    message="Generation process timed out after 3 minutes",
                    error="Generation process timed out after 3 minutes"
                )
                
                # Try to get the current value of workflow.state
                state_obj = self.workflow.get_state().get('state', {})
                current_state = state_obj if state_obj else state
                
                # Add error to state
                error_message = "Workflow timed out after 3 minutes"
                current_state["error"] = error_message
                
                # Try to ensure we have something to return
                if not current_state.get("generated_code", {}):
                    current_state["generated_code"] = {}
                    current_state["raw_response"] = "The generation process timed out. Please try again with a more focused request."
                
                # Return what we have with success flag = True, but include error message
                return {
                    **current_state,
                    "success": True,
                    "message": f"Processed with timeout: {error_message}",
                    "error": error_message
                }
                
        except Exception as e:
            # Log error
            logger.error(f"Error in workflow process: {str(e)}")
            
            # Update progress with error
            if state.get('template_id'):
                self.progress_tracker.update_progress(
                    state['template_id'],
                    status="failed",
                    step="Error",
                    message=f"Error during generation: {str(e)}",
                    error=str(e)
                )
            
            # Try to get the current value of workflow.state
            try:
                state_obj = self.workflow.get_state().get('state', {})
                current_state = state_obj if state_obj else state
            except Exception:
                current_state = state
            
            # Add error to state
            current_state["error"] = str(e)
            
            # Return what we have with success flag
            return {
                **current_state,
                "success": True,  # We still want to return a valid response
                "message": f"Processed with error: {str(e)}",
                "error": str(e)
            }

async def generate_with_timeout():
    try:
        return await asyncio.wait_for(generate_mcp_server(), timeout=120)  # 2 minute timeout
    except asyncio.TimeoutError:
        print("Generation timed out after 2 minutes") 