#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import readline as _
from pathlib import Path
from pprint import pprint

class MalformedConfig(Exception):
    pass

class MakePeer:
    # Defined in each nftables/main.nft
    PORT_RANGE = range(24201, 24300)
    OUR_ASN = 4242420893
    DOMAIN = "dn42.maiyun.me"
    SITES = ("ca04", "ab06", "jp02", "uc01")
    BIRD_TEMPLATE = """protocol bgp {} from dnpeers {{
    neighbor {}%{} as {};
    direct;
}}
"""
    SYSTEMD_NETDEV_TEMPLATE = """# vi: ft=systemd
# /etc/systemd/network/{}.netdev

[NetDev]
Name={}
Kind=wireguard
Description={}

[WireGuard]
ListenPort={}
PrivateKeyFile=/etc/systemd/network/dn42.wgkey

[WireGuardPeer]
PublicKey={}{}
AllowedIPs=10.0.0.0/8
AllowedIPs=172.20.0.0/14
AllowedIPs=172.31.0.0/16
AllowedIPs=fd00::/8
AllowedIPs=fe80::/64
"""
    SYSTEMD_NETWORK_TEMPLATE = """# vi: ft=systemd
# /etc/systemd/network/{}.network

[Match]
Name={}

[Link]
RequiredForOnline=degraded:routable
RequiredFamilyForOnline=ipv6

[Network]
DHCP=no
IPv6AcceptRA=false
IPForward=yes
IPv4ReversePathFilter=no
KeepConfiguration=yes

[Address]
Address={}
Peer={}
"""
    answers: dict[str, str] = {}

    @property
    def _systemd_network(self) -> Path:
        if "site" not in self.answers:
            raise ValueError("site not set")
        site = self.answers["site"]
        path = Path(f"{site}/systemd/network")
        if not path.exists():
            path.mkdir(parents=True)
        return path

    @property
    def _birdconf(self) -> Path:
        if "site" not in self.answers:
            raise ValueError("site not set")
        site = self.answers["site"]
        path = Path(f"{site}/bird/conf.d")
        if not path.exists():
            path.mkdir(parents=True)
        return path

    def __init__(self) -> None:
        self.ask_questions()
        print("Will generate based on the following answers:")
        pprint(self.answers)
        self._print_additional_info()
        resp = input("Continue? [Y/n] ")
        if resp.lower() == "n":
            print("Will not generate files.")
            return
        self._generate_files()

    @staticmethod
    def _parse_choice(choices: tuple[str, ...], answer: str) -> int | None:
        """Parse a user choice."""
        # As a string
        for i, choice in enumerate(choices):
            if choice.lower() == answer.lower():
                return i
        # As a number
        try:
            choiceidx = int(answer)
            if 0 < choiceidx <= len(choices):
                return choiceidx - 1
        except ValueError:
            pass
        return None

    @staticmethod
    def _ask_numeric(question: str, can_strip_prefix: str = "") -> int:
        """Ask a numeric question."""
        while True:
            try:
                ans = input(question)
                if can_strip_prefix and ans.startswith(can_strip_prefix):
                    ans = ans[len(can_strip_prefix):]
                return int(ans)
            except ValueError:
                print("Invalid input, try again.\n")

    @staticmethod
    def _ask_string(question: str) -> str:
        """Ask a string question."""
        return input(question)

    @staticmethod
    def _ask_wgkey(question: str) -> str:
        """Ask for a WireGuard key."""
        def valid_key(key: str) -> bool:
            if len(key) != 44:
                return False
            if key[-1] != "=":
                return False
            chrs = set(key[:-1]) - {'+', '/'}
            return all(c.isalnum() for c in chrs)
        while True:
            key = input(question)
            if valid_key(key):
                return key
            print("Invalid key, try again.\n")

    def _ask_site(self) -> str:
        """Ask for a site name."""
        while True:
            print("Which site is this peer for?")
            for i, name in enumerate(self.SITES):
                print(f"{i+1}. {name}")
            choice = input("Answer: ")
            site = self._parse_choice(self.SITES, choice)
            if site is not None:
                return self.SITES[site]
            print("Invalid choice, try again.\n")

    def _ask_listen_port(self) -> int:
        """Ask for listening port and check for duplicates."""
        netdevs = self._systemd_network.glob("30-dn42-*.netdev")
        LOOKFOR = "ListenPort="
        site_used_ports = set()
        for netdev in netdevs:
            lines = netdev.open(encoding="utf-8").readlines()
            this_port = None
            for line in lines:
                if line.startswith(LOOKFOR):
                    if this_port is not None:
                        raise MalformedConfig(f"multiple {LOOKFOR}")
                    this_port = int(line[len(LOOKFOR):])
            if this_port is None:
                raise MalformedConfig(f"missing {LOOKFOR}")
            site_used_ports.add(this_port)
        print(f"Please select a listening port in {self.PORT_RANGE}")
        print("These ports are in use:")
        pprint(site_used_ports)
        while True:
            port = self._ask_numeric("Which port should we listen on? ")
            if port not in site_used_ports and port in self.PORT_RANGE:
                return port
            print("This port is unavailable.\n")

    def ask_questions(self) -> None:
        """Ask all questions."""
        self.answers["site"] = self._ask_site()
        self.answers["asn"] = str(self._ask_numeric("What is the peer ASN? ", "AS"))
        self.answers["pname"] = self._ask_string(
            "What is a descriptive name for the peer? ")
        self.answers["ploc"] = self._ask_string(
            "What is a descriptive location for the peer? ")
        self._generate_names()
        self.answers["ppub"] = self._ask_wgkey(
            "What is the peer's public key? ")
        self.answers["listen_port"] = str(self._ask_listen_port())
        print("Note: if the peer does not have a public endpoint, leave this blank.")
        self.answers["endpoint"] = self._ask_string(
            "What is the endpoint for the peer? ")
        print("Note: if the peer does not use IPv6LL, fill something else and manually edit the file.")
        asn_lastfour = int(str(self.answers["asn"])[-4:])
        maybe = f"fe80::{asn_lastfour}"
        self.answers["peeraddr"] = self._ask_string(
            f"What is the peer's IPv6 link-local address? [default: {maybe}] ") or maybe
        if '/' not in self.answers["peeraddr"]:
            self.answers["peeraddr"] += "/64"
        self.answers["ownaddr"] = self._ask_string(
            "What is our IPv6 link-local address? [default: fe80::893] ") or "fe80::893"
        if '/' not in self.answers["ownaddr"]:
            self.answers["ownaddr"] += "/64"

    def _generate_names(self) -> None:
        """Generate interface, file, and bird names."""
        # WireGuard interface name
        if len(self.answers["pname"] + self.answers["ploc"]) > 10:
            print("Warning: names are too long, please specify a shorter name for the interface name generation.")
        maybe = self.answers["pname"].lower().replace(" ", "")
        short_name = self._ask_string(
            f"What is the short name for the peer? [default: {maybe}] ") or maybe
        maybe = self.answers["ploc"].lower().replace(" ", "")
        short_loc = self._ask_string(
            f"What is the short location for the peer? [default: {maybe}] ") or maybe
        maybe = "wg{}{}{}".format(
            str(self.answers["asn"])[-4:], short_name, short_loc)
        iface_name = self._ask_string(
            f"The interface name for the peer? [default: {maybe}] ") or maybe
        # systemd-networkd and BIRD configuration file names
        maybe = "30-dn42-{}-{}".format(short_name, short_loc)
        file_name = self._ask_string(
            f"The file name prefix for the peer? [default: {maybe}] ") or maybe
        # systemd-networkd description
        maybe = f"WireGuard tunnel to AS{self.answers['asn']} {self.answers['pname']} {self.answers['ploc']}"
        systemd_desc = self._ask_string(
            f"The description for the peer? [default: {maybe}] ") or maybe
        # BIRD configuration name
        maybe = "{}_{}".format(short_name, short_loc)
        bird_name = self._ask_string(
            f"The BIRD configuration name for the peer? [default: {maybe}] ") or maybe
        # Save the names
        self.answers["iface"] = iface_name
        self.answers["file"] = file_name
        self.answers["systemd"] = systemd_desc
        self.answers["bird"] = bird_name

    def _maybe_write_file(self, file: Path, content: str) -> None:
        """Write a file if it doesn't exist."""
        if file.exists():
            resp = input(f"File {file} already exists, overwrite? [y/N] ")
            if resp.lower() != "y":
                print(f"Skipping {file} generation.")
                return
        with open(file, "w", encoding="utf-8") as f:
            f.write(content)

    def _generate_bird(self) -> None:
        """Generate the BIRD configuration."""
        peerip_nocidr = self.answers["peeraddr"].split("/")[0]
        bird = self.BIRD_TEMPLATE.format(
            self.answers["bird"], peerip_nocidr, self.answers["iface"], self.answers["asn"])
        file = self._birdconf / f"{self.answers['file']}.conf"
        self._maybe_write_file(file, bird)

    def _generate_netdev(self) -> None:
        """Generate the systemd-networkd .netdev file."""
        netdev = self.SYSTEMD_NETDEV_TEMPLATE.format(
            self.answers["file"],
            self.answers["iface"],
            self.answers["systemd"],
            self.answers["listen_port"],
            self.answers["ppub"],
            f"\nEndpoint={self.answers['endpoint']}" if self.answers["endpoint"] else ""
        )
        file = self._systemd_network / f"{self.answers['file']}.netdev"
        self._maybe_write_file(file, netdev)

    def _generate_network(self) -> None:
        """Generate the systemd-networkd .network file."""
        network = self.SYSTEMD_NETWORK_TEMPLATE.format(
            self.answers["file"],
            self.answers["iface"],
            self.answers["ownaddr"],
            self.answers["peeraddr"]
        )
        file = self._systemd_network / f"{self.answers['file']}.network"
        self._maybe_write_file(file, network)

    def _add_interface_to_firewall(self) -> None:
        """Add the interface to nftables/main.nft."""
        site = self.answers["site"]
        file = Path(f"{site}/nftables/main.nft")
        if not file.exists():
            raise MalformedConfig("missing nftables/main.nft")
        lines = file.open(encoding="utf-8").readlines()
        for i, line in enumerate(lines):
            if "__MAKE_PEERING_MARKER" in line:
                break
        else:
            raise MalformedConfig("missing __MAKE_PEERING_MARKER in nftables/main.nft")
        if lines[i+1].strip() != "}":
            raise MalformedConfig("misplaced __MAKE_PEERING_MARKER in nftables/main.nft")
        indents = lines[i].find("#")
        new = f'"{self.answers["iface"]}",\n'
        lines.insert(i, ' ' * indents + new)
        with open(file, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("Please manually check the nftables/main.nft file for correctness.")

    def _print_additional_info(self) -> None:
        """Print node information."""
        node_info = f"{self.answers['site']}.{self.DOMAIN}"
        print(f"Our ASN is {self.OUR_ASN}.")
        try:
            import dns.resolver
            try:
                answers = dns.resolver.resolve(node_info, "TXT")
                for answer in answers:
                    for item in answer.strings:
                        print(item.decode("utf-8"))
            except dns.resolver.NoAnswer:
                print("Could not find any additional information.")
            try:
                _ = dns.resolver.resolve(node_info, "A")
            except dns.resolver.NoAnswer:
                print("This node does not have a public endpoint.")
            else:
                print(f"WireGuard endpoint: {node_info}:{self.answers['listen_port']}")
        except ImportError:
            print("Unable to automatically retrieve node information.")
            print(f"Such information can be found by querying `TXT {node_info}`.")

    def _generate_files(self) -> None:
        """Generate the configuration files."""
        self._generate_netdev()
        self._generate_network()
        self._generate_bird()
        self._add_interface_to_firewall()


if __name__ == "__main__":
    MakePeer()
