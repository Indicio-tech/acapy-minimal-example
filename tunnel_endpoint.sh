#!/bin/bash

AGENT_TUNNEL_ENDPOINT=${AGENT_TUNNEL_ENDPOINT:-http://localhost:4040}
TAILS_TUNNEL_ENDPOINT=${TAILS_TUNNEL_ENDPOINT:-http://localhost:4040}

WAIT_INTERVAL=${WAIT_INTERVAL:-3}
WAIT_ATTEMPTS=${WAIT_ATTEMPTS:-10}

retrieve_endpoint () {
        for _ in $(seq 1 "$WAIT_ATTEMPTS"); do
                #TODO If wait attempts exceeded and we still haven't successfully gotten an endpoint, exit with status 1
                if ! curl -s -o /dev/null -w '%{http_code}' "${1}/url" | grep "200" > /dev/null; then
                        echo "Waiting for tunnel..." 1>&2
                        sleep "$WAIT_INTERVAL" &
                        wait $!
                else
                        break
                fi
        done
}


retrieve_endpoint ${AGENT_TUNNEL_ENDPOINT}
retrieve_endpoint ${TAILS_TUNNEL_ENDPOINT}

ACAPY_ENDPOINT=$(curl --silent "${AGENT_TUNNEL_ENDPOINT}/url" | python -c "import sys, json; print(json.load(sys.stdin)['url'])")
ACAPY_TAILS_SERVER_BASE_URL=$(curl --silent "${TAILS_TUNNEL_ENDPOINT}/api/tunnels" | python -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])")
export ACAPY_ENDPOINT=${ACAPY_ENDPOINT}
export ACAPY_TAILS_SERVER_BASE_URL=${ACAPY_TAILS_SERVER_BASE_URL}
exec "$@"
