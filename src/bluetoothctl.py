# Based on ReachView code from Egor Fedorov (egor.fedorov@emlid.com)
# Updated for Python 3.6.8 on a Raspberry  Pi


import time
import pexpect
import subprocess
import sys
import logging


logger = logging.getLogger("btctl")


class Bluetoothctl:
    """A wrapper for bluetoothctl utility."""

    def __init__(self):

        command_on = subprocess.run(['rfkill','unblock', 'bluetooth'], stderr=subprocess.PIPE)
        # If error output is not empty we raise an error
        if command_on.stderr != b'' :
            logging.error(command_on.stderr)
            raise ConnectionError

        # We check bluetooth interface not to be DOWN
        check_hci = subprocess.run(['hciconfig'], stdout=subprocess.PIPE)
        # if DOWN we try to put it UP
        if str(check_hci.stdout).find("DOWN") != -1:
            hci_up = subprocess.run(['hciconfig', 'hci0', 'UP'], stderr=subprocess.PIPE)
            # If it fail we raise an error
            if hci_up.stderr is not None:
                logging.error(hci_up.stderr)
                raise ConnectionError

        # Once we checked that bluetooth is on, we launch bt-agent in place of bluetoothctl
        self.process = pexpect.spawnu("bt-agent --capability=NoInputNoOutput", echo=False)
        # With bt-agent we expect this string
        self.id_pexpect = "Default agent requested"
        # ADD TGA
        self.process.logfile = sys.stdout

    def __del__(self):
        logging.info("Désactivation du bluetooth")
        # Deactivates bluetooth by running rfkill
        command_off = subprocess.run(['rfkill', 'block bluetooth'], stderr=subprocess.PIPE)
        # If error output is not empty we raise an error
        if command_off.stderr is not None:
            raise ConnectionError

        # We check deactivation of bluetooth
        check_off = subprocess.run(['rfkill', '-o', 'TYPE,SOFT'], stdout=subprocess.PIPE)
        # If it's not deactivated we raise an error
        if str(check_off.stdout).find("bluetooth blocked") == -1:
            raise ConnectionError

    def send(self, command, pause=0):
        self.process.send(f"{command}\n")
        time.sleep(pause)
        if self.process.expect([f'{self.id_pexpect}', pexpect.EOF]):
            raise Exception(f"failed after {command}")

    def get_output(self, *args, **kwargs):
        """Run a command in bluetoothctl prompt, return output as a list of lines."""
        self.send(*args, **kwargs)
        return self.process.before.split("\r\n")

    def start_scan(self):
        """Start bluetooth scanning process."""
        try:
            self.send("scan on")
        except Exception as e:
            logger.error(e)

    def make_discoverable(self):
        """Make device discoverable."""
        try:
            self.send("discoverable on")
        except Exception as e:
            logger.error(e)

    #Ajout TGA
    def make_undiscoverable(self):
        """Make device undiscoverable."""
        try:
            out = self.get_output("discoverable off")
        except Exception as e:
            logger.error(e)

    #Ajout TGA
    def make_pairable(self):
        """Make device pairable."""
        try:
            out = self.get_output("pairable on")
        except Exception as e:
            logger.error(e)

    #Ajout TGA
    def make_unpairable(self):
        """Make device unpairable."""
        try:
            out = self.get_output("pairable off")
        except Exception as e:
            logger.error(e)

    def parse_device_info(self, info_string):
        """Parse a string corresponding to a device."""
        device = {}
        block_list = ["[\x1b[0;", "removed"]
        if not any(keyword in info_string for keyword in block_list):
            try:
                device_position = info_string.index("Device")
            except ValueError:
                pass
            else:
                if device_position > -1:
                    attribute_list = info_string[device_position:].split(" ", 2)
                    device = {
                        "mac_address": attribute_list[1],
                        "name": attribute_list[2],
                    }
        return device

    def get_available_devices(self):
        """Return a list of tuples of paired and discoverable devices."""
        available_devices = []
        try:
            out = self.get_output("devices")
        except Exception as e:
            logger.error(e)
        else:
            for line in out:
                device = self.parse_device_info(line)
                if device:
                    available_devices.append(device)
        return available_devices

    def get_paired_devices(self):
        """Return a list of tuples of paired devices."""
        paired_devices = []
        try:
            out = self.get_output("paired-devices")
        except Exception as e:
            logger.error(e)
        else:
            for line in out:
                device = self.parse_device_info(line)
                if device:
                    paired_devices.append(device)
        return paired_devices

    def get_discoverable_devices(self):
        """Filter paired devices out of available."""
        available = self.get_available_devices()
        paired = self.get_paired_devices()
        return [d for d in available if d not in paired]

    def get_device_info(self, mac_address):
        """Get device info by mac address."""
        try:
            out = self.get_output(f"info {mac_address}")
        except Exception as e:
            logger.error(e)
            return False
        else:
            return out

    def pair(self, mac_address):
        """Try to pair with a device by mac address."""
        try:
            self.send(f"pair {mac_address}", 4)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["Failed to pair", "Pairing successful", pexpect.EOF]
            )
            return res == 1

    def trust(self, mac_address):
        try:
            self.send(f"trust {mac_address}", 4)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["Failed to trust", "Trusted: yes", pexpect.EOF]
            )
            return res == 1

    def remove(self, mac_address):
        """Remove paired device by mac address, return success of the operation."""
        try:
            self.send(f"remove {mac_address}", 3)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["not available", "Device has been removed", pexpect.EOF]
            )
            return res == 1

    def connect(self, mac_address):
        """Try to connect to a device by mac address."""
        try:
            self.send(f"connect {mac_address}", 2)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["Failed to connect", "Connection successful", pexpect.EOF]
            )
            return res == 1

    def disconnect(self, mac_address):
        """Try to disconnect to a device by mac address."""
        try:
            self.send(f"disconnect {mac_address}", 2)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["Failed to disconnect", "Successful disconnected", pexpect.EOF]
            )
            return res == 1

    def expect_disconnection(self):
        """Expect device disconnection"""
        self.process.expect("Connected: no", timeout = None)
        return True


if __name__ == "__main__":

    print("Init bluetooth...")
    bl = Bluetoothctl()
    print("Ready!")
    bl.start_scan()
    print("Scanning for 10 seconds...")
    for i in range(0, 10):
        print(i)
        time.sleep(1)

    print(bl.get_discoverable_devices())
