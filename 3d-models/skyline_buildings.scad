// --- LumenTrace Skyline-Hochhaeuser v2 (Futuristisch, massiv) ---
// Fuenf alternative Wolkenkratzer im Stil der Referenz: gestaffelte
// Setbacks, abgeschraegte/facettierte Koerper, Antennen und horizontale
// LED-Baender als umlaufende NUTEN (keine durchbrochenen Schlitze).
// Die Nuten koennen spaeter mit Leuchtfarbe gefuellt werden oder einfach
// als Schattenfuge dienen. Alle Masse in Millimetern (mm).
//
// Druck: aufrecht. Alle Setbacks gehen nach innen -> ueberhangfrei.
// Koerper sind unten offen ausgehoehlt (Filament sparen), Aussenhaut
// bleibt geschlossen.

// ============================ PARAMETER ============================
wall        = 1.6;    // Wandstaerke beim Aushoehlen
hollow      = true;   // true = unten offen aushoehlen (leicht), false = massiv

band_depth  = 1.4;    // Tiefe der horizontalen LED-Nuten
band_h      = 3.0;    // Hoehe einer Nut
$fn         = 64;

// Welches Gebaeude: "t1".."t5" oder "all"
show_building = "all";

// ============================ HELFER ===============================

// Abgeschraegter Block (Fasen an den 4 oberen Kanten), in XY zentriert.
// taper = Verjuengung der Oberseite (1.0 = gerade).
module chamfer_block(w, d, h, chamf = 3, taper = 1.0) {
    tw = w * taper;
    td = d * taper;
    hull() {
        translate([0, 0, 0.01])         cube([w, d, 0.02], center = true);
        translate([0, 0, h - chamf])    cube([w, d, 0.02], center = true);
        translate([0, 0, h - 0.01])     cube([tw - 2*chamf, td - 2*chamf, 0.02], center = true);
    }
}

// Facettierter (oktogonaler) Schaft, in XY zentriert.
module facet_shaft(across, h, sides = 8, taper = 0.92) {
    cylinder(h = h, d1 = across, d2 = across * taper, $fn = sides);
}

// Werkzeug fuer eine umlaufende Nut auf Hoehe z (fuer rechteckige Tuerme).
module groove_rect(w, d, z) {
    translate([0, 0, z])
        difference() {
            cube([w + 2, d + 2, band_h], center = true);
            cube([w + 2 - 2*band_depth, d + 2 - 2*band_depth, band_h + 2], center = true);
        }
}

// Werkzeug fuer eine umlaufende Nut (fuer facettierte/runde Tuerme).
module groove_round(across, z, sides = 8) {
    translate([0, 0, z])
        difference() {
            cylinder(h = band_h, d = across + 2, $fn = sides, center = true);
            cylinder(h = band_h + 2, d = across + 2 - 2*band_depth, $fn = sides, center = true);
        }
}

// Hoehlt einen zentrierten Koerper von unten aus.
module hollow_cut(w, d, h) {
    if (hollow)
        translate([0, 0, -1])
            cube([w - 2*wall, d - 2*wall, h - wall], center = true);
}

// Cyberpunk-Antennen: eckige Masten (Diamant-Querschnitt), Querstrebe,
// asymmetrische schraege Ausleger und eine Tech-Box an der Basis.
module antennas(z, main = 28, side = 16, spread = 5) {
    translate([0, 0, z]) {
        // Tech-Box an der Basis
        translate([0, 0, 1.5]) cube([7, 7, 3], center = true);
        // Hauptmast, eckig verjuengt
        rotate([0, 0, 45]) cylinder(h = main, d1 = 3.4, d2 = 1.0, $fn = 4);
        // Querstrebe (Funk-Kreuz)
        translate([0, 0, main*0.6]) cube([2*spread + 5, 1.2, 1.2], center = true);
        translate([0, 0, main*0.6]) cube([1.2, 2*spread + 5, 1.2], center = true);
        // asymmetrische Ausleger
        translate([ spread, 0, 0]) rotate([0,  16, 0]) cylinder(h = side, d1 = 1.8, d2 = 0.4, $fn = 4);
        translate([-spread, 0, 0]) rotate([0, -8, 0])  cylinder(h = side*0.65, d1 = 1.8, d2 = 0.4, $fn = 4);
    }
}

// Schraeger Dachschnitt (diagonal) als Schnittwerkzeug, zentriert.
module roof_cut(w, d, z, ang = 22) {
    translate([0, 0, z])
        rotate([ang, 0, 0])
            translate([0, 0, 30])
                cube([w + 20, d + 40, 60], center = true);
}

