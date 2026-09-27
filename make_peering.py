#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import readline as _
from pathlib import Path
from pprint import pprint
from types import MappingProxyType


class MalformedConfig(Exception):
    pass


class MakePeer:
    # Defined in each nftables/main.nft
    PORT_RANGE = range(24201, 24300)
    OUR_ASN = 4242420893
    DOMAIN = "dn42.maiyun.me"
    SITES = ("ca04", "jp02", "uc01")
    SITE_HEX = MappingProxyType({"ca04": "ca04", "jp02": "aa02", "uc01": "2c01"})
    DEFAULT_MTU = MappingProxyType({"ca04": 1420, "jp02": 1420, "uc01": 1420})
    BIRD_TEMPLATE = """protocol bgp {proto_name} from dnpeers {{
    neighbor {addr}%{iface} as {asn};
    bfd {bfd};
    direct;
    ipv4 {{
        import where dn42_filter4im(0x{sitehex}, {asn}, 0, 0, 0);
        export where dn42_filter4ex(0x{sitehex}, {asn}, 0);
    }};
    ipv6 {{
        import where dn42_filter6im(0x{sitehex}, {asn}, 0, 0, 0);
        export where dn42_filter6ex(0x{sitehex}, {asn}, 0);
    }};
}}
"""
    WG_ENV_TEMPLATE = """MTU={mtu}
OUR_v6ADDR={our}
PEER_v6ADDR={peer}
"""
    WG_CONF_TEMPLATE = """# vi: ft=dosini
# /etc/wireguard/{iface}.conf.in

[Interface]
ListenPort = {listen_port}
PrivateKey = @PRIVATE_KEY@

[Peer]
PublicKey = {peer_pub_key}
AllowedIPs = fe80::/64, fd00::/8, 172.31.0.0/16, 172.20.0.0/14, 10.0.0.0/8{endpoint}
"""
    answers: dict[str, str]

    @property
    def _wireguard(self) -> Path:
        if "site" not in self.answers:
            raise ValueError("site not set")
        site = self.answers["site"]
        path = Path(f"{site}/wireguard")
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
        self.answers = {}
        self.ask_questions()
        print("Will generate based on the following answers:")
        pprint(self.answers)
        self._print_additional_info(pre=False)
        resp = input("Continue? [Y/n] ").strip()
        if resp.lower() == "n":
            print("Will not generate files")
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
    def _ask_numeric(
        question: str, can_strip_prefix: str = "", default: int | None = None
    ) -> int:
        """Ask a numeric question."""
        if not question.endswith(" "):
            question += " "
        if default is not None:
            question += f"[default: {default}] "
        while True:
            try:
                ans = input(question).strip()
                if can_strip_prefix and ans.startswith(can_strip_prefix):
                    ans = ans[len(can_strip_prefix) :]
                return int(ans)
            except ValueError:
                if default is not None:
                    return default
                print("Invalid input; try again\n")

    @staticmethod
    def _ask_string(question: str, default: str | None = None) -> str:
        """Ask a string question."""
        if not question.endswith(" "):
            question += " "
        if default is not None:
            question += f"[default: {default}] "
        while True:
            answer = input(question).strip()
            if answer:
                return answer
            elif default is not None:
                return default
            print("A response is required; try again\n")

    @classmethod
    def _ask_choices(
        cls, question: str, choices: tuple[str, ...], default: str | None = None
    ) -> str:
        """Ask for a choice among a fixed set of possible options."""
        if default is not None:
            assert default in choices
            question += f" [default: {default}]"
        while True:
            print(question)
            for i, name in enumerate(choices):
                print(f"{i + 1}. {name}")
            answer = input("Answer: ").strip()
            if not answer and default is not None:
                return default
            got = cls._parse_choice(choices, answer)
            if got is not None:
                return choices[got]
            print("Invalid choice, try again.\n")

    @classmethod
    def _ask_wgkey(cls, question: str, default: str | None = None) -> str:
        """Ask for a WireGuard key."""

        def valid_key(key: str) -> bool:
            if len(key) != 44:
                return False
            if key[-1] != "=":
                return False
            chrs = set(key[:-1]) - {"+", "/"}
            return all(c.isalnum() for c in chrs)

        while True:
            key = cls._ask_string(question, default)
            if valid_key(key):
                return key
            print("Invalid key; try again\n")

    @staticmethod
    def _translate_underscore(original: str) -> str:
        tr = str.maketrans({".": "_", "-": "_", " ": ""})
        return original.translate(tr)

    def _ask_site(self) -> str:
        """Ask for a site name."""
        return self._ask_choices("Which site is this peer for?", self.SITES)

    def _ask_bfd(self) -> str:
        """Ask for BFD support."""
        return self._ask_choices(
            "Do you wish to enable BFD?",
            choices=("on", "off", "graceful"),
            default="off",
        )

    def _ask_asn(self) -> str:
        while True:
            asn = self._ask_numeric("What is the peer (your) ASN?", "AS")
            if 0 < asn < 2**32:
                if asn // 10000 != 424242:
                    print("Warning: non-dn42 ASN")
                return str(asn)
            print("Bad ASN. Please try again.\n")

    def _ask_listen_port(self) -> int:
        """Ask for listening port and check for duplicates."""
        existing = self._wireguard.glob("*.conf.in")
        LOOKFOR = "ListenPort ="
        site_used_ports = set()
        for conf in existing:
            lines = conf.open(encoding="utf-8").readlines()
            this_port = None
            for line in lines:
                if line.startswith(LOOKFOR):
                    if this_port is not None:
                        raise MalformedConfig(f"multiple {LOOKFOR}")
                    this_port = int(line[len(LOOKFOR) :])
            if this_port is None:
                raise MalformedConfig(f"missing {LOOKFOR}")
            site_used_ports.add(this_port)
        available = set(self.PORT_RANGE).difference(site_used_ports)
        print(f"Please select a listening port in {self.PORT_RANGE}")
        print("These ports are in use:")
        pprint(site_used_ports)
        while True:
            port = self._ask_numeric(
                "Which port should we listen on?", default=next(iter(available))
            )
            if port not in site_used_ports and port in self.PORT_RANGE:
                return port
            print("This port is unavailable.\n")

    def ask_questions(self) -> None:
        """Ask all questions."""
        print(
            "Nothing will be touched until the very last step. "
            "You may therefore interrupt the program anytime should there be any mistake.\n"
        )
        self.answers["site"] = self._ask_site()
        self.answers["listen_port"] = str(self._ask_listen_port())
        self._print_additional_info(pre=True)
        print()
        self.answers["asn"] = self._ask_asn()
        self.answers["pname"] = self._ask_string(
            "What is a descriptive short name for the peer?"
        )
        self.answers["ploc"] = self._ask_string(
            "What is a descriptive location code for the peer?"
        )
        self._generate_names()
        self.answers["ppub"] = self._ask_wgkey("What is the peer's public key?")
        print(
            "\nNote: some nodes support MTU 9000. "
            "If the PMTU is higher than 1500, you may want to use a higher value in the following question.\n"
            "If your IPv[46] is tunneled or otherwise has a lower MTU than 1500, please also choose a value accordingly."
        )
        self.answers["wgmtu"] = str(
            self._ask_numeric(
                "What should the WireGuard interface's MTU be?", default=1420
            )
        )
        print("\nNote: if the peer does not have a public endpoint, leave this blank")
        self.answers["endpoint"] = self._ask_string(
            "What is the endpoint for the peer?", default=""
        )
        print(
            "Note: if the peer does not use IPv6LL, fill something else and manually edit the file"
        )
        asn_lastfour = int(self.answers["asn"][-4:])
        maybe = f"fe80::{asn_lastfour}"
        self.answers["peeraddr"] = self._ask_string(
            "What is the peer's IPv6 link-local address?", default=maybe
        )
        if "/" not in self.answers["peeraddr"]:
            self.answers["peeraddr"] += "/64"
        self.answers["ownaddr"] = self._ask_string(
            "What is our IPv6 link-local address?", default="fe80::893"
        )
        if "/" not in self.answers["ownaddr"]:
            self.answers["ownaddr"] += "/64"
        self.answers["bfd"] = self._ask_bfd()

    def _generate_names(self) -> None:
        """Generate interface, file, and bird names."""
        # WireGuard interface name
        if len(self.answers["pname"] + self.answers["ploc"]) > 10:
            print(
                "Warning: names are too long, please specify a shorter interface name"
            )
        short_name = self._translate_underscore(self.answers["pname"].lower())
        short_loc = self._translate_underscore(self.answers["ploc"].lower())
        maybe = "wg{}{}{}".format(self.answers["asn"][-4:], short_name, short_loc)
        iface_name = self._ask_string(
            "A good interface name for the peer?", default=maybe
        )
        # BIRD configuration file names
        maybe = f"30-dn42-{short_name}-{short_loc}"
        file_name = self._ask_string("A good file name for the peer?", default=maybe)
        # BIRD configuration name
        maybe = f"{short_name}_{short_loc}"
        bird_name = self._ask_string(
            "A good BIRD configuration name for the peer?", default=maybe
        )
        # Save the names
        self.answers["iface"] = iface_name
        self.answers["file"] = file_name
        self.answers["bird"] = self._translate_underscore(bird_name)

    def _maybe_write_file(self, file: Path, content: str) -> None:
        """Write a file if it doesn't exist."""
        if file.exists():
            resp = input(f"File {file} already exists, overwrite? [y/N] ").strip()
            if resp.lower() != "y":
                print(f"Skipping {file} generation")
                return
        with open(file, "w", encoding="utf-8") as f:
            f.write(content)

    def _generate_bird(self) -> None:
        """Generate the BIRD configuration."""
        peerip_nocidr = self.answers["peeraddr"].split("/")[0]
        bird = self.BIRD_TEMPLATE.format(
            proto_name=self.answers["bird"],
            addr=peerip_nocidr,
            iface=self.answers["iface"],
            asn=self.answers["asn"],
            sitehex=self.SITE_HEX[self.answers["site"]],
            bfd=self.answers["bfd"],
        )
        file = self._birdconf / f"{self.answers['file']}.conf"
        self._maybe_write_file(file, bird)

    def _generate_wg_conf(self) -> None:
        """Generate /etc/wireguard/{iface}.conf.in."""
        conf = self.WG_CONF_TEMPLATE.format(
            iface=self.answers["iface"],
            listen_port=self.answers["listen_port"],
            peer_pub_key=self.answers["ppub"],
            endpoint=f"\nEndpoint={self.answers['endpoint']}"
            if self.answers["endpoint"]
            else "",
        )
        file = self._wireguard / f"{self.answers['iface']}.conf.in"
        self._maybe_write_file(file, conf)

    def _generate_wg_env(self) -> None:
        """Generate /etc/wireguard/{iface}.env."""
        envf = self.WG_ENV_TEMPLATE.format(
            mtu=self.answers["wgmtu"],
            our=self.answers["ownaddr"],
            peer=self.answers["peeraddr"],
        )
        file = self._wireguard / f"{self.answers['iface']}.env"
        self._maybe_write_file(file, envf)

    def _add_interface_to_firewall(self) -> None:
        """Add the interface and the WG port to nftables/main.nft."""
        site = self.answers["site"]
        file = Path(f"{site}/nftables/main.nft")
        if not file.exists():
            raise MalformedConfig("missing nftables/main.nft")
        lines = file.open(encoding="utf-8").readlines()
        for i, line in enumerate(lines):
            if "__MAKE_PEERING_PORT_MARKER" in line:
                break
        else:
            raise MalformedConfig(
                "missing __MAKE_PEERING_PORT_MARKER in nftables/main.nft"
            )
        if lines[i + 1].strip() != "}":
            raise MalformedConfig(
                "misplaced __MAKE_PEERING_PORT_MARKER in nftables/main.nft"
            )
        indents = lines[i].find("#")
        new = f"{self.answers['listen_port']},\n"
        lines.insert(i, " " * indents + new)
        with open(file, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"Please manually check `{site}/nftables/main.nft` for correctness")

    def _print_additional_info(self, pre: bool) -> None:
        """Print node information."""
        node_info = f"{self.answers['site']}.{self.DOMAIN}"
        print("\nPeering Information:")
        print(f"\tOurASN={self.OUR_ASN}")
        if not pre:
            print(f"\tOurIPv6={self.answers['ownaddr']}")
        print("\tOptions=MP-BPG + Extended Next Hop")
        try:
            import dns.resolver

            try:
                _ = dns.resolver.resolve(node_info, "A")
            except dns.resolver.NoAnswer:
                print("\tWGEndpoint=This node does not have a public endpoint")
            else:
                print(f"\tWGEndpoint={node_info}:{self.answers['listen_port']}")
            try:
                answers = dns.resolver.resolve(node_info, "TXT")
                for answer in answers:
                    for item in answer.strings:
                        print("\t" + item.decode("utf-8"))
            except dns.resolver.NoAnswer:
                print("Could not retrieve more node information")
        except ImportError:
            print("Unable to automatically retrieve node information")
            print(f"Such information can be found by querying `TXT {node_info}`")

    def _generate_files(self) -> None:
        """Generate the configuration files."""
        self._generate_wg_env()
        self._generate_wg_conf()
        self._generate_bird()
        self._add_interface_to_firewall()


if __name__ == "__main__":
    MakePeer()
