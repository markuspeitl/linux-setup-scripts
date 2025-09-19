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

function snap_dir_to_target(){
    tar_bin=$(which tar)
    #tar_bin=
    zstd_bin=$(which zstd)
    gzip_bin=$(which gzip)

    compress_opt=""
    tar_file_ext="tar"
    if [ -n "$zstd_bin" ]; then
        compress_opt="-I 'zstd -7'"
        tar_file_ext="tar.zst"
    elif [ -n "$gzip_bin" ]; then
        compress_opt="-z"
        tar_file_ext="tar.gz"
    else
        echo "No compression binary found, will create uncompressed tar archive"
    fi

    zip_file_ext="zip"
    zip_bin=$(which zip)

    src_dir_path="$1"
    src_dir_path=$(realpath "$src_dir_path")

    target_file_path="$2"
    target_file_path=$(realpath "$target_file_path")

    target_dir_path=$(dirname "$target_file_path")
    mkdir -p "$target_dir_path"


    if [ -n "$tar_bin" ]; then
        echo "Create boot deps snapshot with '$tar_bin'"

        # wanted to avoid eval, but bash refuses to not split it into multiple args by adding quotes
        set -x
        eval "sudo $tar_bin $compress_opt -cf \"$target_file_path.$tar_file_ext\" --absolute-names \"$src_dir_path\""
        set +x

        return 0
    fi

    if [ -n "$zip_bin" ]; then
        echo "Create boot deps snapshot with '$zip_bin'"
        
        set -x
        sudo $zip_bin -r "$target_file_path.$zip_file_ext" "$src_dir_path"
        set +x

        return 0
    fi

    echo "Failed to create snapshot of '$1' 'tar' and 'zip' binaries not found or not in PATH"
}

efi_has_files=$(find "$efi_dir" -type f 2> /dev/null | head -n 1)

if [ -d "$efi_dir" ] && [ -n "$efi_has_files" ]; then
    snap_dir_to_target "$efi_dir" "$backup_dir/efi-snapshot-$file_timestamp"
else
    echo "EFI dir '$efi_dir' does not exist or has no files, skipping"
fi

boot_has_files=$(find "$boot_dir" -type f 2> /dev/null | head -n 1)

if [ -d "$boot_dir" ] && [ -n "$boot_has_files" ]; then
    snap_dir_to_target "$boot_dir" "$backup_dir/boot-snapshot-$file_timestamp"
else
    echo "Boot dir '$boot_dir' does not exist, skipping"
fi
