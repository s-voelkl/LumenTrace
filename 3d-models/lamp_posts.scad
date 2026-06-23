// --- LumenTrace Cyberpunk Street Lamp Posts ---
// Kantige Sci-Fi-Strassenlaternen als Deko entlang der Bahn auf der
// schwarzen Platte. Passend zum Skyline-Stil (skyline_buildings.scad).
// Alle Masse in Millimetern (mm). Massstab passend zur Carrera-Bahn.
//
// Jede Laterne hat eine NUT bzw. eingelassene Flaeche als "LED-Leuchte".
// Mit transparentem Filament gedruckt leuchtet sie im Bahn-Ambiente mit.
// Alle Masten eckig (Diamant-/Quadrat-Querschnitt) fuer den kantigen Look.

// ============================ PARAMETER ============================
post_h      = 55;     // Hoehe des Mastes
post_w      = 5;      // Mast-Schluesselweite (eckig)
base_w      = 14;     // Grundplatte Breite
base_h      = 3;      // Grundplatte Hoehe
arm_len     = 22;     // Auslegerlaenge
glow_depth  = 0.8;    // Tiefe der Leucht-Nut
$fn         = 32;

// Welche Laterne: "lamp_a" | "lamp_b" | "lamp_c" | "all"
show_lamp = "all";

// ============================ HELFER ===============================

// Eckiger Mast (Diamant-Querschnitt), leicht verjuengt.
module post(h = post_h, w = post_w) {
    rotate([0, 0, 45])
        cylinder(h = h, d1 = w*1.41, d2 = w*1.05, $fn = 4);
}

// Kantige Grundplatte mit abgeschraegten Ecken + Tech-Sockel.
module base() {
    hull() {
        cylinder(h = base_h, d = base_w, $fn = 6);
        cylinder(h = 0.1, d = base_w + 3, $fn = 6);
    }
    // Tech-Sockel
    translate([0, 0, base_h]) rotate([0,0,45])
        cylinder(h = 4, d = post_w*2.4, $fn = 4);
}

// Leuchtkopf-Box mit eingelassener Glow-Flaeche an der Unterseite.
module lamp_head(l = 16, w = 6, t = 5) {
    difference() {
        // kantiger Kopf, vorne angeschraegt
        hull() {
            cube([l, w, t], center = true);
            translate([l/2, 0, -t/4]) cube([0.1, w-2, t/2], center = true);
        }
        // Glow-Nut unten
        translate([0, 0, -t/2 + glow_depth/2 - 0.01])
            cube([l - 3, w - 2, glow_depth], center = true);
    }
}

// ============================ LATERNEN =============================

// Lamp A — Klassischer Ausleger (single arm), kantig
module lamp_a() {
    union() {
        base();
        translate([0, 0, base_h]) post();
        // Auslegerarm schraeg nach oben
        translate([0, 0, post_h - 4]) {
            rotate([0, 65, 0])
                cylinder(h = arm_len, d1 = 4, d2 = 3, $fn = 4);
            // Leuchtkopf am Armende (rotate Z->X: x=h*sin, z=h*cos)
            arm_end_x = arm_len * sin(65);
            arm_end_z = arm_len * cos(65);
            translate([arm_end_x + 5, 0, arm_end_z - 1])
                lamp_head();
        }
        // kleine Tech-Box am Mast
        translate([post_w/2, 0, post_h*0.5]) cube([3, 5, 8], center = true);
    }
}

// Lamp B — Doppelausleger (beidseitig), symmetrisch
module lamp_b() {
    union() {
        base();
        translate([0, 0, base_h]) post(post_h + 6);
        for (m = [0, 1]) mirror([m, 0, 0])
            translate([0, 0, post_h]) {
                rotate([0, 72, 0])
                    cylinder(h = arm_len*0.8, d1 = 3.5, d2 = 2.5, $fn = 4);
                ax = arm_len*0.8 * sin(72);
                az = arm_len*0.8 * cos(72);
                translate([ax + 4, 0, az - 1]) lamp_head(13, 5, 4);
            }
        // Querstrebe / Funkmodul oben
        translate([0, 0, post_h + 6]) cube([4, 4, 6], center = true);
        translate([0, 0, post_h + 12]) rotate([0,0,45]) cylinder(h = 8, d1 = 2, d2 = 0.4, $fn = 4);
    }
}

// Lamp C — Monolith-Pylon mit vertikaler Leuchtleiste (sehr cyberpunk)
module lamp_c() {
    pw = 8; ph = 50;
    union() {
        base();
        difference() {
            // kantiger Pylon, oben schraeg angeschnitten
            difference() {
                translate([0, 0, base_h]) rotate([0,0,45])
                    cylinder(h = ph, d1 = pw*1.5, d2 = pw*1.1, $fn = 4);
                // schraeger Kopfschnitt
                translate([0, 0, base_h + ph - 6])
                    rotate([20, 0, 0]) translate([-20,-20,0]) cube([40,40,20]);
            }
            // vertikale Leucht-Nut auf zwei Seiten
            for (a = [0, 90])
                rotate([0,0,a])
                    translate([0, pw*0.6, base_h + ph/2])
                        cube([2.5, glow_depth*2, ph*0.7], center = true);
        }
        // auskragendes Tech-Modul
        translate([pw*0.6, 0, base_h + ph*0.4])
            cube([6, 8, 12], center = true);
    }
}

// ============================ AUSGABE =============================
if      (show_lamp == "lamp_a") lamp_a();
else if (show_lamp == "lamp_b") lamp_b();
else if (show_lamp == "lamp_c") lamp_c();
else {
    lamp_a();
    translate([45, 0, 0]) lamp_b();
    translate([90, 0, 0]) lamp_c();
}
