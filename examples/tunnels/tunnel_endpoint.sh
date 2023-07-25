#!/bin/bash

AGENT_TUNNEL_ENDPOINT=${AGENT_TUNNEL_ENDPOINT:-http://localhost:4040}
TAILS_TUNNEL_ENDPOINT=${TAILS_TUNNEL_ENDPOINT:-http://localhost:4040}

WAIT_INTERVAL=${WAIT_INTERVAL:-3}
WAIT_ATTEMPTS=${WAIT_ATTEMPTS:-10}

liveliness_check () {
        for CURRENT_ATTEMPT in $(seq 1 "$WAIT_ATTEMPTS"); do
                if ! curl -s -o /dev/null -w '%{http_code}' "${1}/status" | grep "200" > /dev/null; then
			if [[ $CURRENT_ATTEMPT -gt $WAIT_ATTEMPTS ]]
			then
				echo "Failed while waiting for 200 status from ${1}"
				exit 1
			fi
			
			echo "Waiting for tunnel..." 1>&2
                        sleep "$WAIT_INTERVAL" &
                        wait $!
                else
                        break
                fi
        done
}


liveliness_check ${AGENT_TUNNEL_ENDPOINT}
liveliness_check ${TAILS_TUNNEL_ENDPOINT}

ACAPY_ENDPOINT=$(curl --silent "${AGENT_TUNNEL_ENDPOINT}/url" | python -c "import sys, json; print(json.load(sys.stdin)['url'])")
ACAPY_TAILS_SERVER_BASE_URL=$(curl --silent "${TAILS_TUNNEL_ENDPOINT}/api/tunnels" | python -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])")
export ACAPY_ENDPOINT=${ACAPY_ENDPOINT}
export ACAPY_TAILS_SERVER_BASE_URL=${ACAPY_TAILS_SERVER_BASE_URL}
exec "$@"

