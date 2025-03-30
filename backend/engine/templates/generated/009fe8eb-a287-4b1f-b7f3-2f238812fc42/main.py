from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import logging
import os
from dotenv import load_dotenv

from client import KiteConnectClient, KiteConnectClientError
from models import GenerateSessionParams, PlaceOrderParams, ModifyOrderParams

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP
mcp = FastMCP(
    service_name="KiteConnect",
    description="MCP server for interacting with the Zerodha Kite Connect API V3, providing tools for order management, portfolio retrieval, market data access, and more."
)

# Initialize Kite Connect Client
API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")

if not API_KEY:
    logger.warning("KITE_API_KEY environment variable not set.")
if not API_SECRET:
    logger.warning("KITE_API_SECRET environment variable not set.")

kite_client = KiteConnectClient(api_key=API_KEY)

@mcp.tool()
def generate_session(params: GenerateSessionParams) -> Dict[str, Any]:
    """
    Generate a user session and obtain an access token using a request token obtained after the login flow.

    Args:
        params: Parameters containing the request_token.

    Returns:
        Dictionary containing user session details including 'access_token', 'public_token', 'user_id', etc.
        The 'access_token' is crucial for subsequent API calls.
    """
    if not API_SECRET:
        logger.error("KITE_API_SECRET is not configured.")
        return {"error": "Server configuration error: KITE_API_SECRET is missing."}

    try:
        logger.info(f"Attempting to generate session for request_token starting with: {params.request_token[:5]}...")
        session_data = kite_client.generate_session(params.request_token, API_SECRET)
        logger.info(f"Successfully generated session for user_id: {session_data.get('user_id')}")
        # Note: The access_token should be stored securely by the caller (e.g., the agent)
        # and passed to subsequent authenticated tool calls.
        return session_data
    except KiteConnectClientError as e:
        logger.error(f"Error generating Kite session: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception("An unexpected error occurred during session generation.")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
def place_order(access_token: str, params: PlaceOrderParams) -> Dict[str, Any]:
    """
    Place an order of a specific variety (regular, amo, co, iceberg, auction).
    Requires a valid access_token obtained from generate_session.

    Args:
        access_token: The access token for the authenticated session.
        params: Parameters for placing the order.

    Returns:
        Dictionary containing the 'order_id' of the placed order or an error message.
    """
    try:
        logger.info(f"Attempting to place order: {params.dict(exclude_unset=True)}")
        order_id = kite_client.place_order(access_token=access_token, params=params)
        logger.info(f"Successfully placed order with ID: {order_id}")
        return {"order_id": order_id}
    except KiteConnectClientError as e:
        logger.error(f"Error placing order: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception("An unexpected error occurred during order placement.")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
def modify_order(access_token: str, params: ModifyOrderParams) -> Dict[str, Any]:
    """
    Modify a pending regular or cover order.
    Requires a valid access_token obtained from generate_session.

    Args:
        access_token: The access token for the authenticated session.
        params: Parameters for modifying the order.

    Returns:
        Dictionary containing the 'order_id' of the modified order or an error message.
    """
    try:
        logger.info(f"Attempting to modify order {params.order_id} with params: {params.dict(exclude={'order_id', 'variety'}, exclude_unset=True)}")
        order_id = kite_client.modify_order(access_token=access_token, params=params)
        logger.info(f"Successfully modified order {params.order_id}. Result ID: {order_id}")
        return {"order_id": order_id}
    except KiteConnectClientError as e:
        logger.error(f"Error modifying order {params.order_id}: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception(f"An unexpected error occurred during order modification for order {params.order_id}.")
        return {"error": f"An unexpected error occurred: {str(e)}"}


if __name__ == "__main__":
    # Example of how to run, typically managed by a process manager like uvicorn
    # uvicorn main:mcp.app --host 0.0.0.0 --port 8000
    logger.info("Starting KiteConnect MCP Server.")
    # The mcp.run() method is for simpler, often single-file examples.
    # For production, use uvicorn directly with mcp.app
    # Example: uvicorn main:mcp.app --reload
    pass # Add uvicorn run command here if needed for simple testing
