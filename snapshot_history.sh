#! /usr/bin/env bash
# snapshot history from host and chroot to location
# Params:
# $1 - target history logs dir (default: /home/$username/repos/linux-setup-scripts/logs)
# Env Variables:
# chroot_dir=/mnt/bootschroot

username=$(whoami)
history_logs_dir="$1"
if [ -z "$history_logs_dir" ]; then
    script_dir=$(dirname "$(realpath "$0")")
    #history_logs_dir=/home/$username/repos/linux-setup-scripts/logs
    history_logs_dir="$script_dir/logs"
fi
#history_logs_dir=$snapshot_dir/logs

mkdir -p "$history_logs_dir"

file_timestamp=$(date +%Y-%m-%d_%Hh-%Mm-%Ss)

function snap_history(){
    src_home_dir="$1"
    target_file="$2"

    history_file="$src_home_dir/.bash_history"
    if [ -f "$history_file" ]; then
        echo "Snapping history from '$history_file' to '$history_logs_dir/$target_file-bash-$file_timestamp.log'"
        cat "$history_file" > "$history_logs_dir/$target_file-bash-$file_timestamp.log"
    fi
    history_file="$src_home_dir/.zsh_history"
    if [ -f "$history_file" ]; then
        echo "Snapping history from '$history_file' to '$history_logs_dir/$target_file-zsh-$file_timestamp.log'"
        cat "$history_file" > "$history_logs_dir/$target_file-zsh-$file_timestamp.log"
    fi
}

chroot_users=$(ls "/home")
for username in $chroot_users; do
    snap_history "/home/$username" "host-$username"
done

snap_history "/root" "host-root-user"

if [ -z "$chroot_dir" ]; then
    chroot_dir=/mnt/bootschroot
fi

if [ ! -d "$chroot_dir" ]; then
    echo "Chroot dir $chroot_dir does not exist, skipping chroot user history snapshot"
    exit 0
fi

chroot_users=$(ls "$chroot_dir/home")
for username in $chroot_users; do
    snap_history "$chroot_dir/home/$username" "chroot-$username"
done

snap_history "$chroot_dir/root" "chroot-root-user"