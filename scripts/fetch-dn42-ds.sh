#!/bin/sh

transform() {
    sed -n 's/^ds-rdata: *\(.*\)$/    trust-anchor: "'"$1"' DS \1"/p'
}

echo "server:"
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/dns/dn42" | transform "dn42."
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/inetnum/172.20.0.0_16" | transform "20.172.in-addr.arpa."
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/inetnum/172.21.0.0_16" | transform "21.172.in-addr.arpa."
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/inetnum/172.22.0.0_16" | transform "22.172.in-addr.arpa."
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/inetnum/172.23.0.0_16" | transform "23.172.in-addr.arpa."
curl -fsSL "https://${AUTH}@git.dn42.dev/dn42/registry/raw/branch/master/data/inet6num/fd00::_8" | transform "d.f.ip6.arpa."
