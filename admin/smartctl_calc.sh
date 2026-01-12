#!/bin/env bash

device_path="$1"

# Crucial_CT275MX300SSD1
# https://www.techpowerup.com/ssd-specs/crucial-mx300-275-gb.d79
# Release Jun 2016, TLC

# TBW: 80 TB
Crucial_CT275MX300SSD1="80"
Crucial_CT250MX200SSD1="80"


dev_info_value(){
    key="$1"
    # sudo smartctl -a "$device_path" | grep -Eio "$key\s*:\s*.+" | cut -d ":" -f 2
    sudo smartctl -x "/dev/sde" | grep -Eio "$key\s*:\s*.+" | cut -d ":" -f 2 | xargs
}

DEVICE_MODEL=$(dev_info_value "device model")
SECTOR_BYTES=$(dev_info_value "sector size" | grep -Eo "^[0-9]+")
LBAs_Written=$(sudo smartctl -a "$device_path" | grep -E "Total_LBAs_Written" | grep -Eo "\-\s+[0-9]+" | grep -Eo "[0-9]+")

if [ -z "$SECTOR_BYTES" ] || [ -z "$LBAs_Written" ]; then
    echo "Could not retrieve sector size or LBAs written from smartctl output."
    exit 1
fi

bytes_to_tb() {
    bytes="$1"
    echo "scale=2; $bytes / (1024^4)" | bc
}

get_smart_attr() {
    device_path="$1"
    attr_name="$2"
    column_name="$3"

    smart_output=$(sudo smartctl -A "$device_path")

    table_header_idx=$(echo "$smart_output" | grep -En "ATTRIBUTE_NAME" | cut -d ':' -f 1)

    table_header=$(echo "$smart_output" | head -n "$table_header_idx" | tail -n 1)
    table_content=$(echo "$smart_output" | tail -n +$((table_header_idx + 1)))

    echo "$table_content"

    table_header_norm=$(echo "$table_header" | tr -s ' ' | tr ' ' '\n')
    column_idx=$(echo "$table_header_norm" | grep -Ein "$column_name" | cut -d ":" -f 1)
    column=$(echo "$table_header_norm" | head -n "$column_idx" | tail -n 1)

    table_content_norm=$(echo "$table_content" | tr -s ' ')
    table_selection=$(echo "$table_content_norm" | grep -Ei "$attr_name")

    for line in $table_selection; do
        line_values=$(echo "$line" | tr ' ' '\n')

        attr_name=$(echo "$line_values" | head -n 2 | tail -n 1)

        value=$(echo "$line_values" | head -n "$column_idx" | tail -n 1)
        echo "$attr_name:$column:$value"
    done
    # table_header_line=$(echo "$smart_output" | grep -E "ATTRIBUTE_NAME")

    # table_header_line=$(echo "$smart_output" | grep -E "ATTRIBUTE_NAME")

    # table_header_norm=$(echo "$table_header_line" | tr -s ' ' | tr ' ' '\n')
    # column_num=$(echo "$table_header_norm" | grep -Ein "$column" | cut -d ":" -f 1)

    # table_lines=$(echo "$smart_output" | grep -Ei "$attr_name")

    # table_lines_norm=$(echo "$table_lines" | tr -s ' ' | tr ' ' '\n')

    # column=$(echo "$table_header_norm" | head -n "$column_num" | tail -n 1)
    # value=$(echo "$table_lines_norm" | head -n "$column_num" | tail -n 1)

    # echo "$column:$value"

}

BYTES_WRITTEN=$((SECTOR_BYTES * LBAs_Written))
TB_WRITTEN=$(bytes_to_tb "$BYTES_WRITTEN")

resolved_tbw="${!DEVICE_MODEL}"
resolved_tbw_bytes=$((resolved_tbw * 1024 * 1024 * 1024 * 1024))
percent_written=$(echo "scale=2; ($BYTES_WRITTEN / $resolved_tbw_bytes) * 100" | bc)

echo "DEVICE MODEL: ${DEVICE_MODEL}"
echo "Sector: ${SECTOR_BYTES} bytes"
echo "WRITTEN: ${TB_WRITTEN} TB / ${resolved_tbw} TBW -> ${percent_written} %"
#echo "WRITTEN: ${TB_WRITTEN} TB / ${resolved_tbw} TB"

# Short self-test
# sudo smartctl /dev/sde -t short
# Short self-test probably blocking instead of running in background (default)
# sudo smartctl /dev/sde -t short --captive
# Abort background self-tests
# sudo smartctl /dev/sde -X


health_passed=$(sudo smartctl -H /dev/sde | grep -Ei "result:\s*.+" | cut -d ":" -f 2 | xargs)
echo "HEALTH: ${health_passed}"

get_smart_attr "$device_path" "Percent_Lifetime_Remain" "RAW_VALUE"
# get_smart_attr "$device_path" "Media_Wearout_Indicator" "RAW_VALUE"
# get_smart_attr "$device_path" "Percentage Used" "RAW_VALUE"
# get_smart_attr "$device_path" "Total_LBAs_Written" "RAW_VALUE"