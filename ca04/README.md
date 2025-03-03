# ca04 server

## Info
Has dn42 connection via BGP and AMPRNet connection via the IPIP mesh.

## Kernel tables
Default table only imports from dn42 by bird.

Table 44 populated by `ampr_ripd` with AMPRNet routes; uses policy-based routing.

## Bird tables
Table `master[46]` pipes to all other tables.

Table `ampr_ripd` syncd by `ampr_ripd_sync` with `table 44`.

dn42 eBGP nodes syncd with `dn42_v[46]`

BGP with dn42 syncd with `dn42_v[46]` and default table.
Internal nodes sync with `master[46]` with pipes to both tables.
