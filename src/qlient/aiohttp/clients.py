from typing import Union

from qlient.core import AsyncClient, Backend

from qlient.aiohttp.backends import AIOHTTPBackend


class AIOHTTPClient(AsyncClient):

    def __init__(
            self,
            backend: Union[str, Backend],
            **kwargs
    ):
        if isinstance(backend, str):
            backend = AIOHTTPBackend(backend)

        super(AIOHTTPClient, self).__init__(backend, **kwargs)
