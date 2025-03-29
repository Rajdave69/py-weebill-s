import asyncio
from binascii import hexlify

from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any
import struct
import logging
import logging
from binascii import hexlify
from crcmod.predefined import Crc
from bleak import BleakScanner, BleakClient


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def crc16_xmodem(data):
    crc_func = Crc("xmodem")
    crc_func.update(bytes(data))
    return crc_func.crcValue


def to_hex(data):
    return ' '.join(f"{x:02X}" for x in data)


# Magic Len  ???? Inc 01 Cmd Data   CRC
# 243c  0800 1812 01  01 02  000000 6f76

# This includes Magic, Len, ????
COMMAND_PREFIX = [0x24, 0x3c, 0x08, 0x00, 0x18, 0x12]

# Three bytes of zeroes
NO_ARGUMENT = [0x00, 0x00, 0x00]



class Command:
    TILT = 0x01
    PAN = 0x02
    ROLL = 0x03
    GET_SOFTWARE_VERSION = 0x04
    GET_BATTERY_SET_TILT_POS = 0x06
    SET_ROLL_POS = 0x07
    SET_PAN_POS = 0x08
    PRESS_BUTTON = 0x20
    SET_CENTER_POINT = 0x21
    GET_TILT_POS = 0x22
    GET_ROLL_POS = 0x23
    GET_PAN_POS = 0x24
    SET_MODE = 0x27
    GET_CAMERA_BRAND = 0x68
    GET_SERIAL_1 = 0x7c
    GET_SERIAL_2 = 0x7f
    GET_SERIAL_3 = 0x7d
    GET_SERIAL_4 = 0x7e


CAMERAS = {
    0x00: "None",
    0x01: "Canon",
    0x02: "Sony",
    0x03: "Panasonic",
    0x04: "Nikon",
    0x05: "CCS",
    0x06: "Fuji",
    0x07: "Olympus",
    0x0a: "rcam",
    0x0b: "bmpcc",
    0x0c: "Sigma",
    0xe0: "Sony USB"
}

MODES = ["PF", "L", "F", "POV", "GO"]
MODE_IDS = {mode: idx for idx, mode in enumerate(MODES)}

class WeebillS:
    def __init__(self, mac_address: str):
        self.increment = 2
        self.mac_address = mac_address
        self.client = BleakClient(self.mac_address)

        self.characteristic_write_without_response = None
        self.characteristic_notify = None

    async def generate_command(self, command, data: list):
        inc = self.increment % 0xFF
        self.increment += 1

        output_array = COMMAND_PREFIX + [inc, 0x01, command] + data

        # We need to compute a XMODEM CRC-16 from after the end of the length argument to the end of the data argument
        crc_segment = output_array[4:]
        crc = crc16_xmodem(crc_segment)

        # Merging the XMODEM CRC-16 with the array of data
        output = output_array + [crc & 0xFF, crc >> 8]

        logging.info(f"-> cmd=0x{command:02X} data={to_hex(data)} ({to_hex(output)})")

        print(output)
        # format output as hex string
        hex_output = hexlify(bytes(output)).decode()
        print(f"Hex output: {hex_output}")

        return output


    async def send_command(self, data):
        # Send the command to the gimbal
        await self.client.write_gatt_char(self.characteristic_write_without_response, bytes(data))
        logger.info(f"with data: {data}")

    async def connect(self):
        await self.client.connect()
        logger.info(f"Connected: {self.client.is_connected}")
        logger.info(self.client.__dict__)

        # Get the required characteristics
        for service in self.client.services:
            logger.info(f"Service: {service}")
            for char in service.characteristics:
                logger.info(f"Characteristic: {char.uuid} - {char.properties}")
                if "write-without-response" in char.properties:
                    self.characteristic_write_without_response = char.uuid
                    print(f"Characteristic Write Without Response: {char.uuid}")
                if "notify" in char.properties:
                    self.characteristic_notify = char.uuid

        logger.info(f"Write Without Response: {self.characteristic_write_without_response}")
        logger.info(f"Notify: {self.characteristic_notify}")


    async def disconnect(self):
        await self.client.disconnect()
        logger.info(f"Disconnected: {self.client.is_connected}")


    def __exit__(self):
        asyncio.run(self.disconnect())




