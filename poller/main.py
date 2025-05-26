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
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')

co = cohere.ClientV2(COHERE_API_KEY)
conn = psycopg.connect(
    host='127.0.0.1',
    port=4010,
    dbname='cavepediav2_db',
    user='cavepediav2_user',
    password='cavepediav2_pw',
    row_factory=dict_row,
)

## init
def create_tables():
    commands = (
        "CREATE EXTENSION IF NOT EXISTS vector",
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            bucket TEXT,
            key TEXT,
            content TEXT,
            embedding vector(1536),
            PRIMARY KEY (bucket, key)
        )
        """)
    for command in commands:
        conn.execute(command)
    conn.commit()
    register_vector(conn)

## processing
def get_presigned_url(bucket, key) -> str:
    client = minio.Minio(
        's3.bigcavemaps.com',
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        region='kansascity',
    )

    url = client.presigned_get_object(bucket, unquote(key))
    return url

def ocr(bucket, key):
    url = get_presigned_url(bucket, key)

    client = anthropic.Anthropic()
    message = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1000,
        temperature=1,
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
                        'text': 'Extract all text from this document. Do not include any summary or conclusions of your own.'
                    }
                ]
            }
        ],
    )
    return message

def process_events():
    rows = conn.execute('SELECT * FROM events')

    for row in rows:
        for record in row['event_data']['Records']:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            print(f'PROCESSING event_time: {row["event_time"]}, bucket: {bucket}, key: {key}')
            print()

            ai_ocr = ocr(bucket, key)
            text = ai_ocr.content[0].text
            text = text.replace('\n',' ')

            embedding=embed(text, 'search_document')
            with conn.cursor() as cur:
                cur.execute('INSERT INTO embeddings (bucket, key, embedding) VALUES (%s, %s, %s::vector);', (bucket, key, embedding))
                cur.execute('DELETE FROM events WHERE event_time = %s', (row['event_time'],))
            conn.commit()

### embeddings
def embed(text, input_type):
    resp = co.embed(
        texts=[text],
        model='embed-v4.0',
        input_type=input_type,
        embedding_types=['float'],
    )
    return resp.embeddings.float[0]

if __name__ == '__main__':
    create_tables()
    process_events()
