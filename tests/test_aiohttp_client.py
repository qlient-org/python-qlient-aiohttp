import pytest
from qlient.core import GraphQLResponse, GraphQLSubscriptionRequest

from qlient.aiohttp.clients import AIOHTTPClient


@pytest.mark.asyncio
async def test_aiohttp_client_str(qlient_aiohttp_client: AIOHTTPClient):
    assert qlient_aiohttp_client.schema is not None


@pytest.mark.asyncio
async def test_async_client_query(qlient_aiohttp_client: AIOHTTPClient):
    result = await qlient_aiohttp_client.query.getBooks(_fields=["title", "author"])
    assert isinstance(result, GraphQLResponse)
    assert isinstance(result.data["getBooks"], list)


@pytest.mark.asyncio
async def test_async_client_mutation(qlient_aiohttp_client: AIOHTTPClient):
    result = await qlient_aiohttp_client.mutation.addBook(
        _fields=["title", "author"], title="1984", author="George Orwell"
    )
    assert isinstance(result, GraphQLResponse)
    assert isinstance(result.data["addBook"], dict)
    assert result.data["addBook"] == {"title": "1984", "author": "George Orwell"}


@pytest.mark.asyncio
async def test_async_client_subscription(qlient_aiohttp_client: AIOHTTPClient):
    count = 0
    result = await qlient_aiohttp_client.subscription.count(target=3, _subscription_id="123", _options={"foo": "bar"})
    assert isinstance(result, GraphQLResponse)
    assert isinstance(result.request, GraphQLSubscriptionRequest)
    assert result.request.subscription_id == "123"
    assert result.request.options == {"foo": "bar"}
    async for num in result:
        assert count == num.data["count"]
        count += 1

    assert count == 3
