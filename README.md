# linux-setup-scripts

## Useful helper scripts

Download this repository to RAM
```sh
bash download_repo.sh linux-setup-scripts
```
Directly execute downloader script from web
```sh
sudo apt update && sudo apt install -y curl
curl -L https://raw.githubusercontent.com/markuspeitl/linux-setup-scripts/master/download_repo.sh | bash -s -- linux-setup-scripts

curl -L http://devswarm.com:99/download_repo.sh | bash -s -- linux-setup-scripts
wget -qO- devswarm.com:99/download_repo.sh | bash -s -- linux-setup-scripts
http http://devswarm.com:99/download_repo.sh | bash -s -- linux-set
```

As for bootstrapping/installing an install medium or live usb is used we do not have persistent storage and state resets on reboot.
To quickly make the scripts accessible in the live environment and move local state and command logs to persistent storage we can mount a remote filesystem via sshfs.

Host device with ssh-server running for getting scripts and storing logs:
```sh
# 1. Setup ssh-server and take note of the PORT (default 22)
# 2. On host to find IP in local network: example: 192.168.0.XXX
ip addr show
```

On live environment mount remote filesystem via sshfs:
```sh
# On target environment
sudo mkdir -p /mnt/linux-setup-scripts
# Not a good idea to give most permissive file permissions on production systems
# but on live usb/cd it does not really matter
sudo chmod -R 777 /mnt/linux-setup-scripts
sshfs -p 22 pmarkus@192.168.0.XXX:/home/pmarkus/repos/linux-setup-scripts /mnt/linux-setup-scripts

# For testing on the maching running the ssh-server itself
sshfs -p 22 pmarkus@localhost:/home/pmarkus/repos/linux-setup-scripts /mnt/linux-setup-scripts
```

Then we can run the scripts in `/mnt/linux-setup-scripts` and additionally store command history or other files that we want to save and retrieve again after reboot.
```sh
history >> /mnt/linux-setup-scripts/logs/command_history_live_env.log
```

Note each user has their own shell history, each shell program has its own history file and chrooted env has different history than host live usb env.
Instead of going to each shell and dumping with the history command we can also access the history files directly. (from live usb)
```sh
cat ~/.bash_history >> /mnt/linux-setup-scripts/logs/host-user.log
cat /root/.bash_history >> /mnt/linux-setup-scripts/logs/root-host-user.log
cat /mnt/chroot/home/pmarkus/.bash_history >> /mnt/linux-setup-scripts/logs/chroot-user.log
cat /mnt/chroot/root/.bash_history >> /mnt/linux-setup-scripts/logs/root-chroot-user.log
# automatized -> run on host shell
chroot_dir=/mnt/bootschroot ./snap_history.sh /mnt/linux-setup-scripts/logs
```
really useful for what programs were installed and config changes.


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

```sh
sudo python3 bootstrap_system_disk.py bootstrap.yml partitions chroot --set prod_pc_setup -it
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


## Setting up easy access to this repo on sever with domain configured and ssh access

Copy files to the server (msrv configured in ~/.ssh/config)
```sh
# note: does place it under the target directory if that exists
scp -r ~/repos/linux-setup-scripts msrv:~/linux-setup-scripts

rsync --archive --recursive --verbose --compress --checksum --delete --exclude="*.img" ~/repos/linux-setup-scripts/ msrv:~/linux-setup-scripts/
```

```sh
ssh msrv

# prepare permissions
chown -R $(whoami) ~/linux-setup-script
chmod -R 755 ~/linux-setup-scripts
cd ~/linux-setup-scripts

sudo -i
apt update
apt upgrade -y

# install nvm (node version manager)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash

# restart shell session
exit
sudo -i

# install latest nodejs
nvm install --lts
node -v
npm install -g npm@latest
npm -v

# install npm packages
npm install -g http-server
npm install -g pm2

# start the server service
pm2 start --name linux-setup-scripts-99 "http-server /home/<user>/linux-setup-scripts -p 99 -a 0.0.0.0"

# test publicly accessible
curl http://devswarm.com:99/README.md
```