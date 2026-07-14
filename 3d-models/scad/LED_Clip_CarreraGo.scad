// --- Carrera Go LED Clip (Flach & Offen / Sichtfeld-Style) ---
// Alle Maße in Millimetern (mm). 
// Passt diese Werte an eure exakten Messungen an!

// --- PARAMETER ---
// 1. Der Pin für die Carrera-Schiene
slot_width = 4.0;      // Breite der Rille (Carrera Go ca. 3mm)
slot_depth = 5.0;      // Wie tief der Pin in die Rille ragt
clip_length = 5.0;     // Wie lang der Clip in Fahrtrichtung ist

// 2. Der LED-Streifen (Horizontal liegend)
strip_width_flat = 13.0; // Breite des flach liegenden Streifens (meist 10-12mm)
strip_thickness = 1.0;  // Dicke des Streifens inkl. Klebeband/Chips
// Diese Nase greift *nur* die alleräußerste Kante des Streifens!
snap_lip_width = 2;  // Wie weit die Nase nach innen ragt (sehr fein)

// 3. Stabilität & Toleranz
wall = 1.6;            // Wandstärke der Basisplatte (die auf der Fahrbahn liegt)
gap_clearance = 0.5;   // Minimaler Freiraum zum Streifen für Toleranz

// --- GENERATOR (Völlig neu konstruiert) ---
module led_clip_flat_sichtfeld() {
    union() {
        // 1. Der Pin (Steckt in der Bahn)
        // Zentriert um den Ursprung für Symmetrie
        translate([0, 0, -slot_depth/2])
            cube([slot_width, clip_length, slot_depth], center=true);
            
        // 2. Die flache Basis (Liegt auf der Fahrbahn auf)
        // Muss breiter sein als der Pin und der Streifen, um Stabilität zu geben
        translate([0, 0, wall/2])
            cube([strip_width_flat + 2*wall + 2*gap_clearance, clip_length, wall], center=true);
            
        // 3. Die sehr niedrigen Halterwände (knapp über Streifendicke)
        wall_height = strip_thickness + gap_clearance; // Etwas höher als Dicke für Halt
        
        // Rechte Wand
        translate([(strip_width_flat/2 + gap_clearance + wall/2), 0, wall + wall_height/2])
            cube([wall, clip_length, wall_height], center=true);
            
        // Linke Wand
        translate([-(strip_width_flat/2 + gap_clearance + wall/2), 0, wall + wall_height/2])
            cube([wall, clip_length, wall_height], center=true);
            
        // 4. Die ultra-feinen Halte-Nasen (Klick-Mechanismus oben)
        // Diese greifen nur die alleräußerste PCB-Kante!
        lip_thickness = 0.8;
        
        // Rechte Nase
        translate([(strip_width_flat/2 + gap_clearance - snap_lip_width/2), 0, wall + wall_height - lip_thickness/2])
            cube([snap_lip_width, clip_length, lip_thickness], center=true);
            
        // Linke Nase
        translate([-(strip_width_flat/2 + gap_clearance - snap_lip_width/2), 0, wall + wall_height - lip_thickness/2])
            cube([snap_lip_width, clip_length, lip_thickness], center=true);
    }
}

// Modell rendern
led_clip_flat_sichtfeld();