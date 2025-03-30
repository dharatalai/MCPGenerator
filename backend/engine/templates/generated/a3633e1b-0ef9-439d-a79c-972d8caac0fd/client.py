import logging
from typing import Optional, Dict, Any, List
from kiteconnect import KiteConnect
from kiteconnect import exceptions as kite_ex

logger = logging.getLogger(__name__)

# Custom Exception for clarity in MCP layer
class KiteClientError(Exception):
    def __init__(self, message: str, original_exception: Exception = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.original_exception = original_exception
        self.details = details or {}
        if isinstance(original_exception, kite_ex.KiteException):
            # Add KiteException specific details if available
            self.details['kite_code'] = getattr(original_exception, 'code', None)
            self.details['kite_message'] = getattr(original_exception, 'message', None)
        super().__init__(self.message)

class KiteConnectClient:
    """Client to interact with the Zerodha Kite Connect API using pykiteconnect."""

    def __init__(self, api_key: Optional[str], access_token: Optional[str]):
        """
        Initializes the Kite Connect client.

        Args:
            api_key: The API key obtained from Zerodha Kite Developer.
            access_token: The access token obtained after successful login flow.
                      Note: This token is short-lived and needs periodic regeneration.
                      MCP server needs a mechanism to refresh/update this token.
        """
        if not api_key:
            logger.error("Kite API Key is required for KiteConnectClient.")
            raise ValueError("Kite API Key not provided.")

        self.api_key = api_key
        self.access_token = access_token
        self._kite = KiteConnect(api_key=self.api_key)

        if self.access_token:
            try:
                self._kite.set_access_token(self.access_token)
                logger.info("KiteConnect client initialized and access token set.")
            except Exception as e:
                logger.error(f"Failed to initialize KiteConnect with provided access token: {e}")
                # Don't raise here, allow initialization but operations will fail until token is valid
                self.access_token = None # Mark token as invalid
        else:
            logger.warning("KiteConnect client initialized without an access token. API calls will fail.")

    def _ensure_token(self):
        """Checks if the access token is set."""
        if not self.access_token or not self._kite.access_token:
            logger.error("Kite API Access Token is not set or invalid.")
            raise KiteClientError("Kite API Access Token is missing or invalid.",
                                  original_exception=kite_ex.TokenException("Access token not set"))

    def _handle_api_error(self, error: Exception, operation: str) -> KiteClientError:
        """Maps KiteConnect exceptions to KiteClientError."""
        logger.error(f"Kite API error during {operation}: {type(error).__name__} - {error}", exc_info=False)

        if isinstance(error, kite_ex.InputException):
            return KiteClientError(f"Invalid input for {operation}: {error.message}", error)
        elif isinstance(error, kite_ex.TokenException):
            # Access token might have expired or is invalid
            self.access_token = None # Clear potentially invalid token
            self._kite.set_access_token(None)
            return KiteClientError(f"Authentication error (token invalid/expired?): {error.message}", error)
        elif isinstance(error, kite_ex.PermissionException):
            return KiteClientError(f"Permission denied for {operation}: {error.message}", error)
        elif isinstance(error, kite_ex.OrderException):
            return KiteClientError(f"Order placement/modification error: {error.message}", error)
        elif isinstance(error, kite_ex.NetworkException):
            return KiteClientError(f"Network error connecting to Kite API: {error.message}", error)
        elif isinstance(error, kite_ex.GeneralException):
            return KiteClientError(f"General Kite API error: {error.message}", error)
        elif isinstance(error, kite_ex.DataException):
             return KiteClientError(f"Kite Data error: {error.message}", error)
        else:
            # Catch-all for unexpected errors
            return KiteClientError(f"An unexpected error occurred during {operation}: {str(error)}", error)

    def place_order(self, variety: str, exchange: str, tradingsymbol: str,
                      transaction_type: str, quantity: int, product: str,
                      order_type: str, price: Optional[float] = None,
                      validity: Optional[str] = None, disclosed_quantity: Optional[int] = None,
                      trigger_price: Optional[float] = None, tag: Optional[str] = None,
                      iceberg_legs: Optional[int] = None, iceberg_quantity: Optional[int] = None,
                      auction_number: Optional[str] = None, validity_ttl: Optional[int] = None) -> Dict[str, str]:
        """Places an order."""
        self._ensure_token()
        try:
            # Filter out None values as pykiteconnect expects absence of key, not None value
            params = {
                k: v for k, v in locals().items()
                if k not in ['self', 'variety'] and v is not None
            }
            logger.debug(f"Placing order with params: variety={variety}, other_params={params}")
            order_id = self._kite.place_order(variety=variety, **params)
            logger.info(f"Successfully placed order: {order_id}")
            return {"order_id": order_id}
        except Exception as e:
            raise self._handle_api_error(e, "place_order")

    def modify_order(self, variety: str, order_id: str,
                       parent_order_id: Optional[str] = None, quantity: Optional[int] = None,
                       price: Optional[float] = None, order_type: Optional[str] = None,
                       trigger_price: Optional[float] = None, validity: Optional[str] = None,
                       disclosed_quantity: Optional[int] = None) -> Dict[str, str]:
        """Modifies a pending order."""
        self._ensure_token()
        try:
            params = {
                k: v for k, v in locals().items()
                if k not in ['self', 'variety', 'order_id'] and v is not None
            }
            logger.debug(f"Modifying order: variety={variety}, order_id={order_id}, params={params}")
            order_id_resp = self._kite.modify_order(variety=variety, order_id=order_id, **params)
            logger.info(f"Successfully modified order {order_id}: {order_id_resp}")
            return {"order_id": order_id_resp}
        except Exception as e:
            raise self._handle_api_error(e, "modify_order")

    def cancel_order(self, variety: str, order_id: str,
                       parent_order_id: Optional[str] = None) -> Dict[str, str]:
        """Cancels a pending order."""
        self._ensure_token()
        try:
            params = {
                k: v for k, v in locals().items()
                if k not in ['self', 'variety', 'order_id'] and v is not None
            }
            logger.debug(f"Cancelling order: variety={variety}, order_id={order_id}, params={params}")
            order_id_resp = self._kite.cancel_order(variety=variety, order_id=order_id, **params)
            logger.info(f"Successfully cancelled order {order_id}: {order_id_resp}")
            return {"order_id": order_id_resp}
        except Exception as e:
            raise self._handle_api_error(e, "cancel_order")

    # --- Placeholder for other potential methods --- 

    # def get_orders(self) -> List[Dict[str, Any]]:
    #     """Retrieves the list of orders for the day."""
    #     self._ensure_token()
    #     try:
    #         logger.debug("Fetching orders")
    #         orders = self._kite.orders()
    #         logger.info(f"Successfully fetched {len(orders)} orders.")
    #         return orders
    #     except Exception as e:
    #         raise self._handle_api_error(e, "get_orders")

    # def get_trades(self, order_id: Optional[str] = None) -> List[Dict[str, Any]]:
    #     """Retrieves the list of trades for the day or for a specific order."""
    #     self._ensure_token()
    #     try:
    #         if order_id:
    #             logger.debug(f"Fetching trades for order_id: {order_id}")
    #             trades = self._kite.order_trades(order_id=order_id)
    #             logger.info(f"Successfully fetched {len(trades)} trades for order {order_id}.")
    #         else:
    #             logger.debug("Fetching all trades for the day")
    #             trades = self._kite.trades()
    #             logger.info(f"Successfully fetched {len(trades)} trades for the day.")
    #         return trades
    #     except Exception as e:
    #         raise self._handle_api_error(e, "get_trades")

    # def get_instruments(self, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
    #     """Retrieves the list of instruments."""
    #     # No token needed for this usually
    #     try:
    #         logger.debug(f"Fetching instruments for exchange: {exchange or 'all'}")
    #         instruments = self._kite.instruments(exchange=exchange)
    #         logger.info(f"Successfully fetched {len(instruments)} instruments.")
    #         return instruments
    #     except Exception as e:
    #         raise self._handle_api_error(e, "get_instruments")