// Auskragender Tech-Arm (Kragarm) auf Hoehe z, in +X-Richtung.
module outrigger(z, len = 14, thick = 4) {
    translate([0, 0, z]) {
        rotate([0, 90, 0])
            cylinder(h = len, d = thick, $fn = 4);
        translate([len, 0, 0]) cube([5, 7, 9], center = true);
    }
}

// ============================ GEBAEUDE =============================

// T1 — Setback-Klassiker mit drei Stufen und Baendern (~150 mm)
module t1() {
    w = 42; d = 42;
    difference() {
        union() {
            chamfer_block(w,    d,    70, 3);
            translate([0,0,70]) chamfer_block(w-12, d-12, 35, 3);
            translate([0,0,105]) chamfer_block(w-24, d-24, 22, 2.5);
            antennas(127, 30);
        }
        // Aushoehlung
        hollow_cut(w, d, 70);
        // LED-Baender im Sockel
        for (z = [18, 30, 42, 54]) groove_rect(w, d, z);
        for (z = [80, 92]) groove_rect(w-12, d-12, z);
    }
}

// T2 — Schlanker Turm mit eingelassenen Mittelpaneelen (~160 mm)
module t2() {
    w = 30; d = 30;
    difference() {
        union() {
            chamfer_block(w, d, 120, 2.5, taper = 0.85);
            translate([0,0,120]) chamfer_block(w-6, d-6, 16, 2);
            antennas(136, 26, 14, 4);
        }
        hollow_cut(w, d, 120);
        // Eingelassene vertikale Paneele (flache Vertiefung, NICHT durchbrochen)
        panel_depth = 0.8;  // bewusst < wall, damit die Wand geschlossen bleibt
        for (a = [0, 90, 180, 270])
            rotate([0,0,a])
                translate([0, d/2 - panel_depth/2 + 0.01, 60])
                    cube([10, panel_depth, 80], center = true);
        // wenige Baender
        for (z = [20, 100]) groove_rect(w, d, z);
    }
}

// T3 — Facettierter Kristall mit schraeger Spitze (~110 mm)
module t3() {
    across = 40;
    difference() {
        union() {
            facet_shaft(across, 90, 8, 0.9);
            antennas(90, 24);
        }
        if (hollow)
            translate([0,0,-1]) cylinder(h = 88, d = across - 2*wall, $fn = 8);
        // schraege Dachkappe abschneiden
        translate([0, 0, 78])
            rotate([16, 0, 0])
                translate([-50, -50, 0]) cube([100, 100, 40]);
        for (z = [22, 38, 54]) groove_round(across, z, 8);
    }
}

// T4 — Zwillingsturm mit Mittelspalt von oben (~140 mm)
module t4() {
    w = 46; d = 26;
    difference() {
        union() {
            chamfer_block(w, d, 95, 3);
            translate([0,0,95]) chamfer_block(w, d-6, 18, 3);
            translate([-w/4, 0, 113]) antennas(0, 22, 0, 0);
            translate([ w/4, 0, 113]) antennas(0, 22, 0, 0);
        }
        hollow_cut(w, d, 95);
        // Mittelspalt von oben (Notch, geht nicht ganz durch)
        translate([0, 0, 60]) cube([6, d + 2, 80], center = true);
        for (z = [22, 34, 46, 58]) groove_rect(w, d, z);
    }
}

// T5 — Oktogonaler Setback-Turm (~135 mm)
module t5() {
    a1 = 44;
    difference() {
        union() {
            facet_shaft(a1, 60, 8, 0.95);
            translate([0,0,60]) facet_shaft(a1-10, 45, 8, 0.95);
            translate([0,0,105]) facet_shaft(a1-22, 18, 8, 0.95);
            antennas(123, 26);
        }
        if (hollow)
            translate([0,0,-1]) cylinder(h = 58, d = a1 - 2*wall, $fn = 8);
        for (z = [16, 28, 40]) groove_round(a1, z, 8);
        for (z = [72, 86]) groove_round(a1-10, z, 8);
    }
}

