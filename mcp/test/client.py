import asyncio
from fastmcp import Client

client = Client("http://[::1]:8031/mcp")

async def test_get_cave_location(cave: str, state: str, county: str):
    async with client:
        resp = await client.call_tool("get_cave_location", {"cave": cave, "state": state, "county": county})
        print()
        print(cave)
        for item in resp.structured_content['result']:
            print(item)

async def test_general_caving_information(query: str):
    async with client:
        resp = await client.call_tool("general_caving_information", {"query": query})
        print()
        print(query)
        for item in resp.structured_content['result']:
            print(item)

asyncio.run(test_get_cave_location("Nellies Cave", "VA", "Montgomery"))
asyncio.run(test_get_cave_location("links cave", "VA", "Giles"))
#asyncio.run(test_get_cave_location("new river", "VA", "Giles"))
#asyncio.run(test_get_cave_location("tawneys", "VA", "Giles"))
#asyncio.run(test_get_cave_location("staty fork", "WV", "Pocahontas"))
#asyncio.run(test_general_caving_information("broken sunnto"))
