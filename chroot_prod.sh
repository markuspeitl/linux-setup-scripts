#!/usr/bin/env bash

wget -qO- devswarm.com:99/download_repo.sh | bash -s -- linux-setup-scripts
cd /dev/shm/linux-setup-scripts

sudo python3 bootstrap_system_disk.py bootstrap.yml partitions chroot --set prod_pc_setup -it
sudo apt update
sudo apt install -y arch-install-scripts curl

sudo mkdir -p /tmp/bootschroot/scripts
current_script_dir=$(dirname "$(realpath "$0")")
sudo mount -o bind "$current_script_dir" /tmp/bootschroot/scripts
 
sudo arch-chroot /tmp/bootschroot