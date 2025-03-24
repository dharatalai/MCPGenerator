from mcp.server.fastmcp import FastMCP
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Any
import requests
import asyncio
import uuid
import os
import sys

# Add the parent directory to sys.path to allow importing from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utility functions
from utils.utils import write_to_log

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("doc_assistant")  # Change name to match your service

# Store active threads
active_threads: Dict[str, List[str]] = {}

# FastAPI service URL - this is the backend service that will process the requests
SERVICE_URL = os.getenv("SERVICE_URL", "http://localhost:8100")

@mcp.tool()
async def create_thread() -> str:
    """Create a new conversation thread.
    Always call this tool before invoking the agent for the first time in a conversation.
    (if you don't already have a thread ID)
    
    Returns:
        str: A unique thread ID for the conversation
    """
    thread_id = str(uuid.uuid4())
    active_threads[thread_id] = []
    write_to_log(f"Created new thread: {thread_id}")
    return thread_id


def _make_request(thread_id: str, user_input: str, config: dict) -> str:
    """Make synchronous request to the backend service"""
    try:
        response = requests.post(
            f"{SERVICE_URL}/process",
            json={
                "message": user_input,
                "thread_id": thread_id,
                "is_first_message": not active_threads[thread_id],
                "config": config
            },
            timeout=300  # 5 minute timeout for long-running operations
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        write_to_log(f"Request timed out for thread {thread_id}")
        raise TimeoutError("Request to service timed out. The operation took longer than expected.")
    except requests.exceptions.RequestException as e:
        write_to_log(f"Request failed for thread {thread_id}: {str(e)}")
        raise


@mcp.tool()
async def process_documentation(thread_id: str, user_input: str, doc_url: str) -> str:
    """Process user request with documentation URL.
    This tool will analyze documentation from the provided URL and generate code or responses.
    
    Args:
        thread_id: The conversation thread ID
        user_input: Description of what you want to build, query, or problem to solve
        doc_url: URL to the API documentation for reference
    
    Returns:
        str: The agent's response with generated code or explanation
    """
    if thread_id not in active_threads:
        write_to_log(f"Error: Thread not found - {thread_id}")
        raise ValueError("Thread not found")

    write_to_log(f"Processing message for thread {thread_id}: {user_input}")
    write_to_log(f"Documentation URL: {doc_url}")

    config = {
        "configurable": {
            "thread_id": thread_id,
            "doc_url": doc_url
        }
    }
    
    try:
        result = await asyncio.to_thread(_make_request, thread_id, user_input, config)
        active_threads[thread_id].append(user_input)
        return result['response']
        
    except Exception as e:
        raise


if __name__ == "__main__":
    write_to_log("Starting MCP server")
    
    # Run MCP server
    mcp.run(transport='stdio') 