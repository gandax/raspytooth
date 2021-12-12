# Based on ReachView code from Egor Fedorov (egor.fedorov@emlid.com)
# Updated for Python 3.6.8 on a Raspberry  Pi


import time
import pexpect
import subprocess
import sys
import logging
import re

logger = logging.getLogger("btctl")


class Bluetoothctl:
    """A wrapper for bluetoothctl utility."""

    def __init__(self):

        command_on = subprocess.run(['rfkill', 'unblock', 'bluetooth'], stderr=subprocess.PIPE)
        # If error output is not empty we raise an error
        if command_on.stderr != b'':
            logging.error(command_on.stderr)
            raise ConnectionError

        # Temporise to let the time to hardware to initialize
        time.sleep(1)

        # We check bluetooth interface not to be DOWN
        check_hci = subprocess.run(['hciconfig'], stdout=subprocess.PIPE)
        # if DOWN we try to put it UP
        if str(check_hci.stdout).find("DOWN") != -1:
            hci_up = subprocess.run(['hciconfig', 'hci0', 'UP'], stderr=subprocess.PIPE)
            # If it fail we raise an error
            if hci_up.stderr != b'':
                logging.error(hci_up.stderr)
                raise ConnectionError

        # Once we checked that bluetooth is on, we launch bt-agent in place of bluetoothctl
        self.process = pexpect.spawnu("bluetoothctl", echo=False)
        # With bt-agent we expect this string
        self.id_pexpect = "bluetooth"
        # ADD TGA
        self.process.logfile = sys.stdout
        self.process_agent = None
        # Initializing regular expression
        self.regexp = re.compile('([A-F0-9]{2}:){5}([A-F0-9]{2})')

    def __del__(self):
        logging.info("Désactivation du bluetooth")
        # Deactivates bluetooth by running rfkill
        command_off = subprocess.run(['rfkill', 'block', 'bluetooth'], stderr=subprocess.PIPE)
        # If error output is not empty we raise an error
        if command_off.stderr != b'':
            raise ConnectionError

        # We check deactivation of bluetooth
        check_off = subprocess.run(['rfkill', '-o', 'TYPE,SOFT'], stdout=subprocess.PIPE)
        # If it's not deactivated we raise an error
        # WARNING : There is 3 " " between bluetooth and blocked
        if str(check_off.stdout).find("bluetooth   blocked") == -1:
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

    def configure_agent(self, waiting_time):
        # Configures a bluetooth-agent in order to initiate connection
        self.process_agent = pexpect.spawn('bt-agent --capability=NoInputNoOutput')
        time.sleep(3)

        # We wait for some connection
        try:
            self.process_agent.expect("Device", timeout=waiting_time)
        except pexpect.TIMEOUT:
            if waiting_time != 0:
                logging.info("Connection Timeout")
                # Get back to undiscoverable
                self.make_undiscoverable()
                # Emptying output
                self._flush_output(self.process_agent)
                return -2
            else:
                # if we are waiting for already paired device connection, no need to process error
                return -3

        else:
            pass

        # When connecting, we retrieve data on connecting device
        connection_infos = self.process_agent.readline()

        # Parsing to get @MAC and device name
        # Output format is :
        # Device: connected_device_name (XX:XX:XX:XX:XX:XX) for UUID 0000YYYYY-0000-1000-8000-00805f9b34fb
        utf8_info_connection = connection_infos.decode('UTF-8')
        # utf8_info_connection = connection_infos
        match_regexp = self.regexp.search(utf8_info_connection)
        # after expect "Device", it remains the following characters ":
        # connected_device_name (XX:XX:XX:XX:XX:XX) for UUID 0000YYYYY-0000-1000-8000-00805f9b34fb"
        prefix = ": "
        tab_info_connection = []
        # Device name
        tab_info_connection.append(utf8_info_connection[(len(prefix)):(match_regexp.span()[0] - 2)])
        # Device MAC
        tab_info_connection.append(match_regexp.group())
        self.id_pexpect = tab_info_connection[0]

        # TODO : Remove the device from paired devices when its fails ==> If raspi has the device on its list but
        # the device not ==> Doesn't work.

        return tab_info_connection

    def close_agent(self):
        # Closes the connection agent
        if self.process_agent is not None:
            self.process_agent.close()
        else:
            raise ValueError

    def expect_disconnection(self):
        """Expect device disconnection"""
        self.process.expect("Connected: no", timeout = None)
        return True

    def _flush_output(self, process_to_flush: pexpect.spawn) -> None:
        '''
        Removing unuses lines to not disturb the following commands
        '''
        process_to_flush.expect(pexpect.TIMEOUT, timeout=2)


