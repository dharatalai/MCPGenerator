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

# Load environment variables
load_dotenv()

# Configure LLMs and APIs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
JINA_API_KEY = os.getenv("JINA_API_KEY", "")

# Define state schema
class AgentState(TypedDict):
    latest_user_message: str
    messages: Annotated[List[bytes], lambda x, y: x + y]
    documentation: str
    implementation_plan: str

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

# Initialize agents
planning_llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-4",
    temperature=0.1
)

coding_llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-3.5-turbo",
    temperature=0.2
)

planning_agent = ChatPromptTemplate.from_messages([
    ("system", """You are an expert planning agent that analyzes API documentation and creates detailed plans for implementing code.
    
    Your task is to:
    1. Analyze the documentation provided
    2. Create a detailed plan for implementing the user's request
    3. Identify key API endpoints, parameters, and data structures
    4. Break down the implementation into clear steps for the coding agent
    
    Be specific, thorough, and clear in your plan. Focus on technical details that will help the coding agent implement the solution efficiently.
    """),
    MessagesPlaceholder(variable_name="history"),
    ("human", """
    User request: {latest_user_message}
    
    Documentation: {documentation}
    
    Create a detailed plan for implementing this request. Include key API endpoints, parameters, and a step-by-step approach.
    """)
])

coding_agent = ChatPromptTemplate.from_messages([
    ("system", """You are an expert coding agent that implements solutions based on detailed plans and API documentation.
    
    Your task is to:
    1. Follow the implementation plan provided
    2. Write clean, well-structured, production-ready code
    3. Include error handling, logging, and documentation
    4. Explain key implementation decisions
    
    Provide complete code solutions that can be used directly in production.
    """),
    MessagesPlaceholder(variable_name="history"),
    ("human", """
    User request: {latest_user_message}
    
    Implementation Plan: {implementation_plan}
    
    Documentation: {documentation}
    
    Generate the complete implementation code for this request. Make sure to include all necessary imports, error handling, and comments.
    """)
])

# Define workflow nodes
async def process_docs_node(state: AgentState, doc_url: str):
    """Node for processing documentation"""
    doc_reader = DocumentationReader()
    documentation = await doc_reader.process_documentation(doc_url)
    return {"documentation": documentation}

async def planning_node(state: AgentState):
    """Node for creating implementation plan"""
    result = await planning_llm.ainvoke(
        planning_agent.format_messages(
            latest_user_message=state["latest_user_message"],
            documentation=state["documentation"],
            history=state.get("messages", [])
        )
    )
    return {"implementation_plan": result.content}

async def coding_node(state: AgentState):
    """Node for generating code implementation"""
    result = await coding_llm.ainvoke(
        coding_agent.format_messages(
            latest_user_message=state["latest_user_message"],
            implementation_plan=state["implementation_plan"],
            documentation=state["documentation"],
            history=state.get("messages", [])
        )
    )
    return {"output": result.content}

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