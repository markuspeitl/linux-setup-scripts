#! /usr/bin/env bash

src_dir_path="$1"
if [ -z "$src_dir_path" ]; then
    echo "Usage: $0 "
    echo "  <src-dir> \$1"
    echo "  <target-file> \$2 (without extension)"
    exit 1
fi
src_dir_path=$(realpath "$src_dir_path")

src_has_files=$(find "$src_dir_path" -type f 2> /dev/null | head -n 1)
if [ -z "$src_has_files" ]; then
    echo "Source directory '$src_dir_path' does not exist or has no files, nothing to do"
    exit 0
fi

target_file_path="$2"
target_file_path=$(realpath "$target_file_path")


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

target_dir_path=$(dirname "$target_file_path")

if [ -n "$tar_bin" ]; then
    echo "Create boot deps snapshot with '$tar_bin'"

    # wanted to avoid eval, but bash refuses to not split it into multiple args by adding quotes

    mkdir -p "$target_dir_path"
    set -x
    eval "sudo $tar_bin $compress_opt -cf \"$target_file_path.$tar_file_ext\" --absolute-names \"$src_dir_path\""
    set +x

    exit 0
fi

if [ -n "$zip_bin" ]; then
    echo "Create boot deps snapshot with '$zip_bin'"
    
    mkdir -p "$target_dir_path"
    set -x
    sudo $zip_bin -r "$target_file_path.$zip_file_ext" "$src_dir_path"
    set +x

    exit 0
fi

echo "Failed to create snapshot of '$1' 'tar' and 'zip' binaries not found or not in PATH"