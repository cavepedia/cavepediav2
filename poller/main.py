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
import logging
from pythonjsonlogger.json import JsonFormatter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = JsonFormatter("{asctime}{message}", style="{")
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

#####

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

## init
# events table is created by minio up creation of event destination
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
            for record in row['value']['Records']:
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                key = unquote(key)
                key = key.replace('+',' ')

                logger.info(f'SPLITTING bucket: {bucket}, key: {key}')

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
                            s3.put_object(f'{bucket}-pages', f'{key}/page-{i + 1}.pdf', bs, len(bs.getvalue()))
                        cur.execute('INSERT INTO embeddings (bucket, key) VALUES (%s, %s);', (f'{bucket}-pages', f'{key}/page-{i + 1}.pdf'))

            cur.execute('DELETE FROM events WHERE key = %s', (row['key'],))
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
    rows = conn.execute("SELECT COUNT(*) FROM embeddings WHERE embedding IS NULL")
    row = rows.fetchone()
    logger.info(f'Found {row["count"]} ready to be processed')

    rows = conn.execute("SELECT * FROM embeddings WHERE embedding IS NULL")

    for row in rows:
        bucket = row['bucket']
        key = row['key']
        logger.info(f'PROCESSING bucket: {bucket}, key: {key}')

        ## claude 4 sonnet ##
        # tier 1 limit: 8k tokens/min
        # tier 2: enough
        # single pdf page: up to 2k tokens
        try:
            ai_ocr = ocr(bucket, key)
            text = ai_ocr.content[0].text

            embedding=embed(text, 'search_document')
            conn.execute('UPDATE embeddings SET content = %s, embedding = %s::vector WHERE bucket = %s AND key = %s;', (text, embedding, bucket, key))
            conn.commit()
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return True

### embeddings
def embed(text, input_type):
    resp = co.embed(
        texts=[text],
        model='embed-v4.0',
        input_type=input_type,
        embedding_types=['float'],
    )
    return resp.embeddings.float[0]

def fix_pages():
    i = 766
    while i > 0:
        conn.execute('UPDATE embeddings SET key = %s WHERE key = %s', (f'public/va/caves-of-virginia.pdf/page-{i}.pdf', f'public/va/caves-of-virginia.pdf/page-{i-1}.pdf'))
        conn.commit()
        i -= 1


if __name__ == '__main__':
    create_tables()
    while True:
        BACKOFF = False

        split_pdfs()
        BACKOFF = process_events()

        if BACKOFF:
            logger.info('backoff detected, sleeping an extra 5 minutes')
            time.sleep(5 * 60)
        logger.info('sleeping 5 minutes')
        time.sleep(5 * 60)
