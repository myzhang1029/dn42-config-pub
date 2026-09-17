#!/bin/sh
NODE="$1"
SN="$NODE/systemd/network"
WG="$NODE/wireguard"
NEED_ENABLE=""

for netdev in $SN/30-dn42-*.netdev; do
    network="$(echo "$netdev" | sed 's/\.netdev$/.network/')"
    ls "$network"
    iface="$(grep Name= "$netdev" | cut -f2- -d=)"
    lport="$(grep ListenPort= "$netdev" | cut -f2- -d=)"
    pkey="$(grep PublicKey= "$netdev" | cut -f2- -d=)"
    endp="$(grep Endpoint= "$netdev" | cut -f2- -d=)"
    ourad="$(grep Address= "$network" | cut -f2- -d=)"
    peerad="$(grep Peer= "$network" | cut -f2- -d=)"
    git rm "$netdev" "$network"
    cat > "$WG/$iface.conf.in" << EOFEOF
# vi: ft=dosini
# /etc/wireguard/$iface.conf.in

[Interface]
ListenPort = $lport
PrivateKey = @PRIVATE_KEY@

[Peer]
PublicKey = $pkey
AllowedIPs = fe80::/64, fd00::/8, 172.31.0.0/16, 172.20.0.0/14, 10.0.0.0/8
Endpoint = $endp
EOFEOF
    cat > "$WG/$iface.env" << EOFEOF
MTU=1420
OUR_v6ADDR=$ourad
PEER_v6ADDR=$peerad
EOFEOF
    git add "$WG/$iface.conf.in" "$WG/$iface.env"
    NEED_ENABLE="$NEED_ENABLE network-dn42-wg@$iface.service"
done

echo "Enable these new services: $NEED_ENABLE"
