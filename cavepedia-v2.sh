#!/bin/bash

set -e

up () {
  docker run \
    --detach \
    --name cp2-pg \
    --restart unless-stopped \
    --env POSTGRES_DB=cavepediav2_db \
    --env POSTGRES_PASSWORD=cavepediav2_pw \
    --env POSTGRES_USER=cavepediav2_user \
    --volume /mammoth/cp2/cp2-pg/data:/var/lib/postgresql/data:rw \
    --publish 127.0.0.1:4010:5432 \
    --network pew-net \
    pgvector/pgvector:pg17
}

down () {
  docker stop cp2-pg || true
  docker rm cp2-pg || true
}

$@
