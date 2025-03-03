#!/bin/sh
echo 'server:'
echo '    local-zone: "blackhole.maiyun.me" redirect'
echo '    local-data: "blackhole.maiyun.me A 198.51.0.0"'
echo '    local-data: "blackhole.maiyun.me AAAA 100::1"'
LIST1="$(curl -L "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=nohtml")"
LIST2="$(curl -L "https://github.com/nextdns/native-tracking-domains/raw/refs/heads/main/domains/apple")"
printf '%s\n%s\n' "$LIST1" "$LIST2" | sort | uniq | awk '{print "    local-zone: \""$1"\" redirect"; print "    local-data: \""$1" CNAME blackhole.maiyun.me\""}'
