#!/bin/bash

set -e

up () {
  docker run \
    --detach \
    --name cp2-pg \
    --restart unless-stopped \
    --env-file $HOME/scripts-private/loser/cavepedia-v2/cp2-pg.env \
    --volume /texas/cp2/cp2-pg/18/data:/var/lib/postgresql/18/docker:rw \
    --publish [::1]:9030:5432 \
    --network pew-net \
    pgvector/pgvector:pg18
}

down () {
  docker stop cp2-pg || true
  docker rm cp2-pg || true
}

$@
