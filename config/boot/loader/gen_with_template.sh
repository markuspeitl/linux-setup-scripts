#!/usr/bin/env bash

# VER=cachyos-lts ROOT=cachy vol=@arch ./gen_with_template.sh cachy-lts-default.conf
# VER=cachyos ROOT=cachy vol=@arch ./gen_with_template.sh cachy-default.conf
# sed -i "s%-lts%%"  /boot/loader/entries/cachy-default.conf
# cat /boot/loader/entries/cachy-default.conf


# ./gen_with_template.sh default-root-6.14.0-29.conf

# kernelp="/09dd90de2f2c4feb96aad43c70b0c4fd/6.14.0-37-generic/linux" initrp="/09dd90de2f2c4feb96aad43c70b0c4fd/6.14.0-37-generic/initrd.img-6.14.0-37-generic" vol="@kubuntu" opt="" ./gen_with_template.sh kubuntu_subdir-root-6.14.0-29.conf

# VER=6.14.0-37 ROOT=09dd90de2f2c4feb96aad43c70b0c4fd/6.14.0-37-generic vol=@kubuntu ./gen_with_template.sh kubuntu_09dd90de__6.14.0-37__default.conf
# VER=6.14.0-29 ROOT=09dd90de2f2c4feb96aad43c70b0c4fd/6.14.0-29-generic vol=@kubuntu ./gen_with_template.sh kubuntu_09dd90de__6.14.0-29__default.conf

# VER=6.14.0-37 vol=@kubuntu ./gen_with_template.sh kubuntu_6.14.0-37__default.conf
# VER=6.14.0-29 vol=@kubuntu ./gen_with_template.sh kubuntu_6.14.0-29__default.conf


printf "\n\nGenerating systemd-boot entry from template\n"

SCRIPT_DIR=$(dirname "$0")
SCRIPT_DIR_ABS=$(realpath "$SCRIPT_DIR")

echo "Script dir $SCRIPT_DIR_ABS"

template_file="$SCRIPT_DIR_ABS/template.conf"
template=$(cat "$template_file")

loader_entries="$SCRIPT_DIR_ABS/entries"

BOOT_PATH=$(realpath "$SCRIPT_DIR/..")

printf "\n"


find_bootf(){
    dir="$1"
    version="$2"
    filter="$3"
    default="$4"

    if [ -z "$version" ] && [ -z "$filter" ]; then
        echo "$default"
        return
    fi

    filtered=$(ls "$dir")

    if [ -n "$version" ]; then
        filtered=$(echo "$filtered" | grep "$version")
    fi

    if [ -n "$filter" ]; then
        filtered=$(echo "$filtered" | grep "$filter")
    fi

    filtered=$(echo "$filtered" | head -n 1)

    boot_file="$filtered"

    if [ -z "$boot_file" ]; then
        echo "$default"
        return
    fi

    rel_dir=$(realpath -m --relative-to "$BOOT_PATH" "$dir")
    # rel_boot=$(relpath "$BOOT_PATH" "$boot_file")
    rel_boot="/$rel_dir/$boot_file"

    echo "$rel_boot"
}

#conf_file="6.14.0-29-generic.conf"
# name="(boot) $name"

search_root="$BOOT_PATH/$ROOT"

# kernel path
if [ -z "$kernelp" ]; then
    # vmlinuz or linux
    kernelp=$(find_bootf "$search_root" "$VER" "linu" "/vmlinuz-6.14.0-29-generic")
fi
echo "Using kernel at: '$kernelp' under '$BOOT_PATH'"


#initramfs_path
if [ -z "$initrp" ]; then

    # initrd or initramfs
    initrp=$(find_bootf "$search_root" "$VER" "init" "/initrd.img-6.14.0-29-generic")
fi
echo "Using initramfs at: '$initrp' under '$BOOT_PATH'"

if [ -z "$vol" ]; then
    vol="@kubuntu"
fi
echo "Using btrfs subvolume '$subvol'"

if [ -z "$opt" ]; then
    opt=""
fi
if [ -n "$opt" ]; then
    echo "Additional kernel options '$opt'"
fi

# systemd-boot bootloader entry config file
conf_file="$1"
if [ -z "$conf_file" ]; then
    kernel_n=$(basename "$kernelp")
    init_n=$(basename "$initrp")
    conf_file="$kernel_n--$init_n.conf"
fi

if [ -z "$name" ]; then
    name="$conf_file"
fi
echo "Using boot entry name '$name'"

conf_file_path="$loader_entries/$conf_file"

echo "Generating to '$conf_file' at '$conf_file_path'"


# VER=6.14-29
# ROOT=""

# VER=6.14-29
# ROOT="09dd90de2f2c4feb96aad43c70b0c4fd"

# VER=cachyos-lts
# ROOT="cachy"



template=$(echo "$template" | sed "s%<name>%$name%")
template=$(echo "$template" | sed "s%<abs-kernel-path>%$kernelp%")
template=$(echo "$template" | sed "s%<abs-initramfs-path>%$initrp%")
template=$(echo "$template" | sed "s%<sub-volume>%subvol=$vol%")
template=$(echo "$template" | sed "s%<kernel-options>%$opt%")


echo " -------- Writing template:  -------- "
echo "$template"
printf " -------- to: \n\n"
echo "$conf_file_path"


if [ -n "DRY" ]; then
    echo "Dry run enabled -> skipping write to -> $conf_file_path"
fi

echo "$template" | sudo tee "$conf_file_path"

echo "Loader entries: "
ls "$loader_entries"

# rd.driver.blacklist=nvidia
# nouveau.blacklist=1
# nvidia_drm.modeset=1

