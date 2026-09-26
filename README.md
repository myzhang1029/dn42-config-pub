# dn42-config
Internet configuration files for AS4242420893, AS211585, and related devices


## For AutoPeer

Run
```
./make_peering.py
```
and follow the dialog to create new peerings.


## dn42 IPAM
`172.23.6.160/28` for routing and ZeroTier allocation. No IPv4 unless necessary.
ZeroTier's IPv6 range is `fdc0:d227:306:ee01::/112`.

In general, each router gets a `/64` (in addition to the ZeroTier `/128` if there is one) for the
host itself, and its site gets a `/56`.

My personal LANs allocate from `fdc0:d227:306:be00::/56` (might use SLAAC and is IPv6-only).

AS211585 IPAM is similar but not disclosed in detail.

## Firewall Design

The overall idea is that all interfaces can be classified into these categories:
1. public interfaces (no ifgroup): untunneled physical interfaces.
2. dn42 peers (in `ifgroup 4242`): carry traffic to/from dn42 eBGP peers.
3. internal peers (in `ifgroup 4040`): carry traffic between internal nodes.
4. AS211585 peers (in `ifgroup 211585`): carry traffic to/from AS211585 eBGP peers.
5. Possibly other interconnections

For transits over physical connections, the interface is classified as both 1. and 4.
(Other types of shared interfaces would use either VLAN or some other form of separation.)

### Input Chain
Idea:
- public interfaces only carry untrusted input traffic.
- dn42 interfaces carry both untrusted input traffic and forwarding traffic.
- internal interfaces carry only both untrusted input traffic, trusted input traffic, and forwarding traffic.

The input chain evaluates the following in order:
1. Accept necessary things like ICMP and conntrack established/related.
2. Accept things that are allowed from all sources (`chain input_everywhere`).
3. Accept routing traffic on internal interfaces, peering traffic, and dn42 internal services (`chain input_dn42`).
4. Accept things local to this machine (`chain input_machdep`).

### Forward Chain
All dn42 traffic fowards without conntrack.

AS211585 traffic forwards if the source/destination is in the AS211585 address space or AS cone.
## Route Tables

### Bird Tables
Table `master[46]` pipes to all other tables.
Internal nodes (Babel and iBGP) sync with `master[46]`.

dn42 eBGP peers import/export using `dn42_v[46]`.
Clearnet AS211585 eBGP import/export using `inet_v[46]`.

### Kernel Tables
- The default table contains only local (true clearnet) routes.
- Table `4242` contains dn42 eBGP routes (syncd from bird `dn42_v[46]`).
- Table `211585` contains AS211585 eBGP routes (syncd from bird `inet_v[46]`), for devices with AS211585 connections.

`nftables` controls forwarding between eBGP peers.

## IGP and Babel
Internal connections use a combination of ZeroTier, GRE, and WireGuard based on the node characteristics.

Tunnel `rxcost` is 30 for GRE, 60 for Wireguard, and 100 for ZeroTier.
We mark tunnel interfaces as `wireless` so that missing `hello`s will continuously alter the route metrics instead of cutting a node off.
`rtt cost 96` is used to match the default of a tunnel.

According to [FRR's manual](https://docs.frrouting.org/en/latest/babeld.html):
> Specifies whether this interface is wireless, which disables a number of optimisations that are only correct on wired interfaces.
> Specifying wireless (the default) is always correct, but may cause slower convergence and extra routing traffic.

## BGP local pref
These BGP local preference shift values (loosely) define the routing policy:
- 100: base
- Connection types:
  - +70: Physical (including VLAN-based) connection
  - +40: Same-city tunnel connection
  - 0: Some average tunnel connection with stable underlying backbone
  - -40: Long tunnel connection
- Routing security:
  - +10: ASPA valid (current unimplemented)
  - +10: RPKI valid
  - reject: RPKI invalid
- AS path length:
  - +30: Direct AS neighbour (i.e. =1)
  - -50: (inet) > 16; (dn42) > 8 (in addition, such routes are not exported to peers)
  - reject: (inet) > 64; (dn42) > 16
