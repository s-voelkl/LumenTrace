# Informationen aus Besprechungen und Todos

## Aktive Todos

27.04.

Bestellung LED Strips

Microcontroller Orchestration:

- apt remove "node red name" für Node auto-start bei ssh
- Testen SignalReader zwischen RPI3 und RPIPico
- Controller special_1 Anschluss
- Mapping Controllereingaben: forward [0,100], special_1 [0,1]
- Sichere Verkabelung der Controller
- 3D-gedrucktes Gehäuse für Microcontroller als Schutz?

LED-Code:

- WS2812 Code ansehen, einfaches Ansteuern probieren
- Display Architektur überdenken
- Converter TrackModule Position in LED-Punkt
- Festlegung Lichteffekte für Vehicle-/Game-States
- Implementierung
- Überholung LED-Streifen Produkt/Möglichkeit finden

Sound:

- Test mit Audiosignalen (wav/mp3), Stereo (l/r), Python Code

## 22.04. Besprechung

Wünsche

- Wunsch nach Überholungsstreifen mit extra LED-Strecke, z.B. für 12 LEDs groß.
- EIngang von Pico als dig. EIngangspin. ANgabe eines internen Pull-Up/-DOwn widerstand angeben (Pull Down bei uns)

Kurvenproblem

- 3d modell zu aufwändig? -> Bahn Grundplatte vielleicht in hälfte teilbar.
- anderer umsetzungsweg: diffuser. schwierig bei kurven, da vorgefertigte Modelle keine Kurvenradien haben.
- in schläuchen steckende ansteuerbare oder kunststoff LEDs vorhanden?

LED-Streifen:

- Adressierbares LED Neon Flex (Pixel Neon / Digital Neon), bzw. WS2812 neon flex 5V
- Beispiel: https://www.ledyilighting.com/addressable-neon-flex/
- hohe Pixeldichte bringt kaum optischen Vorteil, erhöht aber Verlust & Preis. 144p kaum vorhanden, teuer. --> 60p/m
- Einspeisung alle 1-2 Meter?

Sounds:

- Audio-AUsgang im RPI3, jedoch mit schlechter Audio-Qualität. USB zu Aux Kabel.
- Kanalverteilung auf 2 Lautsprecher (Stereo link rechts) für räuimlichkeit. SOnic Pi
- pulseaudio oder pygame für überlappende Audiofiles (z.B. wenn beide Autos die selbe Kurve schnell fahren und/oder einer rausfliegt)
- mehrere Soundkarten zu mehreren Lautsprechern (zusammen mit pulseaudio) https://www.youtube.com/watch?v=k1c2qlfvjBQ
- https://www.amazon.de/Speedlink-USB-betriebene-Stereo-Lautsprecher-Ausgangsleistung-Frequenzbereich-Schwarz/dp/B01HDR5EIK
- https://www.amazon.de/Hama-Lautsprecher-Computer-Notebook-Smartphone/dp/B018VONYPY?th=1
  frühzeitig alles bestellen und abklären

## 29.04. Besprechung

Zu besprechen:

- Bestellte LED-Streifen, Sound-Boxen, SD-Karte. -> einzelexemplare mit 5m bestellen, dann nachbestellen. sd karte neu aufsetzen. 
- aktueller Stand Game-Logik -> passt
- Problematik: Wie Überholstrecke mit LED-Streifen darstellen, sodass es schön bleibt? -> Überholstrecken anders machen

...
