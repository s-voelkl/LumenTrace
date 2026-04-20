import machine as ma
import time

# Setup für ADC und UART
adc_controller = ma.ADC(26)
uart = ma.UART(0, baudrate=115200, tx=ma.Pin(0), rx=ma.Pin(1), bits=8, parity=None, stop=1)

while True:
    # Sensorwert auslesen
    gas_wert = adc_controller.read_u16()
    
    # Debug-Ausgabe im Terminal
    print(f"Gas-Wert: {gas_wert}")
    
    # JSON-String erstellen und über UART senden
    # Wir setzen den gas_wert direkt für controller1 ein
    json_data = '{"controller1":' + str(gas_wert) + '}'
    
    # Alternativ mit f-string (eleganter):
    # json_data = f'{{"controller1":{gas_wert}}}'
    
    uart.write(json_data)
    
    time.sleep(0.05)