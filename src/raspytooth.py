#!/usr/bin/env python

import BluezyPiVocal
import bluezypi
import logging
import os
import RPi.GPIO as GPIO

TIMEOUT = 1200

if not(os.path.exists('/home/pi/logs/messages')):
    with open('/home/pi/logs/messages', 'w') as f:
        pass

logging.basicConfig(filename='/home/pi/logs/messages', filemode='a',
                    format='%(asctime)s - %(filename)s :: %(lineno)d : %(message)s', level=0)

# Defining the pins for the different components
PIN_LED_ON = 11
PIN_LED_BLUETOOTH = 15
PIN_BP_TOGGLE_ON_OFF = 13

# We wait for the On toggling
GPIO.wait_for_edge(PIN_BP_TOGGLE_ON_OFF, GPIO.RISING)

# Initializing the objects
vocal_module = BluezyPiVocal.BluezyPiVocal()

# When it's on, we start the bluetooth
logging.info("Starting bluetooth module")
try:
    bluezy_pi_module = bluezypi.BluezyPi()
except bluezypi.BluezypiError:
    logging.error("Error when starting bluetooth service. End of program.")
    exit()
else:
    pass

# Todo : Expect connection from already paired device or button pressing for new device connection

