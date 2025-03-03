#!/bin/sh

autoreconf -fi
./configure --sysconfdir=/etc --localstatedir=/var --runstatedir=/run/bird
make -j"$(nproc)"
sudo make install
sudo useradd -r bird -M -d /etc/bird -s /sbin/nologin
