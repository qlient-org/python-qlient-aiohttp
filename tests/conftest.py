import asyncio
from typing import List, AsyncGenerator

import aiohttp.web
import pytest
import strawberry
import strawberry.aiohttp.views
import strawberry.subscriptions

from qlient.aiohttp import AIOHTTPBackend, AIOHTTPClient


@pytest.fixture
def strawberry_schema() -> strawberry.Schema:
    @strawberry.type
    class Book:
        title: str
        author: str

    my_books = [
        Book(
            title="The Great Gatsby",
            author="F. Scott Fitzgerald",
        )
    ]

    @strawberry.type
    class Query:
        @strawberry.field
        def get_books(self) -> List[Book]:
            return my_books

    @strawberry.type
    class Mutation:
        @strawberry.mutation
        def add_book(self, title: str, author: str) -> Book:
            book = Book(title=title, author=author)
            my_books.append(book)
            return book

    @strawberry.type
    class Subscription:
        @strawberry.subscription
        async def count(self, target: int = 10) -> AsyncGenerator[int, None]:
            for i in range(target):
                yield i
                await asyncio.sleep(0.1)

    # this line creates the strawberry schema
    return strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)


@pytest.fixture
def qlient_aiohttp_app(strawberry_schema) -> aiohttp.web.Application:
    app = aiohttp.web.Application()
    app.router.add_route(
        "*",
        "/graphql",
        strawberry.aiohttp.views.GraphQLView(
            schema=strawberry_schema,
            subscription_protocols=[
                strawberry.subscriptions.GRAPHQL_TRANSPORT_WS_PROTOCOL,
                strawberry.subscriptions.GRAPHQL_WS_PROTOCOL,
            ],
        ),
    )

    return app


@pytest.fixture
async def qlient_aiohttp_client(aiohttp_client, qlient_aiohttp_app) -> AIOHTTPClient:
    backend = AIOHTTPBackend(
        "/graphql", session=await aiohttp_client(qlient_aiohttp_app)  # noqa
    )
    async with AIOHTTPClient(backend) as client:
        return client
