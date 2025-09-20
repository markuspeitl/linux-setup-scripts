#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# dependencies:
# - debootstrap (installed on system), or tar + gzip + make (for downloading and installing to temporary dir from source)
# - arch-install-scripts (installed on system), or binutils + wget + tar + zstd (for downloading and unpacking the .deb package temporarily -> also works on non-debian systems)
# also some distros might not have pacstrap in the package that is installed
# - mount, dependencies of debootstrap, depedencies of arch-install-scripts (usually stuff installed on most systems)

# installing both takes about 1MB of disk space (non minified bash scripts)

import os
import pathlib
import shutil
import sys

from utils.download_extract_archive import download_archive_unpack


def run_print(cmd: str, dry_run=False) -> None:
    print(f"CMD: {cmd}")

    if dry_run:
        return

    os.system(cmd)


def copy_dir_contents_to(src_dir: str, dest_dir: str) -> None:
    src_path_obj = pathlib.Path(src_dir)
    dest_path_obj = pathlib.Path(dest_dir)

    if not src_path_obj.is_dir():
        raise NotADirectoryError(f"Source path '{src_dir}' is not a directory.")
    if not dest_path_obj.is_dir():
        raise NotADirectoryError(f"Destination path '{dest_dir}' is not a directory.")

    for item in src_path_obj.iterdir():
        dest_item_path = os.path.join(dest_dir, item.name)
        if item.is_dir():

            os.makedirs(dest_item_path, exist_ok=True)
            shutil.copytree(item, dest_item_path, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest_item_path)


def discover_binaries(
    root_dir: str,
    dirs_to_search: list[str] = ["/usr/bin", "/usr/sbin", "/bin", "/sbin"],
    make_executable: bool = False
) -> None:
    print(f"Discovering binaries in '{root_dir}'")
    binary_dict: dict[str, str] = {}
    for search_dir in dirs_to_search:
        abs_search_dir = os.path.join(root_dir, search_dir.lstrip("/"))
        if not os.path.isdir(abs_search_dir):
            continue

        dir_path_obj = pathlib.Path(abs_search_dir)
        for item in dir_path_obj.iterdir():
            if not item.is_file():
                continue

            binary_dict[item.name] = str(item.absolute())
            if make_executable:
                item.chmod(item.stat().st_mode | 0o111)  # Add execute permissions

    return binary_dict


def download_arch_install_scripts(skip_if_installed=True) -> dict[str, str]:

    if skip_if_installed:
        arch_chroot = shutil.which("arch-chroot")
        pacstrap = shutil.which("pacstrap")
        genfstab = shutil.which("genfstab")
        if arch_chroot is not None and pacstrap is not None and genfstab is not None:
            print(f"Found existing arch install scripts binaries at: {arch_chroot}, {pacstrap}, {genfstab}")
            return {
                'arch-chroot': arch_chroot,
                'pacstrap': pacstrap,
                'genfstab': genfstab
            }

    # Requires 'binutils' to be installed for unpacking .deb files, but should be pretty ubiquitous
    download_url = "https://mirrors.edge.kernel.org/ubuntu/pool/universe/a/arch-install-scripts/arch-install-scripts_28-1_all.deb"

    unpacked_dir = download_archive_unpack(download_url, "/dev/shm", redownload=False, flat=False)

    binary_dict: dict[str, str] = discover_binaries(unpacked_dir, make_executable=True)

    for binary_name, binary_path in binary_dict.items():
        print(f"Found binary '{binary_name}' at '{binary_path}'")

    return binary_dict


def download_debootstrap_scripts(skip_if_installed=True) -> str:

    if skip_if_installed:
        existing_binary = shutil.which("debootstrap")
        if existing_binary is not None:
            print(f"Found existing debootstrap binary at: {existing_binary}")
            return existing_binary

    target_tag = "1.0.141"  # Version or branch like "master" or "1.0.141"
    debootstrap_repo_download_url = f"https://salsa.debian.org/installer-team/debootstrap/-/archive/{target_tag}/debootstrap-{target_tag}.tar.gz"

    # archive_name = os.path.basename(debootstrap_repo_download_url)
    # download_file_path = f"/dev/shm/{archive_name}"

    unpacked_dir = download_archive_unpack(debootstrap_repo_download_url, "/dev/shm", redownload=False)

    unpacked_dir_obj = pathlib.Path(unpacked_dir)
    inner_files: list[pathlib.Path] = list(unpacked_dir_obj.iterdir())

    if (inner_files and len(inner_files) == 1):
        copy_dir_contents_to(str(inner_files[0]), unpacked_dir)
    # if (len(str(inner_dir)) > 1):
    #     inner_dir.rm

    cwd = os.getcwd()
    os.chdir(unpacked_dir)
    # In theory not really necessary as the repository already contains binary-like scripts that are just copied during make
    run_print("make all")

    dest_dir = unpacked_dir_obj.joinpath("install").absolute()
    os.makedirs(dest_dir, exist_ok=True)
    run_print(f"export DESTDIR=\"{dest_dir}\" make --always-make install DESTDIR=\"{dest_dir}\"")
    os.chdir(cwd)

    binary_dict: dict[str, str] = discover_binaries(dest_dir, make_executable=True)
    for binary_name, binary_path in binary_dict.items():
        print(f"Found binary '{binary_name}' at '{binary_path}'")

    deboot_scripts_dir = os.path.join(dest_dir, "usr/share/debootstrap")

    return f"DEBOOTSTRAP_DIR=\"{deboot_scripts_dir}\" {binary_dict['debootstrap']}"


