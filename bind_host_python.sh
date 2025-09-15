#! /usr/bin/env bash

# Bind mount host system's python3 binary and libraries into chroot
# To be executed on host system

if [ -z "$chroot_dir" ]; then
    chroot_dir=/mnt/bootschroot
fi

if [ ! -d "$chroot_dir" ]; then
    echo "Chroot dir $chroot_dir does not exist, exiting"
    exit 1
fi

python_bin_path=$(which python3)
if [ -z "$python_bin_path" ]; then
    echo "python3 binary not found, exiting"
    exit 1
fi
chroot_python_bin_path="$chroot_dir$python_bin_path"

if [ -f "$chroot_python_bin_path" ]; then
    echo "Chroot enviroment at '$chroot_dir' has already python3 at '$chroot_python_bin_path' installed, exiting"
    exit 1
fi

touch "$chroot_python_bin_path"
sudo mount --bind "$python_bin_path" "$chroot_python_bin_path"

find "/usr/lib" -maxdepth 1 -iname "python3*" | xargs -I@ sudo mkdir -p "$chroot_dir@"
find "/usr/lib" -maxdepth 1 -iname "python3*" | xargs -I@ sudo mount --bind "@" "$chroot_dir@"

python_lib_dir=$(dirname "$(dirname "$python_bin_path")")/lib/python3.**
if [ ! -d "$python_lib_dir" ]; then
    echo "python3 lib dir $python_lib_dir not found, exiting"
    exit 1
fi

# check python3 dependencies
# ldd /usr/bin/python3
# which ldd

# TODO after you are done delete the chroot python lib dir if it exists
echo "After done using clean up mounted binary with:"
echo "sudo umount $chroot_python_bin_path"
#echo "sudo rm -f $chroot_python_bin_path"
echo "And do not install python3 in chroot enviroment to prevent unknown side effects"



# ------------------------------ Prepare minimal env for chrooting

# # check bash dependencies
# # ldd /usr/bin/bash

# mkdir -p proc sys mnt opt run tmp dev
# sudo mount -o bind /usr/bin/bash /tmp/fakechroot/usr/bin/bash


# #


# # create bin, lib, lib64, libx32, sbin symlinks to /usr

# #ln -s /tmp/fakechroot/usr/bin /tmp/fakechroot/bin 

# # https://www.reddit.com/r/linux4noobs/comments/3e90rr/whats_the_most_minimal_filesystem_i_could_make_to/
# for dir in bin lib lib64 libx32 sbin; do
#     if [ ! -d "$chroot_dir/$dir" ] && [ ! -L "$chroot_dir/$dir" ]; then
#         ln -s "$chroot_dir/usr/$dir" "$chroot_dir/$dir"
#     fi
# done