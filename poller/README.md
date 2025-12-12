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
