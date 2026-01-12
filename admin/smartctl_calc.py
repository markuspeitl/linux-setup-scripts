#!/usr/bin/env python3
import os
import re
import sys
import subprocess


# get values to unpack:
# sudo smartctl -A "/dev/sde" -json | less
# sudo smartctl -H "/dev/sde" -json | less
# sudo smartctl -x "/dev/sde" -json | less
# sudo smartctl -a "/dev/sde" -json | less


def get_cmd(cmd: str):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()

    # print(f"Return code: {process.returncode}")
    # print(stdout.decode().strip())
    # print(stderr.decode().strip())

    # if process.returncode != 0:
    #     print(f"Error executing command: {stderr.decode().strip()}")
    #     sys.exit(1)

    return stdout.decode().strip()


def get_json_cmd(cmd: str):
    stdout = get_cmd(cmd)
    import json
    return json.loads(stdout)


# def get_smart_attrs(device_path: str, attribute_name: str, property: str):
#     data = get_json_cmd(f"sudo smartctl -A \"{device_path}\" -json")
#     attributes = data.get('ata_smart_attributes', {}).get('table', [])

#     out_attrs = {}

#     attr_name_regex = re.compile(attribute_name, re.IGNORECASE)

#     for attr in attributes:
#         if attr_name_regex.match(attr.get('name', '')):
#             attr_name = attr.get('name')
#             out_attrs[attr_name] = {}
#             out_attrs[attr_name][property] = attr.get(property)

#     return out_attrs


def get_smart_attr(device_path: str, attribute_prop: str):
    data = get_json_cmd(f"sudo smartctl -A \"{device_path}\" -json")
    attributes = data.get('ata_smart_attributes', {}).get('table', [])

    attr_prop_parts = attribute_prop.split('.')
    attribute_name = attr_prop_parts[0]
    props = attr_prop_parts[1:]

    for attr in attributes:
        if attribute_name.lower() in attr.get('name', '').lower():
            attr_name = attr.get('name')

            value = attr
            for prop in props:
                value = value.get(prop, {})
            return value

    return None


def get_device_prop(device_path: str, property: str, flag: str = '-x'):

    cmd = f"sudo smartctl {flag} \"{device_path}\" -json"
    # print(f"Executing command: {cmd}")

    data = get_json_cmd(cmd)
    attributes = data
    # attributes = data.get('smartctl', {})

    # print(attributes)

    if '.' not in property:
        return attributes.get(property)

    props = property.split('.')
    value = attributes
    for prop in props:
        value = value.get(prop, {})

    return value

# model_family
# model_name
# serial_number
# firmware_version
# logical_block_size


# sudo smartctl -x /dev/sde -json
#
# sudo smartctl -a /dev/sde -json
# attributes
# sudo smartctl -A /dev/sde -json

device_infos = {
    'Crucial_CT275MX300SSD1': {
        'tbw': 80.0,
        'info': 'https://www.techpowerup.com/ssd-specs/crucial-mx300-275-gb.d79',
        'type': 'TLC',
        'life_remain_map': 'wear',
        # 256M DDR3L dram cache
        # dynamic ~20g slc write cache
        # foundry: tsmc
        'release': 'Jun.2016',
    },
    'Crucial_CT250MX200SSD1': {
        'tbw': 80.0,
        'info': 'https://www.techpowerup.com/ssd-specs/crucial-mx200-250-gb.d84',
        'support': 'https://www.crucial.com/support/ssd-support/mx200-support',
        'type': 'MLC',  # 3000 P/E Cycles
        # Attribute 202 RAW counts percentage of NAND wear consumed, for crucial
        'life_remain_map': 'wear',
        # 512M DDR3 dram cache
        # slc write cache
        # foundry: tsmc
        'release': 'Jan.2015',
    },
    'CT480BX200SSD1': {
        'tbw': 72.0,
        'info': 'https://www.techpowerup.com/ssd-specs/crucial-bx200-480-gb.d100',
        'type': 'TLC',
        'life_remain_map': 'used',
        'release': 2015,
        # 512M DDR3L dram cache
        # ~6G slc write cache, after which throttles to ~64MB/s
    },
    # TBW only useful for guarantee period, which is usually 3 or 5 years
    # for instance both the bx500 (2tb) tlc and qlc versions have a tbw of 720TB
    # but program/erase cycles range from 1.500 - 5000 dending on model and qlc or tlc

    # opt1: https://www.techpowerup.com/ssd-specs/crucial-bx500-2-tb.d961
    # opt2: https://www.techpowerup.com/ssd-specs/crucial-bx500-2-tb.d963
    # opt3: https://www.techpowerup.com/ssd-specs/crucial-bx500-2-tb.d953
    # opt4: https://www.techpowerup.com/ssd-specs/crucial-bx500-2-tb.d95
    # opt5: https://www.techpowerup.com/ssd-specs/crucial-bx500-2-tb.d968
    'CT2000BX500SSD1': {
        # uses Sata3.3 which was defined in 2016
        # there are both TLC and QLC versions of this drive, and micron does not want to clarify which is which and
        # hides any identifying information in smart data

        'tbw': 720.0,
        'info': 'https://www.techpowerup.com/ssd-specs/crucial-bx200-480-gb.d100',
        'type': 'TLC|QLC',
        'life_remain_map': 'wear',
        'release': 2015
    },
    'TS240GSSD220S': {
        # dram: no?
        # slc cache: yes, dynamic?
        'tbw': 80.0,
        # https://www.hardware-corner.net/ssd-database/Transcend-SSD-220S/
        'info': 'https://www.transcend-info.com/Products/No-735',
        # 'type': 'NaN',
        'life_remain_map': 'used',
        'type': 'TLC',
    },
    'Samsung SSD 850 EVO 250GB': {
        'tbw': 75.0,
        'info': 'https://www.techpowerup.com/ssd-specs/samsung-850-evo-250-gb.d29',
        'type': 'TLC',
        'life_remain_map': 'used',
        'release': 'Dez.2014',
        # 512MB DDR2 dram cache
        # 7000 P/E Cycles
    }
}

