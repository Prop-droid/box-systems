#!/usr/bin/env python3
"""Receive tv-pc kernel netconsole (UDP 6666) and append to netconsole.log.

Exists to catch hard freezes on the TV PC: the journal on its disk stops
before the kernel can say anything, but netconsole sends printk lines out
over the LAN as they happen. Box timestamp + sender IP prefix every line.
"""
import os
import socket
import time

LOG = os.path.expanduser("~/systems/tv-pc/netconsole.log")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("0.0.0.0", 6666))
with open(LOG, "a", buffering=1) as f:
    while True:
        data, addr = sock.recvfrom(65535)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        for line in data.decode("utf-8", "replace").splitlines():
            f.write(f"{ts} {addr[0]} {line}\n")
