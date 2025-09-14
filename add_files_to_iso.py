import argparse
import os
import sys
from typing import Any


def transient_mount(
    path: str,
    mount_dir: str
):
    path = os.path.abspath(path)

    if not mount_dir:
        return path

    mount_dir = os.path.abspath(mount_dir)

    if not os.path.exists(mount_dir):
        os.makedirs(mount_dir, exist_ok=True)

    os.system(f"mount -o ro '{path}' '{mount_dir}'")

    return mount_dir


def single_part_iso_mod(source_path, target_path, config: dict[str, Any]):
    mount_root_dir: str = config.get('mount_dir', "/dev/shm/iso_mnt")
    work_dir: str = config.get('work_dir', "/dev/shm/iso_work")

    source_name: str = os.path.basename(source_path)

    source_mount_dir: str = os.path.join(mount_root_dir, source_name)
    transient_mount(source_path, source_mount_dir)

    copy_src_targets: list[str] = config.get('copy_src_targets', [])
    if not copy_src_targets:
        copy_src_targets = []

    files_work_dir: str = source_mount_dir
    if len(copy_src_targets) > 0:
        source_name_no_ext = os.path.splitext(source_name)[1].lower()
        source_work_dir = os.path.join(work_dir, source_name_no_ext)
        os.makedirs(source_work_dir, exist_ok=True)
        os.system(f"cp -rap '{source_mount_dir}/*' '{source_work_dir}/'")

        files_work_dir = source_work_dir

    for copy_src_target in copy_src_targets:
        source_target_parts = copy_src_target.split(':')
        source_copy_path = source_target_parts[0]
        target_copy_path = source_target_parts[1]

        resolved_source_path = os.path.abspath(os.path.expandvars(source_copy_path))
        resolved_target_path = os.path.abspath(os.path.join(files_work_dir, target_copy_path.lstrip('/')))

        if not os.path.exists(resolved_source_path):
            print(f"Source path '{resolved_source_path}' does not exist, skipping")
            continue

        os.makedirs(os.path.dirname(resolved_target_path), exist_ok=True)
        os.system(f"cp -rap '{resolved_source_path}' '{resolved_target_path}'")

    if target_path.lower().endswith('.iso'):
        os.system(f"genisoimage -o '{target_path}' {files_work_dir}")
        return target_path

    if target_path.lower().endswith('.squashfs'):
        os.system(f"mksquashfs '{files_work_dir}' '{target_path}' -comp zstd -Xcompression-level 5 -b 1M -noappend")
        return target_path

    raise Exception(f"Unsupported target path '{target_path}', must end with .iso or .squashfs")

    # os.system(f"mkisofs -o '{target_path}' -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -J -R -V 'Custom ISO' '{files_work_dir}'")


def multi_part_iso_mod(source_path, target_path, inside_img_path, config: dict[str, Any]):
    mount_dir: str = config.get('mount_dir', "/dev/shm/iso_mnt")
    work_dir: str = config.get('work_dir', "/dev/shm/iso_work")

    source_name: str = os.path.basename(source_path)
    source_mount_dir: str = os.path.join(mount_dir, source_name)

    multipart_root_mount_dir = source_mount_dir + "_root"
    transient_mount(source_path, multipart_root_mount_dir)

    source_path = os.path.join(multipart_root_mount_dir, inside_img_path)

    single_part_iso_mod(source_path, target_path, config)


def iso_mod(config: dict[str, Any]):
    source_path: str = config.get('source_path', None)
    target_path: str = config.get('target_path', None)

    multipart_img_path: str | None = config.get('multipart', None)

    # mount_dir: str = config.get('mount_dir', "/dev/shm/iso_mnt")
    # work_dir: str = config.get('work_dir', "/dev/shm/iso_work")

    # source_name: str = os.path.basename(source_path)
    # source_mount_dir: str = os.path.join(mount_dir, source_name)

    if not multipart_img_path:
        return single_part_iso_mod(source_path, target_path, config)

    return multi_part_iso_mod(source_path, target_path, multipart_img_path, config)

    # multipart_root_mount_dir = source_mount_dir + "_root"
    # transient_mount(source_path, multipart_root_mount_dir)

    # source_path = os.path.join(multipart_root_mount_dir, multipart_img_path)
    # transient_mount(source_path, source_mount_dir)

    # if multipart_img_path:
    #     source_path = transient_mount(source_path, iso_mount_dir)


def add_iso_mod_parsing_options(parser: argparse.ArgumentParser):
    # parser.add_argument('-fr', '-oreq', '--force_output_requirements', help="Write requirements to output script even if installed", action='store_true')

    parser.add_argument('source_path', help="Path/url to ISO, .img, .squashfs, dir to put add new files to, not might be copied if installing system from that iso")
    parser.add_argument('target_path', help="Path to write the modified ISO to")
    parser.add_argument('copy_src_targets', nargs='*', help="Pairs of source:target paths to copy from source iso to target iso. Example: 'path/in/host/dir:path/in/iso'")
    parser.add_argument('-mul', '--multipart', help="Image of target system is contained within iso at location. Example 'casper/filesystem.squashfs' for ubuntu iso")
    parser.add_argument('-md', '--mount_dir', help="Mount temporary mounts under this directory", default="/dev/shm/iso_mnt")
    parser.add_argument('-wd', '--work_dir', help="Create temporary files under this directory", default="/dev/shm/iso_work")


def main(parser: argparse.ArgumentParser | None = None):
    parser_description = "Use a .yml file to bootstrap an advanced linux system installation"

    if (not parser):
        parser = argparse.ArgumentParser(
            description=parser_description
        )
        add_iso_mod_parsing_options(parser)

    args: argparse.Namespace = parser.parse_args()

    config: dict[str, Any] = vars(args)
    iso_mod(config)


if __name__ == '__main__':
    sys.exit(main())
