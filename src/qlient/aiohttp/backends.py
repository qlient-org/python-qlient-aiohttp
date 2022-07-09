import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, AsyncGenerator, List

import aiohttp
import qlient.core.__meta__
from qlient.core import AsyncBackend, GraphQLRequest, GraphQLResponse, GraphQLSubscriptionRequest

from qlient.aiohttp.exceptions import ConnectionRejected

logger = logging.getLogger(qlient.core.__meta__.__title__)

# Protocols
GRAPHQL_WS_PROTOCOL = "graphql-ws"
GRAPHQL_TRANSPORT_WS_PROTOCOL = "graphql-transport-ws"

# GQL Control Strings
CONNECTION_INIT = "connection_init"
CONNECTION_ACKNOWLEDGED = "connection_ack"
CONNECTION_ERROR = "connection_error"
CONNECTION_KEEP_ALIVE = "ka"
START = "start"
STOP = "stop"
CONNECTION_TERMINATE = "connection_terminate"
DATA = "data"
ERROR = "error"
COMPLETE = "complete"

SUBSCRIPTION_ID_TO_WS = {}


class AIOHTTPBackend(AsyncBackend):

    @classmethod
    def generate_subscription_id(cls) -> str:
        """Class method to generate unique subscription ids

        Returns:
            A unique subscription id
        """
        return f"qlient:{cls.__name__}:{uuid.uuid4()}".replace("-", "")

    @staticmethod
    def adapt_to_websocket_endpoint(endpoint: str) -> str:
        """Adapt the http endpoint to websocket endpoint

        Args:
            endpoint: the endpoint

        Returns:
            a websocket url
        """
        if endpoint.startswith("https://"):
            return "wss://" + endpoint.replace("https://", "")
        elif endpoint.startswith("http://"):
            return "ws://" + endpoint.replace("http://", "")
        else:
            return endpoint

    @staticmethod
    def make_payload(request: GraphQLRequest) -> Dict[str, Any]:
        """Static method for generating the request payload

        Args:
            request: holds the graphql request

        Returns:
            the payload to send as dictionary
        """
        return {
            "query": request.query,
            "operationName": request.operation_name,
            "variables": request.variables,
        }

    def __init__(
            self,
            endpoint: str,
            ws_endpoint: Optional[str] = None,
            session: Optional[aiohttp.ClientSession] = None,
            subscription_protocols: Optional[List[str]] = None,
    ):
        if ws_endpoint is None:
            ws_endpoint = AIOHTTPBackend.adapt_to_websocket_endpoint(endpoint)

        if not subscription_protocols:
            subscription_protocols = [GRAPHQL_WS_PROTOCOL, GRAPHQL_TRANSPORT_WS_PROTOCOL]

        self.endpoint: str = endpoint
        self.ws_endpoint: str = ws_endpoint
        self.subscription_protocols = subscription_protocols
        self._session: Optional[aiohttp.ClientSession] = session

    @property
    @asynccontextmanager
    async def session(self) -> aiohttp.ClientSession:
        if self._session is not None:
            yield self._session
            return

        async with aiohttp.ClientSession() as session:
            yield session

    async def execute_query(self, request: GraphQLRequest) -> GraphQLResponse:
        """

        Args:
            request:

        Returns:

        """
        payload = self.make_payload(request)
        async with self.session as session:
            async with session.post(self.endpoint, json=payload) as response:
                response_body = await response.json()
                return GraphQLResponse(request, response_body)

    async def execute_mutation(self, request: GraphQLRequest) -> GraphQLResponse:
        """

        Args:
            request:

        Returns:

        """
        return await self.execute_query(request)

    async def execute_subscription(self, request: GraphQLSubscriptionRequest) -> GraphQLResponse:
        """

        Args:
            request:

        Returns:

        """
        payload = self.make_payload(request)
        async with self.session as session:
            request.subscription_id = request.subscription_id or self.generate_subscription_id()
            ws = await session.ws_connect(
                self.endpoint,
                protocols=self.subscription_protocols,
                autoclose=False
            )
            # initiate connection
            await ws.send_json({"type": CONNECTION_INIT, "payload": request.options})

            initial_response = await ws.receive_json()
            if initial_response.get("type") != CONNECTION_ACKNOWLEDGED:
                logger.critical(f"The server did not acknowledged the connection.")
                raise ConnectionRejected("The server did not acknowledge the connection.")

            # connection acknowledged, send request
            await ws.send_json({"type": START, "id": request.subscription_id, "payload": payload})

            SUBSCRIPTION_ID_TO_WS[request.subscription_id] = ws

            async def _make_generator() -> AsyncGenerator:
                msg: aiohttp.WSMessage
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.ERROR:
                        # break the iterator
                        await ws.close()
                        break
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        raise TypeError(f"Expected {aiohttp.WSMsgType.TEXT}; Got {msg.type}")

                    data = msg.json()
                    data_type = data["type"]

                    if data_type in (CONNECTION_TERMINATE, CONNECTION_ERROR, COMPLETE):
                        # break the iterator
                        await ws.close()
                        break

                    if data_type == CONNECTION_KEEP_ALIVE:
                        continue

                    yield GraphQLResponse(request, data["payload"])

            return GraphQLResponse(request, _make_generator())
