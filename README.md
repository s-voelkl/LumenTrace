# LumenTrace

A high-performance MCU-based LED racing simulator. Bringing the classic slot car experience to the world of addressable LEDs with real-time physics and advanced light effects.

## Used Technologies

- Microcontrollers: Raspberry Pi Pico and Raspberry Pi 3 with an micro-SD card for data storage.
- Programming Languages: Arduino C++ for the microcontroller firmware, Python for OOP design, data processing, testing, simulation and visualization.
- Communication Protocols: High-Speed serial communication between Pico and Pi with UART, LED control via WS2812.
- Data Storage: Micro-SD card for storing and running the program on the Pi.

## Features

- Real-time physics simulation for accurate virtual slot car movement, including collision detection, acceleration/deceleration, falling down, recovery, and more.
- Advanced LED effects for immersive racing experience: Car headlights, rear lights, identification lights with warn indicators; track lighting for start/finish line; lap counter and more.
- Player controller with buttons for acceleration, braking, and lane switching, providing an interactive racing experience.
- High-speed communication between the microcontroller and the Raspberry Pi for seamless data exchange and control.
- Simulation with Python for debugging, testing, and visualization of the program logic and physics.

## Classes

Game, Track, TrackModule, LEDStrip, DrivingProfile, Settings, Player, Vehicle, Controller
tbd
