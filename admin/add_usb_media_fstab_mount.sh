#!/bin/env sh

device_part_label="$1"
target_mount_name="$2"

if ! echo "$device_part_label" | grep -q "/dev"; then
    device_part_label="/dev/$device_part_label"
fi

echo "$device_part_label"

device_part_uuid=$(blkid "$device_part_label" | grep -Po "(?<=UUID\=\").+?(?=\")" | head -n 1)

target_mount_path="/mnt/$target_mount_name"
if [ -z "$target_mount_name" ]; then
	target_mount_path=/media
fi

sudo mkdir -p "$target_mount_path"

fstab_newline="UUID=$device_part_uuid \"$target_mount_path\" auto nosuid,nodev,nofail 0 0"

printf "\n# Media device\n" | sudo tee -a /etc/fstab
echo "$fstab_newline" | sudo tee -a /etc/fstab

sudo mount -a