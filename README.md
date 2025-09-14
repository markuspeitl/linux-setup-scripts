# linux-setup-scripts

Download this repository to RAM
```sh
curl -L https://raw.githubusercontent.com/markuspeitl/linux-setup-scripts/master/download_repo.sh | bash -s -- linux-setup-scripts
```

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