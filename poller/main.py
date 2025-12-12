import io
import logging
import os
import time
from urllib.parse import unquote

import anthropic
import boto3
import cohere
import dotenv
import psycopg
from cohere.core.api_error import ApiError
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from pypdf import PdfReader, PdfWriter
from pythonjsonlogger.json import JsonFormatter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = JsonFormatter("{asctime}{message}", style="{")
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

#####

# Load .env file if it exists (for local dev)
dotenv.load_dotenv()

# Required environment variables
COHERE_API_KEY = os.environ["COHERE_API_KEY"]
S3_ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
S3_SECRET_KEY = os.environ["S3_SECRET_KEY"]
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "https://s3.bigcavemaps.com")
S3_REGION = os.environ.get("S3_REGION", "eu")

# Database config
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "cavepediav2_db")
DB_USER = os.environ.get("DB_USER", "cavepediav2_user")
DB_PASSWORD = os.environ["DB_PASSWORD"]

s3 = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    endpoint_url=S3_ENDPOINT,
    region_name=S3_REGION,
)
co = cohere.ClientV2(api_key=COHERE_API_KEY)
conn = psycopg.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    row_factory=dict_row,
)


## init
# events table is created by minio up creation of event destination
def create_tables():
    commands = (
        """
        CREATE TABLE IF NOT EXISTS metadata (
            id SERIAL PRIMARY KEY,
            bucket TEXT,
            key TEXT,
            split BOOLEAN DEFAULT FALSE,
            UNIQUE(bucket, key)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS batches (
            id SERIAL PRIMARY KEY,
            platform TEXT,
            batch_id TEXT,
            type TEXT,
            done BOOLEAN DEFAULT FALSE
        )
        """,
        "CREATE EXTENSION IF NOT EXISTS vector",
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            id SERIAL PRIMARY KEY,
            role TEXT,
            bucket TEXT,
            key TEXT,
            content TEXT,
            embedding vector(1536),
            UNIQUE(bucket, key)
        )
        """,
    )
    for command in commands:
        conn.execute(command)
    conn.commit()
    register_vector(conn)


def import_files():
    """Scan import bucket for any new files; move them to the files bucket and add to db; delete from import bucket"""
    BUCKET_IMPORT = "cavepediav2-import"
    BUCKET_FILES = "cavepediav2-files"
    # get new files; add to db, sync to main bucket; delete from import bucket
    response = s3.list_objects_v2(Bucket=BUCKET_IMPORT)
    if "Contents" in response:
        for obj in response["Contents"]:
            if obj["Key"].endswith("/"):
                continue
            s3.copy_object(
                CopySource={"Bucket": BUCKET_IMPORT, "Key": obj["Key"]},
                Bucket=BUCKET_FILES,
                Key=obj["Key"],
            )
            conn.execute("INSERT INTO metadata (bucket, key) VALUES(%s, %s);", (BUCKET_FILES, obj["Key"]))
            conn.commit()
            s3.delete_object(
                Bucket=BUCKET_IMPORT,
                Key=obj["Key"],
            )


def split_files():
    """Split PDFs into single pages for easier processing"""
    BUCKET_PAGES = "cavepediav2-pages"
    rows = conn.execute("SELECT COUNT(*) FROM metadata WHERE split = false")
    row = rows.fetchone()
    assert row is not None
    logger.info(f"Found {row['count']} files to split.")
    rows = conn.execute("SELECT * FROM metadata WHERE split = false")

    for row in rows:
        bucket = row["bucket"]
        key = row["key"]

        with conn.cursor() as cur:
            logger.info(f"SPLITTING bucket: {bucket}, key: {key}")

            ##### get pdf #####
            s3.download_file(bucket, key, "/tmp/file.pdf")

            ##### split #####
            with open("/tmp/file.pdf", "rb") as f:
                reader = PdfReader(f)

                for i in range(len(reader.pages)):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[i])

                    with io.BytesIO() as bs:
                        writer.write(bs)
                        bs.seek(0)
                        s3.put_object(Bucket=BUCKET_PAGES, Key=f"{key}/page-{i + 1}.pdf", Body=bs.getvalue())
                    page_key = f"{key}/page-{i + 1}.pdf"
                    role = key.split("/")[0]
                    cur.execute(
                        "INSERT INTO embeddings (bucket, key, role) VALUES (%s, %s, %s);",
                        (BUCKET_PAGES, page_key, role),
                    )
            cur.execute("UPDATE metadata SET SPLIT = true WHERE id = %s", (row["id"],))
        conn.commit()


def ocr_create_message(id, bucket, key):
    """Create message to send to claude"""
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": unquote(key)},
    )

    message = {
        "custom_id": f"doc-{id}",
        "params": {
            "model": "claude-haiku-4-5",
            "max_tokens": 4000,
            "temperature": 1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "document", "source": {"type": "url", "url": url}},
                        {
                            "type": "text",
                            "text": "Extract all text from this document. "
                            "Do not include any summary or conclusions of your own.",
                        },
                    ],
                }
            ],
        },
    }

    return message


def ocr(bucket, key):
    """Gets OCR content of pdfs"""
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": unquote(key)},
    )

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4000,
        temperature=1,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "document", "source": {"type": "url", "url": url}},
                    {
                        "type": "text",
                        "text": "Extract all text from this document. "
                        "Do not include any summary or conclusions of your own.",
                    },
                ],
            }
        ],
    )
    return message


def claude_send_batch(batch):
    """Send a batch to claude"""
    client = anthropic.Anthropic()
    message_batch = client.messages.batches.create(requests=batch)

    conn.execute(
        "INSERT INTO batches (platform, batch_id, type) VALUES(%s, %s, %s);", ("claude", message_batch.id, "ocr")
    )
    conn.commit()

    logger.info(f"Sent batch_id {message_batch.id} to claude")


def check_batches():
    """Check batch status"""
    rows = conn.execute("SELECT COUNT(*) FROM batches WHERE done = false")
    row = rows.fetchone()
    assert row is not None
    logger.info(f"Found {row['count']} batch(es) to process.")
    rows = conn.execute("SELECT * FROM batches WHERE done = false")

    client = anthropic.Anthropic()
    for row in rows:
        message_batch = client.messages.batches.retrieve(
            row["batch_id"],
        )
        if message_batch.processing_status == "ended":
            results = client.messages.batches.results(
                row["batch_id"],
            )
            with conn.cursor() as cur:
                for result in results:
                    id = int(result.custom_id.split("-")[1])
                    try:
                        content = result.result.message.content[0].text  # type: ignore[union-attr]
                        cur.execute("UPDATE embeddings SET content = %s WHERE id = %s;", (content, id))
                    except Exception:
                        cur.execute("UPDATE embeddings SET content = %s WHERE id = %s;", ("ERROR", id))
                cur.execute("UPDATE batches SET done = true WHERE batch_id = %s;", (row["batch_id"],))
            conn.commit()


def ocr_main():
    """Checks for any non-OCR'd documents and sends them to claude in batches"""
    ## claude 4 sonnet ##
    # tier 1 limit: 8k tokens/min
    # tier 2: enough
    # single pdf page: up to 2k tokens

    # get docs where content is null
    rows = conn.execute("SELECT COUNT(*) FROM embeddings WHERE content IS NULL LIMIT 1000")
    row = rows.fetchone()
    assert row is not None
    logger.info(f"Batching {row['count']} documents to generate OCR content.")
    rows = conn.execute("SELECT * FROM embeddings WHERE content IS NULL LIMIT 1000")

    # batch docs; set content = WIP
    batch = []
    for row in rows:
        id = row["id"]
        bucket = row["bucket"]
        key = row["key"]

        logger.info(f"Batching for OCR: {bucket}, key: {key}")

        batch.append(ocr_create_message(id, bucket, key))
        conn.execute("UPDATE embeddings SET content = %s WHERE id = %s;", ("WIP", id))
        conn.commit()
    if len(batch) > 0:
        claude_send_batch(batch)


