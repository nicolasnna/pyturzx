import struct
import time
from typing import Optional

from Crypto.Cipher import DES
from usb.core import USBError, find
from usb.util import (
    ENDPOINT_IN,
    ENDPOINT_OUT,
    dispose_resources,
    endpoint_direction,
    find_descriptor,
)

from utils.logger import logging


class TurZX52Driver:
    VENDOR_ID = 0x1CBE
    PRODUCT_ID = 0x0050
    DES_KEY = b"slv3tuzx"

    CMD_SYNC = 10
    CMD_BRIGHTNESS = 14

    def __init__(self):
        self._device = None

    def connect(self) -> bool:
        dev = find(idVendor=self.VENDOR_ID, idProduct=self.PRODUCT_ID)

        if dev is None:
            logging.warning(f"Device {self.VENDOR_ID}:{self.PRODUCT_ID} not found")
            return False

        logging.info(f"Devices found: {dev}")
        self._device = dev

        return True

    def disconnect(self) -> None:
        if self._device is not None:
            dispose_resources(self._device)

        self._device = None

    def set_brightness(self, level: int):
        if level > 100 or level < 0:
            raise ValueError("Brightness level must be [0-100]")

        converted = int(level / 100 * 102)
        logging.info(
            f"Sending brightness command ({self.CMD_BRIGHTNESS}) with value = {converted}"
        )

        return self._send_command(self.CMD_BRIGHTNESS, bytes([converted]))

    def _send_command(self, cmd_id: int, payload: bytes = b""):
        if self._device is None:
            raise RuntimeError("Device not connected. Call connect() first.")

        packet = self._build_command_packet_header(cmd_id)
        packet[8 : 8 + len(payload)] = payload
        encrypted = self._encrypt_command_packet(packet)
        return self._write_to_device(encrypted)

    def _build_command_packet_header(self, cmd_id: int) -> bytearray:
        packet = bytearray(500)
        packet[0] = cmd_id
        packet[2] = 0x1A
        packet[3] = 0x6D
        timestamp = int(
            (time.time() - time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1)))
            * 1000
        )
        packet[4:8] = struct.pack("<I", timestamp)
        return packet

    def _encrypt_with_des(self, key: bytes, data: bytes) -> bytes:
        cipher = DES.new(key, DES.MODE_CBC, key)
        padded_len = (len(data) + 7) // 8 * 8
        padded_data = data.ljust(padded_len, b"\x00")
        return cipher.encrypt(padded_data)

    def _encrypt_command_packet(self, data: bytearray) -> bytearray:
        cipher = DES.new(self.DES_KEY, DES.MODE_CBC, self.DES_KEY)
        padded_len = (len(data) + 7) // 8 * 8
        padded_data = bytes(data).ljust(padded_len, b"\x00")
        encrypted = cipher.encrypt(padded_data)
        final_packet = bytearray(512)
        final_packet[: len(encrypted)] = encrypted
        final_packet[510] = 161
        final_packet[511] = 26
        return final_packet

    def _write_to_device(self, data: bytearray, timeout: int = 2000) -> Optional[bytes]:
        config = self._device.get_active_configuration()
        interface_num = find_descriptor(config, bInterfaceNumber=0)
        if interface_num is None:
            raise RuntimeError("USB Interface 0 not found")

        endpoint_out = find_descriptor(
            interface_num,
            custom_match=lambda e: (
                endpoint_direction(e.bEndpointAddress) == ENDPOINT_OUT
            ),
        )
        endpoint_in = find_descriptor(
            interface_num,
            custom_match=lambda e: (
                endpoint_direction(e.bEndpointAddress) == ENDPOINT_IN
            ),
        )

        if endpoint_out is None or endpoint_in is None:
            raise RuntimeError("Could not find USB endpoints in Interface 0")

        try:
            endpoint_out.write(data, timeout)
        except USBError as e:
            logging.error(f"USB write error: {e}")
            return None

        try:
            resp = endpoint_in.read(512, timeout)
            self._flush_read(endpoint_in)
            return bytes(resp)
        except USBError as e:
            logging.error(f"USB read error: {e}")
            return None

    def _flush_read(self, endpoint_in, timeout: int = 100) -> None:
        for _ in range(5):
            try:
                endpoint_in.read(512, timeout)
            except USBError:
                break
