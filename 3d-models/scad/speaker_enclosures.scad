// --- LumenTrace Lautsprecher-Gehaeuse (Cyberpunk-Skyline-Stil) ---
// Dekorative Huellen fuer das 2.1-Set, gestaltet als Wolkenkratzer
// passend zur Skyline (skyline_buildings.scad) und den Laternen.
// Alle Masse in Millimetern (mm).
//
// Achsen:  x = Breite (Front),  y = Tiefe (Front y=0 -> Hinten y=max),
//          z = Hoehe.  Lautsprecher werden von UNTEN eingeschoben,
//          Bodenplatte separat. Front hat ein Schallfenster, hinten
//          sitzen die Kabel-/Schalter-Aussparungen.
//
// ECHTE MASSE:
//  Satellit (L/R): 85 x 85 x 205,  Kabel hinten bei z=45
//  Subwoofer:      115(B) x 225(T) x 235(H)
//                  Kabel hinten z=30..100,  On/Off hinten z=180..200
//                  (Knoepfe vorne sind im Schallfenster zugaenglich)

// ============================ AUSWAHL =============================
// model: "satellite" | "subwoofer"
model = "satellite";
// part:  "assembled" | "lower" | "upper" | "baseplate"
part  = "assembled";

// ============================ PARAMETER ===========================
wall       = 3.0;     // Wandstaerke
clearance  = 1.0;     // Spiel pro Seite zum Lautsprecher
top_solid  = 6.0;     // Deckenstaerke ueber dem Lautsprecher

// Deko-Spitze
spire_steps = 3;
spire_step_h = 12;
spire_inset = 7;      // Verjuengung pro Stufe und Seite

// Schallfenster (Front)
win_margin_x = 14;    // Randabstand links/rechts
win_z0       = 22;    // Unterkante Fenster
win_top_off  = 24;    // Abstand zur Gehaeuse-Oberkante des Lautsprecherteils
win_bars     = 2;     // Anzahl Querstreben im Fenster

// Druck-Teilung
join_tol = 0.35;
join_h   = 14;

$fn = 48;

// --- Modellabhaengige Werte ---
// [breite_x, tiefe_y, hoehe_z]
spk      = (model == "subwoofer") ? [115, 225, 235] : [85, 85, 205];
split_z  = (model == "subwoofer") ? 130 : 115;

inner_x = spk[0] + 2*clearance;
inner_y = spk[1] + 2*clearance;
outer_x = inner_x + 2*wall;
outer_y = inner_y + 2*wall;
body_h  = spk[2] + top_solid;            // Hauptkoerper (oben geschlossen)
spire_h = spire_steps*spire_step_h;
total_h = body_h + spire_h + 30;         // inkl. Antenne (grob)

// ============================ HELFER ==============================

// Cyberpunk-Antenne (eckig, asymmetrisch)
module cyber_antenna(x, y, z, main = 30) {
    translate([x, y, z]) {
        translate([0,0,1.5]) cube([8, 8, 3], center = true);
        rotate([0,0,45]) cylinder(h = main, d1 = 3.6, d2 = 1.0, $fn = 4);
        translate([0,0,main*0.6]) cube([14, 1.4, 1.4], center = true);
        translate([0,0,main*0.6]) cube([1.4, 14, 1.4], center = true);
        translate([5,0,0]) rotate([0,16,0]) cylinder(h = 16, d1 = 1.8, d2 = 0.4, $fn = 4);
    }
}

// Hohler Hauptkoerper: unten offen, oben geschlossen
module body_shell() {
    difference() {
        cube([outer_x, outer_y, body_h]);
        translate([wall, wall, -1])
            cube([inner_x, inner_y, spk[2] + 1]);
    }
}

