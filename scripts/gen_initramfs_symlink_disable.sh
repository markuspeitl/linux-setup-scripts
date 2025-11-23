#!/usr/bin/env bash

# This script disables the creation of symlinks in the initramfs

echo "do_symlinks = no" >> /etc/kernel-img.conf
echo "relative_links = no" >> /etc/kernel-img.conf