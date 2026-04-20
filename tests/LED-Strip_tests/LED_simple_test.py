import time
from rpi_ws281x import PixelStrip, Color
import argparse
import RPi.GPIO as GPIO
import serial
# import time
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
    

# LED Konfiguration
LED_COUNT      = 144
LED_PIN        = 18
LED_FREQ_HZ    = 800000
LED_DMA        = 10
LED_BRIGHTNESS = 50 
LED_INVERT     = False
LED_CHANNEL    = 0

# Variablen für den Status
controller1 = None
current_pixel = 0

def map_speed(x):
    """ Mappt 49000-65000 auf 0.05s - 0.002s Sleep """
    if x is None:
        return 0.1
    
    # Begrenzung
    x = max(49000, min(65000, x))
    
    in_min, in_max = 49000, 65000
    out_min, out_max = 0.05, 0.002 
    
    return out_min + (float(x - in_min) / float(in_max - in_min) * (out_max - out_min))

def update_leds(strip, pos, color):
    """ Zeichnet ein Auto an Position 'pos' mit Schweif """
    # Erst alles löschen (effizienter: nur die alten LEDs löschen)
    # Für den Anfang löschen wir der Einfachheit halber alles:
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0,0,0))
    
    # Haupt-LED
    strip.setPixelColor(pos, color)
    # Schweif (Rücklicht)
    if pos > 0:
        strip.setPixelColor(pos - 1, Color(20, 20, 20))
    
    strip.show()

# Main Programm
if __name__ == "__main__":
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    print("Echtzeit-Rennen gestartet!")

    try:
        while True:
            # 1. UART DATEN LESEN (Non-blocking)
            if uart.inWaiting() > 0:
                try:
                    received_data = uart.read(uart.inWaiting()).decode('utf-8', errors='ignore')
                    json_matches = re.findall(r'\{[^}]+\}', received_data)
                    
                    for match in json_matches:
                        data = json.loads(match)
                        if 'controller1' in data:
                            controller1 = data['controller1']
                except Exception as e:
                    print(f"Fehler beim Lesen: {e}")

            # 2. GESCHWINDIGKEIT BERECHNEN
            # Wir nutzen controller1, wenn vorhanden, sonst 49000 (Stand)
            speed_val = controller1 if controller1 is not None else 49000
            wait_time = map_speed(speed_val)

            # 3. LED BEWEGEN (Nur wenn nicht auf "Stop")
            # Wenn der Wert nahe 49000 ist, steht das Auto (optional)
            if speed_val > 49100: 
                update_leds(strip, current_pixel, Color(0, 0, 255))
                current_pixel = (current_pixel + 1) % LED_COUNT
            else:
                # Auto steht, aber wir zeigen es an
                update_leds(strip, current_pixel, Color(0, 0, 255))

            # 4. WARTEN (basierend auf Controller-Input)
            time.sleep(wait_time)

    except KeyboardInterrupt:
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, Color(0,0,0))
        strip.show()
        print("\nRennen beendet.")