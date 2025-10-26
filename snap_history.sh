#! /usr/bin/env bash

# bash ./snap_history.sh /root
# bash ./snap_history.sh /root host-root-user
# bash ./snap_history.sh /root host-root-user /home/pmarkus/repos/linux-setup-scripts/logs
# gen_timestamp=1 ./snap_history.sh /home/pmarkus host-pmarkus
# file_timestamp="01-10-2025" ./snap_history.sh /home/pmarkus host-pmarkus

src_home_dir="$1"
target_file="$2"

if [ -z "$target_file" ]; then
    file_name=$(echo "$src_home_dir" | sed 's|/|-|g')
    target_file="host-$file_name-user"
fi

if [ -z "$history_logs_dir" ]; then
    history_logs_dir="$3"
fi
if [ -z "$history_logs_dir" ]; then
    script_dir=$(dirname "$(realpath "$0")")
    #history_logs_dir=/home/$username/repos/linux-setup-scripts/logs
    history_logs_dir="$script_dir/logs"
fi
#history_logs_dir=$snapshot_dir/logs

mkdir -p "$history_logs_dir"

# if [ -z "$file_timestamp" ]; then
#     file_timestamp=$(date +%Y-%m-%d_%Hh-%Mm-%Ss)
# fi

# if [ -z "$file_timestamp" -n "$gen_timestamp" ]; then
#     file_timestamp=""
# fi

if [ -z "$file_timestamp" ] &&  [ -n "$gen_timestamp" ]; then
    #file_timestamp=$(date +%Y-%m-%d_%Hh-%Mm-%Ss)
    file_timestamp=$(date +%d-%m-%Y_%Hh-%Mm-%Ss)
fi

if [ -n "$file_timestamp" ]; then
    file_timestamp_postfix="-$file_timestamp"
fi

# function echo_sudo_if_root_hist(){
#     hist_file="$1"
#     is_root_hist_file=$(echo "$hist_file" | grep -Eo "^/root/.+")
#     if [ -n "$is_root_hist_file" ]; then
#         echo "sudo"
#     fi
# }

function redact_ip_ports(){
    content="$1"
    if [ -z "$content" ]; then
        return
    fi

    ip_regex="([0-9]{1,3}\.){2,3}[0-9]{1,3}"

    content=$(echo "$content" | sed -E "s/@$ip_regex:[0-9]{1,5}/<redacted_ip>:@<redacted_port>/g")
    content=$(echo "$content" | sed -E "s/\s+$ip_regex:[0-9]{1,5}/ <redacted_ip>:<redacted_port>/g")
    # Redact IP addresses
    content=$(echo "$content" | sed -E "s/@$ip_regex/@<redacted_ip>/g")
    content=$(echo "$content" | sed -E "s/\s+$ip_regex/ <redacted_ip>/g")
    # Redact port numbers
    content=$(echo "$content" | sed -E 's/-p\s+[0-9]{1,5}/-p <redacted-port>/g')
    content=$(echo "$content" | sed -E 's/--port\s+[0-9]{1,5}/--port <redacted-port>/g')
    echo "$content"
}

function snap_shell_history(){
    hist_file="$src_home_dir/$1"

    permission_denied=$(cat "$hist_file" 2>&1 | grep -o 'Permission denied')
    
    target_file_path="$history_logs_dir/$target_file-bash$file_timestamp_postfix.log"


    FILE_CONTENT=""

    if [ -f "$hist_file" ]; then
        echo "Snapping history from '$hist_file' to '$target_file_path'"
        FILE_CONTENT=$(cat "$hist_file" 2>/dev/null)
    elif [ -n "$permission_denied" ]; then
        echo "Permission denied to read '$hist_file', trying with sudo..."
        FILE_CONTENT=$(sudo cat "$hist_file" 2>/dev/null)
    else
        echo "History file at '$hist_file' does not exist, skipping..."
    fi

    FILE_CONTENT=$(redact_ip_ports "$FILE_CONTENT")

    [ -n "$FILE_CONTENT" ] && echo "$FILE_CONTENT" > "$target_file_path" && echo "Snapshot saved to '$target_file_path'"
}

snap_shell_history ".bash_history"
snap_shell_history ".zsh_history"