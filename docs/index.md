# Introduction

[![DeepSource](https://deepsource.io/gh/qlient-org/python-qlient-aiohttp.svg/?label=active+issues&token=2ZJ0b1dinekjVtwgJHSy286C)](https://deepsource.io/gh/qlient-org/python-qlient-aiohttp/?ref=repository-badge)
[![DeepSource](https://deepsource.io/gh/qlient-org/python-qlient-aiohttp.svg/?label=resolved+issues&token=2ZJ0b1dinekjVtwgJHSy286C)](https://deepsource.io/gh/qlient-org/python-qlient-aiohttp/?ref=repository-badge)
[![pypi](https://img.shields.io/pypi/v/qlient-aiohttp.svg)](https://pypi.python.org/pypi/qlient-aiohttp)
[![versions](https://img.shields.io/pypi/pyversions/qlient-aiohttp.svg)](https://github.com/qlient-org/python-qlient-aiohttp)
[![license](https://img.shields.io/github/license/qlient-org/python-qlient-aiohttp.svg)](https://github.com/qlient-org/python-qlient-aiohttp/blob/master/LICENSE)

A blazingly fast and modern graphql client based on qlient-core and aiohttp

## Key Features

* Compatible with Python 3.7 and above
* Build on top of ``qlient-core`` and ``aiohttp``

## Quick Preview

_This preview is using the official [github/graphql/swapi-graphql]() graphql api._

```python
import asyncio

from qlient.aiohttp import AIOHTTPClient, GraphQLResponse


async def main():
    async with AIOHTTPClient("https://swapi-graphql.netlify.app/.netlify/functions/index") as client:
        result: GraphQLResponse = await client.query.film(
            ["title", "id"],  # fields selection
            id="ZmlsbXM6MQ=="  # query arguments
        )

        print(result.request.query)
        print(result.data)


asyncio.run(main())
```

Which results in the following query being sent to the server

```graphql
query film($id: ID) {
    film(id: $id) {
        title
        id
    }
}
```

And returns the body below

```json
{
  "film": {
    "title": "A New Hope",
    "id": "ZmlsbXM6MQ=="
  }
}
```