if (not sys.argv or len(sys.argv) <= 1):
    print(f"Usage: {os.path.basename(__file__)} <device_path>")
    sys.exit(1)


script_dir = os.path.dirname(os.path.abspath(__file__))
md_file_path = os.path.join(script_dir, 'smartctl_device_infos.md')


def print_write(line: str):
    with open(md_file_path, 'a+') as f:
        f.write(line + '\n')

    print(line)


# prop name needs to be exact
def get_print_device_prop(device_path: str, property: str, template="- {property}: **{value}**", flag: str = '-x'):

    try:
        value = get_device_prop(device_path, property, flag)

        print_line = template.format(property=property.replace('_', ' ').title(), value=value)
        print_write(print_line)
        return value

    except Exception as e:
        print_write(f"- {property}: **NaN**")
        return "NaN"


def estimate_tb_written(device_path: str, tbw: float | str = 'NaN'):

    total_lbas = get_smart_attr(device_path, 'lbas_written.raw.value')

    if total_lbas:
        try:
            total_lbas_num = int(total_lbas)
            total_bytes_written = total_lbas_num * int(logical_block_size)
            total_tb_written = float(total_bytes_written) / (1024 ** 4)

            if tbw and tbw > 0:
                percent_used = (total_tb_written / tbw) * 100.0

        except Exception as e:
            total_tb_written = "NaN"
            percent_used = "NaN"
    else:

        for cell_type in ['qlc', 'mlc', 'tlc', 'slc']:
            cell_pageblock_writes = get_smart_attr(device_path, f'{cell_type}_writes_32M.raw.value')
            if (cell_pageblock_writes):
                try:
                    total_bytes_written = cell_pageblock_writes * 32 * 1024 * 1024
                    total_tb_written = float(total_bytes_written) / (1024 ** 4)

                    if tbw and tbw > 0:
                        percent_used = (total_tb_written / tbw) * 100.0

                except Exception as e:
                    total_tb_written = "NaN"
                    percent_used = "NaN"

                break

    total_tb_written_str = f"{total_tb_written:.2f}" if isinstance(total_tb_written, float) else total_tb_written
    percent_used = f"{percent_used:.2f}" if isinstance(percent_used, float) else percent_used

    print_write(f"- Total Bytes Written: **{total_tb_written_str} TB / {tbw} TBW** --> **{percent_used}%**")


def estimate_remaining_life(device_path: str, life_remain_map: str = 'used'):
    # percent_lifetime_remain = get_smart_attr(device_path, 'Percent_Lifetime_Remain.raw.value')
    percent_lifetime_remain = get_smart_attr(device_path, 'lifetime.raw.value')
    if percent_lifetime_remain is None:
        return

    if life_remain_map == 'wear':
        print_write(f"- Percent Lifetime Remaining: **{str(100.0 - percent_lifetime_remain)}%**")
        print_write(f"- Percent Wear Accumulated: **{str(percent_lifetime_remain)}%**")
    else:
        print_write(f"- Percent Lifetime Remaining: **{str(percent_lifetime_remain)}%**")
        print_write(f"- Percent Wear Accumulated: **{str(100 - percent_lifetime_remain)}%**")


device_path = sys.argv[1]

# device_path = '/dev/sde'  # Change this to the appropriate device path


serial_number = get_print_device_prop(device_path, 'serial_number',
                                      template="## SN: **{value}**")
model_name = get_print_device_prop(device_path, 'model_name')
firmware_version = get_print_device_prop(device_path, 'firmware_version')
logical_block_size = get_print_device_prop(device_path, 'logical_block_size')

tbw = 'NaN'
info_page = None
life_remain_map = 'used'
cell_type = None
if model_name in device_infos:
    tbw = device_infos[model_name].get('tbw', 'NaN')
    info_page = device_infos[model_name].get('info', None)
    life_remain_map = device_infos[model_name]['life_remain_map']
    cell_type = device_infos[model_name].get('type', None)


estimate_tb_written(device_path, tbw)
estimate_remaining_life(device_path, life_remain_map)

if cell_type:
    print_write(f"- NAND Cell Type: **{cell_type}**")

# print(f"TBW Rating: {tbw} TB")
# print(f"Spec Write Percentage Used: {percent_used:.2f}%")

read_errors = get_smart_attr(device_path, 'read_error_rate.raw.value')
write_errors = get_smart_attr(device_path, 'write_error_rate.raw.value')
print_write(f"- Read / Write Errors: **{read_errors} / {write_errors}**")

power_on_hours = get_smart_attr(device_path, 'on_hours.raw.value')
print_write(f"- Running for: {str(power_on_hours)} hours")

get_device_prop(device_path, 'smart_status.passed', '-H')
print_write("- SMART Status: **PASSED**" if get_device_prop(device_path, 'smart_status.passed', '-H') else "SMART Status: **FAILED**")

print_write("")

# if info_page:
#     print_write(f"More Info: {info_page}")

print("To see device infos run:")
print(f"sudo smartctl -A \"{device_path}\"")
print(f"sudo smartctl -x \"{device_path}\"")
print(f"sudo smartctl -a \"{device_path}\"")