def scan_test(bluetooth_controller : Bluetoothctl):
    # Tests the scan function
    bluetooth_controller.start_scan()
    print("Scanning for 10 seconds...")
    for i in range(0, 10):
        print(i)
        time.sleep(1)
    print(bluetooth_controller.get_discoverable_devices())


def visibility_test(bluetooth_controller : Bluetoothctl):
    # Tests the visibility of the device
    print("[#TEST#] Testing discover functions [#TEST#] ")
    # Making the device discoverable for 5 seconds
    bluetooth_controller.make_discoverable()
    input("Waiting...")
    # Making the device not visible
    bluetooth_controller.make_undiscoverable()


def pairability_test(bluetooth_controller: Bluetoothctl, type_of_pairing : bool):
    # Tests the connection to devices
    # type_of_pairing : True ==> Pairability ; False : Non pairability
    print("[#TEST#] Testing pairability [#TEST#] ")
    # We first make the device discoverable
    bluetooth_controller.make_discoverable()
    if not type_of_pairing:
        bluetooth_controller.make_unpairable()
        print("[#TEST#]  Try to connect your device to bluetooth controller during the next 20 seconds. "
              "It must not work. [#TEST#] ")
        try:
            tab_infos = bluetooth_controller.configure_agent(20)
        except pexpect.TIMEOUT:
            print("The connection did not work ==> Ok.")
        bluetooth_controller.close_agent()
    else:
        bluetooth_controller.make_pairable()
        print("[#TEST#] Try to connect your device to bluetooth controllerduring the next 20 seconds."
              "It must work.[#TEST#] ")
        try:
            tab_infos = bluetooth_controller.configure_agent(20)
        except pexpect.TIMEOUT:
            print('No connection seen. Retry.')

        time.sleep(5)
        bluetooth_controller.close_agent()
        print(f'[#TEST#] Paired devices : {bluetooth_controller.get_paired_devices()}[#TEST#] ')
        input("Waiting for approbation...")


def disconnection_test(bluetooth_controller: Bluetoothctl):
    # Tests the disconnection function
    print("[#TEST#] Testing disconnection.[#TEST#] ")
    print(f'[#TEST#] Paired devices : {bluetooth_controller.get_paired_devices()}[#TEST#] ')
    mac_add_disc = input("MAC address of device to disconnect.")
    bl.disconnect(mac_add_disc)


if __name__ == "__main__":

    print("Init bluetooth...")
    bl = Bluetoothctl()
    print("Ready!")

    print("Functions to test :")
    print("1 : scan_test,")
    print("2 : visibility_test,")
    print("3 : pairability_test,")
    print("4 : Non-pairability_test,")
    print("5 : disconnection_test.")
    print("6 : Killing bluetooth test")
    ok_choice = False

    while not ok_choice:
        function_to_test = int(input("Choose the function you want to test : "))
        ok_choice = True
        if function_to_test == 1:
            scan_test(bl)
        elif function_to_test == 2:
            visibility_test(bl)
        elif function_to_test == 3:
            pairability_test(bl,True)
        elif function_to_test == 4:
            pairability_test(bl, False)
        elif function_to_test == 5:
            disconnection_test(bl)
        elif function_to_test == 6:
            pass
        else:
            print("This is not a function.")
            ok_choice = False

    print("[#TEST#] Testing to put off the bluetooth. [#TEST#] ")
    del bl
    print("End of test")



