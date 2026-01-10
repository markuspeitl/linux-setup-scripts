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
    backup_dir="$script_dir/config"
fi


function copy_config_file(){
    src_file="$1"
    src_dir="$2"
    target_dir="$3"

    relative_file_path=$(realpath --relative-to="$src_dir" "$src_file")
    target_file_path=$(echo "$target_dir/$relative_file_path" | sed 's|//|/|g')
    target_file_dir=$(dirname "$target_file_path")

    
    echo "Copying boot config file '$src_file' to '$target_file_path'"

    [ "$DRY_RUN" = "1" ] && echo "Dry run enabled, not performing extraction ..." && return 0

    mkdir -p "$target_file_dir"
    set -x
    sudo cp "$src_file" "$target_file_path"
    set +x
}

function copy_found_archive() {
    src_dir="$1"
    target_dir="$2"
    match_regex="$3"

    # same syntax as "grep -E" -> posix-extended regexes
    found_files=$(find "$src_dir" -type f -regextype posix-extended -regex "$match_regex" 2> /dev/null)
    if [ -z "$found_files" ]; then
        echo "No $match_regex config files found in '$src_dir' for copying/mirroring to '$target_dir', nothing to do"
        exit 0
    fi


    for config_file in $found_files; do
        copy_config_file "$config_file" "$src_dir" "$target_dir"
    done
}

efi_mirror_dir="$backup_dir/$efi_dir"
boot_mirror_dir="$backup_dir/$boot_dir"

config_match_regex=".+\.(conf|config)$"

copy_found_archive "$efi_dir" "$efi_mirror_dir" ".+\.(conf|config)$"
copy_found_archive "$boot_dir" "$boot_mirror_dir" "$config_match_regex"

copy_config_file "$boot_dir/loader/gen_with_template.sh" "$boot_dir/loader" "$boot_mirror_dir/loader"
copy_config_file "$boot_dir/loader/template.conf" "$boot_dir/loader" "$boot_mirror_dir/loader"