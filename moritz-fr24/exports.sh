#!/usr/bin/env bash

# Map only the known receiver, never an entire USB bus containing media drives.
export APP_FR24_USB_DEVICE=/dev/null
for usb_device in /sys/bus/usb/devices/*; do
  [[ -r "$usb_device/idVendor" && -r "$usb_device/idProduct" ]] || continue
  [[ "$(cat "$usb_device/idVendor")" == 0bda && "$(cat "$usb_device/idProduct")" == 2838 ]] || continue
  bus_number="$(cat "$usb_device/busnum")"
  device_number="$(cat "$usb_device/devnum")"
  [[ "$bus_number" =~ ^[0-9]+$ && "$device_number" =~ ^[0-9]+$ ]] || continue
  printf -v APP_FR24_USB_DEVICE '/dev/bus/usb/%03d/%03d' "$((10#$bus_number))" "$((10#$device_number))"
  export APP_FR24_USB_DEVICE
  break
done
