# Raspberry Pi Pico Config

Run Thonny on Raspberry Pi 3, with a USB connection to the Raspberry Pi Pico (standard variant). In Thonny, select "MicroPython (Raspberry Pi Pico)" as the interpreter.

ADC des Pico hat eine 16 Bit Auflösung, also Werte von 0 bis 65535. Der Schalter aktiviert sich ab 70% (45.874) bis 100% (65.535).
Daher ist ein Mapping des Bereichs 45k-65k auf 0 bis 100 als Prozent der Acceleration nötig.
