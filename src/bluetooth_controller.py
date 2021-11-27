# encoding-utf-8
'''
Created on 20 mai 2021

@author: Thomas
'''


import BluezyPiVocal
import bluezypi
import logging
import os

TIMEOUT = 1200

if not(os.path.exists('/home/pi/logs/messages')):
    with open('/home/pi/logs/messages', 'w') as f:
        pass

logging.basicConfig(filename='/home/pi/logs/messages', filemode='a',
                    format='%(asctime)s - %(filename)s :: %(lineno)d : %(message)s', level=0)


class BluetoothController(object):
    '''
    classdoc
    '''
    
    def __init__(self):
        '''
        doc
        '''
        logging.info("Démarrage du module bluetooth")
        module_bluezy_pi = bluezypi.BluezyPi()
        module_vocal = BluezyPiVocal.BluezyPiVocal()
        # On démarre le module bluetooth
        try :
            module_bluezy_pi.bluetooth_on()
        except bluezypi.BluezypiError :
            logging.error("Erreur à la mise en service du bluetooth")
            exit()
        else :
            pass
        
        return_init_agent = module_bluezy_pi.init_agent(TIMEOUT)
        
        if return_init_agent == -2:
            module_vocal.PronounceNoConnection()
            module_bluezy_pi.go_to_blocked_mode()
        elif return_init_agent == -1:
            module_vocal.PronounceErrorConnection(module_bluezy_pi.connected_device_name)
        else :
            module_vocal.PronounceConnection(module_bluezy_pi.connected_device_name)

        if module_bluezy_pi.bluetooth_module.expect_disconnection():
            module_vocal.PronounceDisconnection(module_bluezy_pi.connected_device_name)
            module_bluezy_pi.reinit_device_infos()

        module_bluezy_pi.go_to_blocked_mode()
        print("Fin du programme")
        

if __name__ == "__main__":
    BluetoothController()
         
         
        