#!/bin/sh
# Re-add the tv-pc netconsole allow rule if the box firewall came up without it.
# box-fw.nft has the rule, but the /etc copy only updates via install.sh (sudo
# password); until then a reboot or reload drops it. Uses the NOPASSWD nft rule.
sudo -n /usr/sbin/nft list chain inet fw input | grep -q 'udp dport 6666' && exit 0
exec sudo -n /usr/sbin/nft add rule inet fw input ip saddr 192.168.1.79 udp dport 6666 accept comment '"tv-pc netconsole"'
