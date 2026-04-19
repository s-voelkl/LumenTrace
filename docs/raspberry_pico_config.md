# Raspberry Pi Pico Config

Run Thonny on Raspberry Pi 3, with a USB connection to the Raspberry Pi Pico (standard variant). In Thonny, select "MicroPython (Raspberry Pi Pico)" as the interpreter.

ADC des Pico hat eine 16 Bit Auflösung, also Werte von 0 bis 65535. Der Schalter aktiviert sich ab 70% (45.874) bis 100% (65.535).
Daher ist ein Mapping des Bereichs 45k-65k auf 0 bis 100 als Prozent der Acceleration nötig.

https://www.elektronik-kompendium.de/sites/raspberry-pi/2707031.htm
https://www.electronicwings.com/raspberry-pi/raspberry-pi-uart-communication-using-python-and-c
https://medium.com/@pqshedy33/uart-serial-communication-experiment-based-on-raspberry-pi-4b-and-stm32-5abe5fe8f152
https://www.elektronik-kompendium.de/sites/raspberry-pi/2802111.htm
