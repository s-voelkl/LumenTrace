import time
import threading
from src.sound.engine_player import EngineSoundPlayer

def run_car(player, name, delay_sec):
    """Eine Funktion, die das Beschleunigen und Abbremsen eines Autos simuliert."""
    if delay_sec > 0:
        print(f"[{name}] Wartet {delay_sec} Sekunden vor dem Start...")
        time.sleep(delay_sec)
        
    print(f"[{name}] Motor im Leerlauf (Startet Links)...")
    player.set_speed(0.0)
    player.set_pan(-1.0) # Starte ganz links!
    time.sleep(2)
    
    print(f"[{name}] Beschleunige und fährt an uns vorbei...")
    for geschwindigkeit in [i / 100 for i in range(0, 101)]:
        player.set_speed(geschwindigkeit)
        
        # Panning geht von -1.0 (Links) zu +1.0 (Rechts), 
        # basierend auf dem Beschleunigungsverlauf
        aktuelles_pan = -1.0 + (geschwindigkeit * 2.0)
        player.set_pan(aktuelles_pan)
        
        time.sleep(0.05)
        
    print(f"[{name}] Top-Speed (Ist jetzt Rechts)...")
    time.sleep(2)
    
    print(f"[{name}] Abbremsen (Bleibt Rechts)...")
    for geschwindigkeit in [0.8, 0.5, 0.2, 0.0]:
        player.set_speed(geschwindigkeit)
        time.sleep(0.5)
        
    print(f"[{name}] Motor aus.")

# 1. Zwei separate Player initialisieren
player1 = EngineSoundPlayer(wav_file="assets/sound/edited_car_audio.mp3", min_pitch=0.5, max_pitch=2.0)
player2 = EngineSoundPlayer(wav_file="assets/sound/edited_car_audio.mp3", min_pitch=0.5, max_pitch=2.0)

# 2. Beide Sounds starten (laufen asynchron im Hintergrund)
player1.start()
player2.start()

try:
    # 3. Threads erstellen - Auto 2 startet 3.5 Sekunden nach Auto 1
    t1 = threading.Thread(target=run_car, args=(player1, "Auto 1 (Leader)", 0.0))
    t2 = threading.Thread(target=run_car, args=(player2, "Auto 2 (Chaser)", 3.5))
    
    # Threads starten
    t1.start()
    t2.start()
    
    # Warten, bis beide Threads ihr Runden-Skript beendet haben
    t1.join()
    t2.join()
    
    print("\nAlle Autos haben den Test beendet.")

except KeyboardInterrupt:
    print("\nVom Nutzer abgebrochen.")
finally:
    # 4. Streams ordentlich beenden
    player1.stop()
    player2.stop()