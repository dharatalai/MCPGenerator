import logging
from kiteconnect import KiteConnect
from kiteconnect import exceptions as kite_exceptions
from models import PlaceOrderParams, ModifyOrderParams
from typing import Dict, Any

logger = logging.getLogger(__name__)

class KiteConnectClientError(Exception):
    """Custom exception for KiteConnectClient errors."""
    pass

class KiteConnectClient:
    """Client to interact with the Zerodha Kite Connect API."""

    def __init__(self, api_key: str, timeout: int = 30):
        """
        Initializes the KiteConnectClient.

        Args:
            api_key: Your Kite Connect API key.
            timeout: Request timeout in seconds.
        """
        if not api_key:
            raise ValueError("API key is required to initialize KiteConnectClient.")
        self.api_key = api_key
        # Initialize KiteConnect instance without access token initially
        self.kite = KiteConnect(api_key=self.api_key)
        self.timeout = timeout
        # Note: access_token is set dynamically via set_access_token or during method calls

    def _handle_kite_exception(self, e: Exception, context: str):
        """Handles common Kite Connect exceptions and raises KiteConnectClientError."""
        error_message = f"Kite API Error ({context}): {type(e).__name__} - {str(e)}"
        logger.error(error_message)
        if isinstance(e, kite_exceptions.TokenException):
            raise KiteConnectClientError(f"Authentication error: {str(e)}. Please regenerate the session.") from e
        elif isinstance(e, kite_exceptions.PermissionException):
            raise KiteConnectClientError(f"Permission denied: {str(e)}.") from e
        elif isinstance(e, kite_exceptions.InputException):
            raise KiteConnectClientError(f"Invalid input: {str(e)}.") from e
        elif isinstance(e, kite_exceptions.OrderException):
            raise KiteConnectClientError(f"Order placement/modification error: {str(e)}.") from e
        elif isinstance(e, kite_exceptions.NetworkException):
            raise KiteConnectClientError(f"Network error communicating with Kite API: {str(e)}.") from e
        elif isinstance(e, kite_exceptions.GeneralException):
            raise KiteConnectClientError(f"General Kite API error: {str(e)}.") from e
        else:
            # Catch any other unexpected Kite exceptions
            raise KiteConnectClientError(error_message) from e

    def generate_session(self, request_token: str, api_secret: str) -> Dict[str, Any]:
        """
        Generates a user session using the request token and API secret.

        Args:
            request_token: The one-time request token.
            api_secret: Your Kite Connect API secret.

        Returns:
            Dictionary containing session details (access_token, public_token, etc.).

        Raises:
            KiteConnectClientError: If session generation fails.
        """
        if not api_secret:
            raise ValueError("API secret is required to generate a session.")
        try:
            logger.debug("Generating Kite session...")
            session_data = self.kite.generate_session(request_token, api_secret=api_secret)
            logger.info(f"Kite session generated successfully for user: {session_data.get('user_id')}")
            # It's recommended NOT to store the access token within the client instance
            # long-term in a multi-user or stateless environment like MCP.
            # Pass it explicitly to methods requiring authentication.
            return session_data
        except Exception as e:
            self._handle_kite_exception(e, "generate_session")

    def place_order(self, access_token: str, params: PlaceOrderParams) -> str:
        """
        Places an order.

        Args:
            access_token: The valid access token for the session.
            params: An instance of PlaceOrderParams containing order details.

        Returns:
            The order ID of the placed order.

        Raises:
            KiteConnectClientError: If placing the order fails.
        """
        self.kite.set_access_token(access_token)
        try:
            # Prepare parameters for the kiteconnect library call
            order_params = {
                "exchange": params.exchange,
                "tradingsymbol": params.tradingsymbol,
                "transaction_type": params.transaction_type,
                "quantity": params.quantity,
                "product": params.product,
                "order_type": params.order_type,
                "price": params.price,
                "trigger_price": params.trigger_price,
                "disclosed_quantity": params.disclosed_quantity,
                "validity": params.validity,
                "validity_ttl": params.validity_ttl,
                "iceberg_legs": params.iceberg_legs,
                "iceberg_quantity": params.iceberg_quantity,
                "auction_number": params.auction_number,
                "tag": params.tag
            }
            # Remove None values as kiteconnect expects absent keys, not None values
            order_params = {k: v for k, v in order_params.items() if v is not None}

            logger.debug(f"Placing order with variety '{params.variety}' and params: {order_params}")
            order_id = self.kite.place_order(variety=params.variety, **order_params)
            logger.info(f"Order placed successfully. Order ID: {order_id}")
            return order_id
        except Exception as e:
            self._handle_kite_exception(e, f"place_order ({params.tradingsymbol})")
        finally:
            # Clear the access token after use if managing state per-request
            self.kite.set_access_token(None)

    def modify_order(self, access_token: str, params: ModifyOrderParams) -> str:
        """
        Modifies a pending order.

        Args:
            access_token: The valid access token for the session.
            params: An instance of ModifyOrderParams containing modification details.

        Returns:
            The order ID of the modified order.

        Raises:
            KiteConnectClientError: If modifying the order fails.
        """
        self.kite.set_access_token(access_token)
        try:
            # Prepare parameters for the kiteconnect library call
            modify_params = {
                "parent_order_id": params.parent_order_id,
                "quantity": params.quantity,
                "price": params.price,
                "trigger_price": params.trigger_price,
                "order_type": params.order_type,
                "disclosed_quantity": params.disclosed_quantity,
                "validity": params.validity
            }
            # Remove None values
            modify_params = {k: v for k, v in modify_params.items() if v is not None}

            logger.debug(f"Modifying order '{params.order_id}' with variety '{params.variety}' and params: {modify_params}")
            order_id = self.kite.modify_order(
                variety=params.variety,
                order_id=params.order_id,
                **modify_params
            )
            logger.info(f"Order '{params.order_id}' modified successfully. Result Order ID: {order_id}")
            return order_id
        except Exception as e:
            self._handle_kite_exception(e, f"modify_order ({params.order_id})")
        finally:
            # Clear the access token after use
            self.kite.set_access_token(None)

    # Add other Kite Connect API methods as needed (e.g., get_holdings, get_positions, get_quote, etc.)
