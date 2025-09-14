# linux-setup-scripts

## Useful helper scripts

Download this repository to RAM
```sh
bash download_repo.sh linux-setup-scripts
```
Directly execute downloader script from web
```sh
curl -L https://raw.githubusercontent.com/markuspeitl/linux-setup-scripts/master/download_repo.sh | bash -s -- linux-setup-scripts
```


## System bootstrapping from config file


**-it** ... ask before doing stuff (interactive mode)


Create partitions configured in bootstrap.yml and filesystems on a disk image file (under stages set `encrypted_single_disk_btrfs_arch`):
```sh
sudo python3 bootstrap_system_disk.py bootstrap.yml partitions --set encrypted_single_disk_btrfs_arch --simulate simulated_disk.img --sim_size 10G --overwrite_sim
```

Mount the partitions from the simulated disk image as a chroot environment
```sh
sudo python3 bootstrap_system_disk.py bootstrap.yml chroot --set encrypted_single_disk_btrfs_arch --simulate simulated_disk.img --sim_size 10G --overwrite_sim
```

Create partitions configured in bootstrap.yml and filesystems on a real disk (under stages set `green_usb_8GB`) + then mount for chroot:
```sh
sudo python3 bootstrap_system_disk.py bootstrap.yml partitions chroot --set green_usb_8GB -it
```

Mount the partitions from the real disk (under stages set `green_usb_8GB`) as a chroot environment
```sh
sudo python3 bootstrap_system_disk.py bootstrap.yml chroot --set green_usb_8GB -it
```

Recursively Umount all mountpoints of the chroot environment for the specified devices
**/dev/bootstrap_loop** is the symlink to the loopback device used for simulated disk images
**/dev/sdb** is the real disk used in the example above 
```sh
sudo python3 bootstrap_system_disk.py bootstrap.yml clean --clean_devices /dev/bootstrap_loop /dev/sdb
```

### Currently supported features:

#### Disk setup

- Partitioning based on configuration
- Filesystem creation based on configuration
    - ext4
    - btrfs
    - fat32
    - ntfs
    - swap (file and partition?)
- Applying luks encryption to partitions
- Nesting a btrfs filesystem inside a luks container
- Creating btrfs subvolumes and persistently applying compression
- Creating partitions and filesystems on sparse image files
- TODO: btrfs raid and multi disk setups

#### Mounting & unmounting -> preparing chroot environment

- Mounting device partitions to mountpoints with mount options
- Mounting luks containers
- Mounting btrfs subvolumes
- Unmounting chroot dir mounts recursively (in correct order = subvol -> luks -> partition)

#### (Untested) Bootstrapping a target system on chroot

- Use **pacstrap** to install `arch` base system (must be installed on host)
- Use **debootstrap** to install base system (must be installed on host)
Examples (debian, ubuntu, .etc)
- TODO: bootstrap system from distro image 
(tricky depends on distro)
    - install a kernel
    - setup & configure a bootloader
    - generate initramfs 
    (enable kernel modules -> can not detect what modules are needed for target system)
    - generate fstab mounts for basic system

#### (TODO) Basic configuration

- Locale, Timezone, Hostname, Keyboard layout and keymap, Text encoding
- Network configuration
- User creation and configuration
- Desktop environment
- Display manager and session initialization 
- Updating/Installing/Removing packages
- TODO generate fstab based on chroot config


## Backup and restore kde plasma configurations

### Why?
A bug in kde caused desktop customizations/settings to be permanently lost on multi monitor configuration change and i had to reconfigure everything from scratch multiple times.
As such this workaround in just backing up and restoring kde configs.


Perform backup with current timestamp
```sh
python3 backup_kde_plasma_desktop.py
```

Restore the latest backup
```sh
python3 backup_kde_plasma_desktop.py -r
```