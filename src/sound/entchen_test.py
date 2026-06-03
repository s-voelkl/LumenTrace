import time
from src.sound.engine_player import EngineSoundPlayer

# Frequenzen der Töne (C-Dur auf Oktave 3)
# Unser synthetischer Motorsound hat eine Basis-Frequenz von 60 Hz
# Pitch-Multiplier = Ziel-Frequenz / 60
notes = {
    'C': 130.81 / 60.0,
    'D': 146.83 / 60.0,
    'E': 164.81 / 60.0,
    'F': 174.61 / 60.0,
    'G': 196.00 / 60.0,
    'A': 220.00 / 60.0,
    'P': 0.0  # Pause
}

# "Alle meine Entchen" Melodie
# Format: (Note, Schläge/Dauer)
melody = [
    ('C', 1), ('D', 1), ('E', 1), ('F', 1),
    ('G', 2), ('G', 2),
    ('A', 1), ('A', 1), ('A', 1), ('A', 1),
    ('G', 4),
    ('A', 1), ('A', 1), ('A', 1), ('A', 1),
    ('G', 4),
    ('F', 1), ('F', 1), ('F', 1), ('F', 1),
    ('E', 2), ('E', 2),
    ('D', 1), ('D', 1), ('D', 1), ('D', 1),
    ('C', 4)
]

# Da wir unseren Pitch direkt steuern wollen, setzen wir min_pitch=0 und max_pitch=10.
# So entspricht set_speed(x) exakt einem Pitch-Multiplier von x * 10
player = EngineSoundPlayer(wav_file="assets/sound/base_engine.wav", min_pitch=0.0, max_pitch=10.0)
player.start()

beat_duration = 0.4 # Dauer eines Taktschlags in Sekunden

try:
    print("Spiele 'Alle meine Entchen' mit reinem V8-Motorsound...")
    for note, beats in melody:
        if note == 'P':
            player.set_speed(0)
        else:
            pitch = notes[note]
            player.set_speed(pitch / 10.0) # Map auf 0.0 - 1.0 Bereich der Methode
        
        # Wir spielen den Ton 90% der Zeit und nehmen ihn dann kurz zurück, 
        # damit man gleiche Töne hintereinander (A A A A) einzeln heraushört
        time.sleep(beat_duration * beats * 0.85)
        
        # Kurze Abdämpfung um die Anschläge voneinander zu trennen
        player.set_speed(0.2) 
        time.sleep(beat_duration * beats * 0.15)

    print("\nLied zu Ende!")

except KeyboardInterrupt:
    print("\nAbgebrochen.")
finally:
    player.stop()
