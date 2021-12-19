#encoding-utf-8
'''
Created on 13 mai 2021

@author: Thomas
'''

import bluetoothctl
import time
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
    """

    """

    def __init__(self):
        '''
        Constructor
        '''
        self.bluetooth_module = bluetoothctl.Bluetoothctl()
        self.connected_device_mac = ""
        self.connected_device_name = ""
        
        # Getting paired device list
        self.paired_devices = self.bluetooth_module.get_paired_devices()

    def __del__(self):
        # At the end, we disconnect the currently connected device and kill bluetooth
        self.disconnect_device()
        del self.bluetooth_module

    def connect_device(self, new_device: bool) -> int:
        '''
        waiting time
        '''

        if new_device:
            # If it's an unregistered device connection we make device pairable
            self.bluetooth_module.make_pairable()
            print("Made pairable")
            # Making device discoverable
            self.bluetooth_module.make_discoverable()
            print("Made discoverable")
            # Initializing command
            # TODO : gestion de l'option --pin ./home/pi/projet_bluetooth/bluetooth_pin ==> Fichier contenant les codes
            # If it's new device we limit the connection time
            global WAITING_TIME
            waiting_time = WAITING_TIME
        else:
            # If the method is not used for new device connection we permit unlimited timeout
            waiting_time = -1
        try:
            print("Waiting for device")
            tab_info_connection = self.bluetooth_module.configure_agent(waiting_time)
        except ConnectionError:
            logging.error("Error during device connection")
            raise

        print("Device found")
        self.connected_device_name = tab_info_connection[0]
        self.connected_device_mac = tab_info_connection[1]

        # If device is not in paired devices list we verify that he has been added
        # TODO : Send notification when device's added
        if not (self.check_if_paired(self.connected_device_mac)):
            try:
                print("Checks pairing")
                paired = self.bluetooth_module.check_pairing(new_device=(waiting_time > 0),
                                                             connected_device_name=self.connected_device_name)
            except ConnectionError:
                logging.error("Pairing error. Module stopped.")
                del self.bluetooth_module
                raise

            if not paired:
                logging.error("Pairing error. Module stopped.")
                del self.bluetooth_module
                raise ConnectionError

        print("Checks connection")
        connected = self.bluetooth_module.check_connection(self.connected_device_mac)
        if connected:
            print("[#TEST#]Connected[#TEST#]")
            logging.info(f'{self.connected_device_name} connected')
        else:
            print("[#TEST#]Not connected[#TEST#]")
            logging.error(f'Error with {self.connected_device_name} device connexion')

        # We kill the agent when the connection is operational
        time.sleep(10)
        print("Killing agent")
        self.bluetooth_module.close_agent()

        # Get back to undiscoverable mode
        self.bluetooth_module.make_undiscoverable()
        # Removing nused lines
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


if __name__ == "__main__":
    print("Initialing bluezyPi tests")
    bluezy_pi = BluezyPi()

    print("Functions to test :")
    print("1 : connect new device,")
    print("2 : connect already known device,")
    print("3 : disconnect device,")
    ok_choice = False

    while not ok_choice:
        function_to_test = int(input("Choose the function you want to test : "))
        ok_choice = True
        if function_to_test == 1:
            if bluezy_pi.connect_device(new_device=True):
                print("Test OK")
            else:
                print("Test KO")
        elif function_to_test == 2:
            bluezy_pi.connect_device(new_device=False)
        elif function_to_test == 3:
            input("Enter the @MAC of the device to disconnect.")
            bluezy_pi.disconnect_device()
        else:
            print("This is not a function.")
            ok_choice = False

    del bluezy_pi