#! /usr/bin/env python3
import os
import re


def install_systemd_boot_for_system():
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

    crpto_part_info = os.popen("lsblk -f /dev/sdc -o FSTYPE,UUID | grep crypto").read().strip()

    if '\n' in crpto_part_info:
        print("Multiple crypto partitions found, not supported")
        exit(1)

    crpto_part_info = re.sub(r'\s+', ' ', crpto_part_info)
    crpto_part_info_parts = crpto_part_info.split(' ')
    crpto_part_uuid = crpto_part_info_parts[1]

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
