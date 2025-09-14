#! /usr/bin/env python3

from typing import Any
import argparse
from datetime import datetime
import shutil
from os import path
import os
import sys
from typing import Callable
from generic_backup_restore import save_restore_locations as save_restore_locations_generic

# Locations from
# https://github.com/paju1986/PlasmaConfSaver/blob/master/com.pajuelo.plasmaConfSaver/contents/scripts/save.sh
plasma_config_locations = [
    # scrot
    # plasma config files
    "plasma-org.kde.plasma.desktop-appletsrc",
    "plasmarc",
    "plasmashellrc",
    "kdeglobals",
    # kwin
    "kwinrc",
    "kwinrulesrc",
    # latte-dock config files
    "lattedockrc",
    "latte",
    # dolphin config
    "dolphinrc",
    # config session desktop
    "ksmserverrc",
    # config input devices
    "kcminputrc",
    # shortcuts
    "kglobalshortcutsrc",
    # klipper config
    "klipperrc",
    # konsole config
    "konsolerc",
    # kscreenlocker config
    "kscreenlockerrc",
    # krunner config
    "krunnerrc",
    # kvantum theme
    "Kvantum",
    # autostart
    "autostart",
    # fonts dpi
    "kcmfonts",
]

plasma_data_paths = [
    # plasma themes and widgets
    "plasma",
    # wallpapers
    "wallpapers",
    # icons
    "icons",
    # color-schemes
    "color-schemes",
    # fonts
    "kfontinst",
]


def process_src_target_locations(
    src_dir: str,
    locations_to_copy: list[str],
    target_dir: str,
    process_src_target_fn: Callable
) -> None:

    src_dir = path.realpath(src_dir)
    target_dir = path.realpath(target_dir)

    src_paths = [path.join(src_dir, relative_path) for relative_path in locations_to_copy]
    target_paths = [path.join(target_dir, relative_path) for relative_path in locations_to_copy]

    for src_path, target_path in zip(src_paths, target_paths):
        if (path.exists(src_path)):

            process_src_target_fn(
                src_path,
                target_path
            )


def get_most_recent_directory(directory_path):
    most_recent_dir = None
    most_recent_time = 0

    for entry in os.listdir(directory_path):
        entry_path = os.path.join(directory_path, entry)

        if os.path.isdir(entry_path):
            entry_mtime = os.path.getmtime(entry_path)

            if entry_mtime > most_recent_time:
                most_recent_time = entry_mtime
                most_recent_dir = entry_path

    return most_recent_dir


def save_restore_locations(config: dict[str, Any] = {}):

    restore = config.get('restore', False)
    backup_dir = config.get('backup_dir', None)
    backup_name = config.get('backup_name', None)

    if not restore and not backup_name:
        backup_name = datetime.now().strftime('%d-%m-%Y__%Hh-%M-%Ssec')

    if (not backup_name and restore):
        most_recent_backup_path = get_most_recent_directory(backup_dir)
        backup_name = path.basename(most_recent_backup_path)
        print(f"Found most recent backup at {most_recent_backup_path} with name {backup_name}")

    if not backup_name:
        print("Empty backup name at restore")
        return

    save_restore_locations_generic({
        'backup_name': backup_name,
        'restore': restore,
        'src_dir': config.get('active_config_dir', None),
        'target_dir': backup_dir,
        'backup_subdir': 'config',
        'backup_locations': plasma_config_locations,
        'dry_run': config.get('dry_run', None)
    })

    """save_restore_locations_generic({
        'backup_name': backup_name,
        'restore': restore,
        'src_dir': config.get('active_data_dir', None),
        'target_dir': backup_dir,
        'backup_subdir': 'data',
        'backup_locations':  plasma_data_paths,
        'dry_run': config.get('dry_run', None)
    })"""

    print(f"Created BACKUP at '{backup_dir}/{backup_name}'")

    if (restore):

        print("Restarting KDE plasma ... ")
        os.system("qdbus org.kde.KWin /KWin reconfigure")
        os.system("konsole -e kquitapp5 plasmashell && kstart5 plasmashell --windowclass plasmashell --window Desktop")


