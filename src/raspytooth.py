#!/usr/bin/env python

import BluezyPiVocal
import bluezypi
import logging
import os
import RPi.GPIO as GPIO
import threading
import time

TIMEOUT = 1200

if not(os.path.exists('/home/pi/logs/messages')):
    with open('/home/pi/logs/messages', 'w') as f:
        pass

logging.basicConfig(filename='/home/pi/logs/messages', filemode='a',
                    format='%(asctime)s - %(filename)s :: %(lineno)d : %(message)s', level=0)


# Defining the pins for the different components
PIN_LED_ON = 11
PIN_LED_BLUETOOTH = 32
PIN_PB_TOGGLE_ON_OFF = 13
PIN_PB_PAIR_DISCONNECT = 16

# Initializing hardware
GPIO.setup(PIN_LED_ON, GPIO.OUT)
PIN_PWM = GPIO.PWM(PIN_LED_BLUETOOTH, 0)
PIN_PWM.start(0)
GPIO.setup(PIN_PB_TOGGLE_ON_OFF, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_PB_PAIR_DISCONNECT, GPIO.IN)
GPIO.add_event_detect(PIN_PB_PAIR_DISCONNECT, GPIO.RISING)
END_PROGRAM = False


# Defining the callback function
def watch_off_switching(end_sem: threading.Semaphore, bluetooth_module: bluezypi.BluezyPi):
    # Accessing to global variable
    global END_PROGRAM
    # Watches the evolution of the on off switch position
    while not END_PROGRAM:
        if GPIO.input(PIN_PB_TOGGLE_ON_OFF) == 0:
            # We communicate to the other threads to stop
            END_PROGRAM = True

    # We wait for the other threads to finish there are two thread to terminate
    end_sem.acquire(blocking=True)
    end_sem.acquire(blocking=True)

    # Once it's finished we switch off the bluetooth
    del bluetooth_module
    # Ending program


def wait_for_connection(bluetooth_module: bluezypi.BluezyPi, personal_sem: threading.Semaphore,
                        other_thread_sem: threading.Semaphore, ending_sem: threading.Semaphore):
    # Watch the output of the bluetooth process to determine if there's a connection
    event = False
    while not event or can_still_connect or END_PROGRAM:
        connection = bluetooth_module.connect_device(new_device=False)
        if connection == 1:
            # TODO : Stop new connection process when connection is made
            event = True
        # Trying to acquire semaphore. If already released it means that something happened in the other thread
        can_still_connect = not(other_thread_sem.acquire(blocking=True, timeout=0.0))

    # When loop is finished, we determine what ended it
    if not can_still_connect:
        # In this case, it means that the other thread get a connection
        logging.info("A pairing procedure has been launched, the known device connection watch has ended.")
    elif event:
        # In this case, the current thread get a connection, we tell this to the other thread
        logging.info("Known device connection.")
        # We release the semaphore in order to tell the other thread that something happended
        personal_sem.release()

    # We need to release end semaphore when this thread ends because it won't end if we do not
    # (the ending thread will wait indefinitely to have the semaphore released)
    ending_sem.release()


def wait_for_new_connect_or_disconnect(bluetooth_module: bluezypi.BluezyPi, personal_sem: threading.Semaphore,
                                       other_thread_sem: threading.Semaphore, ending_sem: threading.Semaphore,
                                       blinking_thread: threading.Thread, connection_ended_sem: threading.Semaphore):
    # Wait for the new connection button to be pressed in order to initiate pairing
    event = False
    can_still_connect = True

    while not event or can_still_connect:
        event = GPIO.event_detected(PIN_PB_PAIR_DISCONNECT)
        can_still_connect = not(other_thread_sem.acquire(blocking=True, timeout=0.0))

    if not can_still_connect:
        # In this case, it means that the other thread get a connection
        logging.info("A known device has been connected, it means that we must disconnect "
                     "it and wait for new connection.")
    elif event:
        # In this case, the current thread get a connection
        logging.info("Pairing procedure launched.")
        # We release the semaphore in order to tell the other thread that something happended
        personal_sem.release()

    if END_PROGRAM:
        # We release ending semaphore
        ending_sem.release()
    else:
        # If we didn't end the loop because of switching off then we launch connection
        blinking_thread.start()
        connection = bluetooth_module.connect_device(new_device=True)
        # Once connection is done we release the semaphore to end blinking
        connection_ended_sem.release()


def blinking_led(end_connection_sem: threading.Semaphore):
    # Blinks a led while new pairing is occurring
    global PIN_PWM
    dc = 5
    increase = True
    while not(end_connection_sem.acquire()):
        PIN_PWM.ChangeDutyCycle(dc)
        time.sleep(0.1)
        if increase and dc < 100:
            dc += 5
        elif dc == 100:
            increase = False
        elif dc == 0:
            increase = True
        else:
            dc -= 5


# Going to BluetoothON state
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

# Initializing threading objects
sem_known_device_connection = threading.Semaphore()
sem_new_connection = threading.Semaphore()
sem_end = threading.Semaphore()
sem_end_connection = threading.Semaphore()
thread_blinking = threading.Thread(target=blinking_led(), args=(sem_end_connection,))
thread_known_device_connection = threading.Thread(target=wait_for_connection,
                                                  args=(bluezy_pi_module, sem_new_connection,
                                                        sem_known_device_connection, sem_end,))
thread_new_connection = threading.Thread(target=wait_for_new_connect_or_disconnect,
                                         args=(bluezy_pi_module, sem_known_device_connection, sem_new_connection,
                                               sem_end, thread_blinking, sem_end_connection))
thread_ending = threading.Thread(target=watch_off_switching, args=(sem_end,))


thread_ending.start()

# Todo : Get connection from already paired device or button pressing for new device connection
thread_known_device_connection.start()

while not END_PROGRAM:
    thread_new_connection.start()
    thread_known_device_connection.join()
    thread_new_connection.join()

logging.info("Ending raspytooth.")
