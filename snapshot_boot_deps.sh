#! /usr/bin/env bash

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

if [ -z "$file_timestamp" ] &&  [ -n "$gen_timestamp" ]; then
    file_timestamp=$(date +%d-%m-%Y_%Hh-%Mm-%Ss)
fi

if [ -n "$file_timestamp" ]; then
    file_timestamp_postfix="-$file_timestamp"
fi


script_dir=$(dirname "$(realpath "$0")")
archive_dir_script="$script_dir/utils/archive-dir.sh"

bash "$archive_dir_script" "$efi_dir" "$backup_dir/efi-snapshot$file_timestamp_postfix"
bash "$archive_dir_script" "$boot_dir" "$backup_dir/boot-snapshot$file_timestamp_postfix"
