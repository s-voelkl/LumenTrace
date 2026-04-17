import RPi.GPIO as GPIO
import serial

GPIO.setmode(GPIO.BOARD)
GPIO.setup(15, GPIO.IN)  # RX pin

uart = serial.Serial(
    port='/dev/ttyS0',  # Default UART port on GPIO 14/15
    # port='/dev/serial0',  # Default UART port on GPIO 14/15
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)
# while True:
#     rxData = uart.read(10)
#     print(rxData.decode('utf-8'))

while True:
    received_data = ser.read()              #read serial port
    sleep(0.03)
    data_left = ser.inWaiting()             #check for remaining byte
    received_data += ser.read(data_left)
    print (received_data)                   #print received data
    ser.write(received_data)                #transmit data serially 