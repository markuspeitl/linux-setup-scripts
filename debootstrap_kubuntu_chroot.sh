#! /usr/bin/env bash

# To run 
# sh /scripts/debootstrap_kubuntu_chroot.sh

# To be executed inside chroot

apt update
apt upgrade -y

apt install --no-install-recommends \
  linux-image-generic-hwe-24.04 \
  linux-headers-generic-hwe-24.04 \
  linux-firmware \
  initramfs-tools \
  efibootmgr

apt install micro vim curl -y

dpkg-reconfigure tzdata
dpkg-reconfigure locales
dpkg-reconfigure keyboard-configuration


host_name=glass-ryzen
echo "$host_name" > /etc/hostname
echo "127.0.0.1 $host_name" >> /etc/hosts

# root password
passwd

user_name=pmarkus
useradd -mG sudo $user_name
passwd $user_name

cp /etc/skel/.* /home/$user_name/

systemctl enable systemd-networkd

network_file=/etc/systemd/network/20-wired.network
network_template=$(cat << 'EOF'
[Match]
Name=enp4s0

[Network]
DHCP=yes
EOF
)
#| tee "$network_file"
echo "$network_template" > "$network_file"

ip addr show
echo "Please enter network adapter name to use (e.g. enp0s3):"
read adapter_name

sed -i "s/enp4s0/$adapter_name/g" "$network_file"

apt install \
  at \
  btrfs-progs \
  curl \
  dmidecode \
  ethtool \
  git \
  gnupg \
  htop \
  man \
  patch \
  screen \
  software-properties-common \
  zsh \
  zstd -y
#  needrestart \
#  openssh-server \
#  gawk \
#  tmux \
#  firewalld \
#  fwupd \

apt install kubuntu-desktop -y

apt install systemd-boot