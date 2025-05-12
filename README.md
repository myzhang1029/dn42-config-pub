# dn42-config
Internet configuration files for AS4242420893 and related devices

## Plan
`172.23.6.160/28` for routing and ZeroTier allocation. Its IPv6 range is `fdc0:d227:306:ee01::/112`.

In general, each router (and thus each site) gets a `/64` (in addition to the ZeroTier allocation if there is one).

Raspberry Pi LAN allocates from `172.23.6.176/28`. Its IPv6 range is `fdc0:d227:306:ab01::/64` (might use SLAAC).

## 44Net
Routes for `44.63.16.192/28` are propagated via Babel. On each 44Net-connected device, Policy-Based Routing is set up to return 44Net traffic to the same gateway.
