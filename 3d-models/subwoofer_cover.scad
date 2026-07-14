// --- LumenTrace Subwoofer-Haube (liegend, zum Drueberstuelpen) ---
// Der Subwoofer liegt auf seiner GROSSEN Flaeche (225 x 235 mm) flach auf
// der Platte, nur 115 mm hoch. Diese Haube wird einfach drueber gestuelpt:
// 5 Seiten geschlossen, UNTEN OFFEN, keine Bodenplatte, kein Einschub.
//
// Druck: KOPFUEBER (geschlossene Oberseite liegt flach am Bett) -> keine
// Bridge, kein Support. Da 225/235 > 210er Bett, wird die Haube in 4
// Viertel geteilt und an den planen Kanten verklebt.
//
// Alle Masse in Millimetern (mm).

// ============================ MASSE ===============================
// Subwoofer liegend: Footprint x/y, Hoehe z
sub_x = 235;   // grosse Flaeche, Kante A (war Hoehe)
sub_y = 225;   // grosse Flaeche, Kante B (war Tiefe/Laenge)
sub_z = 115;   // Hoehe im Liegen (war Breite)

clearance = 2.0;   // Spiel zum bequemen Drueberstuelpen (pro Seite)
wall      = 2.0;   // Wandstaerke (Deko-Haube, muss nicht tragend sein)
top_thick = 1.6;   // Deckenstaerke (duenner = viel weniger Material/Zeit,
                   // da die liegende Decke die groesste Flaeche ist)
air_top   = 1.5;   // Luft ueber dem Subwoofer

// Deko: horizontale Baender als Nuten
band_depth = 1.2;
band_h     = 3.0;

// Lueftung (Verstaerker wird warm): Schlitze
vent = true;

// Ausgabe: "assembled" | "q1" | "q2" | "q3" | "q4"
// q1..q4 sind die vier Druck-Viertel, bereits KOPFUEBER fuers Bett gedreht.
part = "assembled";

// ============================ ABGELEITET ==========================
ix = sub_x + 2*clearance;
iy = sub_y + 2*clearance;
ih = sub_z + air_top;
ox = ix + 2*wall;
oy = iy + 2*wall;
oz = ih + top_thick;   // + geschlossene Oberseite
$fn = 32;

// ============================ MODULE ==============================

// Umlaufende Nut auf Hoehe z (Deko-Band)
module groove(z) {
    difference() {
        translate([-1, -1, z]) cube([ox + 2, oy + 2, band_h]);
        translate([band_depth, band_depth, z - 1]) cube([ox - 2*band_depth, oy - 2*band_depth, band_h + 2]);
    }
}

// Lueftungsschlitze: nur vertikal an allen vier Seiten (druckbar, kein
// Bridge). Keine Schlitze in der Oberseite -> die liegt beim Druck am Bett.
module vents() {
    n = 9;
    for (i = [1 : n]) {
        sx = ox * i/(n+1) - 1.5;
        translate([sx, -1, 20])             cube([3, wall + 2, oz - 45]);
        translate([sx, oy - wall - 1, 20])  cube([3, wall + 2, oz - 45]);
    }
    m = 9;
    for (j = [1 : m]) {
        sy = oy * j/(m+1) - 1.5;
        translate([-1, sy, 20])             cube([wall + 2, 3, oz - 45]);
        translate([ox - wall - 1, sy, 20])  cube([wall + 2, 3, oz - 45]);
    }
}

// Komplette Haube (unten offen)
module cover() {
    difference() {
        cube([ox, oy, oz]);
        // Innenraum, unten offen
        translate([wall, wall, -1]) cube([ix, iy, ih + 1]);
        // Deko-Baender
        for (z = [25, 45, 65, 85]) groove(z);
        if (vent) vents();
    }
}

// Ein Viertel ausschneiden (qx,qy in {0,1}) und KOPFUEBER fuers Bett drehen
module quarter(qx, qy) {
    // kopfueber: um X drehen, dann auf z=0 anheben
    translate([0, 0, oz])
        rotate([180, 0, 0])
            intersection() {
                cover();
                translate([qx * ox/2, qy * oy/2, -1])
                    cube([ox/2, oy/2, oz + 2]);
            }
}

// ============================ AUSGABE =============================
if      (part == "assembled") cover();
else if (part == "q1")        quarter(0, 0);
else if (part == "q2")        quarter(1, 0);
else if (part == "q3")        quarter(0, 1);
else if (part == "q4")        quarter(1, 1);
