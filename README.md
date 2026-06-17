# dn42-config
Internet configuration files for AS4242420893 and related devices


## For AutoPeer

Run
```
./make_peering.py
```
and follow the dialog to create new peerings.


## Address Space Plan
`172.23.6.160/28` for routing and ZeroTier allocation. Its IPv6 range is `fdc0:d227:306:ee01::/112`.

In general, each router (and thus each site) gets a `/64` (in addition to the ZeroTier allocation if there is one).

My personal LAN allocates from `172.23.6.176/28`. Its IPv6 range is `fdc0:d227:306:be05::/64` (might use SLAAC).

## Route Tables

### Bird Tables
Table `master[46]` pipes to all other tables.
Internal nodes (Babel and iBGP) sync with `master[46]`.

dn42 eBGP peers import/export using `dn42_v[46]`.
Clearnet AS211585 eBGP import/export using `inet_v[46]`.

### Kernel Tables
- The default table contains only local (true clearnet) routes and internal inter-node routes.
- Table `4242` contains dn42 eBGP routes (syncd from bird `dn42_v[46]`).
- Table `211585` contains AS211585 eBGP routes (syncd from bird `inet_v[46]`), for devices with AS211585 connections/

`nftables` controls forwarding between eBGP peers.

## IGP and Babel
Internal connections use a combination of ZeroTier, GRE, and WireGuard based on the node characteristics.

Tunnel `rxcost` is 30 for GRE, 60 for Wireguard, and 100 for ZeroTier.
We mark tunnel interfaces as `wireless` so that missing `hello`s will continuously alter the route metrics instead of cutting a node off.
`rtt cost 96` is used to match the default of a tunnel.

According to [FRR's manual](https://docs.frrouting.org/en/latest/babeld.html):
> Specifies whether this interface is wireless, which disables a number of optimisations that are only correct on wired interfaces.
> Specifying wireless (the default) is always correct, but may cause slower convergence and extra routing traffic.
