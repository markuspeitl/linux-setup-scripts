#! /usr/bin/env python3

from typing import Any
import argparse
from datetime import datetime
import shutil
from os import path
import os
import sys
from typing import Callable


def process_src_target_locations(
    src_dir: str,
    locations_to_copy: list[str],
    target_dir: str,
    process_src_target_fn: Callable,
    *args,
    **kw_args
) -> None:

    print(f"Copying {len(locations_to_copy)} locations from {src_dir} to {target_dir}")

    src_dir = path.realpath(src_dir)
    target_dir = path.realpath(target_dir)

    src_paths = [path.join(src_dir, relative_path) for relative_path in locations_to_copy]
    target_paths = [path.join(target_dir, relative_path) for relative_path in locations_to_copy]

    for src_path, target_path in zip(src_paths, target_paths):

        process_src_target_fn(
            src_path,
            target_path,
            *args,
            **kw_args
        )


def copy_src_target(
    src_path,
    target_path,
    dry_run=False
):
    if (dry_run):
        print(f"Copying fs path at {src_path} --> {target_path}")
        return

    if (not path.exists(src_path)):
        return

    target_dir = path.dirname(target_path)
    if not path.exists(target_dir):
        os.makedirs(target_dir)

    if (path.isdir(src_path)):

        print(f"Copying dir: {src_path} --> {target_path}")
        shutil.copytree(src_path, target_path, dirs_exist_ok=True, symlinks=True)
    else:

        print(f"Copying file: {src_path} --> {target_path}")
        shutil.copy2(src_path, target_path, follow_symlinks=True)
# else:
#   print(f"Src path does not exist: {src_path}")


def copy_locations(
    src_dir: str,
    locations_to_copy: list[str],
    target_dir: str,
    *args,
    **kw_args
) -> None:

    return process_src_target_locations(
        src_dir,
        locations_to_copy,
        target_dir,
        copy_src_target,
        *args,
        **kw_args
    )


def get_src_locations_target_cfg(config: dict[str, Any] = {}):
    src_dir = config.get('src_dir', None)
    target_dir = config.get('target_dir', None)
    backup_name = config.get('backup_name', None)
    backup_relative_paths = config.get('backup_locations', None)
    if (len(src_dir) < 4):
        return
    if (len(target_dir) < 4):
        return
    if (not backup_relative_paths):
        return

    backup_dir_path: str = path.join(target_dir, backup_name)

    backup_subdir = config.get('backup_subdir', None)
    if (backup_subdir):
        backup_dir_path = path.join(backup_dir_path, backup_subdir)

    return src_dir, backup_relative_paths, backup_dir_path


def save_locations(config: dict[str, Any] = {}):

    src_dir, backup_relative_paths, target_dir = get_src_locations_target_cfg(config)
    # print(f"Copying {len(backup_relative_paths)} locations from {backup_dir_path} to {src_dir}")
    copy_locations(src_dir, backup_relative_paths, target_dir, config.get('dry_run', False))


def restore_locations(config: dict[str, Any] = {}):

    src_dir, backup_relative_paths, target_dir = get_src_locations_target_cfg(config)
    # print(f"Copying {len(backup_relative_paths)} locations from {src_dir} to {backup_dir_path}")
    copy_locations(target_dir, backup_relative_paths, src_dir, config.get('dry_run', False))


def save_restore_locations(config: dict[str, Any] = {}):
    if (config.get('restore', None)):
        return restore_locations(config)

    return save_locations(config)


def add_parsing_options(
    parser: argparse.ArgumentParser,
    default_src_dir: str = None,
    default_target_dir: str = None
):

    parser.add_argument('backup_name', help="")
    parser.add_argument('-r', '--restore', action='store_true', help="")
    parser.add_argument('-l', '--backup_locations', '-locations', nargs='+', help="Relative paths from src dir to back up")
    parser.add_argument('-dry', '--dry_run', action='store_true', help="")

    parser.add_argument('-s', '--src_dir', '-src', help="The directory to back up file or dirs from", default=default_src_dir)
    parser.add_argument('-t', '--target_dir', help="", default=default_target_dir)
    parser.add_argument('-bs', '--backup_subdir', help="Select a subdirectory under the 'backup_name'd dir to back up files/dirs to")


def main(parser: argparse.ArgumentParser | None = None):
    parser_description = ""

    if (not parser):
        parser = argparse.ArgumentParser(
            description=parser_description
        )
        add_parsing_options(parser)

    args: argparse.Namespace = parser.parse_args()

    config: dict[str, Any] = vars(args)
    save_restore_locations(config)


if __name__ == '__main__':
    sys.exit(main())
