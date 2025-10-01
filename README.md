# dn42-config
Internet configuration files for AS4242420893 and related devices

## Plan
`172.23.6.160/28` for routing and ZeroTier allocation. Its IPv6 range is `fdc0:d227:306:ee01::/112`.

In general, each router (and thus each site) gets a `/64` (in addition to the ZeroTier allocation if there is one).

My personal LAN allocates from `172.23.6.176/28`. Its IPv6 range is `fdc0:d227:306:be05::/64` (might use SLAAC).

## 44Net
Routes for `44.63.16.192/28` are propagated via Babel. On each 44Net-connected device, Policy-Based Routing is set up to return 44Net traffic to the same gateway.

## IGP and Babel
Internal connections use a combination of ZeroTier, GRE, and Wireguard based on the node characteristics.

Tunnel `rxcost` is 30 for GRE, 60 for Wireguard, and 100 for ZeroTier.
We mark tunnel interfaces as `wireless` so that missing `hello`s will continuously alter the route metrics instead of cutting a node off.
`rtt cost 96` is used to match the default of a tunnel.

According to [FRR's manual](https://docs.frrouting.org/en/latest/babeld.html):
> Specifies whether this interface is wireless, which disables a number of optimisations that are only correct on wired interfaces.
> Specifying wireless (the default) is always correct, but may cause slower convergence and extra routing traffic.
