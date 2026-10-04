#!/bin/sh

# shellcheck shell=dash

qopt="-q"
filt="filtand"
N=""
find_deleted_since=""
apply="0"
yes="0"

filtand() {
    sed "s/ and//"
}

set_node_name() {
    if [ -z "$N" ]; then
        if [ -d "$1" ]; then
            N="$1"
        else
            echo "Unknown node name: $1"
            exit 2
        fi
    else
        echo "Only one positional argument allowed"
        exit 2
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
        --since=*)
            find_deleted_since="${1#--since=}"
            ;;
        -y)
            yes="1"
           ;;
        --)
            shift
            break
            ;;
        -*)
            echo "Unknown option: $1"
            exit 2
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
    echo "Usage: $0 [-avy] [--since=REV] [--] name"
    exit 2
fi

find_deleted() {
    git log --no-renames --diff-filter=D --pretty=format: --name-only "$1" | sort | uniq | grep "^$N/"
}

path_in_etc() {
    # sed "s|^$N/|/etc/|"
    stripped="${1#"$N/"}"
    if [ "$stripped" = "$1" ]; then return 1; fi
    echo "/etc/$stripped"
}

ask_if_proceed() {
    # Returns 0 if should proceed; 1 if not
    # no apply = dry run
    if [ "$apply" -ne 1 ]; then return 1; fi
    # yes = no confirm
    if [ "$yes" -eq 1 ]; then return 0; fi
    # In case we need to get another stdin to get the answer
    read -r -p "$1? (y/n) " ans < /dev/tty
    if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
        return 0
    fi
    return 1
}

mkdir_cp_without_perm() {
    dir="$(dirname "$2")"
    mkdir -p "$dir"
    cat "$1" > "$2"
}

updated=0
t=$(mktemp -d -p "" check.sh.XXXXXX) || exit 3
trap 'rm -rf "$t"; exit' EXIT

if ! [ -z "$find_deleted_since" ]; then
    find_deleted "$find_deleted_since.." > "$t/deleted"
    while IFS= read -r name; do
        etcname="$(path_in_etc "$name")" || continue
        [ -f "$etcname" ] || continue
        echo "Removed $etcname" | $filt
        ask_if_proceed "Delete $etcname" || continue
        rm "$etcname"
        updated=1
    done < "$t/deleted"
fi

find "$N" -follow -type f \! -path "$N/README.md" > "$t/updated"
while IFS= read -r name; do
    etcname="$(path_in_etc "$name")"
    if ! diffout="$(diff "$qopt" "$name" "$etcname")"; then
        echo "$diffout" | $filt
        ask_if_proceed "Apply changes to $etcname" || continue
        mkdir_cp_without_perm "$name" "$etcname"
        updated=1
    fi
done < "$t/updated"

exit "$updated"
