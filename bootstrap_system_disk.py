#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# Usage:
# boots ./bootstrap.yml partitions #use 'set' defined the .yml file
# boots ./bootstrap.yml chroot #use 'set' defined the .yml file
# boots ./bootstrap.yml partitions chroot #use 'set' defined the .yml file
# boots ./bootstrap.yml --simulate ./simulated_disk.img --sim_size 10G -osim partition
# boots ./bootstrap.yml --set usb_multiboot mount

from io import TextIOWrapper
import json
import os
import stat
from string import Formatter
import sys
import time
from typing import Any, TypedDict
import shutil
import atexit

# ------------------------ Common functions -------------------------


def load_yml_config(source_path: str) -> dict[str, Any]:
    import yaml
    try:
        with open(source_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading YAML file {source_path}: {e}")
        sys.exit(1)


def run_cmd(
    cmd: str,
    fd_path: str = None,
    fd_mode: str = 'a+'
) -> None:
    if not fd_path:
        print(cmd)
        os.system(cmd)
        return

    with open(fd_path, fd_mode) as fd:
        fd.write(f"{cmd}\n")


def print_write(
    message: str,
    fd_path: str = None,
    fd_mode: str = 'a+'
) -> None:
    print(message)

    if not fd_path:
        return

    with open(fd_path, fd_mode) as fd:
        fd.write(f"# {message}\n")


def append_cmd(
    cmd: str,
    fd_path: str = None,
    fd_mode: str = 'a+'
) -> None:
    if not fd_path:
        return

    with open(fd_path, fd_mode) as file_fd:
        file_fd.write(f"{cmd}\n")


def identify_system() -> str:
    import platform
    system = platform.system()
    if system != 'Linux':
        raise ValueError(f"Unsupported system: {system}. This script is designed for Linux systems only.")

    apt_path: str | None = shutil.which('apt')
    if apt_path:
        return 'debian'
    pacman_path: str | None = shutil.which('pacman')
    if pacman_path:
        return 'pacman_path'
    dnf_path: str | None = shutil.which('dnf')
    if dnf_path:
        return 'dnf_path'

    raise ValueError("Unsupported package manager. This script currently supports Debian, Pacman, and DNF based systems.")


def get_cfg_or_arg_key(file_cfg: dict[str, Any], args_cfg: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in args_cfg:
        return args_cfg[key]
    if key in file_cfg:
        return file_cfg[key]
    return default


def get_first_defined_key(cfg: dict[str, Any], keys: list[str], default: Any) -> Any:
    for key in keys:
        if key in cfg:
            return cfg[key]
    return default

# possibly inflate template values


def input_variable_value(
    key: str
) -> str:
    print(f"Variable '{key}' is not defined or is empty in the configuration.")
    entered_value: str = input(f"Please enter a value for '{key}': ")
    if not entered_value:
        raise ValueError(f"Variable '{key}' is required -> but nothing was provided -> exiting")

    enter_stripped_value = entered_value.strip()
    if not enter_stripped_value:
        raise ValueError(f"Variable '{key}' is required -> but nothing was provided -> exiting")

    return enter_stripped_value


def get_variable_value(
    key: str,
    value: Any,
) -> Any:
    if isinstance(value, str) and not value.strip():
        return input_variable_value(key)

    # if isinstance(value, int) and value == 0:
    #     return int(input_variable_value(key))

    if value is None:
        return input_variable_value(key)

    return value


def get_variables(
    stage_cfg: dict[str, Any],
    config: dict[str, Any] = {},
) -> dict[str, Any]:
    variables: dict[str, Any] = stage_cfg.get('variables', {})
    for key, value in variables.items():

        if config.get(key, None) is not None:
            variables[key] = config[key]
            continue

        variables[key] = get_variable_value(key, value)

    # copy global config keyValue pairs if not already defined/entered with value in variables
    for key, value in config.items():
        # TODO: only for primitives?
        if key not in variables or variables[key] is None:
            variables[key] = value

    return variables


def merge_args_to_config(
    config: dict[str, Any],
    args_config: dict[str, Any]
) -> None:
    if not args_config:
        return

    for key, value in args_config.items():
        if value is not None:
            if config.get(key) is None:
                config[key] = value
            elif isinstance(config[key], (int, str, float, bool, list)):  # , list, dict
                config[key] = value


def escape_double_quotes(
    text: str
) -> str:
    if not text:
        return text

    # Escape double quotes by replacing them with \"
    return text.replace('"', '\\"')


def format_if_set(
    template: str,
    variables: dict[str, Any],
    default: str = ''
) -> str:
    formatter_parsed_keys = [i[1] for i in Formatter().parse(template) if i[1] is not None]
    contained_key = formatter_parsed_keys[0]
    if contained_key in variables and variables[contained_key] is not None:
        return template.format(**variables)
    return default


class CommandSet(TypedDict):
    opt: dict[str, dict[str, str]]
    cmd: dict[str, str]

# Example:
# command_set: dict[str, str] = {
#     'opt': {
#         'part_label_opt': {
#             'passed_key': '--label {part_label}',
#         }
#     },
#     'cmd': {
#         'passed_key': 'mkfs.btrfs {part_label_opt} {part_device}',
#     }
# }


def inflate_command_set_item(
    key: str,
    variables: dict[str, Any],
    command_set: CommandSet = {}
) -> str:
    if key not in command_set['cmd']:
        raise ValueError(f"Command key '{key}' not found in command set")

    for option_key in command_set['opt']:
        target_key: str = option_key
        selected_opt_template: str = command_set['opt'][option_key][key]
        inflated_opt: str = format_if_set(
            selected_opt_template,
            variables,
            default=''
        )
        variables[target_key] = inflated_opt

    command_template: str = command_set['cmd'][key]
    return command_template.format(**variables)


def install_argparse_if_missing() -> None:
    try:
        import argparse
    except ImportError:
        print("argparse module is not installed. Installing it now...")
        run_cmd("pip install argparse")
        print("argparse module installed successfully.")

        print("Please rerun the script after the installation has finished.")


install_argparse_if_missing()


# ------------------------ Run commands and installing packages -------------------------


def platform_system_install(
    packages: str,
    system_type=None,
    output_script: str | None = None
) -> None:
    if not system_type:
        system_type = identify_system()

    if system_type == 'debian':
        run_cmd(f"sudo apt install {packages} -y", fd_path=output_script)
    elif system_type == 'pacman_path':
        run_cmd(f"sudo pacman -S {packages} --noconfirm", fd_path=output_script)
    elif system_type == 'dnf_path':
        run_cmd(f"sudo dnf install {packages} -y", fd_path=output_script)
    else:
        raise ValueError(f"Unsupported system type: {system_type}")


def continue_guard(message: str = "Do you want to continue? (y/n): ") -> bool:
    response: str = input(message).strip().lower()
    if response in ['y', 'yes']:
        return True
    elif response in ['n', 'no']:
        print("Exiting as per user request.")
        sys.exit(0)

    print("Invalid response, repeating.")
    return continue_guard(message)


def ensure_requirements(
    binary_alias: str,
    packages: str,
    output_script: str | None = None,
    required_for: str = "creating LUKS partitions",
    output_requirements: bool = False
) -> None:

    if output_requirements and output_script:
        platform_system_install(packages, output_script=output_script)
        return

    if not shutil.which(binary_alias):
        print_write(f"{binary_alias} is not installed on the system and required for {required_for}, installing it now...", output_script=output_script)
        platform_system_install(packages, output_script=output_script)

    if not output_script and not shutil.which(binary_alias):
        raise ValueError(f"{binary_alias} is not installed on the system and required for {required_for} -> exiting")


def append_script_file_guard(
    target_file: str,
    fd_path: str | None = None
) -> None:
    if not fd_path:
        return

    append_cmd(
        f"[ -f \"{target_file}\" ] "
        "|| { echo "
        f"\"{target_file} was not found -> exiting\";"
        "exit 1; }",
        fd_path=fd_path
    )


def produces_output(
    command: str
) -> bool:
    command_output = os.popen(command).read().strip()
    return bool(command_output)


def command_produces_output_guard(
    command: str,
    fd_path: str | None = None
) -> None:

    if not fd_path:
        command_output = os.popen(command).read().strip()
        if not command_output:
            raise ValueError(f"Command guard '{command}' did not produce any output -> exiting")
        return

    escaped_cmd: str = escape_double_quotes(command)

    append_cmd(
        "[ -z \"$( " + escaped_cmd + " )\" ] "
        "|| { echo "
        f"\"Command guard '{escaped_cmd}' did not produce any output -> exiting\";"
        "exit 1; }",
        fd_path=fd_path
    )


def init_output_script(config: dict[str, Any] = {}) -> TextIOWrapper | None:
    output_script: str = config.get('output', None)
    if not output_script:
        return None

    if not os.path.isabs(output_script):
        output_script = os.path.realpath(output_script)
        config['output'] = output_script

    output_script = os.path.abspath(output_script)
    with open(output_script, 'w+') as fd:
        fd.write("#! /bin/bash\n")
        fd.write("# This script was generated by the bootstrap_system_disk.py script\n")
        fd.write("# It contains commands to bootstrap the system disk as defined in the configuration file\n")
        fd.write("\n")


def prepare_install_env(config: dict[str, Any] = {}) -> str:
    system_type: str = config.get('system', None)
    if not system_type:
        system_type = identify_system()
        config['system'] = system_type

    output_script: str = config.get('output', None)
    bt_dependencies: list[str] = config.get('dependencies', None)
    if bt_dependencies and bt_dependencies.get('prepare', None):
        prep_deps: dict[str, str] = bt_dependencies.get('prepare', {})
        if prep_deps.get(system_type, None):
            prep_cmd: str = prep_deps.get(system_type, {})
            run_cmd(prep_cmd, fd_path=output_script)
    return system_type

# ------------------------ Cleanup resources -------------------------


def umount_luks_device(
    crypto_device: dict[str, Any]
) -> None:
    if not crypto_device:
        print("No crypto device provided -> skipping LUKS unmount")
        return

    # Close LUKS device
    luks_name: str = crypto_device.get('name', None)

    crypto_children: list[str] = crypto_device.get('children', [])
    if crypto_children:
        for child in crypto_children:
            umount_luks_device(child)

    if not luks_name:
        print("No LUKS name provided in the crypto device -> skipping LUKS unmount")
        return

    if os.path.exists(f"/dev/mapper/{luks_name}"):
        print(f"Closing LUKS device at \"/dev/mapper/{luks_name}\"")
        os.system(f"sudo cryptsetup luksClose \"/dev/mapper/{luks_name}\"")

        # print(f"Unmounting LUKS device {luks_name}")
        # os.system(f"sudo umount -l \"/dev/mapper/{luks_name}\""


def recursive_umount_close(
    selected_device: dict[str, Any],
) -> None:
    if not selected_device:
        return

    children: list[str] = selected_device.get('children', None)

    if children:
        for child in children:
            recursive_umount_close(
                selected_device=child
            )

    # Is leaf node
    mountpoints: list[str] = [mountpoint for mountpoint in selected_device.get('mountpoints', []) if mountpoint]
    if mountpoints:
        for mountpoint in mountpoints:
            print(f"Unmounting {mountpoint} from {selected_device['name']}")
            os.system(f"sudo umount \"{mountpoint}\"")
            # os.system(f"sudo umount -l \"{mountpoint}\"")

    fs_type: str = selected_device.get('fstype', None)
    if not fs_type:
        return

    if 'crypto' in fs_type:
        umount_luks_device(
            crypto_device=selected_device
        )


def cleanup_device_resources(
    device_path: str
) -> None:

    if not os.path.exists(device_path):
        print(f"Target device {device_path} does not exist -> skipping cleanup")
        return

    # if not produces_output(f"losetup -l {device_path} 2> /dev/null"):
    #     print(f"Loop device {device_path} is not in use -> skipping cleanup")
    #     return

    block_devices = lsblk_json(device_path)
    if not block_devices:
        print(f"device {device_path} is not mounted -> skipping cleanup")
        return

    if block_devices:

        # If cleanup was called before natural exit or termination -> resources do not need to be cleaned up anymore
        atexit.unregister(cleanup_resources_at_exit)

        selected_device = block_devices[0]
        if selected_device:
            print(f"Cleaning up device {device_path} resources -> umounting mountpoints + detaching luks containers")
            recursive_umount_close(selected_device)

    # mounts_output = os.popen(f"lsblk --noheadings -f \"{loop_device}\" --list -o MOUNTPOINTS").read().strip()
    # if mounts_output:
    #     mounts = mounts_output.split()
    #     mounts = [m for m in mounts if m.strip()]  # Remove empty strings

    #     if mounts:
    #         for mount in mounts:
    #             os.system(f"sudo umount -l \"{mount}\"")

    # if not produces_output(f"losetup -l {loop_device} | grep -o '{image_path}'"):
    #    return

    if produces_output(f"losetup -l {device_path} 2> /dev/null"):
        os.system(f"sudo losetup --detach {device_path}")

    # if device_path.startswith('/dev/loop') and os.path.exists(device_path):
    #     print(f"Detaching loop device at {device_path}")
    #     os.system(f"sudo losetup --detach {device_path}")


# ------------------------ Partitioning devices -------------------------

part_alias_guids: dict[str, str] = {
    'linux': '0FC63DAF-8483-4772-8E79-3D69D8477DE4',
    'swap': '0657FD6D-A4AB-43C4-84E5-0933C84B4F4F',
    'home': '933AC7E1-2EB4-4F13-B844-0E14E2AEF915',
    'raid': 'A19D880F-05FC-4D3B-A006-743F0F84911E',
    'uefi': 'C12A7328-F81F-11D2-BA4B-00A0C93EC93B',
    'lvm': 'E6D6D379-F507-44C2-A23C-238F2A3DF928',
    'eboot': 'BC13C2FF-59E6-4262-A352-B275FD6F7172',
    'windows': 'EBD0A0A2-B9E5-4433-87C0-68B6B72699C7'
}
part_alias_guids['efi'] = part_alias_guids['uefi']  # Alias for UEFI
# sfdisk --list-types --label gpt
short_alias_hex_codes: dict[str, str] = {
    'L': part_alias_guids['linux'],  # Linux filesystem
    'S': part_alias_guids['swap'],  # Swap
    'H': part_alias_guids['home'],  # Home
    'U': part_alias_guids['uefi'],  # UEFI
    'R': part_alias_guids['raid'],  # RAID
    'LVM': part_alias_guids['lvm'],  # LVM
    'eboot': part_alias_guids['eboot'],  # Linux extended boot
    'win': part_alias_guids['windows']  # Microsoft basic data (Windows)
}


def validate_part_type_code(part_type: str, name="") -> str:
    # can not use fdisk numbers in sfdisk
    # if isinstance(part_type, int) or part_type.isdigit():
    #     if int(part_type) in range(1, 128):
    #         return True
    #     raise ValueError(f"{name} Partition type '{part_type}' is not a valid partition type -> must be a number between 1 and 127")

    if ('-' in part_type):
        part_type = part_type.replace('-', '')
        if len(part_type) != 32:
            raise ValueError(f"{name} Partition type '{part_type}' is not a valid UUID format -> must be 32 characters long, excluding dashes")

        return True

    part_guid: str | None = part_alias_guids.get(part_type, None)
    if part_guid:
        return part_guid

    part_hex: str | None = short_alias_hex_codes.get(part_type, None)
    if part_hex:
        return part_hex

    raise ValueError(f"{name} Partition type '{part_type}' is not a valid partition type -> must be a number between 1 and 127 or a valid UUID format")


def generate_partition_scheme(
    part_scheme_path: str = '/tmp/partitions.sh',
    part_definitions: dict[str, Any] = {},
    variables: dict[str, Any] = {}
) -> str:
    if not part_definitions:
        raise ValueError("Partition definitions must be provided to generate a partition scheme")

    part_scheme: str = variables.get('scheme', 'gpt')

    configured_to_end: bool = False
    with open(part_scheme_path, 'w+') as part_script:
        # part_script.write("#! /bin/bash\n")
        part_script.write(f"label: {part_scheme}\n")
        part_script.write(f"unit: sectors\n")

        sector_size: str = variables.get('sector_size', None)
        if sector_size:
            part_script.write(f"sector-size: {sector_size}\n")

        for part_key, part_info in part_definitions.items():

            line_parts: list[str] = []

            start_sector: str = part_info.get('start', None)
            if start_sector:
                start_sector_str: str = f"start={start_sector}"
                line_parts.append(start_sector_str)

            part_size: str = part_info.get('size', None)
            if not part_size and configured_to_end:
                raise ValueError(f"Partition '{part_key}' is configured to end of disk, but the disk is already filled with previous partitions.")

            if not part_size:
                configured_to_end = True
            else:
                line_parts.append(f"size={part_size}")

            part_type: str = part_info.get('type', None)
            if not part_type:
                raise ValueError(f"Partition '{part_key}' is not configured with a type -> is required -> exiting")

            mapped_part_type = validate_part_type_code(part_type)
            line_parts.append(f"type={mapped_part_type}")

            partition_line: str = '; '.join(line_parts)
            if not partition_line.strip():
                raise ValueError(f"Partition '{part_key}' is not configured properly -> skipping partition")

            print("Adding entry for partition with: ")
            print(f"Start: {start_sector}, Size: {part_size}, Type: {part_type} -> {mapped_part_type}")

            part_script.write(f"{partition_line}\n")

    print(f"GENERATED: ----------- {part_scheme_path} --------------------:")
    with open(part_scheme_path, 'r') as part_script_fd:
        print(part_script_fd.read().strip())
    print(f"----------------------------------------------------:")

    return part_scheme_path


def intall_partitions(
    part_scheme_path: str,
    # variables: dict[str, Any] = {},
    config: dict[str, Any] = {},
    output_script: str | None = None
) -> list[str]:
    target_device: str = config.get('target_device', None)
    if not target_device:
        raise ValueError("Target device must be defined in the configuration under 'variables' -> exiting")

    # Reference:
    # sudo sfdisk --dump /dev/sdd > /dev/shm/sda-pt.dump
    # To run: sudo sfdisk /dev/sdd < /dev/shm/sda-pt.dump
    ensure_requirements(
        'sfdisk',
        'util-linux',
        output_script=output_script,
        required_for="creating partitions on the disk",
        output_requirements=config.get('force_output_requirements', False)
    )

    if not os.path.exists(part_scheme_path):
        raise FileNotFoundError(f"Partition scheme file '{part_scheme_path}' does not exist -> exiting")

    os.chmod(part_scheme_path, 0o755)

    real_target_device: str = target_device
    if os.path.islink(target_device):
        real_target_device = os.readlink(real_target_device)
        print_write(f"Resolved from {target_device} to real target device symlink to {real_target_device}", fd_path=output_script)
        target_device = real_target_device

    print_write(f"Running partition script at '{part_scheme_path}' on '{target_device}' -> existing partitions:", fd_path=output_script)
    run_cmd(f"sudo sfdisk -l {target_device}")

    if config.get('interactive'):
        print(f"This will wipe the partition table on device {target_device}:")
        continue_guard()

    run_cmd(f"sudo sfdisk --label gpt --wipe always '{target_device}' < {part_scheme_path}", fd_path=output_script)

    if shutil.which('partprobe'):
        print(f"Running partprobe on {target_device} to update partition table")
        run_cmd(f"sudo partprobe {target_device}", fd_path=output_script)

    # Target device has partitions on it
    # command_produces_output_guard(f"sudo sfdisk -l {target_device} | grep -E \"^/dev/\"")

    list_part_devices_cmd: str = f"sudo sfdisk -l '{target_device}' -o Device 2> /dev/null | grep \"^/dev\""
    part_devices_out = os.popen(list_part_devices_cmd).read().strip()
    if not part_devices_out:
        raise ValueError(f"No partitions found on target device '{target_device}' after running partition script -> exiting")
    part_devices: list[str] = part_devices_out.splitlines()
    part_devices = [part.strip() for part in part_devices if part.strip()]
    print(f"Created new partitions: {', '.join(part_devices)} @ {target_device}")
    return part_devices


# ------------------------ Formatting partitions / block devices -------------------------


command_set: dict[str, str] = {
    'opt': {
        'part_label_opt': {
            'btrfs': '--label {part_label}',
            'ext4': '-L {part_label}',
            'vfat': '-n {part_label}',
            'fat32': '-n {part_label}',
            'ntfs': '--label {part_label}',
            'swap': ''
        }
    },
    'cmd': {
        'btrfs': 'mkfs.btrfs {part_label_opt} {part_device}',
        'ext4': 'mkfs.ext4 {part_label_opt} -F {part_device}',
        'vfat': 'mkfs.vfat {part_label_opt} -F32 {part_device}',
        'fat32': 'mkfs.vfat {part_label_opt} -F32 {part_device}',
        'ntfs': 'mkfs.ntfs --fast {part_label_opt} {part_device}',
        'swap': 'mkswap {part_device}'
        # 'xfs': 'mkfs.xfs -f {part_device}',
    }
}


def check_fs_type(
    part_device: str,
) -> str | None:
    check_fs_type_template: str = "lsblk --noheadings -o FSTYPE {part_device}"
    check_fs_cmd: str = check_fs_type_template.format(part_device=part_device)
    fs_type: str = os.popen(check_fs_cmd).read().strip()
    # print(f"Partition {part_device} already has a filesystem of type {fs_type}")
    if not fs_type:
        print(f"Partition {part_device} does not have a filesystem -> returning None")
        return None

    return fs_type


def create_filesystem_on(
    part_device: str,
    filesystem: str,
    part_info: dict[str, Any],
    config: dict[str, Any] = {}
) -> str:
    mkfs_command: str = inflate_command_set_item(
        filesystem,
        {
            'part_label': part_info.get('name'),
            'part_device': part_device
        },
        command_set=command_set
    )
    if not mkfs_command:
        raise ValueError(f"mkfs command for filesystem '{filesystem}' is not defined in the command set -> exiting")

    output_script: str | None = config.get('output_script', None)
    print_write(f"Creating filesystem on {part_device} with command: {mkfs_command}", fd_path=output_script)
    if config.get('interactive'):
        continue_guard()

    run_cmd(f"sudo {mkfs_command} || exit", fd_path=output_script)

    # Make sure fs changes are synced to prevent check failure
    if shutil.which('partprobe'):
        run_cmd(f"sudo partprobe {part_device}", fd_path=output_script)
    # needs some time to sync on slow devices
    time.sleep(1)

    fs_type = check_fs_type(part_device)

    if not fs_type:
        raise ValueError(f"Failed to create filesystem on {part_device} -> exiting")

    return fs_type


def format_partitions(
    part_devices: list[str],
    part_definitions: dict[str, Any] = {},
    # variables: dict[str, Any] = {},
    config: dict[str, Any] = {}
) -> None:
    if not part_devices:
        raise ValueError("No partition devices provided to format")

    output_script: str | None = config.get('output_script', None)

    index: int = 0
    for part_key, part_info in part_definitions.items():
        part_filesystem: str = get_first_defined_key(part_info, ['filesystem', 'fs'], None)
        if not part_filesystem:
            print(f"Partition '{part_key}' does not have target filesystem defined in config -> skipping filesystem creation")
            continue
        if index >= len(part_devices):
            print(f"Warning: More partitions defined than available devices -> skipping partition '{part_key}'")
            continue

        part_device_path: str = part_devices[index]
        if not os.path.exists(part_device_path):
            print(f"Partition device {part_device_path} does not exist -> skipping filesystem creation")
            index += 1
            continue

        existing_fs_type: str | None = check_fs_type(part_device_path)
        if existing_fs_type and config.get('interactive'):
            confirmed: bool = input(f"Partition {part_device_path} already has a filesystem of type {existing_fs_type}. Are you sure you want to format it as {part_filesystem}? (y/n): ").strip().lower() == 'y'
            if not confirmed:
                print(f"Skipping formatting of partition {part_device_path}")
                index += 1
                continue

        part_device_path = prepare_luks_partitions(
            part_device_path,
            part_info,
            config=config
        )

        part_device_fs: str = create_filesystem_on(
            part_device_path,
            part_filesystem,
            part_info,
            config=config
        )

        if (part_device_fs != 'btrfs'):
            index += 1
            continue

        subvolumes_info: dict[str, Any] = part_info.get('subvolumes', None)
        if not subvolumes_info:
            index += 1
            continue

        install_btrfs_subvolumes(
            part_device_path,
            subvolumes_info,
            output_script=output_script,
            output_requirements=config.get('force_output_requirements', False),
            config=config
        )

        index += 1


# ------------------------ Handling LUKS disk encryption -------------------------
# https://www.redhat.com/en/blog/disk-encryption-luks


def unlock_luks_partition(
    part_device: str,
    luks_device_name: str = 'bootsluks',
    luks_passphrase: str | None = None,
) -> str:
    output_script = None

    luks_device_path: str = f"/dev/mapper/{luks_device_name}"
    if os.path.exists(luks_device_path):
        print(f"LUKS device {luks_device_name} at path {luks_device_path} already exists -> closing before reopening")
        run_cmd(f"sudo cryptsetup luksClose {luks_device_name}")

    if not luks_passphrase:
        luks_passphrase = input(f"Please enter the passphrase for the LUKS partition {part_device}: ").strip()
        if not luks_passphrase:
            raise ValueError("LUKS passphrase is required but not provided -> exiting")

    print_write(f"Opening LUKS partition {part_device} with name {luks_device_name}", fd_path=output_script)
    luks_open_cmd: str = f"echo -n \"{luks_passphrase}\" | sudo cryptsetup luksOpen '{part_device}' {luks_device_name} --key-file -"
    print(luks_open_cmd)
    run_cmd(luks_open_cmd, fd_path=output_script)

    return "/dev/mapper/" + luks_device_name


def install_luks_partition(
    part_device: str,
    luks_part_info: dict[str, Any],
    output_script: str | None = None,
    output_requirements: bool = False,
    config: dict[str, Any] = {}
) -> None:
    luks_device_name: str = luks_part_info.get('luks_device_name', 'luks')
    luks_passphrase: str = luks_part_info.get('luks_passphrase', None)
    if not luks_passphrase:
        luks_passphrase = input(f"Please enter the passphrase for the LUKS partition {part_device}: ").strip()
        if not luks_passphrase:
            raise ValueError("LUKS passphrase is required but not provided -> exiting")

    ensure_requirements(
        'cryptsetup',
        'cryptsetup',
        output_script=output_script,
        required_for="creating LUKS partitions",
        output_requirements=output_requirements
    )

    luks_format_cmd: str = f"echo -n \"{luks_passphrase}\" | sudo cryptsetup luksFormat \"{part_device}\" --batch-mode --type luks2 --key-file -"
    # --batch-mode --> non interactive

    print(f"Running LUKS format command: {luks_format_cmd}")
    if config.get('interactive'):
        continue_guard()

    run_cmd(luks_format_cmd, fd_path=output_script)

    return unlock_luks_partition(
        part_device,
        luks_device_name=luks_device_name,
        luks_passphrase=luks_passphrase
    )


def prepare_luks_partitions(
    part_device: str,
    part_info: dict[str, Any],
    config: dict[str, Any] = {},
) -> str | None:
    luks_part_info: dict[str, Any] = part_info.get('luks', None)
    if not luks_part_info:
        return part_device

    luks_part_device: str = install_luks_partition(
        part_device,
        luks_part_info,
        output_script=config.get('output_script', None),
        output_requirements=config.get('force_output_requirements', False),
        config=config
    )
    return luks_part_device


# ------------------------ BTRFS fs management -------------------------

# https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html#subvolume-flags
# https://btrfs.readthedocs.io/en/latest/btrfs-property.html#man-property-set


def install_btrfs_subvolumes(
    part_device: str,
    subvolumes_info: dict[str, Any],
    output_script: str | None = None,
    output_requirements: bool = False,
    config: dict[str, Any] = {}
) -> None:

    ensure_requirements(
        'btrfs',
        'btrfs-progs',
        output_script=output_script,
        required_for="creating btrfs volumes and subvolumes",
        output_requirements=output_requirements
    )

    temp_subvol_path: str = '/tmp/btrfs_subvolumes'
    if not os.path.exists(temp_subvol_path):

        if not output_script:
            os.makedirs(temp_subvol_path)
        else:
            append_cmd(f"mkdir -p '{temp_subvol_path}'", fd_path=output_script)

    run_cmd(f"sudo mount '{part_device}' '{temp_subvol_path}'", fd_path=output_script)

    for subvol_key, subvol_info in subvolumes_info.items():
        subvol_name: str = subvol_info.get('name', subvol_key)

        subvol_path: str = os.path.join(temp_subvol_path, subvol_name)
        subvol_cmd: str = f"sudo btrfs subvolume create '{subvol_path}'"

        print_write(f"Creating Btrfs subvolume {subvol_name} at {subvol_path} with command: {subvol_cmd}", fd_path=output_script)
        run_cmd(subvol_cmd, fd_path=output_script)

        compression_option: str = get_first_defined_key(subvol_info, ['compression', 'compress'], None)
        if compression_option:
            compression_type: str = compression_option
            if ':' in compression_type:
                compression_type, compression_level = compression_type.split(':', 1)

            set_compression_cmd: str = f"sudo btrfs property set '{subvol_path}' compression {compression_type}"
            # if compression_level:
            #     set_compression_cmd += f" {compression_level}"
            print(f"Setting compression for subvolume {subvol_name} with command: {set_compression_cmd}")
            run_cmd(set_compression_cmd, fd_path=output_script)

        read_only_option: bool = subvol_info.get('read_only', False)
        if read_only_option:
            set_read_only_cmd: str = f"sudo btrfs property set '{subvol_path}' ro true"
            print(f"Setting subvolume {subvol_name} to read-only with command: {set_read_only_cmd}")
            run_cmd(set_read_only_cmd, fd_path=output_script)

        no_cow_option: bool = subvol_info.get('nocow', False)
        if no_cow_option:
            # recursively set nocow to all files in the subvolume dir
            set_nocow_cmd: str = f"chattr -R +C '{subvol_path}'"
            run_cmd(set_nocow_cmd, fd_path=output_script)

        is_swap: str = subvol_info.get('swap', False)
        if is_swap or subvol_key == 'swap':
            swap_size: str = subvol_info.get('size', None)
            if swap_size is None:
                get_memory_size_cmd: str = "grep MemTotal /proc/meminfo | tr -s ' ' | cut -d ' ' -f2"
                swap_size = os.popen(get_memory_size_cmd).read().strip()
                if not swap_size:
                    raise ValueError("Swap size is not defined in the subvolume info and could not be determined from /proc/meminfo -> exiting")

            run_cmd(f"sudo mount '{part_device}' -o 'defaults,nodatacow,nodatasum,noatime,compress=no,subvol={subvol_name}' '{subvol_path}'")

            swap_file = f"{subvol_path}/swapfile"
            run_cmd(f"sudo truncate -s 0 '{swap_file}'", fd_path=output_script)
            run_cmd(f"chattr +C '{swap_file}'", fd_path=output_script)
            run_cmd(f"sudo fallocate -l '{swap_size}' '{swap_file}'", fd_path=output_script)
            run_cmd(f"sudo chmod 600 '{swap_file}'", fd_path=output_script)
            run_cmd(f"sudo mkswap '{swap_file}'", fd_path=output_script)

            run_cmd(f"sudo umount '{subvol_path}'")

            # should be done in running system
            # run_cmd(f"sudo swapon '{swap_file}'", fd_path=output_script)

    # sudo btrfs subvolume list /tmp/btrfs_subvolumes
    run_cmd(f"sudo umount '{temp_subvol_path}'", fd_path=output_script)

    if output_script:
        return

    # check_anything_mounted_cmd: str = f"findmnt --noheadings {temp_subvol_path}"
    check_anything_mounted_cmd: str = f"mount | grep -o '{temp_subvol_path}'"
    mounted_info: str = os.popen(check_anything_mounted_cmd).read().strip()
    if mounted_info:
        print(f"Warning: Something under {temp_subvol_path} is still mounted after unmounting -> skipping remove -> please check manually")
    else:
        command_output = os.popen(f"ls '{temp_subvol_path}' | wc -l").read().strip()
        print(f"Removing temporary subvolume mount directory {temp_subvol_path} containing {command_output} entries?")
        if config.get('interactive'):
            continue_guard()

        os.rmdir(temp_subvol_path)

# ------------------------ Debugging and files as virtual disk devices -------------------------


default_valid_img_extensions: list[str] = ['.img', '.iso', '.qcow2', '.vmdk', '.vdi', '.raw', '.sqsh', '.squash', '.squashfs'],


def setup_loopback_device(
    image_path: str,
    target_device_path: str = '/dev/bootstrap_loop',
    image_size: str = '10G',
    use_existing: bool = False,
) -> str | None:
    if produces_output(f"losetup -l {target_device_path} 2> /dev/null"):
        print_write(f"Loop device {target_device_path} exists and is in use -> detaching it")
        cleanup_device_resources(target_device_path)
        # run_cmd(f"sudo losetup --detach {target_device_path}")

    # creates a sparse file with the maxium growth to size of 1G: truncate --size 1G disk.img
    # to expand: truncate -s +1G sparse.img
    # to or set a new size of the sparse file: truncate -s 5G sparse.img
    # to show apparent size of the sparse file: ls -lh disk.img
    # to show the actual size of the sparse file: du -h disk.img
    if not use_existing or not os.path.exists(image_path):
        print_write(f"Creating simulation image at {image_path} with size {image_size}")
        run_cmd(f"truncate --size {image_size} '{image_path}'")
    else:
        print_write(f"Using existing simulation image at {image_path}")

    if not is_mountable_image(image_path):
        raise ValueError(f"Simulation path '{image_path}' is not a valid mountable image file -> valid extensions:"
                         f" {', '.join(default_valid_img_extensions)} -> exiting")

    if os.path.exists(target_device_path):
        if os.path.islink(target_device_path):
            print_write(f"Removing existing symlink {target_device_path} to recreate it")
            os.remove(target_device_path)
        else:
            raise ValueError(f"Simulation loop device {target_device_path} already exists and is not a symlink -> please remove it manually or use a different name")

    append_cmd(f"rm -f {target_device_path}")

    # setup loop device to image and create symlink to it at specified path, as loop device numbers are not guaranteed to stay the same
    run_cmd(f"sudo ln -s \"$(sudo losetup --partscan --find --show '{image_path}')\" {target_device_path} || exit 1")
    if not os.path.exists(target_device_path):
        raise ValueError(f"Simulation loop device {target_device_path} does not exist after 'losetup' -> please run the script with root privileges or create the device manually")

    append_script_file_guard(target_device_path)

    check_loop_file_mounted_cmd = f"losetup --list | grep -o '{image_path}'"
    if not produces_output(check_loop_file_mounted_cmd):
        raise ValueError(f"Not Loop device is set up pointing to the image file {image_path} after setup -> exiting")

    if not produces_output(f"losetup -l {target_device_path} 2> /dev/null"):
        raise ValueError(f"Target device {target_device_path} is not a loop device, after setup -> please check the setup")

    # Create loop device yourself with mknod -> not recommended
    # https://blog.devops.dev/linux-loop-devices-451002bf69d9
    # b ... create a block buffered special file
    # 7 ... the driver to use --> loopback device
    # 1 ... id/number of the loop device (limited by system) -> better to find a free one
    # https://www.kernel.org/doc/html/latest/admin-guide/devices.html#loop-devices
    # https://www.man7.org/linux/man-pages/man2/mknod.2.html
    # run_cmd(f"mknod /dev/loop5544 b || exit 1")
    # if not output_script and not os.path.exists('/dev/loop5544'):
    #     raise ValueError("Simulation loop device /dev/loop5544 does not exist after 'mknod' -> please run the script with root privileges or create the device manually")

    # Show info: losetup /dev/loop34
    # Create alias through symlink: sudo ln -s /dev/loop34 /dev/bootrap_loop (note auto cleaning on reboot -> /dev is recreated on reboot)
    # Kernel >= 5.13 -> use name: sudo losetup --name=myloop0 disk.img  --- and access /dev/loop/by-name/myloop0
    # sudo losetup --detach /dev/loop

    return target_device_path


def setup_simulation_environment(
    config: dict[str, Any] = {},
    bootstrap_loop_device: str = '/dev/bootstrap_loop',
    use_existing: bool = False,
    valid_img_extensions: list[str] = ['.img', '.iso', '.qcow2', '.vmdk', '.vdi', '.raw', '.sqsh', '.squash', '.squashfs'],
) -> str | None:
    output_script: str | None = config.get('output', None)

    sim_path: str = config.get('simulate', None)
    sim_path = os.path.realpath(sim_path)

    if not sim_path:
        print("No simulation path provided in the configuration under 'simulate' -> skipping simulation setup")
        return None

    sim_size: str = config.get('sim_size', '10G')
    if not use_existing and not sim_size:
        raise ValueError("Simulation size must be provided in the configuration under 'sim_size'")

    overwrite_sim: bool = config.get('overwrite_sim', False)
    if not os.path.exists(sim_path):
        print_write(f"Simulation image does not exist at {sim_path} -> creating it", fd_path=output_script)
        return setup_loopback_device(
            image_path=sim_path,
            target_device_path=bootstrap_loop_device,
            image_size=sim_size,
            use_existing=use_existing
        )
    if overwrite_sim:
        return setup_loopback_device(
            image_path=sim_path,
            target_device_path=bootstrap_loop_device,
            image_size=sim_size,
            use_existing=use_existing
        )

    raise ValueError(f"Simulation image already exists at {sim_path} -> please delete or use the '--overwrite_sim' option to overwrite it")


def is_mountable_image(
    image_path: str,
    valid_img_extensions: list[str] = ['.img', '.iso', '.qcow2', '.vmdk', '.vdi', '.raw', '.sqsh', '.squash', '.squashfs'],
) -> str:
    ltarget_stat: os.stat_result = os.lstat(image_path)
    target_stat: os.stat_result = os.stat(image_path)

    # https://docs.python.org/3/library/stat.html
    # is a regular file
    if stat.S_ISREG(ltarget_stat.st_mode):
        if not image_path.endswith(tuple(valid_img_extensions)):
            return False
        return True

    if stat.S_ISREG(target_stat.st_mode):
        if not image_path.endswith(tuple(valid_img_extensions)):
            return False
        return True

    return False


def cleanup_resources_at_exit(target_device: str) -> None:
    cleanup_device_resources(target_device)

    if os.path.islink(target_device) and target_device.startswith('/dev/'):
        print(f"Removing symlink {target_device} on exit")
        os.remove(target_device)


def setup_device_node_cleanup(
    target_device: str,
    disable_close_cleanup: bool = False
) -> None:
    if not target_device:
        print("No target device defined in the configuration under 'target_device' -> skipping cleanup setup")
        return

    if not disable_close_cleanup:
        atexit.register(cleanup_resources_at_exit, target_device=target_device)


def find_target_device(
    target_device: str | None = None,
) -> str | None:
    """
    Find the target device in the system based on path
    the provided name or label.
    or by the label or name of a child device at maximum depth 1.
    """
    if not target_device:
        print("No target device, path, label or device id provided in the configuration under 'target_device':")
        user_input: str = input("Please enter the target device path, label or id, examples: device path </dev/sdX>, device id term <9207217BF1696510008>, child label <GREEN_EFI>: ").strip()
        if not user_input:
            raise ValueError("Target device must be provided to find it in the system -> exiting")
        target_device = user_input

    if os.path.exists(target_device):
        return target_device

    if target_device.startswith('/dev/'):
        raise ValueError(f"Target device '{target_device}' does not exist in the system -> exiting")

    lsblk_json_output: dict[str, Any] = lsblk_json()

    for block_device in lsblk_json_output:
        if block_device.get('label') == target_device or block_device.get('name') == target_device:
            resolved_device = f"/dev/{block_device['name']}"
            print(f"Found target device by its label or name of '{target_device}' @ {resolved_device}")
            return resolved_device

        for child_block_device in block_device.get('children', []):
            if child_block_device.get('label') == target_device or child_block_device.get('name') == target_device:
                resolved_device = f"/dev/{block_device['name']}"
                print(f"Found target device by the label or name of its child partition '{target_device}' @ {resolved_device}")

                return resolved_device

    find_by_id_cmd = f"ls /dev/disk/by-id | grep {target_device} | grep --invert-match '\\-part'"
    target_device_id: str = os.popen(find_by_id_cmd).read().strip()
    if target_device_id:
        if len(target_device_id.splitlines()) > 1:
            raise ValueError(f"Multiple devices found with ID '{target_device}' -> please specify a unique device name or ID")
        device_path: str = f"/dev/disk/by-id/{target_device_id}"
        if not os.path.exists(device_path):
            raise ValueError(f"Target device ID '{target_device_id}' does not exist in the system -> exiting")
        resolved_path: str = os.path.realpath(device_path)
        # resolved_path: str = os.readlink(device_path)
        if not os.path.exists(resolved_path):
            raise ValueError(f"Resolved target device ID '{target_device_id}' does not exist in the system -> exiting")

        print(f"Found target device by its unique device id ID, search term '{target_device}' found '{device_path}' resolved to '{resolved_path}'")
        return resolved_path

    raise ValueError(f"Target device '{target_device}' not found in the system -> exiting")


def prepare_target_device_lifecycle(
    config: dict[str, Any] = {},
    loop_device_path: str = '/dev/bootstrap_loop',
    valid_img_extensions: list[str] = ['.img', '.iso', '.qcow2', '.vmdk', '.vdi', '.raw', '.sqsh', '.squash', '.squashfs'],
    use_existing=False,
    disable_close_cleanup: bool = False
) -> None:
    sim_path: str = config.get('simulate', None)
    if sim_path:
        target_device = setup_simulation_environment(
            config,
            bootstrap_loop_device=loop_device_path,
            use_existing=use_existing,
            valid_img_extensions=valid_img_extensions
        )
        config['target_device'] = target_device
        setup_device_node_cleanup(target_device, disable_close_cleanup=disable_close_cleanup)
        return

    target_device: str | None = config.get('target_device', None)
    target_device = find_target_device(target_device)
    config['target_device'] = target_device

    cleanup_device_resources(target_device)

    # lstat -> does not follow symlinks, os.stat follows them
    ltarget_stat: os.stat_result = os.lstat(target_device)
    target_stat: os.stat_result = os.stat(target_device)
    if stat.S_ISBLK(target_stat.st_mode) or stat.S_ISBLK(ltarget_stat.st_mode):
        print(f"Target device '{target_device}' is a block device -> setting it up for device operations (mount, parition, format, etc.)")
        setup_device_node_cleanup(target_device, disable_close_cleanup=disable_close_cleanup)
        return target_device

    if is_mountable_image(
        image_path=target_device,
        valid_img_extensions=valid_img_extensions
    ):
        print(f"Target device '{target_device}' is a mountable image file -> setting it up as loopback device to disk image")
        target_device = setup_loopback_device(
            image_path=target_device,
            target_device_path=loop_device_path,
            use_existing=use_existing
        )
        config['target_device'] = target_device
        setup_device_node_cleanup(target_device, disable_close_cleanup=disable_close_cleanup)
        return

    raise ValueError(f"Invalid target device for setup '{target_device}' is not a block device or a mountable image file with ext:"
                     f" {', '.join(valid_img_extensions)} -> exiting")


# ------------------------ High level functions -------------------------


def exec_partitions_installer(
    stage_cfg: dict[str, Any],
    set_config: dict[str, Any] = {},
    config: dict[str, Any] = {},
    system_type: str = 'debian',
    output_script: str | None = None
) -> None:
    variables: dict[str, Any] = get_variables(stage_cfg, config=config)
    config.update(variables)

    prepare_target_device_lifecycle(
        config,
        use_existing=False
    )

    parts: dict[str, Any] = get_first_defined_key(
        stage_cfg,
        ['partitions', 'parts'],
        {}
    )
    if not parts:
        print_write("Part table not defined in the configuration -> skipping 'partitions' stage", output_script)
        return

    part_scheme_path: str = generate_partition_scheme(
        part_scheme_path='/tmp/partitions.sh',
        part_definitions=parts,
        variables=variables
    )

    part_devices: list[str] = intall_partitions(
        part_scheme_path=part_scheme_path,
        # variables=variables,
        config=config,
        output_script=output_script
    )

    format_partitions(
        part_devices=part_devices,
        part_definitions=parts,
        # variables=variables,
        config=config
    )

    return part_devices

    # target_device: str = variables.get('target_device', None)
    # real_target_device: str = target_device
    # if os.path.islink(target_device):
    #     real_target_device = os.readlink(real_target_device)
    #     print_write(f"Resolved from {target_device} to real target device symlink to {real_target_device}")


def lsblk_json(
    device: str = None,
    ignore_parent: bool = False,
) -> dict[str, Any]:
    """
    Get JSON output of lsblk command for the specified device.
    """

    if device:
        cmd: str = f"lsblk -f '{device}' --json"
    else:
        cmd: str = "lsblk -f --json"

    output: str = os.popen(cmd).read().strip()
    if not output:
        raise ValueError(f"No output from lsblk command for device {device} -> exiting")

    lsblk_output = json.loads(output)
    if not lsblk_output:
        return None

    if not lsblk_output.get('blockdevices', None):
        return None

    out_block_devices = lsblk_output['blockdevices']

    if ignore_parent:
        out_block_devices = out_block_devices[0].get('children', [])

    return out_block_devices


def sfdisk_json(
    device: str,
    ignore_parent: bool = False,
) -> dict[str, Any]:
    """
    Get JSON output of sfdisk command for the specified device.
    """
    cmd: str = f"sudo sfdisk -l '{device}' --json"
    output: str = os.popen(cmd).read().strip()
    if not output:
        raise ValueError(f"No output from sfdisk command for device {device} -> exiting")

    sfdisk_output = json.loads(output)
    table = sfdisk_output['partitiontable']
    if not ignore_parent:
        return table

    return table.get('partitions', [])


# def get_extended_parts_info(
#     parent_device: str,
# ) -> dict[str, Any]:
#     # lsblk -f /dev/sdb --json
#     # sudo sfdisk -l /dev/sdb -o Device,Type | grep "^/dev"
#     block_infos: list[dict[str, Any]] = lsblk_json(parent_device, ignore_parent=True)
#     part_infos: list[dict[str, Any]] = sfdisk_json(parent_device, ignore_parent=True)


def select_part_device(
    identify_matcher: str,
    part_devices: list[str],
    source_device: str | None = None,
) -> str:
    if not identify_matcher:
        raise ValueError("Identify matcher must be provided to select a partition device -> exiting")

    if source_device:

        source_device_name: str = os.path.basename(source_device)

        simple_candidate: str = source_device_name + str(identify_matcher)
        if simple_candidate in part_devices:
            return f"/dev/{simple_candidate}"

        block_infos: list[dict[str, Any]] = lsblk_json(source_device, ignore_parent=True)
        for block_info in block_infos:
            if block_info.get('fstype', '').startswith(identify_matcher):
                return f"/dev/{block_info['name']}"
            if identify_matcher == block_info.get('label', ''):
                return f"/dev/{block_info['name']}"
            if identify_matcher == block_info.get('uuid', ''):
                return f"/dev/{block_info['name']}"
            if identify_matcher == block_info.get('name', ''):
                return f"/dev/{block_info['name']}"

    for part_device in part_devices:
        part_device = os.path.basename(part_device)
        if part_device.endswith(identify_matcher):
            return f"/dev/{part_device}"

    raise ValueError(f"No partition device found matching the identify matcher '{identify_matcher}' -> exiting")


def unlock_if_luks_defined(
    part_device: str,
    part_info: dict[str, Any],
) -> str:
    luks_info: dict[str, Any] = part_info.get('luks', None)
    if not luks_info:
        return part_device

    luks_device_name: str = luks_info.get('luks_device_name', 'bootsluks')
    luks_passphrase: str = luks_info.get('luks_passphrase', None)
    # part_device: str = f"/dev/mapper/{luks_device_name}"
    part_device = unlock_luks_partition(
        part_device,
        luks_device_name=luks_device_name,
        luks_passphrase=luks_passphrase
    )
    return part_device


def add_dict_mount_option(
    option_value: str | None,
    mount_options_dict: dict[str, Any],
) -> None:
    if not option_value:
        return

    if '=' not in option_value:

        if option_value in mount_options_dict:
            del mount_options_dict[option_value]

        mount_options_dict[option_value] = True
        return

    key_value: list[str] = option_value.split('=')

    if key_value[0] in mount_options_dict:
        del mount_options_dict[option_value]

    mount_options_dict[key_value[0]] = key_value[1]


def get_mount_options_str(
    mount_options_dict: dict[str, Any],
) -> str:
    if not mount_options_dict:
        return ''

    mount_options: list[str] = []
    for option, value in mount_options_dict.items():
        if value is True:
            mount_options.append(option)
        else:
            mount_options.append(f"{option}={value}")

    return ','.join(mount_options)


def mount_defined_partition(
    part_info: dict[str, Any],
    source_device: str,
    target_root: str = '/mnt/device_parts',
    addon_mount_options: str | None = None,
) -> None:
    relative_mount: str | None = part_info.get('mount', None)

    if not relative_mount:
        # print_write(f"Partition for {source_device} does not have a mount point defined -> skipping mount", fd_path=None)
        return

    mount_point = os.path.join(target_root, relative_mount.lstrip('/'))
    if not os.path.exists(mount_point):
        print_write(f"Creating mount point directory {mount_point}")
        run_cmd(f"sudo mkdir -p '{mount_point}'")

    mount_point = os.path.realpath(mount_point)

    mount_options_str: str = part_info.get('mount_options', '')
    mount_options: list[str] | None = mount_options_str.split(',')

    mount_options_dict: dict[str, Any] = {}
    for mount_option in mount_options:
        add_dict_mount_option(mount_option, mount_options_dict)

    ssd_option: str | None = part_info.get('ssd', False)
    if ssd_option:
        add_dict_mount_option('ssd', mount_options_dict)

    nocow_option: str | None = part_info.get('nocow', False)
    if nocow_option:
        add_dict_mount_option('nodatacow', mount_options_dict)

    nosum_option: str | None = part_info.get('nosum', False)
    if nosum_option:
        add_dict_mount_option('nodatasum', mount_options_dict)

    compress_option: str | None = get_first_defined_key(part_info, ['compression', 'compress'], None)
    if compress_option:
        add_dict_mount_option(f'compress={compress_option}', mount_options_dict)

    if addon_mount_options:
        for addon_mount_option in addon_mount_options.split(','):
            add_dict_mount_option(addon_mount_option, mount_options_dict)

    result_mount_options_str = get_mount_options_str(mount_options_dict)

    if not result_mount_options_str:
        result_mount_options_str = 'defaults'

    run_cmd(f"sudo mount -o {result_mount_options_str} '{source_device}' '{mount_point}'")

    verify_correct_mount_cmd: str = f"sudo mount | grep '{mount_point}' | grep -Eo '^/dev/[a-zA-Z0-9\\-\\_\\/\\@]+'"
    mounted_device: str = os.popen(verify_correct_mount_cmd).read().strip()
    if not mounted_device:
        raise ValueError(f"Failed to mount partition {source_device} to {mount_point} with options '{result_mount_options_str}' -> exiting")
    if mounted_device != source_device:
        raise ValueError(f"Mounted device {mounted_device} does not match source device {source_device} -> exiting")


def mount_subvol_parts(
    source_device: str,
    subvol_part_infos: dict[str, Any],
    target_root: str = '/mnt/device_parts',
) -> None:
    if not subvol_part_infos:
        # print_write("No subvolume partition infos provided -> skipping subvolume mount", fd_path=None)
        return

    target_mount_name: str = os.path.basename(target_root)
    temp_btrfs_root: str = os.path.join('/tmp/temp_btrfs_roots', target_mount_name)
    os.makedirs(temp_btrfs_root, exist_ok=True)
    run_cmd(f"sudo mount -o defaults '{source_device}' '{temp_btrfs_root}'")
    print_write(f"Mounted BTRFS partition {source_device} to temporary root {temp_btrfs_root}", fd_path=None)
    list_btrfs_subvolumes_cmd: str = f"sudo btrfs subvolume list '{temp_btrfs_root}'"
    subvolumes_list_str: str = os.popen(list_btrfs_subvolumes_cmd).read().strip()
    if not subvolumes_list_str:
        print_write(f"No subvolumes found in BTRFS partition {source_device} -> skipping subvolume mount", fd_path=None)
        run_cmd(f"sudo umount '{temp_btrfs_root}'")
        return
    subvolumes_list_lines: list[str] = subvolumes_list_str.splitlines()
    subvolumes_list: list[str] = []
    for line in subvolumes_list_lines:
        parts = line.split(' ')
        subvol_name = parts[-1]
        subvolumes_list.append(subvol_name)

    for subvol_key, subvol_info in subvol_part_infos.items():
        subvol_name: str = subvol_info.get('name', subvol_key)
        if not subvol_name:
            print(f"Subvolume {subvol_key} does not have a 'subvol' " + "{name}" + " defined -> skipping mount")
        if subvol_name not in subvolumes_list:
            print(f"Subvolume {subvol_name} not found in BTRFS partition at {source_device}, available: {','.join(subvolumes_list)} -> skipping mount")
            continue

        mount_defined_partition(
            part_info=subvol_info,
            source_device=source_device,
            target_root=target_root,
            addon_mount_options='subvol=' + subvol_name,
        )

    print("Mounted subvolumes list:")
    # run_cmd(f"sudo mount | grep '{part_device}'")
    run_cmd(f"sudo mount | grep '{target_root}'")
    print("Existing subvolumes or chroot mount:")
    run_cmd(f"sudo btrfs subvolume list '{target_root}'")


def mount_device_parts(
    source_device: str,
    system_parts: dict[str, Any],
    target_root: str = '/mnt/device_parts',
) -> None:
    if not source_device:
        raise ValueError("Source device must be defined to mount its partitions -> exiting")
    if not os.path.exists(source_device):
        raise FileNotFoundError(f"Source device '{source_device}' does not exist in the system -> exiting")
    if not os.path.exists(target_root):
        print_write(f"Creating target root directory {target_root} for mounting partitions", fd_path=None)
        run_cmd(f"sudo mkdir -p '{target_root}'")

    target_device_parts_cmd: str = f"lsblk -f --list -o NAME {source_device} | tail -n +3"
    target_device_parts: str = os.popen(target_device_parts_cmd).read().strip()
    target_device_parts = target_device_parts.splitlines()

    for part_key, part_info in system_parts.items():

        identify_matcher: str = str(part_info.get('identify', None))
        if not identify_matcher:
            if not identify_matcher:
                raise ValueError(f"Partition '{part_key}' does not have an identify matcher or name defined -> exiting")

        part_device: str = select_part_device(
            identify_matcher=identify_matcher,
            part_devices=target_device_parts,
            source_device=source_device
        )
        part_device = unlock_if_luks_defined(
            part_device=part_device,
            part_info=part_info,
        )

        subvolumes: dict[str, Any] = part_info.get('subvolumes', None)
        mount_subvol_parts(
            source_device=part_device,
            subvol_part_infos=subvolumes,
            target_root=target_root,
        )

        mount_defined_partition(
            part_info=part_info,
            source_device=part_device,
            target_root=target_root
        )


def mount_system_root(
    stage_cfg: dict[str, Any],
    set_config: dict[str, Any] = {},
    config: dict[str, Any] = {},
) -> None:
    variables: dict[str, Any] = get_variables(stage_cfg, config=config)
    config.update(variables)

    prepare_target_device_lifecycle(
        config,
        use_existing=True,
        disable_close_cleanup=True
    )
    # output_script: str = config.get('output', None)

    target_device: str = config.get('target_device', None)
    if not target_device:
        raise ValueError("Target device must be defined in the configuration under 'variables' -> exiting")

    real_target_device: str = target_device
    if os.path.islink(target_device):
        real_target_device = os.readlink(real_target_device)
        print_write(f"Resolved from {target_device} to real target device symlink to {real_target_device}")
        target_device = real_target_device

    if not target_device.startswith('/dev/'):
        find_part_command = f"lsblk -f --list -o NAME,LABEL,UUID | grep \"{target_device}\" | grep -Eo \"^[a-z0-9]+\""
        found_target_part = os.popen(find_part_command).read().strip()
        if not found_target_part:
            raise ValueError(f"Target device with '{target_device}' not found in the system -> exiting")

        map_device_cmd = f"lsblk -ndo pkname '/dev/{found_target_part}'"
        target_device = os.popen(map_device_cmd).read().strip()

    if not os.path.exists(target_device):
        raise ValueError(f"Target device '{target_device}' does not exist in the system -> exiting")

    target_device_name: str = os.path.basename(target_device)

    chroot_mount: str = config.get('chroot_mount', None)
    if not chroot_mount:
        chroot_mount = config.get('mount', '/tmp/bootstrap_mount')

    system_parts: dict[str, Any] = get_first_defined_key(
        stage_cfg,
        ['partitions', 'parts'],
        {}
    )
    if not system_parts:
        print_write("Part table not defined in the configuration -> skipping 'chroot' mount stage")
        return

    if not os.path.exists(chroot_mount):
        print_write(f"Creating chroot mount point directory {chroot_mount}", fd_path=config.get('output', None))
        run_cmd(f"sudo mkdir -p '{chroot_mount}'", fd_path=config.get('output', None))

    mount_device_parts(
        source_device=target_device,
        system_parts=system_parts,
        target_root=chroot_mount,
    )


def clean_devices(
    stage_cfg: dict[str, Any],
    set_config: dict[str, Any] = {},
    config: dict[str, Any] = {},
) -> None:
    # Note if any program is open with the parititions -> unmounting and cleaning could fail
    # --> can cause problems if the same encrpted luks device is mounted in multiple places, through those side effects
    output_script: str | None = config.get('output', None)
    target_devices: list[str] = config.get('clean_devices', [])

    if not target_devices:
        print_write("No target devices defined in the configuration under 'target_devices' or 'clean_devices' -> skipping 'clean' stage", fd_path=output_script)
        return

    for target_device in target_devices:
        if not os.path.exists(target_device):
            print_write(f"Target device {target_device} does not exist -> skipping cleaning", fd_path=output_script)
            continue

        if os.path.islink(target_device):
            target_device = os.readlink(target_device)
            print_write(f"Resolved symlink {target_device} to real target device", fd_path=output_script)

        cleanup_device_resources(target_device)


def run_ensure_dependency_stages(
    stage_cfg: dict[str, Any],
    set_config: dict[str, Any] = {},
    config: dict[str, Any] = {}
) -> None:
    processed_stages: list[str] = config.get('processed_stages', [])
    depends_stages: list[str] | str = get_first_defined_key(stage_cfg, ['depend', 'depends'], [])
    if isinstance(depends_stages, str):
        depends_stages = [depends_stages]

    for depends_stage in depends_stages:
        if depends_stage in processed_stages:
            continue
        run_stage(depends_stage, set_config, config)


def run_cmd_in_chroot(
    command: str,
    chroot_path: str,
    chroot_bin: str = 'arch-chroot'
) -> None:
    if not os.path.exists(chroot_path):
        raise ValueError(f"Chroot path '{chroot_path}' does not exist in the system -> exiting")

    chroot_path = os.path.realpath(chroot_path)

    return run_cmd(f"{chroot_bin} '{chroot_path}' /bin/bash -c \"{command}\"")


def run_lines_in_chroot(
    script_lines: str,
    chroot_path: str,
    chroot_bin: str = 'arch-chroot'
) -> None:
    if not os.path.exists(chroot_path):
        raise ValueError(f"Chroot path '{chroot_path}' does not exist in the system -> exiting")
    chroot_path = os.path.realpath(chroot_path)

    first_line = f"cat << 'EOF' | {chroot_bin} '{chroot_path}' /bin/bash"
    last_line = "EOF"

    chroot_command_parts: list[str] = [first_line, script_lines, last_line]
    command: str = '\n'.join(chroot_command_parts)

    return run_cmd(command)


def run_file_in_chroot(
    file_path: str,
    chroot_path: str,
    chroot_bin: str = 'arch-chroot'
) -> None:
    if not os.path.exists(file_path):
        raise ValueError(f"File path '{file_path}' does not exist in the system -> exiting")

    file_path = os.path.realpath(file_path)
    file_contents: str = ''
    with open(file_path, 'r') as fd:
        file_contents = fd.read()

    return run_lines_in_chroot(
        script_lines=file_contents,
        chroot_path=chroot_path,
        chroot_bin=chroot_bin
    )


def install_system(
    stage_cfg: dict[str, Any],
    set_config: dict[str, Any] = {},
    config: dict[str, Any] = {}
) -> None:

    run_ensure_dependency_stages(stage_cfg, set_config, config)

    target_system_type: str | None = stage_cfg.get('type')
    program_binary: str | None = stage_cfg.get('program')

    if not target_system_type and not program_binary:
        raise ValueError("Either 'type' or 'program' must be defined in the 'install' stage configuration -> exiting")

    if not program_binary:
        if target_system_type == 'debian' or target_system_type == 'ubuntu':
            program_binary = 'debootstrap'
        elif target_system_type == 'arch' or target_system_type == 'manjaro':
            program_binary = 'pacstrap'
        else:
            raise ValueError(f"Unsupported system type '{target_system_type}' defined in the 'install' stage configuration -> exiting")

    # TODO try fallback to default location /usr/bin/{program_binary}

    program_binary = os.path.expanduser(program_binary)
    program_path: str | None = shutil.which(program_binary)
    if not program_path or not os.path.exists(program_path):
        raise ValueError(f"Installation program '{program_binary}' not found in the system PATH -> exiting")

    chroot_mount_point: str | None = set_config.get('chroot_mount', None)
    if not chroot_mount_point:
        chroot_mount_point = stage_cfg.get('chroot', {}).get('variables', {}).get('mount', None)

    if not chroot_mount_point:
        chroot_mount_point = config.get('chroot_mount', None)

    if not chroot_mount_point:
        chroot_mount_point = config.get('mount', '/tmp/bootstrap_mount')

    chroot_mount_point = get_variable_value('chroot_mount', chroot_mount_point)
    if not os.path.exists(chroot_mount_point):
        raise ValueError(f"Chroot mount point '{chroot_mount_point}' does not exist in the system -> exiting")

    print_write(f"Using installation program '{program_binary}' found at '{program_path}'")

    bootstrap_options = None

    cmd: str | None = None
    source_url: str | None = stage_cfg.get('source', None)

    # https://packages.debian.org/stable/debootstrap - https://salsa.debian.org/installer-team/debootstrap
    if target_system_type == 'debian':
        bootstrap_options = stage_cfg.get('deb', {})
        source_url = bootstrap_options.get('source', "http://deb.debian.org/debian")

        components = bootstrap_options.get('components', 'main,contrib,non-free')
        target_system_arch = bootstrap_options.get('arch', 'amd64')
        release: str = bootstrap_options.get('release', 'stable')

        cmd = f"sudo {program_path} --arch={target_system_arch} --components={components} {release} '{chroot_mount_point}' '{source_url}'"

    elif target_system_type == 'ubuntu':
        bootstrap_options = stage_cfg.get('deb', {})
        source_url = bootstrap_options.get('source', "http://de.archive.ubuntu.com/ubuntu")

        components = bootstrap_options.get('components', 'main,contrib,non-free')
        target_system_arch = bootstrap_options.get('arch', 'amd64')
        release: str = bootstrap_options.get('release', 'noble')

        cmd = f"sudo {program_path} --arch={target_system_arch} --components={components} {release} '{chroot_mount_point}' '{source_url}'"
        # "debootstrap noble /mnt http://de.archive.ubuntu.com/ubuntu"

    # apparently when using debian host https://packages.debian.org/search?searchon=sourcenames&keywords=arch-install-scripts
    # in the bullseye package the pacstrap script is missing
    # https://gitlab.archlinux.org/archlinux/arch-install-scripts/-/blob/master/pacstrap.in?ref_type=heads
    # https://packages.debian.org/bookworm/all/arch-install-scripts/download (workaround download and install .deb package manually)
    elif target_system_type == 'arch' or target_system_type == 'manjaro':
        bootstrap_options = stage_cfg.get('arch', {})
        # source_url = bootstrap_options.get('source', "https://mirrors.kernel.org/archlinux/")
        packages: str = bootstrap_options.get('packages', 'base linux linux-firmware sudo')
        # -M option to not copy the host's /etc/pacman.d/mirrorlist
        # -G avoids copying the host's pacman keyring to the target
        # -K Initialize an empty pacman keyring in the target
        cmd = f"sudo {program_path} -M -G -K '{chroot_mount_point}' {packages}"

        # cmd = f"sudo {program_path} -C '{source_url}' -G -M '{chroot_mount_point}' {packages}"

    os.system(cmd)


# ------------------------ Invoking stages/main functions -------------------------
default_stage_exec_map = {
    'partitions': exec_partitions_installer,
    'chroot': mount_system_root,
    'clean': clean_devices,
    'install': install_system,
}


def select_run_set(
    config: dict[str, Any] = {},
) -> dict[str, Any]:
    selected_set: str = get_first_defined_key(config, ['set', 'selected_set'], None)
    set_defs: dict[str, Any] = get_first_defined_key(config, ['sets', 'set_defs', 'set_definitions'], None)

    if not selected_set:
        return config.get('sets', {})

    return set_defs.get(selected_set, {})


def run_stage(
    stage_key: str,
    set_config: dict[str, Any] = {},
    config: dict[str, Any] = {},
    stage_exec_map: dict[str, Any] = default_stage_exec_map
) -> None:
    output_script: str = config.get('output', None)

    stage_exec_fn = stage_exec_map.get(stage_key, None)
    stage_config: dict[str, Any] = set_config.get(stage_key, {})

    print_write(f"Running Stage '{stage_key}'", fd_path=output_script)

    if not stage_exec_fn:
        print_write(f"Stage {stage_key} not defined in the execution map -> skipping stage.", fd_path=output_script)
        return None

    if callable(stage_exec_fn):
        stage_exec_fn(
            stage_config,
            set_config=set_config,
            config=config
        )

        if 'processed_stages' not in config:
            config['processed_stages'] = []
        config['processed_stages'].append(stage_key)

    else:
        print_write(f"Stage {stage_key} is not a callable function -> skipping stage.", fd_path=output_script)


def run_stages(
    stages: list[str],
    set_config: dict[str, Any] = {},
    config: dict[str, Any] = {},
    stage_exec_map: dict[str, Any] = default_stage_exec_map
) -> None:

    for stage_key in stages:
        run_stage(
            stage_key,
            set_config,
            config,
            stage_exec_map=stage_exec_map
        )


def load_config(
    config_path: str,
    args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not config_path:
        raise ValueError("Configuration path must be provided in the args or config")

    if config_path.startswith('github@'):
        target_parts: list[str] = config_path.split('@')
        target_source: str = target_parts[0]
        location_parts: list[str] = target_parts[1].split('/')
        username: str = location_parts[0]
        repo_name: str = location_parts[1]
        file_path: str = '/'.join(location_parts[2:])

        # example: github@markuspeitl/my-linux-scripts/docs/configure-network-drive.txt
        # results in: https://github.com/markuspeitl/my-linux-scripts/raw/refs/heads/master/docs/configure-network-drive.txt
        raw_file_path: str = f"https://github.com/{username}/{repo_name}/raw/refs/heads/master/{file_path}"
        print(f"Loading configuration from GitHub: {raw_file_path}")
        config_path = raw_file_path

    if config_path.startswith('http://') or config_path.startswith('https://') or config_path.startswith('www.'):
        print(f"Loading configuration from URL: {config_path}")
        import requests
        response = requests.get(config_path)
        if response.status_code != 200:
            raise ValueError(f"Failed to load configuration from URL {config_path} with status code {response.status_code}")
        config_path = '/tmp/bootstrap_config.yml'
        with open(config_path, 'w') as f:
            f.write(response.text)

    if not config_path or not os.path.exists(config_path):
        raise ValueError(f"Configuration file {config_path} does not exist -> exiting")

    source_path: str = args.get('source_path', None)
    if not source_path:
        raise ValueError("Source path must be provided in the config")
    bootstrap_config = load_yml_config(source_path)
    merge_args_to_config(bootstrap_config, args)

    return bootstrap_config


def bootstrap_defined_system(config: dict[str, Any] = {}):
    print('Calling bootstrap_defined_system')
    bootstrap_config = load_config(
        config_path=config.get('source_path', None),
        args=config
    )

    init_output_script(bootstrap_config)
    system_type: str = prepare_install_env(bootstrap_config)

    run_stage_keys: list[str] = bootstrap_config.get('stages', None)
    if not run_stage_keys:
        raise ValueError("No stages defined in the bootstrap configuration or passed as args -> exiting")

    selected_set_config: dict[str, Any] = select_run_set(bootstrap_config)
    run_stages(
        run_stage_keys,
        set_config=selected_set_config,
        config=bootstrap_config
    )

# ------------------------ Parsing arguments -------------------------


import argparse


def add_simulation_parsing_options(parser: argparse.ArgumentParser):
    parser.add_argument('-sim', '--simulate',
                        help="Specify the path to an disk.img file to simulate the installation process. Note: still installs requirements on host system",
                        type=str, default=None)
    parser.add_argument('-sims', '--sim_size', help="Size of the simulation image", default='10G')
    parser.add_argument('-osim', '--overwrite_sim', help="Overwrite simulation image even if it exists", action='store_true')


def add_bootstrap_parsing_options(parser: argparse.ArgumentParser):
    # parser.add_argument('-fr', '-oreq', '--force_output_requirements', help="Write requirements to output script even if installed", action='store_true')

    parser.add_argument('source_path', help="Path/url or github specifier to .yml file containing part table, fs info and install scripts")
    parser.add_argument('stages', nargs='*', help="Which defined stages to run and setup during the bootstrap process")
    parser.add_argument('-sys', '--system', help="Target host system to run the bootstrap on", default=identify_system())
    parser.add_argument('-set', '--set', help="Which defined set to run -> without the stages in 'sets' are executed without a set label")

    parser.add_argument('-cd', '--clean_devices', nargs='+', help="Clean up multiple loop devices with the 'clean' stage, in case not properly closed or removed")
    # parser.add_argument('-s', '--stages', nargs='+', help="Which defined stages to run and setup during the bootstrap process")
    # parser.add_argument('-t', '--target', help="Which defined set to run -> without the stages in 'sets' are executed without a set label")

    # Output script not supported anymore
    # parser.add_argument('-o', '--output', help="Output commands to a script instead of executing them directly")

    parser.add_argument('-td', '--target_device', help="Manually specify the block device to target for partitioning and formatting")
    parser.add_argument('-m', '--mount', help="@chroot: Mount point for the system root, if not specified will use config.mount or /tmp/bootstrap_mount")
    parser.add_argument('-it', '--interactive', help="Asks whether to continue with certain operations", action='store_true')
    add_simulation_parsing_options(parser)


def main(parser: argparse.ArgumentParser | None = None):
    parser_description = "Use a .yml file to bootstrap an advanced linux system installation"

    if (not parser):
        parser = argparse.ArgumentParser(
            description=parser_description
        )
        add_bootstrap_parsing_options(parser)

    args: argparse.Namespace = parser.parse_args()

    config: dict[str, Any] = vars(args)
    bootstrap_defined_system(config)


if __name__ == '__main__':
    sys.exit(main())
