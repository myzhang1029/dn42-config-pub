#!/bin/sh

# download_check url destination
# return 0 if unchanged
dl() {
    t="$2".new
    rm -f "$t"
    curl -fsSL --remote-time --time-cond "$2" -o "$t" "$1" || {
        e=$?
        rm -f "$t"
        # Fast bail for systemd
        exit "$e"
    }
    [ -f "$t" ] || return 0
    diff "$t" "$2" > /dev/null
    d=$?
    mv "$t" "$2"
    return $d
}

dl https://dn42.burble.com/roa/dn42_roa_bird2_4.conf /etc/bird/roa_dn42_v4.conf
v4_updated=$?
dl https://dn42.burble.com/roa/dn42_roa_bird2_6.conf /etc/bird/roa_dn42_v6.conf
v6_updated=$?

if [ "$v4_updated" -eq 1 ] || [ "$v6_updated" -eq 1 ]; then
    birdc configure
fi
