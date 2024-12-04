#!/bin/bash

# Down any remaining containers
echo "Downing any remaining containers"
docker compose down -v

echo "Successfully downed"

# Generate next seed, slap it into the docker-compose.yml
SEED=$(pwgen 32 1)
if [ -z "$SEED" ]; then
  echo "Failed to generate seed using pwgen"
  exit 1
fi


LINE_NUMBER=241
INSERT_CONTENT="        --seed $SEED"

# Insert the content into the specific line in docker-compose.yml
sed -i '' "${LINE_NUMBER}i\\
$INSERT_CONTENT
" docker-compose.yml

echo "Seed inserted into docker-compose.yml at line $LINE_NUMBER"

# Build next example
# Down containers author and endorser
# Run example 2
# docker compose build --no-cache && \
# docker compose down && \
# echo "Stopped containers" && \
# docker compose up -d endorser && \
# docker compose up -d author && \
# docker compose run example2

# # Delete line number with seed
# echo "Deleting line number with seed"
# sed -i '' '93d' docker-compose.yml