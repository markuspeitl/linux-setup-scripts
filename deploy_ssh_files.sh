#!/usr/bin/env bash

current_dir=$(dirname "$(realpath "$0")")
echo "Current dir: $current_dir"

function print_run_command() {
    echo "Run command:"
    echo "$*"
    echo "----"
    $@
}

#https://git-scm.com/docs/githooks
#https://linux.die.net/man/1/rsync

print_run_command rsync --archive \
--verbose --compress --recursive --checksum --delete --timeout=5 \
--exclude=\"*.img\" \
"$current_dir/" \
msrv:~/linux-setup-scripts/

# --dry-run


# cat << 'EOF' | tee .git/hooks/post-commit
# #!/usr/bin/env bash
# # echo "Hook cwd: $(cwd)"
# current_dir=$(dirname "$(realpath "$0")")
# echo "Hook current dir: $current_dir"
# repo_dir=$(realpath "$current_dir/../..")
# echo "Hook repo dir: $repo_dir"
# deploy_script_path="$repo_dir/deploy_ssh_files.sh"
# echo "Hook running script: $deploy_script_path"

# bash "$deploy_script_path"
# EOF
# chmod +x .git/hooks/post-commit