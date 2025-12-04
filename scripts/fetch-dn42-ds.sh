#!/bin/sh

set -eo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <outpath>" >&2
    exit 1
fi
out="$1"
outdir="$(dirname "$1")"
temp="$(mktemp "$outdir"/fetch-dn42-ds.XXXXXXX)"
temp2="$(mktemp "$outdir"/fetch-dn42-ds.XXXXXXX)"

trap 'rm -f "$temp" "$temp2"' EXIT

transform() {
    sed -n 's/^ds-rdata: *\(.*\)$/    trust-anchor: "'"$1"' DS \1"/p'
}

echo "server:" | tee "$temp" | tee "$temp2"
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/dns/dn42" | transform "dn42." | tee -a "$temp"
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/inetnum/172.20.0.0_16" | transform "20.172.in-addr.arpa." | tee -a "$temp"
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/inetnum/172.21.0.0_16" | transform "21.172.in-addr.arpa." | tee -a "$temp"
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/inetnum/172.22.0.0_16" | transform "22.172.in-addr.arpa." | tee -a "$temp"
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/inetnum/172.23.0.0_16" | transform "23.172.in-addr.arpa." | tee -a "$temp"
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/inet6num/fd00::_8" | transform "d.f.ip6.arpa." | tee -a "$temp"

if diff "$temp" "$temp2" > /dev/null; then
    echo "Empty response from server" >&2
    exit 2
fi
mv "$temp" "$out"