// T6 — Turm mit konkaver Glasfassade (~120 mm)
module t6() {
    w = 40; d = 34; h = 120;
    dent = 7;            // Tiefe der Einwoelbung
    cr = 80;             // Radius der Kruemmung
    difference() {
        union() {
            chamfer_block(w, d, h, 3, 0.95);
            translate([0,0,h]) chamfer_block(w-8, d-6, 12, 2);
            antennas(h + 12, 24);
        }
        hollow_cut(w, d, h);
        // Konkave Front: vertikaler Zylinder dellt die Vorderseite ein
        translate([0, d/2 + cr - dent, -1])
            cylinder(h = h + 2, r = cr, $fn = 96);
        for (z = [18, 34, 50, 66]) groove_rect(w, d, z);
    }
}

// T7 — Pyramiden-Spitze (Transamerica-Stil, ~130 mm)
module t7() {
    w = 46;
    difference() {
        union() {
            chamfer_block(w, w, 38, 3);
            translate([0,0,38]) chamfer_block(w, w, 80, 3, taper = 0.18);
            antennas(118, 22);
        }
        hollow_cut(w, w, 38);
        for (z = [12, 26]) groove_rect(w, w, z);
    }
}

// T8 — Zwillingstuerme mit Skybridge (Petronas-Stil, ~140 mm)
// Hinweis: Die Bruecke hat eine kurze freie Spannweite -> ggf. minimaler
// Stuetzdruck noetig, oder Bruecke nach dem Druck einkleben.
module t8() {
    sw = 22; h = 130; gap = 16;
    off = gap/2 + sw/2;
    union() {
        for (x = [-off, off])
            translate([x, 0, 0])
                difference() {
                    facet_shaft(sw, h, 6, 0.9);
                    if (hollow) translate([0,0,-1]) cylinder(h = h-2, d = sw-2*wall, $fn = 6);
                    for (z = [20, 34, 48]) groove_round(sw, z, 6);
                }
        // Skybridge
        translate([0, 0, h*0.62]) cube([gap + sw*0.6, sw-6, 7], center = true);
        // Dachspitzen
        translate([-off,0,0]) antennas(h, 18, 0, 0);
        translate([ off,0,0]) antennas(h, 18, 0, 0);
    }
}

// T9 — Verdrehter Turm (Turning-Torso-Stil, ~120 mm, massiv)
module t9() {
    w = 32; layers = 24; lh = 5; twist = 3;  // 3 Grad pro Schicht
    union() {
        for (i = [0 : layers-1]) {
            s = 1 - i*0.012;
            translate([0, 0, i*lh])
                rotate([0, 0, i*twist])
                    chamfer_block(w*s, w*s, lh + 0.1, 1.2);
        }
        antennas(layers*lh, 18);
    }
}

// T10 — Cyberpunk-Megablock: asymmetrisch, schraeges Dach, Kragarme (~150 mm)
module t10() {
    w = 40; d = 30;
    difference() {
        union() {
            // Hauptschaft, leicht verjuengt
            chamfer_block(w, d, 95, 2, 0.96);
            // versetzter Aufsatz (asymmetrisch)
            translate([ -6, 0, 95]) chamfer_block(w-14, d-4, 30, 2);
            // Kragarme mit Tech-Boxen auf verschiedenen Hoehen
            translate([0, 0, 0]) outrigger(40, 13, 4);
            mirror([1,0,0]) outrigger(62, 11, 4);
            outrigger(78, 10, 3.5);
            antennas(125, 30, 18, 7);
        }
        hollow_cut(w, d, 95);
        // aggressiver Diagonalschnitt am Dach
        roof_cut(w-14, d-4, 110, 26);
        // scharfe vertikale Kerben an den Seiten (Schattenfugen)
        for (s = [-1, 1])
            translate([s*w/2, 0, 50]) rotate([0,0,45]) cube([3, 3, 90], center = true);
        for (z = [16, 28, 40, 52, 64]) groove_rect(w, d, z);
    }
}

// ============================ AUSGABE =============================
if      (show_building == "t1") t1();
else if (show_building == "t2") t2();
else if (show_building == "t3") t3();
else if (show_building == "t4") t4();
else if (show_building == "t5") t5();
else if (show_building == "t6") t6();
else if (show_building == "t7") t7();
else if (show_building == "t8") t8();
else if (show_building == "t9") t9();
else if (show_building == "t10") t10();
else {
    t1();
    translate([70, 0, 0])   t2();
    translate([130, 0, 0])  t3();
    translate([195, 0, 0])  t4();
    translate([260, 0, 0])  t5();
    translate([330, 0, 0])  t6();
    translate([400, 0, 0])  t7();
    translate([470, 0, 0])  t8();
    translate([540, 0, 0])  t9();
    translate([610, 0, 0])  t10();
}
