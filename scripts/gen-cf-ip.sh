#!/bin/sh

v=${1:-6}

cat << EOF
set cf_ip${v} {
    type ipv${v}_addr
    flags interval
    elements = { $(curl https://api.cloudflare.com/client/v4/ips | jq --raw-output ".result.ipv${v}_cidrs.[]" | xargs | tr ' ' ,) }
}
EOF