def add_parsing_options(parser: argparse.ArgumentParser):

    plasma_config_path = path.expanduser("~/.config")
    target_config_path = path.expanduser("~/.kde_desktop_backup")
    plasma_data_path = "/usr/share/plasma/"

    parser.add_argument('backup_name', nargs='?', help="")
    parser.add_argument('-r', '--restore', action='store_true', help="")
    parser.add_argument('-cd', '--active_config_dir', help="", default=plasma_config_path)
    parser.add_argument('-dd', '--active_data_dir', help="", default=plasma_data_path)
    parser.add_argument('-bd', '--backup_dir', help="", default=target_config_path)
    parser.add_argument('-dry', '--dry_run', action='store_true', help="")


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


# mkdir "plasmaConfSaver/"
# rm - Rf
# mkdir
# screenshot
# spectacle - b - n - o
# if latte-dock was running when we saved then create a flag file for running it on restore
"""if pgrep -x latte-dock > /dev/null
then
    touch 
fi"""

"""
def save_locations(config: dict[str, Any] = {}):

    active_config_path = config.get('active_config_dir', None)
    active_data_path = config.get('active_data_dir', None)
    backup_base_dir_path = config.get('backup_dir', None)
    backup_name = config.get('backup_name', None)

    if (len(active_config_path) < 4):
        return
    if (len(active_data_path) < 4):
        return
    if (len(backup_base_dir_path) < 4):
        return

    if not backup_name:
        backup_name = datetime.now().strftime('%d-%m-%Y__%Hh-%Mm-%Ssec')

    backup_dir_path: str = path.join(backup_base_dir_path, backup_name)
    backup_config_path: str = path.join(backup_dir_path, 'config')
    backup_data_path: str = path.join(backup_dir_path, 'data')

    print(f"Copying locations from {active_config_path} to {backup_config_path}")
    copy_locations(active_config_path, plasma_config_locations, backup_config_path)

    print(f"Copying locations from {active_data_path} to {backup_data_path}")
    copy_locations(active_data_path, plasma_data_paths, backup_data_path)


def restore_locations(config: dict[str, Any] = {}):

    active_config_path = config.get('active_config_dir', None)
    active_data_path = config.get('active_data_dir', None)
    backup_base_dir_path = config.get('backup_dir', None)
    backup_name = config.get('backup_name', None)

    if (len(active_config_path) < 4):
        return
    if (len(active_data_path) < 4):
        return
    if (len(backup_base_dir_path) < 4):
        return

    backup_dir_path: str = path.join(backup_base_dir_path, backup_name)
    backup_config_path: str = path.join(backup_dir_path, 'config')
    backup_data_path: str = path.join(backup_dir_path, 'data')

    print(f"Copying locations from {backup_config_path} to {active_config_path}")
    copy_locations(backup_config_path, plasma_config_locations, active_config_path)

    print(f"Copying locations from {backup_data_path} to {active_data_path}")
    copy_locations(backup_data_path, plasma_data_paths, active_data_path)
"""


"""def copy_src_target(
    src_path,
    target_path
):
    target_dir = path.dirname(target_path)
    if not path.exists(target_dir):
        os.makedirs(target_dir)

    if (path.isdir(src_path)):

        print(f"Copying dir: {src_path} --> {target_path}")
        # shutil.copytree(src_path, target_path)
    else:

        print(f"Copying file: {src_path} --> {target_path}")
        # shutil.copy2(src_path, target_path)
# else:
#   print(f"Src path does not exist: {src_path}")


def copy_locations(
    src_dir: str,
    locations_to_copy: list[str],
    target_dir: str
) -> None:

    return process_src_target_locations(
        src_dir,
        locations_to_copy,
        target_dir,
        copy_src_target
    )
"""
