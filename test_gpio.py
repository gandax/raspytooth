#!/usr/bin/env python

import RPi.GPIO as GPIO
import os
import time

#n définit le pin de la LED 1
PIN_LED1 = 11
PIN_BP1 = 13

GPIO.setwarnings(False)

#On configure le pin (entree) 
GPIO.setmode(GPIO.BOARD)
GPIO.setup(PIN_LED1, GPIO.OUT)
GPIO.setup(PIN_BP1, GPIO.IN)
state_led = False

for i in range(5):
    GPIO.output(PIN_LED1,state_led)
    state_led = not(state_led)
    GPIO.wait_for_edge(PIN_BP1, GPIO.RISING)

time.sleep(5)
GPIO.cleanup()