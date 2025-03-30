import os
import logging
from kiteconnect import KiteConnect
from kiteconnect import exceptions as kite_ex

logger = logging.getLogger(__name__)

# Custom Exception for KiteConnect Client Errors
class KiteConnectError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details

class KiteConnectClient:
    """Client to interact with the Zerodha Kite Connect API using pykiteconnect."""

    def __init__(self):
        """Initializes the KiteConnect client using API key and access token from environment variables."""
        self.api_key = os.getenv("KITE_API_KEY")
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")

        if not self.api_key:
            raise KiteConnectError("KITE_API_KEY environment variable not set.")
        # Access token is crucial for authenticated calls
        if not self.access_token:
            logger.warning("KITE_ACCESS_TOKEN environment variable not set. Authenticated calls will fail.")
            # Depending on use case, might raise error or allow partial functionality
            # raise KiteConnectError("KITE_ACCESS_TOKEN environment variable not set.")

        try:
            self.kite = KiteConnect(api_key=self.api_key)
            # Set access token if available. Most methods require it.
            if self.access_token:
                self.kite.set_access_token(self.access_token)
                logger.info("KiteConnect client initialized and access token set.")
            else:
                logger.warning("KiteConnect client initialized WITHOUT access token. Only public methods might work.")

            # Optional: Set a default timeout (in seconds)
            self.kite.set_timeout(10)

        except Exception as e:
            logger.exception("Failed to initialize KiteConnect instance")
            raise KiteConnectError(f"Failed to initialize KiteConnect: {e}")

    def _handle_api_error(self, error: Exception, context: str):
        """Handles exceptions raised by the KiteConnect library."""
        error_type = type(error).__name__
        error_message = str(error)
        details = {"type": error_type, "message": error_message}

        if isinstance(error, kite_ex.InputException):
            logger.error(f"Input Error during {context}: {error_message}")
            raise KiteConnectError(f"Invalid input provided for {context}.", details=details)
        elif isinstance(error, kite_ex.TokenException):
            logger.error(f"Token Error during {context}: {error_message}. Check API Key and Access Token.")
            raise KiteConnectError(f"Authentication error during {context}. Please check credentials.", details=details)
        elif isinstance(error, kite_ex.PermissionException):
            logger.error(f"Permission Error during {context}: {error_message}")
            raise KiteConnectError(f"Permission denied for {context}.", details=details)
        elif isinstance(error, kite_ex.OrderException):
            logger.error(f"Order Placement/Modification Error during {context}: {error_message}")
            raise KiteConnectError(f"Order error during {context}.", details=details)
        elif isinstance(error, kite_ex.NetworkException):
            logger.error(f"Network Error during {context}: {error_message}")
            raise KiteConnectError(f"Network error communicating with Kite API during {context}.", details=details)
        elif isinstance(error, kite_ex.GeneralException):
            logger.error(f"General Kite API Error during {context}: {error_message}")
            raise KiteConnectError(f"A general Kite API error occurred during {context}.", details=details)
        else:
            logger.exception(f"An unexpected error occurred during {context}")
            raise KiteConnectError(f"An unexpected error occurred during {context}.", details=details)

    def place_order(self, **kwargs):
        """Places an order."""
        context = "placing order"
        if not self.access_token:
            raise KiteConnectError("Access token is required for placing orders.")
        try:
            # Filter out None values before sending to kite.place_order
            order_params = {k: v for k, v in kwargs.items() if v is not None}
            logger.debug(f"Placing order with filtered params: {order_params}")
            return self.kite.place_order(**order_params)
        except Exception as e:
            self._handle_api_error(e, context)

    def modify_order(self, **kwargs):
        """Modifies an existing order."""
        context = f"modifying order {kwargs.get('order_id')}"
        if not self.access_token:
            raise KiteConnectError("Access token is required for modifying orders.")
        try:
            # Filter out None values
            modify_params = {k: v for k, v in kwargs.items() if v is not None}
            logger.debug(f"Modifying order with filtered params: {modify_params}")
            return self.kite.modify_order(**modify_params)
        except Exception as e:
            self._handle_api_error(e, context)

    def cancel_order(self, **kwargs):
        """Cancels an order."""
        context = f"cancelling order {kwargs.get('order_id')}"
        if not self.access_token:
            raise KiteConnectError("Access token is required for cancelling orders.")
        try:
            # Filter out None values
            cancel_params = {k: v for k, v in kwargs.items() if v is not None}
            logger.debug(f"Cancelling order with filtered params: {cancel_params}")
            return self.kite.cancel_order(**cancel_params)
        except Exception as e:
            self._handle_api_error(e, context)

    def get_orders(self):
        """Retrieves the list of orders for the day."""
        context = "fetching orders"
        if not self.access_token:
            raise KiteConnectError("Access token is required for fetching orders.")
        try:
            logger.debug("Fetching all orders for the day")
            return self.kite.orders()
        except Exception as e:
            self._handle_api_error(e, context)
