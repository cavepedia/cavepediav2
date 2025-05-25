from pgvector.psycopg import register_vector, Bit
from urllib.parse import quote
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
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')

co = cohere.ClientV2(COHERE_API_KEY)
conn = psycopg.connect(
    host='127.0.0.1',
    port=4010,
    dbname='cavepediav2_db',
    user='cavepediav2_user',
    password='cavepediav2_pw',
)

def create_tables():
    commands = (
        "CREATE EXTENSION IF NOT EXISTS vector",
        """
        CREATE TABLE IF NOT EXISTS events (
            key TEXT PRIMARY KEY,
            value JSONB
        )
        """,
        "DROP TABLE IF EXISTS embeddings",
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            bucket TEXT,
            key TEXT,
            content TEXT,
            embedding bit(1536),
            PRIMARY KEY (bucket, key)
        )
        """)
    for command in commands:
        conn.execute(command)
    conn.commit()
    register_vector(conn)

def insert_text(bucket, key, text):
    with conn.cursor() as cur:
        command = 'INSERT INTO embeddings (bucket, key, content) VALUES (%s, %s, %s);'
        cur.execute(command, (bucket, key, text))
    conn.commit()

def process_events():
    with conn.cursor() as cur:
        cur.execute('SELECT * FROM events')

        for row in cur.fetchall():
            for record in row[1]['Records']:
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']

                ai = extract_data(bucket, key)
                text = ai.content[0].text
                text = text.replace('\n',' ')
                insert_text(bucket, key, text)

# https://github.com/pgvector/pgvector-python/blob/master/examples/cohere/example.py
def embed(text, input_type):
    resp = co.embed(
        texts=[text],
        model='embed-v4.0',
        input_type=input_type,
        embedding_types=['ubinary'],
    )
    return [np.unpackbits(np.array(embedding, dtype=np.uint8)) for embedding in resp.embeddings.ubinary]

def generate_embeddings():
    cur = conn.cursor()
    cur.execute('SELECT * FROM embeddings WHERE embedding IS NULL')
    rows = cur.fetchall()

    for row in rows:
        inputs = ['mycontent']
        embeddings=embed(row[2], 'search_document')

        for content, embedding in zip(inputs, embeddings):
            conn.execute('INSERT INTO embeddings (bucket, key, content, embedding) VALUES (%s, %s, %s, %s)', ('mybucket', 'mykey', content, Bit(embedding).to_text()))
            conn.commit()

#        sql = 'UPDATE embeddings SET embedding = %s', (Bit(embeddings[0]))
def get_presigned_url(bucket, key) -> str:
    client = minio.Minio(
        's3.bigcavemaps.com',
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        region='kansascity',
    )

    url = client.presigned_get_object(bucket, key)
    return url

def extract_data(bucket, key):
    url = get_presigned_url(bucket, key)

    client = anthropic.Anthropic()
    message = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1000,
        temperature=1,
        system='You are an OCR service. Extract all data from the provided document.',
        messages=[
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'document',
                        'source': {
                            'type': 'url',
                            'url': url
                        }
                    },
                    {
                        'type': 'text',
                        'text': 'Extract data from this document. Do not include any summary or conclusions of your own. Only include text from the document.'
                    }
                ]
            }
        ],
    )
    return message

def search():
    query = 'door'
    query_embedding = embed(query, 'search_query')[0]

    rows = conn.execute('SELECT content FROM embeddings ORDER BY embedding <~> %s LIMIT 5', (Bit(query_embedding).to_text(),)).fetchall()
    for row in rows:
        print(row)

if __name__ == '__main__':
#    create_tables()
#    process_events()
#    generate_embeddings()
    search()
