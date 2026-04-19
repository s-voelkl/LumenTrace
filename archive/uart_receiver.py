import RPi.GPIO as GPIO
import serial
import time
import re
import json

GPIO.setmode(GPIO.BOARD)
GPIO.setup(15, GPIO.IN)  # RX pin

uart = serial.Serial(
    port='/dev/ttyS0',  # Default UART port on GPIO 14/15
    # port='/dev/serial0',  # Default UART port on GPIO 14/15
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

# while True:
#     rxData = uart.read(10)
#     print(rxData.decode('utf-8'))

controller1 = controller2 = controller3 = controller4 = None

while True:
    received_data = uart.read()              #read serial port
    data_left = uart.inWaiting()             #check for remaining byte
    received_data += uart.read(data_left)
    decoded_data = received_data.decode('utf-8')
    
    # Find all valid JSON objects (containing { and })
    json_matches = re.findall(r'\{[^}]+\}', decoded_data)
    
    for match in json_matches:
        try:
            data = json.loads(match)
            # Extract controller values from the JSON object
            if 'controller1' in data:
                controller1 = data['controller1']
            if 'controller2' in data:
                controller2 = data['controller2']
            if 'controller3' in data:
                controller3 = data['controller3']
            if 'controller4' in data:
                controller4 = data['controller4']
        except json.JSONDecodeError:
            continue
    
    print("Received:", decoded_data)                   #print received data
    # uart.write(received_data)                #transmit data serially 
    print("Controller1:", controller1, "Controller2:", controller2, "Controller3:", controller3, "Controller4:", controller4)
    time.sleep(0.1)
    