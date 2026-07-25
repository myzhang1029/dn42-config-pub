import sys
from dataclasses import dataclass


@dataclass
class Record:
    name: str
    port: int
    proto: str
    aliases: list[str]
    comment: str | None


type RecordLine = Record | str | None


def eprint(l: str) -> None:
    print(l, file=sys.stderr)


def parse_line(line: str) -> RecordLine:
    parts = line.split()
    for i, part in enumerate(parts):
        if part.startswith("#"):
            # Force a space after the pound
            if part[1:]:
                comment = "# " + part[1:] + " " + " ".join(parts[i + 1 :])
            else:
                comment = " ".join(parts[i:])
            parts = parts[:i]
            break
    else:
        comment = None
    if parts:
        name = parts[0]
        sport, proto = parts[1].split("/")
        port = int(sport)
        aliases = parts[2:]
        return Record(name, port, proto, aliases, comment)
    return comment


def parse_file(filename: str) -> list[RecordLine]:
    return [parse_line(line) for line in open(filename)]


# Name manipulation


def norm_name(name: str) -> str:
    return name.replace("_", "-").lower()


# If the duplication in port is due to capitalization or hyphen/underscore, merge them
def equiv_name(left: str, right: str) -> bool:
    return norm_name(left) == norm_name(right)


def covers(big: RecordLine, small: RecordLine) -> bool:
    assert isinstance(big, Record)
    assert isinstance(small, Record)
    bnames = set(norm_name(x) for x in [big.name] + big.aliases)
    snames = set(norm_name(x) for x in [small.name] + small.aliases)
    return (
        big.port == small.port
        and big.proto == small.proto
        and bnames.issuperset(snames)
    )


def dedupe(large: list[RecordLine], small: list[RecordLine]) -> list[RecordLine]:
    keep = []

    def contains(rec: RecordLine) -> bool:
        for big in large:
            if not isinstance(big, Record):
                continue
            if covers(big, rec):
                return True
        return False

    for l in small:
        if not isinstance(l, Record) or not contains(l):
            keep.append(l)
        else:
            print(f"present: {l}")
    return keep


def check_dup_assignments_merge_case(records: list[RecordLine]) -> None:

    # Check that each name corresponds to a unique port for each proto
    # [proto][name] = (port, idx)
    found_names: dict[str, dict[str, tuple[int, int]]] = {}
    # Check that each port/proto only appear once
    # (port, proto): idx
    seen_ports: dict[tuple[int, str], int] = {}
    deleted_idx: list[int] = []

    for i, l in enumerate(records):
        if not isinstance(l, Record):
            continue
        name = l.name
        port = l.port
        proto = l.proto
        aliases = l.aliases
        comment = l.comment
        if proto not in found_names:
            found_names[proto] = {}
        if (port, proto) in seen_ports:
            prev_found = seen_ports[(port, proto)]
            prev_found_rec = records[prev_found]
            eprint(f"{(port, proto)} appears at {prev_found} and {i}")
            assert isinstance(prev_found_rec, Record)
            if not aliases and equiv_name(name, prev_found_rec.name):
                eprint(
                    f"{(port, proto)}: merging {name}[{i}] into {prev_found_rec.name}[{prev_found}]"
                )
                prev_found_rec.aliases.append(name)
                deleted_idx.append(i)
                continue
            if covers(prev_found_rec, l) or covers(l, prev_found_rec):
                eprint(
                    f"{(port, proto)}: {name}[{i}] and {prev_found_rec.name}[{prev_found}] covers each other"
                )
                if prev_found_rec.comment is None:
                    if comment and comment != "#":
                        prev_found_rec.comment = "# Merged: " + comment
                elif prev_found_rec.comment != comment:
                    prev_found_rec.comment += comment or ""
                old_names = set([prev_found_rec.name] + prev_found_rec.aliases)
                new_names = [name] + aliases
                for n in new_names:
                    if n not in old_names:
                        prev_found_rec.aliases.append(n)
                deleted_idx.append(i)
                continue
        if name in found_names[proto]:
            prev = found_names[proto][name]
            if prev[0] != port:
                eprint(
                    f"{name} already points to {prev[0]}[{prev[1]}] but will also point to {port}[{i}]"
                )
        found_names[proto][name] = (port, i)
        for alias in aliases:
            if alias in found_names[proto]:
                prev = found_names[proto][alias]
                if prev[0] != port:
                    eprint(
                        f"{alias} already points to {prev[0]}[{prev[1]}] but will also point to {port}[{i}]"
                    )
            found_names[proto][alias] = (port, i)
        seen_ports[(port, proto)] = i
    for idx in sorted(deleted_idx, reverse=True):
        del records[idx]


def output(record: RecordLine) -> str:
    if isinstance(record, Record):
        name = record.name
        port = record.port
        proto = record.proto
        aliases = record.aliases
        comment = record.comment
        part2 = f" {port}/{proto}"
        part3 = " ".join([""] + aliases)
        part4 = (" " + comment) if comment else ""
        s = "{:16s}{:12s}{:16s}{}".format(name, part2, part3, part4)
        return s.strip()
    return record or ""


if __name__ == "__main__":
    data = parse_file(sys.argv[1])
    check_dup_assignments_merge_case(data)
    with open(sys.argv[1], "w") as f:
        for record in data:
            print(output(record), file=f)
