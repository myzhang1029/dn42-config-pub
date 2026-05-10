SUDO=sudo

.PHONY: seins-%
.DELETE_ON_ERROR:

%.mod: %.te
	checkmodule -M -m -o $@ $<

%.pp: %.mod
	semodule_package -o $@ -m $<

seins-%: %.pp
	$(SUDO) semodule -i $<
	rm -f $*.mod $*.pp
