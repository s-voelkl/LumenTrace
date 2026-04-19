# import machine as ma
# import time
# adc_controller = ma.ADC(26)

# uart = ma.UART(0, baudrate=9600, tx=ma.Pin(0), rx=ma.Pin(1), bits=8, parity=None, stop=1)

# while True:
#     gas_wert = adc_controller.read_u16()
#     print(gas_wert, "transmitted:", str(gas_wert).encode('utf-8'))
#     uart.write(str(gas_wert).encode('utf-8'))
#     time.sleep(0.5)