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

class BluezyPiError(Exception):
    pass

class BPConnectionError(BluezyPiError):
    pass



class BluezyPi(object):
    '''
    classdocs
    '''
    

    def __init__(self):
        '''
        Constructor
        '''
        self.module_bluetooth = bluetoothctl.Bluetoothctl()
        self.connected_device_mac = ""
        self.connected_device_name = ""
        
        #On récupère la liste des appareils appairés
        self.paired_devices = self.module_bluetooth.get_paired_devices()
        
        #On initialise l'expression régulière
        self.regexp = re.compile('([A-F0-9]{2}:){5}([A-F0-9]{2})')
        
    
    def BluetoothOn(self):
        '''
        Active la fonctionnalité bluetooth en passant par le process RFKILL (blocage soft)
        '''
        #On active le bluetooth via RFKILL
        logging.info("Activation du bluetooth")
        
        commande_on = subprocess.run(['rfkill','unblock', 'bluetooth'], stderr=subprocess.PIPE)
        #Si la sortie d'erreur est non vide, on remonte une exception
        if commande_on.stderr != b'' :
            logging.error(commande_on.stderr)
            raise BluezyPiError
        
        #On vérifie que l'interface bluetooth n'est pas DOWN
        check_hci = subprocess.run(['hciconfig'], stdout=subprocess.PIPE)
        #Si elle est DOWN on essaie de la mettre UP
        if str(check_hci.stdout).find("DOWN") != -1:
            hci_up = subprocess.run(['hciconfig', 'hci0', 'UP'], stderr=subprocess.PIPE)
            #Si on échoue, on remonte une erreur
            if hci_up.stderr is not None:
                logging.error(hci_up.stderr)
                raise BluezyPiError
        
    def BluetoothOff(self):
        '''
        Désactive la fonctionnalité bluetooth en passant par le process RFKILL (blocage soft)
        '''
        logging.info("Désactivation du bluetooth")
        
        #On active le bluetooth via RFKILL
        commande_off = subprocess.run(['rfkill','block bluetooth'], stderr=subprocess.PIPE)
        #Si la sortie d'erreur est non vide, on remonte une exception
        if commande_off.stderr is not None :
            raise BluezyPiError
                           
        #On vérifie que l'interface bluetooth est bien bloquée
        check_off = subprocess.run(['rfkill', '-o', 'TYPE,SOFT'], stdout=subprocess.PIPE)
        #Si ce n'est pas le cas, on lève une erreur
        if str(check_off.stdout).find("bluetooth blocked") == -1:
            raise BluezyPiError
        
    
    def ConnectDevice(self):
        '''
        #On se met en attente de la demande d'autorisation de service
        self.module_bluetooth.process.expect('Authorize service\r\n')        
        #Quand on la reçoit, on transmet l'autorisation
        self.module_bluetooth.process.sendline('yes')
        
        #On se remet de suite en attente de la deuxième demande
        self.module_bluetooth.process.expect('Authorize service\r\n')
        #Quand on la reçoit, on transmet l'autorisation
        self.module_bluetooth.process.sendline('yes')     
        '''
        pass
        
    def InitAgent(self, duree_attente):
        '''
        Initialise un agent de connexion en mode NoInputNoOuput et se met en attente d'une connexion
        '''
        
        logging.info("Initialisation agent bluetooth")
        #On rend l'appareil pariable
        self.module_bluetooth.make_pairable()
        #On vide la sortie
        self._flush_output()
        
        #On rend l'appareil bluetooth visible
        self.module_bluetooth.make_discoverable()        
        #On vide la sortie
        self._flush_output()
        
        #On initialise la commande
        #TODO : gestion de l'option --pin ./home/pi/projet_bluetooth/bluetooth_pin
        process_agent = pexpect.spawn('bt-agent --capability=NoInputNoOutput')
        
        time.sleep(3)
        
        #On se met en attente de la connexion
        try :
            process_agent.expect("Device", timeout = duree_attente)
        #TODO : Traiter le timeout
        except pexpect.TIMEOUT:
            logging("Timeout connexion")
            #On tue le process bt-agent quand on est sur que la connexion s'est faite
            process_agent.close()
            #On retourne en mode non-visible
            self.module_bluetooth.make_undiscoverable()
            #On vide la sortie
            self._flush_output()
            return -2
        else :
            pass
        
        #Quand la connexion se fait, on récupère les infos sur l'appareil qui se connecte
        info_connection = process_agent.readline()
        
        #On parse info connexion pour récupérer l'@MAC ainsi que le nom de l'appareil
        #Le format du retour est :
        #Device: connected_device_name (XX:XX:XX:XX:XX:XX) for UUID 0000YYYYY-0000-1000-8000-00805f9b34fb
        utf8_info_connection = info_connection.decode('UTF-8')
        print(utf8_info_connection)
        match_regexp = self.regexp.search(utf8_info_connection)
        #Après expect "Device", il ne nous reste que ": connected_device_name (XX:XX:XX:XX:XX:XX) for UUID 0000YYYYY-0000-1000-8000-00805f9b34fb"
        prefix = ": "
        tab_info_connection = []
        tab_info_connection.append(utf8_info_connection[(len(prefix)):(match_regexp.span()[0]- 2)])
        tab_info_connection.append(match_regexp.group())
        
        self.connected_device_name = tab_info_connection[0]
        self.connected_device_mac =  tab_info_connection[1]
        
        self.module_bluetooth.id_pexpect = self.connected_device_name
        
        #Si l'appareil ne fait pas partie des appareils appairés, on l'ajoute
        if not(self.CheckIfPaired(self.connected_device_mac)):
            #On attend que l'appareil se soit appairé pour l'approuver
            self.module_bluetooth.process.expect(["Paired: yes"])
            #On vide la sortie
            self._flush_output()
            logging.info(f'{self.connected_device_name} appairé')
            
        
        #On Vérifie la connexion avec le bluetoothctl
        self.module_bluetooth.send(f'info {self.connected_device_mac}')
        try :
            self.module_bluetooth.process.expect("Connected: yes")
            #On vide la sortie
            self._flush_output()
            
        except pexpect.TIMEOUT:
            logging.error(f'Erreur à la connexion de l\'appareil {self.connected_device_name}')
            return -1
        else :
            logging.info(f'{self.connected_device_name} connecté')
        
        
        #On tue le process bt-agent quand on est sûr que la connexion s'est faite
        process_agent.close()
        
        #On retourne en mode non-visible
        self.module_bluetooth.make_undiscoverable()
        #On vide la sortie
        self._flush_output()
        logging.info("end_init_agent")
        return 1
        
    
    def DisconnectDevice(self):
        '''
        Déconnecte l'appareil actuellement connecté
        '''
        if self.module_bluetooth.disconnect(self.connected_device_mac) :
            self.ReinitDeviceInfos()
            logging.info(f'{self.connected_device_name} déconnecté')
            return True
        else:
            logging.error(f'{self.connected_device_name} : erreur à la déconnexion.')
            return False
            
        
       
    def ReinitDeviceInfos(self):
        self.connected_device_mac = ""
        self.connected_device_name = ""
        self.module_bluetooth.id_pexpect = "bluetooth"
    
    
    def GoToBlockedMode(self):
        '''
        Etat nominal lorsqu'il n'y pas de tentative de connexion en cours
        '''  
        self.module_bluetooth.make_unpairable()
        self.module_bluetooth.make_undiscoverable()
        logging.info("Passage en mode déconnecté")        
       
    def CheckIfPaired(self, device_mac):
        '''
        Vérifie si un appareil est déjà appairé
        '''
        for device in self.paired_devices:
            if device.get('mac_address') == device_mac:
                logging.info(f'{device_mac} appairé')
                return True
        return False
        
    def _flush_output(self):
        '''
        Vide la sortie pour ne pas perturber les commandes suivantes
        '''
        self.module_bluetooth.process.expect(pexpect.TIMEOUT, timeout = 2)