def embeddings_main():
    """Generate embeddings"""
    count_query = """
        SELECT COUNT(*) FROM embeddings
        WHERE content IS NOT NULL AND content != 'ERROR' AND content != 'WIP' AND embedding IS NULL
    """
    rows = conn.execute(count_query)
    row = rows.fetchone()
    assert row is not None
    logger.info(f"Batching {row['count']} documents to generate embeddings.")
    select_query = """
        SELECT id, key, bucket, content FROM embeddings
        WHERE content IS NOT NULL AND content != 'ERROR' AND content != 'WIP' AND embedding IS NULL
    """
    rows = conn.execute(select_query)

    for row in rows:
        logger.info(f"Generating embeddings for id: {row['id']}, bucket: {row['bucket']}, key: {row['key']}")
        embedding = embed(row["content"], "search_document")
        conn.execute("UPDATE embeddings SET embedding = %s::vector WHERE id = %s;", (embedding, row["id"]))
        conn.commit()


### embeddings
def embed(text, input_type):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = co.embed(
                texts=[text],
                model="embed-v4.0",
                input_type=input_type,
                embedding_types=["float"],
                output_dimension=1536,
            )
            assert resp.embeddings.float_ is not None
            return resp.embeddings.float_[0]
        except ApiError as e:
            if e.status_code == 502 and attempt < max_retries - 1:
                time.sleep(30**attempt)  # exponential backoff
                continue
            raise Exception("cohere max retries exceeded")


def fix_pages():
    i = 766
    while i > 0:
        new_key = f"public/va/caves-of-virginia.pdf/page-{i}.pdf"
        old_key = f"public/va/caves-of-virginia.pdf/page-{i - 1}.pdf"
        conn.execute("UPDATE embeddings SET key = %s WHERE key = %s", (new_key, old_key))
        conn.commit()
        i -= 1


if __name__ == "__main__":
    create_tables()

    while True:
        import_files()
        split_files()
        check_batches()
        ocr_main()
        embeddings_main()

        logger.info("sleeping 5 minutes")
        time.sleep(5 * 60)
