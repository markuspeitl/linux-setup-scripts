#!/usr/bin/env bash

# Executed by post-commit git hook to deploy ssh files to server using rsync
# (-> for keeping scripts in sync -> that can then be executed via url)

# .git/hooks/post-commit
    # #!/usr/bin/env bash
    # # echo "Hook cwd: $(cwd)"
    # current_dir=$(dirname "$(realpath "$0")")
    # echo "Hook current dir: $current_dir"
    # repo_dir=$(realpath "$current_dir/../..")
    # echo "Hook repo dir: $repo_dir"
    # deploy_script_path="$repo_dir/deploy_ssh_files.sh"
    # echo "Hook running script: $deploy_script_path"

    # bash "$deploy_script_path"

current_dir=$(dirname "$(realpath "$0")")
echo "Current dir: $current_dir"

SCRIPT_ENABLED="0"

function print_run_command() {

    if [ "$SCRIPT_ENABLED" != "1" ] ; then
        echo "SCRIPT_ENABLED is not set to 1, skipping command:"
        echo "$*"
        return
    fi

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
msrv-ip:~/linux-setup-scripts/
# --dry-run

# Example for running script on server:
# curl -L http://devswarm.com:99/download_repo.sh | bash -s -- linux-setup-scripts


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