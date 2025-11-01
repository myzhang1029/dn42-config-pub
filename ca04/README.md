# ca04 server

## Info
Has dn42 and public AS211585 connections via BGP.

## Kernel tables
Default table only imports from dn42 by bird.

## Bird tables
Table `master[46]` pipes to all other tables.

dn42 eBGP nodes syncd with `dn42_v[46]`

BGP with dn42 syncd with `dn42_v[46]` and default table.
Internal nodes sync with `master[46]` with pipes to both tables.