def mount_scripts_dir(chroot_dir_path: str, dry_run=False) -> None:
    # Bind mount current scripts dir from host to chroot env
    # to exchange scripts and data

    current_script_dir: str = os.path.dirname(os.path.abspath(__file__))
    scripts_mount_path = f"{chroot_dir_path}/scripts"

    mount_cmd = f"mount --bind '{current_script_dir}' '{scripts_mount_path}'"
    if dry_run:
        print(f"CMD: {mount_cmd}")
        return
    os.makedirs(scripts_mount_path, exist_ok=True)
    os.system(mount_cmd)


def prepare_dependencies(dry_run=False) -> tuple[str, str]:
    if dry_run:
        return "arch-chroot", "debootstrap"

    arch_install_bins: dict[str, str] = download_arch_install_scripts(skip_if_installed=False)
    print(f"arch install scripts: \n{arch_install_bins}")
    debootstrap = download_debootstrap_scripts(skip_if_installed=True)
    print(f"debootstrap script: \n{debootstrap}")
    return arch_install_bins['arch-chroot'], debootstrap


default_ignored_packages: list[str] = [
    # "snapd",
    "cloud-init",
    "landscape-common",
    "popularity-contest",
    "ubuntu-advantage-tools"
]
default_enabled_repositories: list[str] = [
    "main",
    "restricted",
    "universe"
]
default_release_codename: str = "noble"  # Ubuntu 24.04 LTS
default_mirror: str = "http://de.archive.ubuntu.com/ubuntu"


def prepare_debootstrap_target_cmd(
    chroot_target_path: str,
    debootstrap_bin: str = "debootstrap",
    mirror_url: str = default_mirror,
    target_arch: str = "amd64",
    release_codename: str = default_release_codename,
    dry_run: bool = False
) -> str:
    if not chroot_target_path:
        raise ValueError("'chroot_target_path' must be a valid path to bootstrap a system onto it")

    # if is not a mount point -> bind mount to itself to make it a mount point (for findmnt etc -> more info in debootstrap source)

    if not dry_run:
        os.makedirs(chroot_target_path, exist_ok=True)
    if not os.path.ismount(chroot_target_path):
        run_print(f"mount --bind '{chroot_target_path}' '{chroot_target_path}'", dry_run=dry_run)

    bootstrap_cmd = f"{debootstrap_bin} --arch=\"{target_arch}\" {release_codename} \"{chroot_target_path}\" {mirror_url}"

    return bootstrap_cmd


def write_chroot_cfg_file(
    target_path: str,
    content: str,
    system_root_dir: str = None,
    dry_run=False
) -> None:
    if system_root_dir is None and not os.path.isabs(target_path):
        raise ValueError("'system_root_dir' must be specified if 'target_path' is not an absolute path")

    if system_root_dir:
        target_path = os.path.join(system_root_dir, target_path)

    if dry_run:
        print(f"Writing to '{target_path}':\n{content}")
        return

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)


# currently only a config for ubuntu/debian systems
def init_apt_sources_list(
    system_root_dir: str,
    mirror_url: str = "http://de.archive.ubuntu.com/ubuntu",
    release_codename: str = "noble",
    sources_list_content: str = None,  # if specified -> custom sources.list content
    enabled_repositories: list[str] = ["main", "restricted", "universe"],  # , "multiverse"]
    dry_run=False
) -> None:
    if not system_root_dir:
        raise ValueError("'system_root_dir' must be a valid path to put a 'sources.list' file onto it")

    sources_list_path = os.path.join(system_root_dir, "etc/apt/sources.list")

    if sources_list_content is not None and len(sources_list_content) > 0:
        print(f"Using custom sources.list content:\n{sources_list_content}")
        write_chroot_cfg_file(sources_list_path, sources_list_content, dry_run=dry_run)
        return

    if enabled_repositories is None or len(enabled_repositories) == 0:
        raise ValueError("'enabled_repositories' must contain at least one repository like 'main' or 'universe' if no custom 'sources_list_content' is specified")

    repositories_str = " ".join(enabled_repositories)
    apt_repositories_sources = []
    apt_repositories_sources.append(f"deb {mirror_url} {release_codename} {repositories_str}")
    apt_repositories_sources.append(f"deb {mirror_url} {release_codename}-updates {repositories_str}")
    apt_repositories_sources.append(f"# deb {mirror_url} {release_codename}-backports {repositories_str}")
    apt_repositories_sources.append(f"deb http://security.ubuntu.com/ubuntu {release_codename}-security {repositories_str}")
    sources_list_content = "\n".join(apt_repositories_sources) + "\n"

    print(f"Using generated 'sources.list' content:\n{sources_list_content}")
    write_chroot_cfg_file(sources_list_path, sources_list_content, dry_run=dry_run)


