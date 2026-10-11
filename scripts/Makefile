SUDO ?= sudo

.PHONY: %.seins clean-selinux _FORCE
.DELETE_ON_ERROR:
.SECONDARY:

# Don't do anything by default
all:
	@echo Try make MODULE.seins, make install-bird

_FORCE:

### SELinux stuff

# Optional
SEPOLICY_MK ?= /usr/share/selinux/devel/Makefile

%.pp: %.te %.fc %.if
	@if [ -f $(SEPOLICY_MK) ]; then \
		$(MAKE) -f $(SEPOLICY_MK) $@; \
	else \
		echo Building modules without m4 support; \
		checkmodule -M -m -o $*.mod $<; \
		semodule_package -o $@ -m $*.mod -f $*.fc; \
	fi
	rm -rf tmp $*.mod

%.if:
	-[ ! -f $@ ] && touch $@

%.fc:
	-[ ! -f $@ ] && touch $@

%.seins: %.pp
	$(SUDO) semodule -i $<

clean-selinux:
	rm -f *.mod *.pp
	rm -rf tmp
	for file in *.fc *.if; do if [ ! -s $$file ]; then rm -f $$file; fi; done


### Bird stuff

configure: configure.ac
	autoreconf -fi

Makefile: configure
	./configure --sysconfdir=/etc --localstatedir=/var --runstatedir=/run/bird

bird birdc birdcl: Makefile _FORCE
	$(MAKE)

install-bird: bird birdc birdcl Makefile
	$(SUDO) make install
	grep bird /etc/passwd || $(SUDO) useradd -r bird -M -d /etc/bird -s /sbin/nologin
