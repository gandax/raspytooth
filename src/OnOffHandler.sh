# Defining pin numbers
pin_on_off=2
pin_led_on_off=0

# Defining pin modes
gpio mode $pin_b_on_off in
gpio mode $pin_led_on_off out

# Main loop
while true
do
		# Checking pin state in order to activate or deactivate our bluetooth program
        pin_state=$(gpio read $pin_b_on_off)
        if [ $pin_state = 1 ]
        then
                # Program is active so powering state led
				gpio write $pin_led_on_off 1
                sleep 2

        elif [ $pin_state = 0 ]
        then
                #Program deactivated so we put off the led
				gpio write $pin_led_on_off 0
                sleep 2
        fi
done

