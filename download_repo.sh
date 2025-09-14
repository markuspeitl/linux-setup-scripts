#! /usr/bin/env bash

repo_name=$1

repo_download_url=https://github.com/markuspeitl/$repo_name/archive/refs/heads/master.zip

target_dir=/dev/shm
zip_file="$target_dir/$repo_name.zip"

curl -L -o "$zip_file" "$repo_download_url"
unzip -o "$zip_file" -d "$target_dir/$repo_name"

echo "Downloaded to $target_dir/$repo_name"