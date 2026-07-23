#!/bin/sh -eu

autoreconf -fi
./configure --sysconfdir=/etc --localstatedir=/var --runstatedir=/run/bird
make -j"$(nproc)"
sudo make install
grep bird /etc/passwd || sudo useradd -r bird -M -d /etc/bird -s /sbin/nologin
