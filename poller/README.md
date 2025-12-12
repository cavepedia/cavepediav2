# poller

Processes documents and indexes them to be searched.

Every 5 minutes, this polls for new documents as follows:
1. Moves any documents from `s3://cavepediav2-import` to `s3://cavepediav2-files` and updates the `metadata` table.
    * This table has a `split` column, indicating if the file has been split into individual pages.
2. Checks the `metadata` table for any unsplit files, then splits them and stores the pages in `s3://cavepediav2-pages` and creates an row in the `embeddings` table for each page.
3. Checks claude for any OCR batches that have finished, then stores the results in the `embeddings` table.
4. Checks the `embeddings` table for un-OCR'd pages and batches them in groups of 1000 to be OCR'd by claude.
    * Only 1 batch is created per 5 minutes, as it can be easy to overload the server hosting the files.
    * A temporary public S3 file link is generated using a presigned s3 url.
5. Checks the `embeddings` table for any rows that have been OCR'd, but do not have embeddings generated, then generates embeddings with cohere.
    * No batching is used with cohere.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `COHERE_API_KEY` | Yes | - | Cohere API key for embeddings |
| `S3_ACCESS_KEY` | Yes | - | S3/MinIO access key |
| `S3_SECRET_KEY` | Yes | - | S3/MinIO secret key |
| `DB_PASSWORD` | Yes | - | PostgreSQL password |
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key for OCR |
| `DB_HOST` | No | localhost | PostgreSQL host |
| `DB_PORT` | No | 5432 | PostgreSQL port |
| `DB_NAME` | No | cavepediav2_db | PostgreSQL database name |
| `DB_USER` | No | cavepediav2_user | PostgreSQL username |
| `S3_ENDPOINT` | No | https://s3.bigcavemaps.com | S3 endpoint URL |
| `S3_REGION` | No | eu | S3 region |

## Development

```bash
# Create .env file with required variables
cp .env.example .env

# Install dependencies
uv sync

# Run
python main.py
```

## Deployment

The poller is automatically built and pushed to `git.seaturtle.pw/cavepedia/cavepediav2-poller:latest` on push to main.

```bash
docker run \
  -e COHERE_API_KEY="xxx" \
  -e S3_ACCESS_KEY="xxx" \
  -e S3_SECRET_KEY="xxx" \
  -e DB_PASSWORD="xxx" \
  -e DB_HOST="postgres" \
  -e ANTHROPIC_API_KEY="xxx" \
  git.seaturtle.pw/cavepedia/cavepediav2-poller:latest
```
