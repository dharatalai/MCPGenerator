from typing import TypedDict, List, Dict, Any, Optional
from enum import Enum
import logging
import os
import json
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
import openai
import sys

# Add parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from db.database import get_db
from db.models.template import Template
from db.models.server import MCPServer

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

# LLM API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

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
        
        # Initialize client using OpenRouter
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
    
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
        
        # Compile workflow
        return builder.compile(checkpointer=self.memory)
    
    async def _planning_node(self, state: AgentState) -> Dict[str, Any]:
        """Planning node for creating implementation plan."""
        try:
            planning_prompt = f"""
            You are an expert planning agent that analyzes API documentation to create MCP (Model Context Protocol) servers.
            
            USER REQUEST: {state.get('latest_user_message', '')}
            
            API DOCUMENTATION:
            
            {state.get('raw_documentation', '')[:7000]}
            
            Your task is to:
            1. Analyze the provided API documentation
            2. Identify the key endpoints and functionalities that should be exposed as MCP tools
            3. Create a detailed plan for implementing an MCP server using the FastMCP framework
            4. Break down the implementation into clear steps
            
            The implementation must follow the FastMCP pattern:
            ```python
            from mcp.server.fastmcp import FastMCP
            
            mcp = FastMCP("service_name")
            
            @mcp.tool()
            async def tool_name(param1: str, param2: int):
                # Implementation
                return result
                
            if __name__ == "__main__":
                mcp.run(transport="stdio")
            ```
            
            Return a JSON object with the following structure:
            {
                "service_name": "Name of the MCP service",
                "description": "Description of the service",
                "tools": [
                    {
                        "name": "tool_name",
                        "description": "Tool description",
                        "parameters": [
                            {"name": "param_name", "type": "param_type", "description": "Parameter description"}
                        ],
                        "returns": "Description of what the tool returns",
                        "endpoint": "API endpoint to call",
                        "method": "HTTP method"
                    }
                ],
                "auth_requirements": {
                    "type": "Type of authentication (API key, OAuth, etc.)",
                    "credentials": ["List of required credentials"]
                },
                "dependencies": [
                    "List of Python package dependencies"
                ]
            }
            """
            
            # Using Deepseek R1 for planning
            response = self.client.chat.completions.create(
                model="deepseek/deepseek-r1-zero:free",
                messages=[{"role": "user", "content": planning_prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                extra_headers={
                    "HTTP-Referer": "https://mcp-saas.dev",
                    "X-Title": "MCP SaaS"
                }
            )
            
            implementation_plan = response.choices[0].message.content
            
            return {"implementation_plan": implementation_plan}
        except Exception as e:
            logger.error(f"Error in planning node: {str(e)}")
            return {"error": f"Planning step failed: {str(e)}"}
    
    async def _coding_node(self, state: AgentState) -> Dict[str, Any]:
        """Coding node for generating MCP server implementation."""
        try:
            coding_prompt = f"""
            You are an expert coding agent that implements MCP (Model Context Protocol) servers using FastMCP.
            
            USER REQUEST: {state.get('latest_user_message', '')}
            
            IMPLEMENTATION PLAN:
            {state.get('implementation_plan', '')}
            
            Your task is to generate complete, working code for an MCP server according to the implementation plan.
            The code should:
            1. Use the FastMCP framework
            2. Implement proper error handling
            3. Follow Python best practices
            4. Include type annotations
            5. Be well documented
            
            Generate the following files:
            1. main.py - The main MCP server implementation
            2. requirements.txt - Dependencies needed
            3. .env.example - Example environment variables
            4. README.md - Documentation for using the MCP server
            
            Return a JSON object with the following structure:
            {
                "files": {
                    "main.py": "Complete Python code here",
                    "requirements.txt": "List of dependencies",
                    ".env.example": "Example environment variables",
                    "README.md": "Documentation"
                }
            }
            """
            
            # Using Qwen for code generation
            response = self.client.chat.completions.create(
                model="qwen/qwen2.5-72b-instruct:free",
                messages=[{"role": "user", "content": coding_prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                extra_headers={
                    "HTTP-Referer": "https://mcp-saas.dev",
                    "X-Title": "MCP SaaS"
                }
            )
            
            generated_code = json.loads(response.choices[0].message.content)
            
            return {"generated_code": generated_code.get("files", {})}
        except Exception as e:
            logger.error(f"Error in coding node: {str(e)}")
            return {"error": f"Code generation failed: {str(e)}"}
    
    async def _validation_node(self, state: AgentState) -> Dict[str, Any]:
        """Validation node for checking the generated code."""
        try:
            # In a real implementation, we would run code validation here
            # For now, we'll just save the template to the database
            
            # Get DB session
            db = next(get_db())
            
            # Create template if not exists
            if not state.get("template_id"):
                # Parse implementation plan for template metadata
                try:
                    plan = json.loads(state.get("implementation_plan", "{}"))
                    service_name = plan.get("service_name", "Custom MCP")
                    description = plan.get("description", "Custom MCP server")
                    
                    # Create template
                    template = Template(
                        name=service_name,
                        description=description,
                        category="custom",
                        is_public=False,
                        created_by=state.get("user_id"),
                        config_schema=plan.get("auth_requirements", {})
                    )
                    
                    db.add(template)
                    db.commit()
                    db.refresh(template)
                    
                    # Store generated files
                    # In a real implementation, save files to disk or DB
                    
                    return {
                        "template_id": template.id,
                        "validation_result": "Template created successfully"
                    }
                except Exception as e:
                    logger.error(f"Error creating template: {str(e)}")
                    return {"error": f"Template creation failed: {str(e)}"}
            
            return {"validation_result": "Validation passed"}
        except Exception as e:
            logger.error(f"Error in validation node: {str(e)}")
            return {"error": f"Validation failed: {str(e)}"}
    
    async def process(self, state: AgentState) -> Dict[str, Any]:
        """
        Process a user request to generate an MCP server.
        
        Args:
            state: The initial state for the workflow
            
        Returns:
            The final state after workflow completion
        """
        try:
            result = await self.workflow.ainvoke(state)
            return result
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return {"error": f"Workflow execution failed: {str(e)}"} 