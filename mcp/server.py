from fastmcp import FastMCP
from fastmcp.server.auth.providers.auth0 import Auth0Provider
from psycopg.rows import dict_row
import cohere
import dotenv
import psycopg
import os

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


# The Auth0Provider utilizes Auth0 OIDC configuration
auth_provider = Auth0Provider(
    config_url="https://dev-jao4so0av61ny4mr.us.auth0.com/.well-known/openid-configuration",
    client_id="oONcxma5PNFwYLhrDC4o0PUuAmqDekzM",
    client_secret="4Z7Wl12ALEtDmNAoERQe7lK2YD9x6jz7H25FiMxRp518dnag-IS2NLLScnmbe4-b",
    audience="https://dev-jao4so0av61ny4mr.us.auth0.com/me/",
    base_url="https://mcp.caving.dev",
    # redirect_path="/auth/callback"                            # Default value, customize if needed
)

mcp = FastMCP("Cavepedia MCP")

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
    return search(f'{cave} Location, latitude, Longitude. Located in {state} and {county} county.')

@mcp.tool
def general_caving_information(query: str) -> list[dict]:
    """General purpose endpoint for any topic related to caves. Returns up to 5 mates, orderd by most to least relevant."""
    return search(query)

# Add a protected tool to test authentication
@mcp.tool
async def get_token_info() -> dict:
    """Returns information about the Auth0 token."""
    from fastmcp.server.dependencies import get_access_token

    token = get_access_token()

    return {
        "issuer": token.claims.get("iss"),
        "audience": token.claims.get("aud"),
        "scope": token.claims.get("scope")
    }

if __name__ == "__main__":
    mcp.run(transport='http', host='::1', port=9031)
