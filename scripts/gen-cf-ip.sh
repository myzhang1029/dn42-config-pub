#!/bin/sh

cf_ips=$(curl -fsS https://api.cloudflare.com/client/v4/ips) || exit

echo "chain _input_cf {"
for v in 6 4; do
    proto=ip
    [ "$v" = 6 ] && proto=ip6
    cidrs="$(jq -nr --argjson ips "$cf_ips" '$ips.result["ipv'$v'_cidrs"] | join(", ")')"
    echo "    $proto saddr { $cidrs } $proto daddr @local_cf_ipv$v accept"
done
echo "}"
