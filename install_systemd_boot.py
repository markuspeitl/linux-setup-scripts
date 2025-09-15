#! /usr/bin/env python3
import datetime
import json
import os
import re
import sys

selected_root_part = sys.argv[1]
print(f"Selected root part: {selected_root_part}")
if not os.path.exists(selected_root_part):
    print(f"Selected root part {selected_root_part} does not exist")
    exit(1)

block_infos = os.popen(f"blkid {selected_root_part} -o json").read().strip()
print(f"blkid info for {selected_root_part}: {block_infos}")
block_infos_parsed = json.loads(block_infos)
root_blockdev_uuid = block_infos_parsed["uuid"]
print(f"Root block device UUID: {root_blockdev_uuid}")
if not root_blockdev_uuid:
    print(f"Could not find UUID for {selected_root_part}")
    exit(1)


def install_systemd_boot_for_system():

    path_timestamp = datetime.datetime.now().strftime("%y_%m_%d-%H_%M_%S")

    os.makedirs("/home/pmarkus/bootloader_backups", exist_ok=True)
    os.system(f"tar -I 'zstd -7' -cf /home/pmarkus/bootloader_backups/boot_backup_{path_timestamp}.tar.zst --absolute-names /boot")
    os.system(f"tar -I 'zstd -7' -cf /home/pmarkus/bootloader_backups/efi_backup_{path_timestamp}.tar.zst --absolute-names /efi")

    os.system("update-initramfs -c -k all")
    os.system("systemctl set-default graphical.target")

    os.system("apt install systemd-boot-efi")
    os.system("apt install systemd-boot")

    os.system("bootctl install --boot-path=/boot --esp-path=/efi")
    os.system("bootctl status")
    os.system("bootctl update")

    os.system("chmod 700 /efi/loader/random-seed")


def general_dboot_config(loader_conf_dir="/boot/loader"):
    loader_conf_dir = os.path.abspath(loader_conf_dir)
    os.makedirs(loader_conf_dir, exist_ok=True)
    systemd_boot_type_file = os.path.join(loader_conf_dir, "entries.srel")
    os.system(f"echo \"type1\" > {systemd_boot_type_file}")

    bootloader_conf = os.path.join(loader_conf_dir, "loader.conf")

    if not os.path.exists(bootloader_conf):
        os.system(f"echo \"timeout 15\" > {bootloader_conf}")


def generate_boot_entry(entry_title, entries_dir):

    entries_dir = os.path.abspath(entries_dir)

    os.makedirs(entries_dir, exist_ok=True)

    # crpto_part_info = os.popen("lsblk -f -o FSTYPE,UUID | grep crypto").read().strip()

    # if '\n' in crpto_part_info:
    #     print("Multiple crypto partitions found, not supported")
    #     exit(1)

    # crpto_part_info = re.sub(r'\s+', ' ', crpto_part_info)
    # crpto_part_info_parts = crpto_part_info.split(' ')
    # crpto_part_uuid = crpto_part_info_parts[1]

    # find out with blkid /dev/luks-partitions --> UUID entry
    crpto_part_uuid = root_blockdev_uuid

    root_subvol = "@kubuntu"

    conf_entry_template = f"""\
title {entry_title}
linux /vmlinuz
initrd /initrd.img
options rd.luks.name={crpto_part_uuid}=bootsluks root=/dev/mapper/bootsluks rw rootflags=subvol={root_subvol} verbose
    """

    conf_entry_template = conf_entry_template.strip()

    # https://www.man7.org/linux/man-pages/man7/dracut.cmdline.7.html
    # https://wiki.archlinux.org/title/Systemd-boot
    # Might come in handy:
    # https://articles.akadata.ltd/booting-ubuntu-24-04-with-zfs-root-and-systemd-boot-a-hard-earned-guide/

    entry_file_path = os.path.join(entries_dir, "kubuntu-luks-edge.conf")
    with open(entry_file_path, "w") as f:
        f.write(conf_entry_template)

    print(f"Wrote systemd-boot entry to {entry_file_path}")
    print(f'-------- {entry_file_path} ---------------')
    print(conf_entry_template)
    print('-------------------------------------------')


# Example:
# title Arch Linux
# linux /arch/vmlinuz-linux-lts
# initrd /arch/intel-ucode.img
# initrd /arch/amd-ucode.img
# initrd /arch/initramfs-linux-lts.img
# options rd.luks.name=edd0897e-753d-470b-90c5-39ef659bb0b1=luks root=/dev/mapper/luks rw rootflags=subvol=/arch verbose


install_systemd_boot_for_system()

dboot_conf_dir = "/tmp/fake-dboot"
boot_entries_dir = os.path.join(dboot_conf_dir, "entries")
os.makedirs(boot_entries_dir, exist_ok=True)

general_dboot_config(dboot_conf_dir)
generate_boot_entry("Kubuntu Noble (luks/btrfs)", boot_entries_dir)
