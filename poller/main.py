from pgvector.psycopg import register_vector, Bit
from psycopg.rows import dict_row
from urllib.parse import unquote
from pypdf import PdfReader, PdfWriter
import anthropic
import cohere
import dotenv
import datetime
import io
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

s3 = minio.Minio(
    's3.bigcavemaps.com',
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    region='kansascity',
)
co = cohere.ClientV2(COHERE_API_KEY)
conn = psycopg.connect(
    host='127.0.0.1',
    port=4010,
    dbname='cavepediav2_db',
    user='cavepediav2_user',
    password='cavepediav2_pw',
    row_factory=dict_row,
)

BACKOFF = False

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

## splitting
def split_pdfs():
    rows = conn.execute('SELECT * FROM events')

    for row in rows:
        with conn.cursor() as cur:
            for record in row['event_data']['Records']:
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                key = unquote(key)

                print(f'SPLITTING bucket: {bucket}, key: {key}')

                ##### get pdf #####
                with s3.get_object(bucket, key) as obj:
                    with open('/tmp/file.pdf', 'wb') as f:
                        while True:
                            chunk = obj.read(1024)
                            if not chunk:
                                break
                            f.write(chunk)

                ##### split #####
                with open('/tmp/file.pdf', 'rb') as f:
                    reader = PdfReader(f)

                    for i in range(len(reader.pages)):
                        writer = PdfWriter()
                        writer.add_page(reader.pages[i])

                        with io.BytesIO() as bs:
                            writer.write(bs)
                            bs.seek(0)
                            s3.put_object('cavepedia-v2-pages', f'{key}/page-{i}.pdf', bs, len(bs.getvalue()))
                        cur.execute('INSERT INTO embeddings (bucket, key) VALUES (%s, %s);', (f'{bucket}-pages', f'{key}/page-{i}.pdf'))

            cur.execute('DELETE FROM events WHERE event_time = %s', (row['event_time'],))
        conn.commit()

## processing
def ocr(bucket, key):
    url = s3.presigned_get_object(bucket, unquote(key))

    client = anthropic.Anthropic()
    message = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=4000,
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
    rows = conn.execute('SELECT * FROM embeddings WHERE embedding IS NULL')

    for row in rows:
        bucket = row['bucket']
        key = row['key']
        print(f'PROCESSING bucket: {bucket}, key: {key}')

        # tier 1 limit: 4k tokens/min
        # single pdf = 2-3k tokens
        max_retries = 5
        retry_delay = 30
        for attempt in range(max_retries):
            try:
                ai_ocr = ocr(bucket, key)
                text = ai_ocr.content[0].text
                text = text.replace('\n',' ')

                embedding=embed(text, 'search_document')
                conn.execute('UPDATE embeddings SET content = %s, embedding = %s::vector WHERE bucket = %s AND key = %s;', (text, embedding, bucket, key))
                conn.commit()
                break
            except anthropic.APIStatusError as e:
                if e.type == 'overloaded_error':
                    if attempt < max_retries - 1:
                        sleep_time = retry_delay * (2 ** attempt)
                        print(f"Overload error. Retrying in {sleep_time:.2f} seconds...")
                        time.sleep(sleep_time)
                    else:
                        print('Max retries reached.')
                        raise
                else:
                    raise
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                BACKOFF = True
                break

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
    while True:
        BACKOFF = False

        split_pdfs()
        process_events()

        if BACKOFF:
            print('BACKOFF')
            time.sleep(10 * 60)
        time.sleep(5 * 60)
