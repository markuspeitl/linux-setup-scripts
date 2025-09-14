#! /usr/bin/env bash

repo_name=$1

if [ -z "$repo_name" ]; then
    echo "Usage: $0 <repo_name>"
    echo "Example: $0 linux-setup-scripts"
    exit 1
fi
if [ -z "$TARGET_BRANCH" ]; then
    TARGET_BRANCH="master"
fi
if [ -z "$GH_USER" ]; then
    GH_USER="markuspeitl"
fi

repo_download_url=https://github.com/$GH_USER/$repo_name/archive/refs/heads/$TARGET_BRANCH.zip
repo_branch_url=https://github.com/$GH_USER/$repo_name/tree/$TARGET_BRANCH

if [ -z "$DOWNLOAD_DIR" ]; then
    DOWNLOAD_DIR=/dev/shm
fi

repo_unzip_dir="$DOWNLOAD_DIR/$repo_name-unzip"
repo_target_dir="$DOWNLOAD_DIR/$repo_name"
repo_branch_dir="$repo_unzip_dir/$repo_name-$TARGET_BRANCH"

zip_file="$DOWNLOAD_DIR/$repo_name.zip"
# if [ -f "$zip_file" ]; then
#     rm -f "$zip_file"
# fi
curl -L "$repo_download_url" -o "$zip_file"

# if [ -d "$repo_unzip_dir" ]; then
#     rm -f "$repo_unzip_dir"
# fi
unzip -o "$zip_file" -d "$repo_unzip_dir"

if [ -d "$repo_target_dir" ]; then
    rm -rf "$repo_target_dir"
fi
mv "$repo_branch_dir" "$repo_target_dir"

rm -f "$zip_file"
rm -rf "$repo_unzip_dir"


echo ""
echo "Downloaded archive: "
echo "$repo_download_url"
echo "From branch: "
echo "$repo_branch_url"
echo "To: "
echo "$repo_target_dir"