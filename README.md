# dn42-config
Internet configuration files for AS4242420893 and related devices

## Address Space Plan
`172.23.6.160/28` for routing and ZeroTier allocation. Its IPv6 range is `fdc0:d227:306:ee01::/112`.

In general, each router (and thus each site) gets a `/64` (in addition to the ZeroTier allocation if there is one).

My personal LAN allocates from `172.23.6.176/28`. Its IPv6 range is `fdc0:d227:306:be05::/64` (might use SLAAC).

## Route Tables

- The default table contains only local (true clearnet) routes and internal inter-node routes.
- Table `4242` contains dn42 eBGP routes.
- Table `211585` contains AS211585 eBGP routes.

`nftables` controls forwarding between eBGP peers.

## IGP and Babel
Internal connections use a combination of ZeroTier, GRE, and Wireguard based on the node characteristics.

Tunnel `rxcost` is 30 for GRE, 60 for Wireguard, and 100 for ZeroTier.
We mark tunnel interfaces as `wireless` so that missing `hello`s will continuously alter the route metrics instead of cutting a node off.
`rtt cost 96` is used to match the default of a tunnel.

According to [FRR's manual](https://docs.frrouting.org/en/latest/babeld.html):
> Specifies whether this interface is wireless, which disables a number of optimisations that are only correct on wired interfaces.
> Specifying wireless (the default) is always correct, but may cause slower convergence and extra routing traffic.
