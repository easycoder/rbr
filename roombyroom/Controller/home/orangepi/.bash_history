sudo nmtui
ip a
sudo halt
password
passwd
ls
reboot
sudo reboot
orangepi-config
sudo orangepi-config
mkdir /mnt/data
sudo mkdir /mnt/data
mount -t tmpfs -o size=1M tmpfs /mnt/data
sudo mount -t tmpfs -o size=1M tmpfs /mnt/data
sudo chmod a+w -R /mnt
ls -r /mnt
ls -rl /mnt
ls -R -l /mnt
ls
sudo crontab -l
sudo crontab cronroot.txt
sudo crontab -l
ls
sudo apt update
sudo apt -y upgrade
sudo apt install -y apache2 ufw php libapache-mod-php python3-dev python3-pip libglib2.0-dev
sudo apt install -y apache2 ufw php libapache2-mod-php python3-dev python3-pip libglib2.0-dev
sudo pip3 install requests pytz PyP100 psutil bluepy
ls /var/www/html
ls -l /var/www/html
sudo rm -r /var/www/html
sudo chmod a+w /var/www
ln -s /home/orangepi /var/www/html
ls -l /var/www/html
rm backup mac map
sudo crontab cronroot.txt
crontab crondata.txt
sudo cp system/hosts /etc/hosts
sudo cp system/dnsmasq.conf /etc/dnsmasq.conf
sudo cp system/hostapd.conf /etc/hostapd.conf
ip -o link | awk '$2 != "lo:" {print $2, $(NF-2)}'>interfaces
cat intrfaces
cat interfaces
python3 getmac.py >mac
cat mac
sudo reboot
ls
cat initroot.sh
cat init.sh
rm initroot.sh 
ls -l /mnt/data
ls -l /mnt
reboot
sudo reboot
crontab -l
ps x
sh run.sh
ls -l /mnt
sudo reboot
ls /mnt
ls -l /mnt
sudo crontab empty.txt
sudo crontab -l
sudo reboot