// Cyberpunk-Schallgitter: vertikale Lamellen-Schlitze (Front = y 0).
// Der Lautsprecher bleibt dahinter verdeckt; ~55% offene Flaeche fuer
// guten Klang. Vertikale Schlitze drucken aufrecht ueberhangfrei.
grille_slot = 4.0;   // Schlitzbreite
grille_step = 7.0;   // Raster (Schlitz + Steg)
module front_window() {
    gw = outer_x - 2*win_margin_x;
    gh = body_h - win_z0 - win_top_off;
    n = floor((gw + (grille_step - grille_slot)) / grille_step);
    group_w = n*grille_slot + (n-1)*(grille_step - grille_slot);
    x0 = (outer_x - group_w) / 2;
    for (i = [0 : n-1])
        translate([x0 + i*grille_step, -1, win_z0])
            cube([grille_slot, wall + 2, gh]);
}
// Horizontale Querstege unterbrechen das Gitter (Stabilitaet + Tech-Look)
module front_bars() {
    win_w = outer_x - 2*win_margin_x;
    win_h = body_h - win_z0 - win_top_off;
    for (i = [1 : win_bars]) {
        bz = win_z0 + win_h * i/(win_bars+1);
        translate([win_margin_x, 0, bz - 1.5])
            cube([win_w, wall, 3.0]);
    }
}

// Rundes Kabelloch hinten (y = max)
module cable_hole(z, dia = 14) {
    translate([outer_x/2, outer_y - wall - 1, z])
        rotate([-90, 0, 0])
            cylinder(h = wall + 2, d = dia);
}

// Rechteckige Aussparung hinten (y = max), Hoehenbereich z0..z1
module rear_opening(z0, z1, width = 40) {
    translate([(outer_x - width)/2, outer_y - wall - 1, z0])
        cube([width, wall + 2, z1 - z0]);
}

// Gestaffelte Deko-Spitze + Antenne auf body_h
module spire() {
    translate([0, 0, body_h]) {
        for (i = [0 : spire_steps-1]) {
            ins = spire_inset * i;
            translate([ins, ins, i*spire_step_h])
                cube([outer_x - 2*ins, outer_y - 2*ins, spire_step_h]);
        }
    }
    cyber_antenna(outer_x/2, outer_y/2, body_h + spire_h, 30);
}

// Komplettes Gehaeuse (ungeteilt)
module enclosure_full() {
    union() {
        difference() {
            union() {
                body_shell();
                spire();
            }
            front_window();
            if (model == "subwoofer") {
                rear_opening(30, 100, 50);    // Kabelausgaenge
                rear_opening(180, 200, 40);   // On/Off
            } else {
                cable_hole(45, 14);           // Satellit: Kabel hinten z=45
            }
        }
        front_bars();
    }
}

// --- Steck-Kragen fuer geteilten Druck ---
module join_collar() {
    translate([wall + join_tol, wall + join_tol, split_z])
        difference() {
            cube([inner_x - 2*join_tol, inner_y - 2*join_tol, join_h]);
            translate([wall, wall, -1])
                cube([inner_x - 2*join_tol - 2*wall, inner_y - 2*join_tol - 2*wall, join_h + 2]);
        }
}

module lower_part() {
    union() {
        intersection() {
            enclosure_full();
            cube([outer_x, outer_y, split_z]);
        }
        join_collar();
    }
}

module upper_part() {
    translate([0, 0, -split_z])
        intersection() {
            enclosure_full();
            translate([0, 0, split_z]) cube([outer_x, outer_y, total_h]);
        }
}

// Separate Bodenplatte mit Einrast-Lippe + Kabelschlitz hinten
module baseplate() {
    plate_h = 4;
    lip_h   = 6;
    union() {
        cube([outer_x, outer_y, plate_h]);
        translate([wall + join_tol, wall + join_tol, plate_h])
            difference() {
                cube([inner_x - 2*join_tol, inner_y - 2*join_tol, lip_h]);
                translate([wall, wall, -1])
                    cube([inner_x - 2*join_tol - 2*wall, inner_y - 2*join_tol - 2*wall, lip_h + 2]);
                // Kabelschlitz hinten
                translate([(inner_x)/2 - 8, inner_y - 2*join_tol - wall - 1, -1])
                    cube([16, wall + 2, lip_h + 2]);
            }
    }
}

// ============================ AUSGABE =============================
if      (part == "assembled") { lower_part(); translate([outer_x + 25, 0, 0]) upper_part(); }
else if (part == "lower")     lower_part();
else if (part == "upper")     upper_part();
else if (part == "baseplate") baseplate();
