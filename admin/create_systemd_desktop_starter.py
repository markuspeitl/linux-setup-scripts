#!/usr/bin/env python3

import os
import re
import subprocess
import sys
import getpass


# Commit message: Add code to enable and start the systemd unit file

# Features:
# - Added function print_exec_cmd to print and execute a command
# - Added function find_desktop_file to find a desktop file in a directory
# - Added function extract_executable_path_from_desktop_file to extract the executable path from a desktop file
# - Added function write_systemd_unit_file to write a systemd unit file for a given binary path
# - Updated the commit message to reflect the changes made


def print_exec_cmd(cmd):
    """
    Print and execute a command.

    Args:
        cmd (str): The command to execute.
    """
    print(f"Executing: {cmd}")
    os.system(cmd)


def find_desktop_file(
    desktop_files_dir_path: str,
    desktop_partial_name: str
):
    """
    Find a desktop file in a directory.

    Args:
        desktop_files_dir_path (str): The path to the directory containing the desktop files.
        desktop_partial_name (str): The partial name of the desktop file to search for.

    Returns:
        str: The path of the found desktop file, or None if not found.
    """
    for entry in os.scandir(desktop_files_dir_path):
        if entry.is_file() and desktop_partial_name in entry.name:
            return entry.path
    return None


def extract_executable_path_from_desktop_file(desktop_file_path: str):
    """
    Extract the executable path from a desktop file.

    Args:
        desktop_file_path (str): The path to the desktop file.

    Returns:
        str: The executable path extracted from the desktop file.
    """
    with open(desktop_file_path, "r") as f:
        desktop_file_content: str = "" + f.read()

        exec_pattern = re.compile(r"(?<=Exec=).+")

        desktop_binary_match = exec_pattern.search(desktop_file_content)
        desktop_binary_path: str = desktop_binary_match.group(0)
        return desktop_binary_path


def write_systemd_unit_file(
    binary_path: str,
    systemd_unit_files_dir: str = "/etc/systemd/user",
    dry_run: bool = False
):
    """
    Write a systemd unit file for a given binary path.

    Args:
        binary_path (str): The path to the binary.
        systemd_unit_files_dir (str): The directory to write the systemd unit file to.
        dry_run (bool): If True, only print the unit file content without writing it.

    Returns:
        str: The path of the written unit file.
    """
    unit_file_path: str = os.path.join(
        systemd_unit_files_dir,
        os.path.basename(binary_path) + ".service"
    )

    unit_file_content: str = f"""
[Unit]
Description=Desktop starter for {desktop_partial_name}
Type=simple
TimeoutStartSec=0

[Service]
ExecStart={binary_path}

[Install]
WantedBy=default.target
"""

    if dry_run:
        print(unit_file_content)
        return unit_file_path

    subprocess.run(
        ["sudo", "tee", unit_file_path],
        input=unit_file_content.encode(),
        check=True)

    return unit_file_path


desktop_files_dir_path: str = os.path.expanduser(
    "~/.local/share/applications"
)

desktop_partial_name = sys.argv[1]
print(
    f"Searching for desktop file with name containing: {desktop_partial_name}"
)

desktop_file = find_desktop_file(
    desktop_files_dir_path,
    desktop_partial_name
)
if not desktop_file:
    print("Desktop file not found")
    sys.exit(1)

binary_path = extract_executable_path_from_desktop_file(desktop_file)
print(f"Binary path extracted from desktop file: {binary_path}")

unit_file_path = write_systemd_unit_file(
    binary_path,
    # dry_run=True
)

print(
    f"Systemd unit file created at: {unit_file_path} \n"
    f" for {desktop_partial_name} with binary path: {binary_path}"
)

current_user = getpass.getuser()
# print(f"Current user name: {current_user}")

print_exec_cmd(
    f"sudo chown {current_user} {unit_file_path}"
)

print_exec_cmd(
    f"systemctl --user enable {os.path.basename(unit_file_path)}"
)

print_exec_cmd(
    f"systemctl --user start {os.path.basename(unit_file_path)}"
)
