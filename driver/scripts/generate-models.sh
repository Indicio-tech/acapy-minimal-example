#!/usr/bin/env bash
set -e

cd "$(dirname "$0")" || exit

CONTAINER_RUNTIME=${CONTAINER_RUNTIME:-docker}
NAME="datamodel-codegen"
API_URL="https://raw.githubusercontent.com/Indicio-tech/acapy-openapi/0.7.4/openapi.yml"

${CONTAINER_RUNTIME} build -t ${NAME} - << DOCKERFILE
FROM python:3.10

WORKDIR /usr/src/app

RUN pip install datamodel-code-generator[http]

ENTRYPOINT ["datamodel-codegen"]
DOCKERFILE

${CONTAINER_RUNTIME} run --rm -it -v "../:/usr/src/app:z" ${NAME} \
    --url "${API_URL}" \
    --output ./controller/models.py \
    --field-constraints \
    --use-schema-description \
    --enum-field-as-literal all \
    --reuse-model
