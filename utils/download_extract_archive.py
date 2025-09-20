#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pathlib
import shutil
import sys


def run_print(cmd: str) -> None:
    print(f"CMD: {cmd}")
    os.system(cmd)


def ensure_bin_in_path(bin_name: str) -> bool:
    from shutil import which

    bin_resolved_path = which(bin_name)

    if bin_resolved_path is None:
        raise FileNotFoundError(f"Required binary '{bin_name}' not found in PATH.")

    return None


def get_extract_archive_cmd(archive_path: str, dest_path: str) -> str:

    archive_name = os.path.basename(archive_path)
    name_parts = archive_name.split(".")
    archive_full_suffix = ".".join(name_parts[1:])  # Join all suffixes after the first dot

    if name_parts[-1] == "zip":
        ensure_bin_in_path("unzip")
        return f"unzip -o '{archive_path}' -d '{dest_path}'"

    if name_parts[-1] == "tar":
        ensure_bin_in_path("tar")
        return f"tar -xf '{archive_path}' -C '{dest_path}'"

    if name_parts[-1] == "deb":
        ensure_bin_in_path("ar")
        ensure_bin_in_path("tar")
        return f"ar vx '{archive_path}' --output '{dest_path}'"
        # return f"ar x '{archive_path}' && tar -xf 'data.tar.*' -C '{dest_path}'"

    archive_two_suffix = ".".join(name_parts[-2:])

    if archive_two_suffix in ["tar.gz", "tgz"]:
        ensure_bin_in_path("tar")
        ensure_bin_in_path("gzip")
        return f"tar -xzf '{archive_path}' -C '{dest_path}'"

    if archive_two_suffix in ["tar.bzip2", "tar.bz2", "tbz2"]:
        ensure_bin_in_path("tar")
        ensure_bin_in_path("bzip2")
        return f"tar -xjf '{archive_path}' -C '{dest_path}'"

    if archive_two_suffix in ["tar.xz", "txz"]:
        ensure_bin_in_path("tar")
        ensure_bin_in_path("xz")
        return f"tar -xJf '{archive_path}' -C '{dest_path}'"

    if archive_two_suffix in ["tar.zstd", "tar.zst", "tzst", "tzt"]:
        ensure_bin_in_path("tar")
        ensure_bin_in_path("zstd")
        return f"tar -I zstd -xvf '{archive_path}' -C '{dest_path}'"

    raise ValueError(f"Unsupported archive format: '{archive_full_suffix}' for file '{archive_name}'")


def download_file(
    src_url_or_path: str,
    download_dir: str,
    redownload=True
) -> None:

    src_path_obj: pathlib.PurePath = pathlib.PurePath(src_url_or_path)

    if os.path.exists(src_path_obj):
        # Local file path
        return src_url_or_path

    local_archive_path: str = f"{download_dir}/{src_path_obj.name}"

    download_dest_dir: str = os.path.dirname(local_archive_path)
    os.makedirs(download_dest_dir, exist_ok=True)

    if os.path.exists(local_archive_path) and not redownload:
        print(f"File already exists and redownload is False: {local_archive_path}")
        return local_archive_path

    download_cmd = f"wget -O '{local_archive_path}' '{src_url_or_path}'"
    os.system(download_cmd)

    return local_archive_path


def download_archive_unpack(
    src_archive: str,
    dest_dir_path: str = None,
    redownload=True,
    flat=False
) -> None:

    if dest_dir_path is None:
        dest_dir_path = os.getcwd()

    download_dir = dest_dir_path
    if flat:
        download_dir = "/dev/shm"

    local_archive_path: str = download_file(
        src_archive,
        download_dir,
        redownload=redownload
    )

    print(f"Extracting archive: {local_archive_path}")

    local_archive_path_obj: pathlib.PurePath = pathlib.PurePath(local_archive_path)
    name_parts = local_archive_path_obj.name.split(".")
    only_name = name_parts[0]
    archive_full_suffix = ".".join(name_parts[1:])

    target_dest_path: str = f"{dest_dir_path}/{only_name}"
    if flat:
        target_dest_path = dest_dir_path
        os.makedirs(os.path.dirname(target_dest_path), exist_ok=True)
    else:
        os.makedirs(target_dest_path, exist_ok=True)

    print(f"Getting extract command from: {local_archive_path} to {target_dest_path}")

    extract_cmd = get_extract_archive_cmd(local_archive_path, target_dest_path)
    run_print(extract_cmd)

    if archive_full_suffix == "deb":
        # Special handling for .deb files, which extract to current dir
        # and create multiple files
        data_tar_files: list[pathlib.Path] = list(pathlib.Path(target_dest_path).glob("data.tar.*"))
        if len(data_tar_files) == 0:
            raise FileNotFoundError("No 'data.tar.*' file found after extracting .deb file.")
        if len(data_tar_files) > 1:
            raise FileExistsError("Multiple 'data.tar.*' files found after extracting .deb file.")

        data_tar_file = str(data_tar_files[0])
        print(f"Extracting data archive from .deb: {data_tar_file}")
        extract_cmd = get_extract_archive_cmd(data_tar_file, target_dest_path)

        run_print(extract_cmd)

        # Clean up extracted data.tar.* file
        # os.remove(data_tar_file)

    return target_dest_path


import argparse
from typing import Any


def archive_extract_script(config: dict[str, Any] = {}):
    print('Calling ')

    return download_archive_unpack(
        src_url=config.get('source'),
        dest_dir_path=config.get('target'),
        redownload=config.get('redownload', True),
        flat=config.get('flat', False)
    )


def add_archive_extract_parsing_options(parser: argparse.ArgumentParser):
    parser.add_argument('source', help="Path or URL of the archive to extract")
    parser.add_argument('target', help="Target dir under which the extracted archive should be placed", nargs='?')
    parser.add_argument('-fl', '--flat', action='store_true', help="Instead of creating a subdir for the extracted archive, extract directly to target dir")
    parser.add_argument('-re', '--redownload', action='store_true', help="Redownload even if file exists")


def main(parser: argparse.ArgumentParser | None = None):
    parser_description = "Download and extract archive from URL"

    if (not parser):
        parser = argparse.ArgumentParser(
            description=parser_description
        )
        add_archive_extract_parsing_options(parser)

    args: argparse.Namespace = parser.parse_args()

    config: dict[str, Any] = vars(args)
    archive_extract_script(config)


if __name__ == '__main__':
    sys.exit(main())
