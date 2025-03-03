#!/bin/bash

qopt="-q"
filt="filtand"
N=""
apply="0"

filtand() {
    sed "s/ and//"
}

set_node_name() {
    if [ -z "$N" ]; then
        if [ -d "$1" ]; then
            N="$1"
        else
            echo "Unknown node name: $1"
            exit 1
        fi
    else
        echo "Only one positional argument allowed"
        exit 1
    fi
}

while [ -n "$1" ]; do
    case "$1" in
        -a)
            apply="1"
            # implies -v
            qopt="--unified=1"
            filt="cat"
            ;;
        -v)
            qopt="--unified=1"
            filt="cat"
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "Unknown option: $1"
            exit 1
            ;;
        *)
            set_node_name "$1"
            ;;
    esac
    shift
done

while [ -n "$1" ]; do
    set_node_name "$1"
    shift
done

if [ -z "$N" ]; then
    echo "Usage: $0 [-av] name"
    exit 1
fi

find "$N" -follow -type f -not -path "$N/README.md" -print0 | while IFS= read -r -d '' name; do
    # sed "s|^$N/|/etc/|"
    etcname="/etc/${name#"$N"/}"
    diff "$qopt" "$name" "$etcname" | $filt
    diffresult="${PIPESTATUS[0]}"
    if [ "$diffresult" -ne 0 ] && [ "$apply" -eq 1 ]; then
        # need to get another stdin to get the answer
        read -r -p "Apply changes to $etcname? (y/n) " ans < /dev/tty
        if [ "$ans" = "y" ]; then
            cat "$name" > "$etcname"
        fi
    fi
done
