from pgvector.psycopg import register_vector, Bit
from psycopg.rows import dict_row
from urllib.parse import unquote
import anthropic
import cohere
import dotenv
import datetime
import json
import minio
import numpy as np
import os
import psycopg
import time

dotenv.load_dotenv('/home/paul/scripts-private/lech/cavepedia-v2/poller.env')

COHERE_API_KEY = os.getenv('COHERE_API_KEY')

co = cohere.ClientV2(COHERE_API_KEY)
conn = psycopg.connect(
    host='127.0.0.1',
    port=4010,
    dbname='cavepediav2_db',
    user='cavepediav2_user',
    password='cavepediav2_pw',
    row_factory=dict_row,
)

def embed(text, input_type):
    resp = co.embed(
        texts=[text],
        model='embed-v4.0',
        input_type=input_type,
        embedding_types=['float'],
    )
    return resp.embeddings.float[0]

def search():
    query = 'links trip with not more than 2 people'
    query_embedding = embed(query, 'search_query')

    rows = conn.execute('SELECT * FROM embeddings ORDER BY embedding <=> %s::vector LIMIT 5', (query_embedding,)).fetchall()
    for row in rows:
        print(row['bucket'])
        print(row['key'])

if __name__ == '__main__':
    search()
