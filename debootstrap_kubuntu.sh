#! /usr/bin/env bash


chroot_mount_point=/tmp/bootschroot

sudo -i
add-apt-repository universe
apt update
apt install debootstrap arch-install-scripts micro vim curl -y

debootstrap noble "$chroot_mount_point" http://de.archive.ubuntu.com/ubuntu

cat << 'EOF' | sudo tee "$chroot_mount_point/etc/apt/sources.list"
deb http://de.archive.ubuntu.com/ubuntu/ noble main restricted universe
deb http://de.archive.ubuntu.com/ubuntu/ noble-updates main restricted universe
deb http://de.archive.ubuntu.com/ubuntu/ noble-security main restricted universe
EOF
# #deb http://de.archive.ubuntu.com/ubuntu/ noble-backports main restricted universe multiverse

cat << 'EOF' | sudo tee "$chroot_mount_point/etc/apt/preferences.d/ignored-packages"
Package: snapd cloud-init landscape-common popularity-contest ubuntu-advantage-tools
Pin: release *
Pin-Priority: -1
EOF

scripts_dir=$(dirname "$(realpath "$0")")

mount -o bind "$scripts_dir" "$chroot_mount_point/scripts"

arch-chroot "$chroot_mount_point"