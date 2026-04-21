Done:
Controller-Steuerung, Übertragung zu Raspy3 von Pico.

Todo:

- LED Band ansteuern, testen, live einbinden (sodass Datenmodell direkt von Raspy3 auf die LED geht).
- Nächster Test: LED-Band mit Leuchtkästchen, das sich je nach Eingabe des Controllers bewegt.
- Mapping des Controllers: von 45k-65k auf 0 bis 100, eventuell mit Widerständen rumspielen.
- OOP Datenmodell umsetzen: Game-Logic: testen auf raspy mit neuem receive code mit pico. außerdem game log und game start testen.


Sound:
- pulseaudio oder pygame für überlappende Audiofiles (z.B. wenn beide Autos die selbe Kurve schnell fahren und/oder einer rausfliegt)
- mehrere Soundkarten zu mehreren Lautsprechern (zusammen mit pulseaudio) https://www.youtube.com/watch?v=k1c2qlfvjBQ