def init_ignore_pkgs_config(
    system_root_dir: str,
    ignored_packages: list[str],
    dry_run=False
) -> None:
    if not system_root_dir:
        raise ValueError("'system_root_dir' must be a valid path to put an 'ignored-packages' file onto it")

    if ignored_packages is None or len(ignored_packages) == 0:
        return

    print(f"Ignoring packages: {ignored_packages}")

    ignored_packages_path = os.path.join(system_root_dir, "etc/apt/preferences.d/ignored-packages")
    ignored_pkgs_string = " ".join(ignored_packages)
    ignored_package_contents: list[str] = [
        f"Package: {ignored_pkgs_string}",
        "Pin: release *",
        "Pin-Priority: -1"
    ]
    ignored_packages_content = "\n".join(ignored_package_contents) + "\n"

    write_chroot_cfg_file(ignored_packages_path, ignored_packages_content, dry_run=dry_run)


def debootstrap_basic_system(
    chroot_target_path: str,
    mirror_url: str = default_mirror,
    target_arch: str = "amd64",
    release_codename: str = default_release_codename,
    ignored_packages: list[str] = default_ignored_packages,
    enabled_repositories=default_enabled_repositories,
    enter_chroot: bool = True,
    dry_run: bool = False
) -> None:
    arch_chroot, debootstrap = prepare_dependencies(dry_run=dry_run)
    bootstrap_cmd = prepare_debootstrap_target_cmd(
        chroot_target_path,
        debootstrap_bin=debootstrap,
        mirror_url=mirror_url,
        target_arch=target_arch,
        release_codename=release_codename,
        dry_run=dry_run
    )
    run_print(bootstrap_cmd, dry_run=dry_run)

    init_apt_sources_list(
        chroot_target_path,
        mirror_url=mirror_url,
        release_codename=release_codename,
        sources_list_content=None,
        enabled_repositories=enabled_repositories,
        dry_run=dry_run
    )
    init_ignore_pkgs_config(chroot_target_path, ignored_packages=ignored_packages, dry_run=dry_run)

    mount_scripts_dir(chroot_target_path, dry_run=dry_run)

    if enter_chroot:
        run_print(f"{arch_chroot} '{chroot_target_path}'", dry_run=dry_run)


import argparse
from typing import Any


def debootstrap_basic_system_from_args(config: dict[str, Any] = {}):
    debootstrap_basic_system(
        chroot_target_path=config.get('chroot_target_path'),
        mirror_url=config.get('mirror', default_mirror),
        target_arch=config.get('arch', "amd64"),
        release_codename=config.get('release_codename', default_release_codename),
        ignored_packages=config.get('ignore_packages', default_ignored_packages),
        enabled_repositories=config.get('enabled_repositories', default_enabled_repositories),
        enter_chroot=config.get('enter_chroot', True),
        dry_run=config.get('dry_run', False)
    )


def add_debootstrap_basic_system_parsing_options(parser: argparse.ArgumentParser):
    parser.add_argument('chroot_target_path', help="Path to dir where the basic system should be installed/bootstrapped on")
    parser.add_argument('-mu', '--mirror', help="Mirror URL to use, where to get packages from", default=default_mirror)
    parser.add_argument('-ar', '--arch', help="Architecture to debootstrap, e.g. amd64, arm64, .etc", default="amd64")
    parser.add_argument('-rc', '--release_codename', help="Release codename to use examples: noble, jammy, trixie, bullseye, buster", default=default_release_codename)
    parser.add_argument('-ir', '--ignore_packages', help="List of packages to ignore and prevent to be installed", nargs='*', default=default_ignored_packages)
    parser.add_argument('-er', '--enabled_repositories', help="List of repositories to enable (space separated)", nargs='*', default=default_enabled_repositories)
    parser.add_argument('-cs', '--custom_sources', help="Custom sources.list file to use instead of generating one", default=None)
    parser.add_argument('-ec', '--enter_chroot', action='store_true', help="Enter the chroot environment after bootstrapping the basic system")
    parser.add_argument('-dry', '--dry_run', action='store_true', help="Do not actually run commands, just print them")


def main(parser: argparse.ArgumentParser | None = None):
    parser_description = "Create a basic system with debootstrap for chrooting into and bootstrap dependencies required"

    if (not parser):
        parser = argparse.ArgumentParser(
            description=parser_description
        )
        add_debootstrap_basic_system_parsing_options(parser)

    args: argparse.Namespace = parser.parse_args()

    config: dict[str, Any] = vars(args)
    debootstrap_basic_system_from_args(config)


if __name__ == '__main__':
    sys.exit(main())
