# Raspberry Pi 06 (ab06)

## Info
Has dn42 connection via BGP and AREDN connection via `olsrd` and babel.

## Kernel tables
Default table imports dn42, AMPR, and AREDN routes by bird.
The AREDN default route should automatically get a lower priority as it is a /8.
Specific AREDN routes are usually longer than dn42 routes and are thus preferred.

Table 44 will contain AMPR routes from `bird`. Currently not used.

Table 45 populated by `olsrd` with AREDN routes.

## Bird tables
Table `master[46]` pipes to all other tables.

Table `aredn_olsr` syncd by `aredn_sync` with `table 45`.

dn42 eBGP nodes syncd with `dn42_v[46]`

BGP with dn42 syncd with `dn42_v[46]` and default table.
Internal nodes sync with `master[46]` with pipes to both tables.
