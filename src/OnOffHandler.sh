# Defining pin numbers
pin_on_off=2
pin_led_on_off=0
scan_time=5

# Defining pin modes
gpio mode $pin_b_on_off in
gpio mode $pin_led_on_off out

program_on=0

# Main loop
while true
do
		# Checking pin state in order to activate or deactivate our bluetooth program
	sleep $scan_time
	pin_state=$(gpio read $pin_b_on_off)
	if [ $pin_state = 1 ] || [ $program_on = 0 ]
	then
		# Program is active so powering state led
		gpio write $pin_led_on_off 1
		# Insert code to launch main py program here
    python /home/pi/projet_bluetooth/raspytooth.py

	elif [ $pin_state = 0 ]
	then
		# Program deactivated so we put off the led
		gpio write $pin_led_on_off 0
    $program_on=0

	fi
done

