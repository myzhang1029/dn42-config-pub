# dn42-config
Internet configuration files for AS4242420893 and related devices

## Plan
`172.23.6.160/28` for routing and ZeroTier allocation. Its IPv6 range is `fdc0:d227:306:ee01::/112`.

Raspberry Pi LAN allocates from `172.23.6.176/28`. Its IPv6 range is `fdc0:d227:306:ab01::/64` (might use SLAAC).

## 44Net
Routes for `44.63.16.192/28` are propagated via Babel. On each 44Net-connected device, Policy-Based Routing is set up to return 44Net traffic to the same gateway.

# Ports
Allocated from a continuous range to ease firewall configuration:
- 24201=hujk
- 24202=Potat0
- 24203=iedon
- 24204=kskb
- 24205=Kioubits
- 24206=kskb Neo
- 24207=RoutedBits
- 24208=Maraun
- 24209=Lare
- 24210=SUNNET
- 24211=Tech 9
- 24212=Duststars
- 24213=Sidereal
- 24300=Internal Things
