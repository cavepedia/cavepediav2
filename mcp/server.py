from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from psycopg.rows import dict_row
import cohere
import dotenv
import psycopg
import os
import json

dotenv.load_dotenv('/home/pew/scripts-private/loser/cavepedia-v2/poller.env')

COHERE_API_KEY = os.getenv('COHERE_API_KEY')

co = cohere.ClientV2(COHERE_API_KEY)
conn = psycopg.connect(
    host='::1',
    port=9030,
    dbname='cavepediav2_db',
    user='cavepediav2_user',
    password='cavepediav2_pw',
    row_factory=dict_row,
)

mcp = FastMCP("Cavepedia MCP")

def get_user_roles() -> list[str]:
    """Extract user roles from the X-User-Roles header."""
    headers = get_http_headers()
    print(f"[MCP] All headers: {dict(headers)}")
    roles_header = headers.get("x-user-roles", "")
    print(f"[MCP] X-User-Roles header: {roles_header}")
    if roles_header:
        try:
            return json.loads(roles_header)
        except json.JSONDecodeError:
            return []
    return []

def embed(text, input_type):
    resp = co.embed(
        texts=[text],
        model='embed-v4.0',
        input_type=input_type,
        embedding_types=['float'],
    )
    return resp.embeddings.float[0]

def search(query) -> list[dict]:
    query_embedding = embed(query, 'search_query')

    rows = conn.execute('SELECT * FROM embeddings WHERE embedding IS NOT NULL ORDER BY embedding <=> %s::vector LIMIT 5', (query_embedding,)).fetchall()
    docs = []
    for row in rows:
        docs.append({ 'key': row['key'], 'content': row['content']})
    return docs

@mcp.tool
def get_cave_location(cave: str, state: str, county: str) -> list[dict]:
    """Lookup cave location as coordinates. Returns up to 5 matches, ordered by most to least relevant."""
    roles = get_user_roles()
    print(f"get_cave_location called with roles: {roles}")
    return search(f'{cave} Location, latitude, Longitude. Located in {state} and {county} county.')

@mcp.tool
def general_caving_information(query: str) -> list[dict]:
    """General purpose endpoint for any topic related to caves. Returns up to 5 matches, ordered by most to least relevant."""
    roles = get_user_roles()
    print(f"general_caving_information called with roles: {roles}")
    return search(query)

@mcp.tool
def get_user_info() -> dict:
    """Get information about the current user's roles."""
    roles = get_user_roles()
    return {
        "roles": roles,
    }

if __name__ == "__main__":
    mcp.run(transport='http', host='::1', port=9031)
