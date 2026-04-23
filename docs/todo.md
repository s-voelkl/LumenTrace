Done:
Controller-Steuerung, Übertragung zu Raspy3 von Pico.

Todo:

- LED Band ansteuern, testen, live einbinden (sodass Datenmodell direkt von Raspy3 auf die LED geht).
- Nächster Test: LED-Band mit Leuchtkästchen, das sich je nach Eingabe des Controllers bewegt.
- Mapping des Controllers: von 45k-65k auf 0 bis 100, eventuell mit Widerständen rumspielen.
- OOP Datenmodell umsetzen: Game-Logic: testen auf raspy mit neuem receive code mit pico. außerdem game log und game start testen.
- @Simon: todos aus todo liste handy

---

Besprechung:

- Wunsch nach Überholungsstreifen mit extra LED-Strecke, z.B. für 12 LEDs groß.
- EIngang von Pico als dig. EIngangspin. ANgabe eines internen Pull-Up/-DOwn widerstand angeben (Pull Down bei uns)

Kurvenproblem:

- 3d modell zu aufwändig? -> Bahn Grundplatte vielleicht in hälfte teilbar.
- anderer umsetzungsweg: diffuser. schwierig bei kurven, da vorgefertigte Modelle keine Kurvenradien haben.
- in schläuchen steckende ansteuerbare oder kunststoff LEDs vorhanden?

LED-Streifen:

- Adressierbares LED Neon Flex (Pixel Neon / Digital Neon), bzw. WS2812 neon flex 5V
- Beispiel: https://www.ledyilighting.com/addressable-neon-flex/
- hohe Pixeldichte bringt kaum optischen Vorteil, erhöht aber Verlust & Preis. 144p kaum vorhanden, teuer. --> 60p/m
- Einspeisung alle 1-2 Meter?

Sounds:

- AUdio-AUsgang im RPI3, jedoch mit schlechter Audio-Qualität. USB zu Aux Kabel.
- Kanalverteilung auf 2 Lautsprecher (Stereo link rechts) für räuimlichkeit. SOnic Pi
- pulseaudio oder pygame für überlappende Audiofiles (z.B. wenn beide Autos die selbe Kurve schnell fahren und/oder einer rausfliegt)
- mehrere Soundkarten zu mehreren Lautsprechern (zusammen mit pulseaudio) https://www.youtube.com/watch?v=k1c2qlfvjBQ
- https://www.amazon.de/Speedlink-USB-betriebene-Stereo-Lautsprecher-Ausgangsleistung-Frequenzbereich-Schwarz/dp/B01HDR5EIK
- https://www.amazon.de/Hama-Lautsprecher-Computer-Notebook-Smartphone/dp/B018VONYPY?th=1
  frühzeitig alles bestellen und abklären
