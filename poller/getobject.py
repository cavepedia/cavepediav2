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

def getobject():
    bucket = 'cavepedia-v2'
    key = 'public/var/fyi/VAR-FYI 1982-01.pdf'
    with s3.get_object(bucket, key) as obj:
        with open('/tmp/file.pdf', 'wb') as f:
            while True:
                chunk = obj.read(1024)
                if not chunk:
                    break
                f.write(chunk)

if __name__ == '__main__':
    getobject()
