from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated, List, Any
from jina import Client as JinaClient
from dotenv import load_dotenv
from utils.utils import write_to_log
import os
import openai
import json
import logging
import re

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure LLMs and APIs
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
JINA_API_KEY = os.getenv("JINA_API_KEY", "")

# Fallback OpenRouter key if none is found in environment
if not OPENROUTER_API_KEY:
    logger.warning("No OpenRouter API key found in environment variables. Using a demo key for testing.")
    OPENROUTER_API_KEY = "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"

# Initialize OpenRouter client
openai_client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://mcp-saas.dev",
        "X-Title": "MCP SaaS"
    }
)

# Define model configurations
PLANNING_MODEL = "deepseek/deepseek-r1-zero:free"
CODING_MODEL = "anthropic/claude-3-haiku:free"

# Define state schema
class AgentState(TypedDict):
    latest_user_message: str
    messages: Annotated[List[bytes], lambda x, y: x + y]
    documentation: str
    implementation_plan: str
    output: str

# Helper function to extract JSON from various formats
def extract_json_from_response(content: str) -> str:
    """Extract JSON from a response that might be wrapped in markdown or LaTeX."""
    # Look for JSON within LaTeX \boxed{} command
    boxed_match = re.search(r'\\boxed\{\s*```(?:json)?\s*(.*?)```\s*\}', content, re.DOTALL)
    if boxed_match:
        return boxed_match.group(1).strip()
    
    # Look for JSON within markdown code blocks
    code_block_match = re.search(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()
    
    # If no structured format is found, return the original content
    return content

class DocumentationReader:
    """Class to read and process documentation using Jina AI"""
    
    def __init__(self):
        """Initialize the documentation reader with Jina API key"""
        self.jina_client = JinaClient(api_key=JINA_API_KEY)
    
    async def process_documentation(self, doc_url: str) -> str:
        """Extract and process documentation from the given URL"""
        try:
            response = await self.jina_client.crawl(
                url=doc_url,
                max_depth=2,
                extract_text=True
            )
            content = response.get("text", "")
            write_to_log(f"Retrieved {len(content)} characters of documentation from {doc_url}")
            
            if len(content) > 50000:
                content = content[:50000]
            return content
            
        except Exception as e:
            write_to_log(f"Error processing documentation from {doc_url}: {str(e)}")
            return f"Error retrieving documentation: {str(e)}"

# Define workflow nodes
async def process_docs_node(state: AgentState, doc_url: str):
    """Node for processing documentation"""
    doc_reader = DocumentationReader()
    documentation = await doc_reader.process_documentation(doc_url)
    return {"documentation": documentation}

async def planning_node(state: AgentState):
    """Node for creating implementation plan"""
    try:
        planning_prompt = f"""
        You are an expert planning agent that analyzes API documentation and creates detailed plans for implementing code.
        
        Your task is to:
        1. Analyze the documentation provided
        2. Create a detailed plan for implementing the user's request
        3. Identify key API endpoints, parameters, and data structures
        4. Break down the implementation into clear steps for the coding agent
        
        Be specific, thorough, and clear in your plan. Focus on technical details that will help the coding agent implement the solution efficiently.
        
        User request: {state["latest_user_message"]}
        
        Documentation: {state["documentation"][:7000]}
        
        Create a detailed plan for implementing this request. Include key API endpoints, parameters, and a step-by-step approach.
        
        IMPORTANT: Your response must be ONLY the JSON object without any LaTeX formatting or markdown code blocks.
        """
        
        # Using Deepseek R1 for planning
        response = openai_client.chat.completions.create(
            model=PLANNING_MODEL,
            messages=[{"role": "user", "content": planning_prompt}],
            temperature=0.1,
            extra_headers={
                "HTTP-Referer": "https://mcp-saas.dev",
                "X-Title": "MCP SaaS"
            }
        )
        
        implementation_plan = response.choices[0].message.content
        
        # Extract JSON if needed
        implementation_plan = extract_json_from_response(implementation_plan)
        
        return {"implementation_plan": implementation_plan}
    except Exception as e:
        logger.error(f"Error in planning node: {str(e)}")
        return {"error": f"Planning step failed: {str(e)}"}

async def coding_node(state: AgentState):
    """Node for generating code implementation"""
    try:
        coding_prompt = f"""
        You are an expert coding agent that implements solutions based on detailed plans and API documentation.
        
        Your task is to:
        1. Follow the implementation plan provided
        2. Write clean, well-structured, production-ready code
        3. Include error handling, logging, and documentation
        4. Explain key implementation decisions
        
        Provide complete code solutions that can be used directly in production.
        
        User request: {state["latest_user_message"]}
        
        Implementation Plan: {state["implementation_plan"]}
        
        Documentation: {state["documentation"][:5000]}
        
        Generate the complete implementation code for this request. Make sure to include all necessary imports, error handling, and comments.
        """
        
        # Using Claude instead of Qwen
        response = openai_client.chat.completions.create(
            model=CODING_MODEL,
            messages=[{"role": "user", "content": coding_prompt}],
            temperature=0.2,
            extra_headers={
                "HTTP-Referer": "https://mcp-saas.dev",
                "X-Title": "MCP SaaS"
            }
        )
        
        output = response.choices[0].message.content
        
        # Extract JSON if needed
        output = extract_json_from_response(output)
        
        return {"output": output}
    except Exception as e:
        logger.error(f"Error in coding node: {str(e)}")
        return {"error": f"Code generation failed: {str(e)}"}

def create_workflow():
    """Create the agent workflow using LangGraph"""
    
    # Build workflow
    builder = StateGraph(AgentState)
    
    # Add nodes
    builder.add_node("process_docs", process_docs_node)
    builder.add_node("planning", planning_node)
    builder.add_node("coding", coding_node)
    
    # Set edges
    builder.add_edge(START, "process_docs")
    builder.add_edge("process_docs", "planning")
    builder.add_edge("planning", "coding")
    builder.add_edge("coding", END)
    
    # Configure persistence
    memory = MemorySaver()
    workflow = builder.compile(checkpointer=memory)
    
    return workflow 