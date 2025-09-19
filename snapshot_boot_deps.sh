#! /usr/bin/env bash

file_timestamp=$(date +%Y-%m-%d_%Hh-%Mm-%Ss)


if [ -z "$efi_dir" ]; then
    efi_dir="/efi"
fi
if [ -z "$boot_dir" ]; then
    boot_dir="/boot"
fi
if [ -z "$backup_dir" ]; then
    backup_dir="$1"
fi
if [ -z "$backup_dir" ]; then
    script_dir=$(dirname "$(realpath "$0")")
    backup_dir="$script_dir/logs"
fi

script_dir=$(dirname "$(realpath "$0")")
archive_dir_script="$script_dir/utils/archive-dir.sh"


bash $archive_dir_script "$efi_dir" "$backup_dir/efi-snapshot-$file_timestamp"
bash $archive_dir_script "$boot_dir" "$backup_dir/boot-snapshot-$file_timestamp"
