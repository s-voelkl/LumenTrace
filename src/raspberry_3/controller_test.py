import machine
import utime

# ADC an Pin 26 (GP26) aktivieren
adc_controller = machine.ADC(26)

# UART (Serielle Schnittstelle) für später vorbereiten
# TX ist GP0 (Pin 1), RX ist GP1 (Pin 2)
uart = machine.UART(0, baudrate=9600, tx=machine.Pin(0), rx=machine.Pin(1))

print("Pico ist bereit! Zeig mir deine Gaspedal-Skills...")

while True:
    # Wert lesen (0 bis 65535)
    gas_wert = adc_controller.read_u16()
    
    # Text-Paket bauen (z.B. "C1:45000\n")
    daten_paket = f"C1:{gas_wert}\n"
    
    # Über UART an den Pi 3 senden (für später)
    uart.write(daten_paket)
    
    # Für unseren jetzigen Test: In der Thonny-Konsole anzeigen
    print(daten_paket.strip()) 
    
    utime.sleep(0.1) # 10 Mal pro Sekunde messen