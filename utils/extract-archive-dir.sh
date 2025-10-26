#! /usr/bin/env bash

src_archive="$1"
target_dir="$2"

src_archive=$(realpath "$src_archive")

#DRY_RUN=

if [ -z "$src_archive" ] || [ -z "$target_dir" ]; then
    echo "Usage: $0 "
    echo "  <src-archive> \$1"
    echo "  <target-dir> \$2"
    exit 1
fi

if [ ! -f "$src_archive" ]; then
    echo "Source archive '$src_archive' does not exist, nothing to do"
    exit 1
fi

if [ -z "$DRY_RUN" ]; then
    mkdir -p "$target_dir"
fi

is_tar_archive=$(echo "$src_archive" | grep -Eo "\.tar")
is_zip_archive=$(echo "$src_archive" | grep -Eo "\.zip$")

if [ -z "$is_tar_archive" ] && [ -z "$is_zip_archive" ]; then
    echo "Source archive '$src_archive' is not a .tar or a .zip archive, cannot extract"
    exit 1
fi

if [ -n "$is_zip_archive" ]; then
    echo "Extracting zip archive '$src_archive' to '$target_dir'"

    [ "$DRY_RUN" = "1" ] && echo "Dry run enabled, not performing extraction ..." && exit 0

    set -x
    unzip "$src_archive" -d "$target_dir"
    set +x

    exit 0
fi


is_zstd_archive=$(echo "$src_archive" | grep -Eo "(\.zst|\.zstd)$")
is_bzip2_archive=$(echo "$src_archive" | grep -Eo "(\.bz2|\.bzip2)$")
is_gzip_archive=$(echo "$src_archive" | grep -Eo "(\.gz|\.gzip)$")


decompress_opt=""
if [ -n "$is_zstd_archive" ]; then
    echo "Extracting zstd compressed tar archive '$src_archive' to '$target_dir'"
    decompress_opt="--zstd"
    #zstd_bin=$(which zstd)

    [ "$DRY_RUN" = "1" ] && echo "Dry run enabled, not performing extraction ..." && exit 0
    set -x
    tar --extract --zstd --file "$src_archive" --directory "$target_dir"
    set +x
elif [ -n "$is_bzip2_archive" ]; then
    echo "Extracting bzip2 compressed tar archive '$src_archive' to '$target_dir'"
    decompress_opt="--bzip2"

    [ "$DRY_RUN" = "1" ] && echo "Dry run enabled, not performing extraction ..." && exit 0
    set -x
    tar --extract --bzip2 --file "$src_archive" --directory "$target_dir"
    set +x
elif [ -n "$is_gzip_archive" ]; then
    echo "Extracting gzip compressed tar archive '$src_archive' to '$target_dir'"
    decompress_opt="--gzip"

    [ "$DRY_RUN" = "1" ] && echo "Dry run enabled, not performing extraction ..." && exit 0
    set -x
    tar --extract --gzip --file "$src_archive" --directory "$target_dir"
    set +x
else
    echo "Extracting uncompressed tar archive '$src_archive' to '$target_dir'"

    [ "$DRY_RUN" = "1" ] && echo "Dry run enabled, not performing extraction ..." && exit 0
    set -x
    tar --extract --file "$src_archive" --directory "$target_dir"
    set +x
fi

