import logging
import asyncio
from kiteconnect import KiteConnect
from kiteconnect import exceptions as kite_ex
from typing import Dict, Any, Union
from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams, SuccessResponse, ErrorResponse

logger = logging.getLogger(__name__)

# Mapping Kite exceptions to string identifiers
KITE_EXCEPTION_MAP = {
    kite_ex.InputException: "InputException",
    kite_ex.TokenException: "TokenException",
    kite_ex.PermissionException: "PermissionException",
    kite_ex.OrderException: "OrderException",
    kite_ex.NetworkException: "NetworkException",
    kite_ex.DataException: "DataException",
    kite_ex.GeneralException: "GeneralException",
}

class KiteConnectClient:
    """Client to interact with the Kite Connect API using pykiteconnect."""

    def __init__(self, api_key: str, access_token: str):
        """
        Initializes the KiteConnect client.

        Args:
            api_key: The Kite Connect API key.
            access_token: The Kite Connect access token for the session.

        Raises:
            ValueError: If api_key or access_token is missing.
            kite_ex.TokenException: If the access token is invalid during initialization (e.g., profile fetch).
        """
        if not api_key or not access_token:
            logger.error("Kite API Key or Access Token not provided.")
            raise ValueError("Kite API Key and Access Token are required.")

        self.api_key = api_key
        self.access_token = access_token
        try:
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            logger.info("KiteConnect client initialized successfully.")
            # Optional: Add a check like fetching profile to ensure token validity early
            # try:
            #     self.kite.profile()
            #     logger.info("KiteConnect access token verified.")
            # except kite_ex.TokenException as e:
            #     logger.error(f"KiteConnect TokenException during initialization: {e}")
            #     raise
        except Exception as e:
            logger.exception("Failed to initialize KiteConnect client.")
            raise

    async def _run_sync_kite_call(self, func, *args, **kwargs) -> Union[Dict[str, Any], ErrorResponse]:
        """Runs a synchronous pykiteconnect function in a thread pool."""
        try:
            # Use asyncio.to_thread if Python 3.9+
            # result = await asyncio.to_thread(func, *args, **kwargs)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
            logger.debug(f"Kite API call {func.__name__} successful.")
            return result
        except (kite_ex.InputException,
                kite_ex.TokenException,
                kite_ex.PermissionException,
                kite_ex.OrderException,
                kite_ex.NetworkException,
                kite_ex.DataException,
                kite_ex.GeneralException) as e:
            error_type = KITE_EXCEPTION_MAP.get(type(e), "UnknownKiteException")
            logger.error(f"Kite API Error ({error_type}) in {func.__name__}: {e}", exc_info=False)
            return ErrorResponse(message=str(e), error_type=error_type)
        except Exception as e:
            logger.exception(f"Unexpected error during Kite API call {func.__name__}: {e}")
            return ErrorResponse(message=f"An unexpected error occurred: {str(e)}", error_type="UnexpectedException")

    async def place_order_async(self, params: PlaceOrderParams) -> Union[SuccessResponse, ErrorResponse]:
        """Asynchronously places an order using Kite Connect."""
        logger.info(f"Placing order: {params.tradingsymbol} {params.transaction_type} Qty: {params.quantity}")
        # pykiteconnect expects None for optional fields not provided, Pydantic handles this
        result = await self._run_sync_kite_call(
            self.kite.place_order,
            variety=params.variety,
            exchange=params.exchange,
            tradingsymbol=params.tradingsymbol,
            transaction_type=params.transaction_type,
            quantity=params.quantity,
            product=params.product,
            order_type=params.order_type,
            price=params.price,
            validity=params.validity,
            disclosed_quantity=params.disclosed_quantity,
            trigger_price=params.trigger_price,
            validity_ttl=params.validity_ttl,
            iceberg_legs=params.iceberg_legs,
            iceberg_quantity=params.iceberg_quantity,
            auction_number=params.auction_number,
            tag=params.tag
        )
        if isinstance(result, ErrorResponse):
            return result
        elif isinstance(result, dict) and 'order_id' in result:
            return SuccessResponse(data=OrderResponse(order_id=result['order_id']))
        else:
            logger.error(f"Unexpected response format from place_order: {result}")
            return ErrorResponse(message="Unexpected response format from Kite API", error_type="ApiResponseFormatError")

    async def modify_order_async(self, params: ModifyOrderParams) -> Union[SuccessResponse, ErrorResponse]:
        """Asynchronously modifies a pending order using Kite Connect."""
        logger.info(f"Modifying order ID: {params.order_id} Variety: {params.variety}")
        result = await self._run_sync_kite_call(
            self.kite.modify_order,
            variety=params.variety,
            order_id=params.order_id,
            parent_order_id=params.parent_order_id,
            quantity=params.quantity,
            price=params.price,
            order_type=params.order_type,
            trigger_price=params.trigger_price,
            validity=params.validity,
            disclosed_quantity=params.disclosed_quantity
        )
        if isinstance(result, ErrorResponse):
            return result
        elif isinstance(result, dict) and 'order_id' in result:
             return SuccessResponse(data=OrderResponse(order_id=result['order_id']))
        else:
            logger.error(f"Unexpected response format from modify_order: {result}")
            return ErrorResponse(message="Unexpected response format from Kite API", error_type="ApiResponseFormatError")

    async def cancel_order_async(self, params: CancelOrderParams) -> Union[SuccessResponse, ErrorResponse]:
        """Asynchronously cancels a pending order using Kite Connect."""
        logger.info(f"Cancelling order ID: {params.order_id} Variety: {params.variety}")
        result = await self._run_sync_kite_call(
            self.kite.cancel_order,
            variety=params.variety,
            order_id=params.order_id,
            parent_order_id=params.parent_order_id
        )
        if isinstance(result, ErrorResponse):
            return result
        elif isinstance(result, dict) and 'order_id' in result:
             return SuccessResponse(data=OrderResponse(order_id=result['order_id']))
        else:
            logger.error(f"Unexpected response format from cancel_order: {result}")
            return ErrorResponse(message="Unexpected response format from Kite API", error_type="ApiResponseFormatError")
