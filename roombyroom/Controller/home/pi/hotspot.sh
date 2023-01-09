nmcli con add type wifi ifname wlan0 con-name RBR autoconnect yes ssid "OPiHotspot"
nmcli con modify RBR 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared
nmcli con modify RBR wifi-sec.key-mgmt wpa-psk
nmcli con modify RBR wifi-sec.psk "itworks4me"
nmcli con modify RBR ipv4.addresses 10.42.0.1
nmcli con up RBR

