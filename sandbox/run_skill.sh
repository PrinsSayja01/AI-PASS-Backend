#!/bin/bash
docker run --rm \
  --network=none \
  --memory=512m \
  --cpus=1 \
  aipass-skill-runtime "$@"
