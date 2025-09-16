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


# cd .git/hooks || exit 1
# touch post-commit
# echo "#!/usr/bin/env bash" > post-commit