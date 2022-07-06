import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, AsyncGenerator, List

import aiohttp
import qlient.core.__meta__
from qlient.core import AsyncBackend, GraphQLRequest, GraphQLResponse

from qlient.aiohttp.exceptions import ConnectionRejected

logger = logging.getLogger(qlient.core.__meta__.__title__)


class AIOHTTPBackend(AsyncBackend):

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

    @staticmethod
    async def make_generator(socket: aiohttp.ClientWebSocketResponse) -> AsyncGenerator:
        msg: aiohttp.WSMessage
        async for msg in socket:
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            yield msg.json()

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
            subscription_protocols = ["graphql-ws", "graphql-transport-ws"]

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
        payload = self.make_payload(request)
        async with self.session as session:
            async with session.post(self.endpoint, json=payload) as response:
                response_body = await response.json()
                return GraphQLResponse(request, response_body)

    async def execute_mutation(self, request: GraphQLRequest) -> GraphQLResponse:
        return await self.execute_query(request)

    async def execute_subscription(self, request: GraphQLRequest) -> GraphQLResponse:
        payload = self.make_payload(request)
        async with self.session as session:
            async with session.ws_connect(self.endpoint, protocols=self.subscription_protocols) as ws:
                # initiate connection
                await ws.send_json({"type": "connection_init", "payload": {}})

                initial_response = await ws.receive_json()
                if initial_response.get("type") != "connection_ack":
                    logger.critical(f"The server did not acknowledged the connection.")
                    raise ConnectionRejected("The server did not acknowledge the connection.")

                # connection acknowledged, send request
                await ws.send_json(payload)

                return GraphQLResponse(request, self.make_generator(ws))
