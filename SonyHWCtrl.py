#!/usr/bin/env python3

"""
A few design choices:
I wanted this thing to work without putting in a mac address if you only have 1 device connected, but that means I need some enumeration.
Pybluez only offers a full scan, which causes audio stutter on my devices. That's why there is the dependency on bluez on dbus.
The downside of this is that you can only control devices you are correctly connected too, but I don't mind that limitation if you don't enter a mac manually.
The whole scanning is bypassed if you enter a mac manually anyway, so that should support controlling devices connected to another audio source.

Copyright (c) Dries007 - 2021
Based on data from https://github.com/Plutoberth/SonyHeadphonesClient
"""

import sys
from dataclasses import dataclass
from typing import List, Union
import socket
import struct
import argparse

import bluetooth  # => pybluez

ap = argparse.ArgumentParser(prog="SonyHWCtrl", description="Control your Sony Headphones from the command line.",
                             epilog="DISCLAIMER: USE AT OWN RISK. THIRD PARTY TOOL. NOT AFFILIATED WITH SONY.")
ap.add_argument("--fov", action="store_true", default=False, help="Enable 'Focus on Voice' mode. Only available if asm >= 2.")
ap.add_argument("--asl", type=int, default=0, help="Set 'Ambient Sound Level'. 0 and 1 are marked as 'noise suppression' in the app. Maximum is 19.")
ap.add_argument("--mac", help="Specify the mac address of the device you want to control. Not required if there is only 1 valid device connected.")
args = ap.parse_args()

# Control point UUID, also used to detect Sony devices that can be controlled.
SONY_UUID = "96cc203e-5068-46ad-b32d-e316f5e069ba"

# Some constants that appear to be missing from (the imports of) some of the bluetooth packages.
RFCOMM_LM = 3
RFCOMM_LM_AUTH = 2
RFCOMM_LM_ENCRYPT = 4

# Makes pycharm happy about socket.setsockopt
BTSocket = Union[socket.socket, bluetooth.BluetoothSocket]


@dataclass
class Device:
    address: str

    _socket: BTSocket = None
    _seq: int = 0

    def __enter__(self) -> 'Device':
        # find_service -> resolve the RFCOMM port number for this UUID
        services = bluetooth.find_service(uuid=SONY_UUID, address=self.address)
        assert len(services) == 1
        service = services[0]
        # basically equivalent to python's socket, but why not use it
        sock: BTSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.setsockopt(bluetooth.SOL_RFCOMM, RFCOMM_LM, RFCOMM_LM_AUTH | RFCOMM_LM_ENCRYPT)
        sock.connect((service["host"], service["port"]))
        # prevent blocking forever
        sock.settimeout(5)
        self._socket = sock
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._socket.close()

    def send_command(self, data: bytes):
        # <START_MARKER>ESCAPE_SPECIALS(<DATA_TYPE><SEQ_NUMBER><BIG ENDIAN 4 BYTE SIZE OF UNESCAPED DATA><DATA><1 BYTE CHECKSUM>)<END_MARKER>
        tmp = bytes([12, self._seq & 0xFF]) + struct.pack(">I", len(data)) + data
        # quite literally a checksum
        tmp += bytes([sum(tmp) & 0xFF])
        self._seq += 1
        # < = > are escaped characters if in message, they are the start & end markers.
        escaped = [62]  # starting marker
        escaped_chars = {
            60: 44,
            61: 45,
            62: 46,
        }
        for byte in tmp:
            if byte in escaped_chars:
                escaped.append(61)
                byte = escaped_chars[byte]
            escaped.append(byte)
        escaped.append(60)  # ending marker
        tmp = bytes(escaped)
        self._socket.send(tmp)
        reply = self._socket.recv(2048)
        assert reply[1] == 0x01   # ACK
        assert reply[-2] == 0x02  # Checksum (hardcoded)


def get_valid_devices() -> List[Device]:
    """
    Get a list of devices, currently connected via the bluez stack, that have the required UUID.
    This uses the D-Bus and requires that the bluez service is running.
    """
    from pydbus import SystemBus, bus

    system_bus: bus.Bus = SystemBus()
    bluez = system_bus.get('org.bluez', '/')
    # It pains me to use CamelCasing in Python, but when in rome...
    # noinspection PyPep8Naming
    ObjectManager = bluez["org.freedesktop.DBus.ObjectManager"]
    # noinspection PyPep8Naming
    ManagedObjects = ObjectManager.GetManagedObjects()

    valid_devices = []
    for handle, properties in ManagedObjects.items():
        if "org.bluez.Device1" not in properties:
            continue
        device1 = properties["org.bluez.Device1"]
        uuids = device1["UUIDs"]
        if SONY_UUID not in uuids:
            continue
        address = device1["Address"]
        valid_devices.append(Device(address))
    return valid_devices


def encode_parameters(asl: int, voice_focus: bool) -> bytes:
    """
    Encode the parameters to control the headset.
    Most of the info from this function was taken from SonyHeadphonesClient.

    :param asl: Ambient Sound Level. -1 = disable. 0 or 1 are 'noise canceling', up to 19 is allowed.
    :param voice_focus: Enable "Focus on voice". Only an option starting at ASL >= 2
    """
    # Some basic input validation, otherwise the headset stops accepting input via RFCOMM
    assert -1 <= asl < 20
    if voice_focus:
        assert asl >= 2

    # Noise cancellation level
    nc_level = 0
    if asl == 1:
        nc_level = 1
    elif asl == 0:
        nc_level = 2

    # Also allow disabling of the sound control all together
    effect = 17
    if asl == -1:
        effect = 0
        asl = 0xFF

    voice = 1 if voice_focus else 0
    return bytes([
        104,        # Set parameter
        2,          # Noise cancelling and ambient sound mode
        effect,     # Options are: 0 off, 1 on, 16 adjustment in progress, 17 adjustment complete.
        1,          # Set noise canceling level
        nc_level,   # Noise canceling level
        1,          # Set ambient sound level
        voice,      # Focus on voice?
        asl         # Ambient sound level
    ])


def main():
    if args.mac:
        # Manually specified mac, not verified.
        device = Device(args.mac)

    else:
        # Smart scan for available headsets with the correct UUID
        valid_devices = get_valid_devices()
        if len(valid_devices) == 0:
            print("No valid devices found. Make sure you are connected.")
            return 1
        elif len(valid_devices) == 1:
            device = valid_devices[0]
        else:
            print("More than 1 valid device is connected. Specify the mac address.")
            return 2

    # encode (and validate) before making connection to avoid annoying headset.
    data = encode_parameters(args.asl, args.fov)

    # open socket & send command
    with device:
        device.send_command(data)


if __name__ == '__main__':
    sys.exit(main())


