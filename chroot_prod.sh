#!/usr/bin/env bash

sudo apt update
sudo apt install -y arch-install-scripts curl
#wget -qO- devswarm.com:99/download_repo.sh | bash -s -- linux-setup-scripts

echo "Downloading pull script ..."

wget -O /dev/shm/download_repo.sh devswarm.com:99/download_repo.sh

bash /dev/shm/download_repo.sh linux-setup-scripts || exit 1
#curl -L devswarm.com:99/download_repo.sh | bash -s -- linux-setup-scripts

sleep 2
cd /dev/shm/linux-setup-scripts/ || exit 1

echo "Starting chroot mounting ..."

sudo python3 bootstrap_system_disk.py bootstrap.yml chroot --set prod_pc_setup -it || exit 1

if [ ! -d /tmp/bootschroot ]; then
    echo "Chroot dir /tmp/bootschroot does not exist, exiting"
    exit 1
fi

echo "Bind mounting and chrooting ..."

sudo mkdir -p /tmp/bootschroot/scripts
current_script_dir=$(dirname "$(realpath "$0")")
sudo mount -o bind "$current_script_dir" /tmp/bootschroot/scripts
 
sudo arch-chroot /tmp/bootschroot