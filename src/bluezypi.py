#encoding-utf-8
'''
Created on 13 mai 2021

@author: Thomas
'''

import bluetoothctl
import subprocess
import pexpect
import time
import re
import logging
import os

if not(os.path.exists('/home/pi/logs/messages')):
    with open('/home/pi/logs/messages', 'w') as f:
        pass
    
logging.basicConfig(filename='/home/pi/logs/messages', filemode='a',format='%(asctime)s - %(filename)s :: %(lineno)d : %(message)s', level=0)

WAITING_TIME = 45

class BluezypiError(Exception):
    pass


class BpConnectionError(BluezypiError):
    pass


class BluezyPi(object):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.bluetooth_module = bluetoothctl.Bluetoothctl()
        self.connected_device_mac = ""
        self.connected_device_name = ""
        
        # Getting paired device list
        self.paired_devices = self.bluetooth_module.get_paired_devices()
        
        # Initializing regular expression
        self.regexp = re.compile('([A-F0-9]{2}:){5}([A-F0-9]{2})')

    def __del__(self):
        # At the end, we disconnect the currently connected device and kill bluetooth
        self.disconnect_device()
        del self.bluetooth_module

    def connect_device(self, new_device: bool) -> int:
        '''
        waiting time
        '''

        if new_device:
            # If it's an unregisterd device connection we make device pairable
            self.bluetooth_module.make_pairable()
            # Flushing output of agent
            self._flush_output()

            # Making device discoverable
            self.bluetooth_module.make_discoverable()
            # Flushing output of agent
            self._flush_output()
            # Initializing command
            # TODO : gestion de l'option --pin ./home/pi/projet_bluetooth/bluetooth_pin ==> Fichier contenant les codes
            time.sleep(3)

            # If it's new device we limit the connection time
            global WAITING_TIME
            waiting_time = WAITING_TIME
        else:
            # If the method is not used for new device connection we permit unlimited timeout
            waiting_time = 0

        # We wait for some connection
        try:
            self.bluetooth_module.process.expect("Device", timeout=waiting_time)
        except pexpect.TIMEOUT:
            if not new_device:
                logging.info("Connection Timeout")
                # Get back to undiscoverable
                self.bluetooth_module.make_undiscoverable()
                # Emptying output
                self._flush_output()
                return -2
            else:
                # if we are waiting for already paired device connection, no need to process error
                return -3

        else:
            pass

        # When connecting, we retrieve data on connecting device
        connection_infos = self.bluetooth_module.process.readline()

        # Parsing to get @MAC and device name
        # Output format is :
        # Device: connected_device_name (XX:XX:XX:XX:XX:XX) for UUID 0000YYYYY-0000-1000-8000-00805f9b34fb
        utf8_info_connection = connection_infos.decode('UTF-8')
        match_regexp = self.regexp.search(utf8_info_connection)
        # after expect "Device", it remains the following characters ":
        # connected_device_name (XX:XX:XX:XX:XX:XX) for UUID 0000YYYYY-0000-1000-8000-00805f9b34fb"
        prefix = ": "
        tab_info_connection = []
        tab_info_connection.append(utf8_info_connection[(len(prefix)):(match_regexp.span()[0] - 2)])
        tab_info_connection.append(match_regexp.group())

        self.connected_device_name = tab_info_connection[0]
        self.connected_device_mac = tab_info_connection[1]

        self.bluetooth_module.id_pexpect = self.connected_device_name

        # If device is not in paired devices list we add it
        # TODO : Send notification when device's added
        if not (self.check_if_paired(self.connected_device_mac)):
            if not new_device:
                # Waiting for pairing to approve device
                self.bluetooth_module.process.expect(["Paired: yes"])
                # Removing unused lines
                self._flush_output()
                logging.info(f'{self.connected_device_name} paired')
            else:
                # Raise an error if an unregisterd device is connecting automatically
                logging.error(f'The unregistered device {self.connected_device_name} is trying to connect. Abortion.')
                del self.bluetooth_module
                raise ConnectionError

        # Check connection by asking the info of the device to the bluetooth module
        self.bluetooth_module.send(f'info {self.connected_device_mac}')
        try:
            self.bluetooth_module.process.expect("Connected: yes")
            # Removing unused lines
            self._flush_output()

        except pexpect.TIMEOUT:
            logging.error(f'Error with {self.connected_device_name} device connexion')
            return -1
        else:
            logging.info(f'{self.connected_device_name} connected')

        # We kill the agent when the connection is operational
        self.bluetooth_module.process.close()

        # Get back to undiscoverable mode
        self.bluetooth_module.make_undiscoverable()
        # Removing nused lines
        self._flush_output()
        logging.info("end_init_agent")
        return 1

    def disconnect_device(self) -> bool:
        '''
        Disconnect currently connected device
        '''
        if self.bluetooth_module.disconnect(self.connected_device_mac):
            self.reinit_device_infos()
            logging.info(f'{self.connected_device_name} disconnected')
            return True
        else:
            logging.error(f'{self.connected_device_name} : error during disconnection')
            return False

    def reinit_device_infos(self):
        self.connected_device_mac = ""
        self.connected_device_name = ""
        self.bluetooth_module.id_pexpect = "bluetooth"

    def go_to_blocked_mode(self) -> None:
        '''
        Nominal state when there's no connection
        '''  
        self.bluetooth_module.make_unpairable()
        self.bluetooth_module.make_undiscoverable()
        logging.info("Going to blocked mode")
       
    def check_if_paired(self, device_mac) -> bool:
        '''
        Check if device's already paired
        '''
        for device in self.paired_devices:
            if device.get('mac_address') == device_mac:
                logging.info(f'{device_mac} already paired')
                return True
        return False

    def _flush_output(self) -> None:
        '''
        Removing unuses lines to not disturb the following commands
        '''
        self.bluetooth_module.process.expect(pexpect.TIMEOUT, timeout=2)
