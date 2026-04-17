# Aufbau: Pico 
# - UART0-TX (1) mit UART1-RX (12)
# - UART0-RX (2) mit UART1-TX (11)

# Baudrate: typischerweise 9600
# Anzahl der Datenbits: typischerweise 8
# Anzahl der Stopbits: Typischerweise 1
# Parität: Typischerweise None oder 0

# Bibliotheken laden
from machine import UART, Pin
from time import sleep

# UART0 initialisieren
uart0 = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1), bits=8, parity=None, stop=1)
print('UART0:', uart0)
print()

# UART1 initialisieren
uart1 = UART(1, baudrate=9600, tx=Pin(8), rx=Pin(9), bits=8, parity=None, stop=1)
print('UART1:', uart1)
print()

# Daten zum Senden
txData = 'Hallo Welt'

# Hauptprogramm
while True:
    # Daten senden
    print('Daten senden:', txData)
    uart0.write(txData)
    sleep(1)
    # Daten empfangen und ausgeben
    rxData = uart1.readline()
    try:
        print('Daten empfangen:', rxData.decode('utf-8'))
    except (AttributeError):
        print('Verbindung prüfen')
    sleep(1)
    print()