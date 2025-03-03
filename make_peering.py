#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import inspect
import readline as _
from pathlib import Path
from pprint import pprint


class MakePeer:
    SITES = ("ca03", "ca04", "ab01", "ab06", "jp02")
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
    answers = {}

    def __init__(self):
        self.ask_questions()
        print("Will generate based on the following answers:")
        pprint(self.answers)
        self._generate_files()
        print("Now, insert this rule into firewalld:")
        print('<interface name="{}"/>'.format(self.answers["iface"]))

    def _parse_choice(self, choices: tuple[str], answer: str) -> int | None:
        """Parse a user choice."""
        # As a string
        for i, choice in enumerate(choices):
            if choice.lower() == answer.lower():
                return i
        # As a number
        try:
            choice = int(answer)
            if 0 < choice <= len(choices):
                return choice - 1
        except ValueError:
            pass
        return None

    def _ask_numeric(self, question: str, can_strip_prefix: str = "") -> int:
        """Ask a numeric question."""
        while True:
            try:
                ans = input(question)
                if can_strip_prefix and ans.startswith(can_strip_prefix):
                    ans = ans[len(can_strip_prefix):]
                return int(ans)
            except ValueError:
                print("Invalid input, try again.\n")

    def _ask_string(self, question: str) -> str:
        """Ask a string question."""
        return input(question)

    def _ask_wgkey(self, question: str) -> str:
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
            for i, site in enumerate(self.SITES):
                print(f"{i+1}. {site}")
            choice = input("Answer: ")
            site = self._parse_choice(self.SITES, choice)
            if site is not None:
                return self.SITES[site]
            print("Invalid choice, try again.\n")

    def ask_questions(self):
        """Ask all questions."""
        self.answers["site"] = self._ask_site()
        self.answers["asn"] = self._ask_numeric("What is the peer ASN? ", "AS")
        self.answers["pname"] = self._ask_string(
            "What is a descriptive name for the peer? ")
        self.answers["ploc"] = self._ask_string(
            "What is a descriptive location for the peer? ")
        self._generate_names()
        self.answers["ppub"] = self._ask_wgkey(
            "What is the peer's public key? ")
        self.answers["listen_port"] = self._ask_numeric(
            "Which port should we listen on? ")
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

    def _generate_names(self):
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

    def _maybe_write_file(self, file: Path, content: str):
        """Write a file if it doesn't exist."""
        if file.exists():
            resp = input(f"File {file} already exists, overwrite? [y/N] ")
            if resp.lower() != "y":
                print(f"Skipping {file} generation.")
                return
        with open(file, "w") as f:
            f.write(content)

    def _generate_bird(self):
        """Generate the BIRD configuration."""
        peerip_nocidr = self.answers["peeraddr"].split("/")[0]
        bird = self.BIRD_TEMPLATE.format(
            self.answers["bird"], peerip_nocidr, self.answers["iface"], self.answers["asn"])
        file = Path(
            "{}/bird/conf.d/{}.conf".format(self.answers["site"], self.answers["file"]))
        self._maybe_write_file(file, bird)

    def _generate_netdev(self):
        """Generate the systemd-networkd .netdev file."""
        netdev = self.SYSTEMD_NETDEV_TEMPLATE.format(
            self.answers["file"],
            self.answers["iface"],
            self.answers["systemd"],
            self.answers["listen_port"],
            self.answers["ppub"],
            f"\nEndpoint={self.answers['endpoint']}" if self.answers["endpoint"] else ""
        )
        file = Path(
            "{}/systemd/network/{}.netdev".format(self.answers["site"], self.answers["file"]))
        self._maybe_write_file(file, netdev)

    def _generate_network(self):
        """Generate the systemd-networkd .network file."""
        network = self.SYSTEMD_NETWORK_TEMPLATE.format(
            self.answers["file"],
            self.answers["iface"],
            self.answers["ownaddr"],
            self.answers["peeraddr"]
        )
        file = Path(
            "{}/systemd/network/{}.network".format(self.answers["site"], self.answers["file"]))
        self._maybe_write_file(file, network)

    def _generate_files(self):
        """Generate the configuration files."""
        self._generate_netdev()
        self._generate_network()
        self._generate_bird()


if __name__ == "__main__":
    MakePeer()
