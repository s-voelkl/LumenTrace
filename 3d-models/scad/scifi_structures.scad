// --- LumenTrace Sci-Fi-Strukturen: Kraftwerke & Strommasten ---
// Erweiterung der Skyline: Kuehltuerme, Reaktorkuppel, Tanks, ein
// kompletter Kraftwerks-Komplex, Hochspannungsmasten und ein
// auskragendes Sci-Fi-Hochhaus. Diese duerfen Stuetzen brauchen.
// Alle Masse in Millimetern (mm).

$fn = 48;
wall = 1.6;

// Ausgabe-Auswahl:
// "all" | "cooling_tower" | "reactor" | "chimney" | "tank"
// | "power_plant" | "pylon" | "cantilever_tower" | "reactor_spire"
show = "all";

// ============================ HELFER ==============================

// Strebe (Zylinder) zwischen zwei Punkten p1 und p2
module strut(p1, p2, d = 1.6) {
    v = [p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]];
    len = norm(v);
    if (len > 0.01) {
        translate(p1)
            // ausrichten entlang v
            rotate([0, acos(v[2]/len), atan2(v[1], v[0])])
                cylinder(h = len, d = d, $fn = 6);
    }
}

// Umlaufende Nut (Deko-Band) auf einem Zylinder
module ring_groove(z, r, depth = 1.0, h = 2.5) {
    translate([0, 0, z])
        rotate_extrude($fn = 64)
            translate([r - depth, 0]) square([depth + 0.1, h]);
}

// ============================ KUEHLTURM ===========================
// Hyperboloid-Schale (breit unten, Taille, leicht ausgestellt oben).
module cooling_tower(h = 90, r_base = 30, r_waist = 19, r_top = 24) {
    // Profil-Stuetzpunkte (radius, hoehe)
    pts_out = [
        [r_base,        0],
        [r_base*0.9,    h*0.12],
        [r_waist,       h*0.45],
        [r_waist*1.05,  h*0.7],
        [r_top,         h]
    ];
    pts_in = [ for (i = [len(pts_out)-1 : -1 : 0]) [max(pts_out[i][0]-wall, 0.5), pts_out[i][1]] ];
    rotate_extrude($fn = 80)
        polygon(concat(pts_out, pts_in));
}

// ============================ REAKTORKUPPEL =======================
module reactor_dome(r = 24, base_h = 20) {
    // Sockel-Zylinder + Halbkugel-Kuppel, hohl
    difference() {
        union() {
            cylinder(h = base_h, r = r);
            translate([0, 0, base_h]) sphere(r = r);
        }
        // aushoehlen
        translate([0, 0, -1]) cylinder(h = base_h + 1, r = r - wall);
        translate([0, 0, base_h]) sphere(r = r - wall);
        // unten offen bleibt durch die Bohrung
    }
    // Deko-Ringe am Sockel
    for (z = [6, 13]) ring_groove(z, r);
}

// Kuppel mit Antennenspitze (Variante)
module reactor_spire() {
    reactor_dome();
    translate([0, 0, 20 + 24]) cylinder(h = 22, d1 = 3, d2 = 0.6, $fn = 4);
}

// ============================ SCHORNSTEIN =========================
module chimney(h = 95, r1 = 9, r2 = 6) {
    difference() {
        cylinder(h = h, r1 = r1, r2 = r2);
        translate([0, 0, -1]) cylinder(h = h + 2, r1 = r1 - wall, r2 = r2 - wall);
    }
    // Warnstreifen als Ringe oben
    for (z = [h-8, h-16, h-24]) ring_groove(z, r2 + (r1-r2)*(h-z)/h);
}

// ============================ TANK ================================
module tank(h = 30, r = 14) {
    difference() {
        union() {
            cylinder(h = h, r = r);
            translate([0, 0, h]) scale([1, 1, 0.4]) sphere(r = r); // gewoelbter Deckel
        }
        translate([0, 0, -1]) cylinder(h = h, r = r - wall);
    }
    for (z = [8, 18]) ring_groove(z, r);
}

// ============================ KRAFTWERK-KOMPLEX ===================
module power_plant() {
    // Grundplatte
    plate = [150, 90];
    translate([-plate[0]/2, -plate[1]/2, 0]) cube([plate[0], plate[1], 4]);

    // zwei Kuehltuerme
    translate([-42,  18, 4]) cooling_tower(h = 80, r_base = 26, r_waist = 16, r_top = 21);
    translate([-42, -22, 4]) cooling_tower(h = 80, r_base = 26, r_waist = 16, r_top = 21);
    // Reaktorkuppel
    translate([18, 0, 4]) reactor_dome(r = 22, base_h = 16);
    // Schornstein
    translate([55, 22, 4]) chimney(h = 90, r1 = 8, r2 = 5);
    // Tankgruppe
    translate([55, -18, 4]) tank(h = 26, r = 12);
    translate([55, -42, 4]) tank(h = 20, r = 9);
    // ein paar Verbindungsrohre (Streben)
    strut([18, 0, 14], [42, 22, 12], 2.5);
    strut([-16, 0, 12], [10, 0, 12], 2.5);
}

// ============================ STROMMAST (PYLON) ===================
// Stilisierter Gittermast: 4 verjuengte Beine, X-Streben in Ebenen,
// zwei Ausleger-Kreuze mit Isolator-Stummeln, Spitze.
module power_pylon(h = 120) {
    base = 22;   // halbe Fussbreite
    topw = 6;    // halbe Kopfbreite
    levels = 6;

    // Beinpositionen als Funktion der Hoehe (lineare Verjuengung)
    function half_at(z) = base + (topw - base) * (z/h);
    corners = [[1,1],[1,-1],[-1,-1],[-1,1]];

    // 4 Beine
    for (c = corners)
        for (i = [0 : levels-1]) {
            z0 = h * i/levels;   z1 = h * (i+1)/levels;
            p0 = [c[0]*half_at(z0), c[1]*half_at(z0), z0];
            p1 = [c[0]*half_at(z1), c[1]*half_at(z1), z1];
            strut(p0, p1, 2.4);
        }

    // X-Streben in jeder Ebene auf allen 4 Seiten
    for (i = [0 : levels-1]) {
        z0 = h * i/levels;   z1 = h * (i+1)/levels;
        for (s = [0:3]) {
            a = corners[s]; b = corners[(s+1)%4];
            pa0 = [a[0]*half_at(z0), a[1]*half_at(z0), z0];
            pa1 = [a[0]*half_at(z1), a[1]*half_at(z1), z1];
            pb0 = [b[0]*half_at(z0), b[1]*half_at(z0), z0];
            pb1 = [b[0]*half_at(z1), b[1]*half_at(z1), z1];
            strut(pa0, pb1, 1.5);
            strut(pb0, pa1, 1.5);
            strut(pa1, pb1, 1.5); // horizontale Verbindung oben
        }
    }

    // zwei Ausleger-Ebenen (Cross-Arms) mit Isolator-Stummeln
    for (z = [h*0.62, h*0.82]) {
        arm = (z < h*0.7) ? 34 : 26;
        hw = half_at(z);
        for (sgn = [-1, 1]) {
            tip = [sgn*arm, 0, z];
            strut([sgn*hw, hw, z], tip, 2.0);
            strut([sgn*hw, -hw, z], tip, 2.0);
            strut([sgn*hw, 0, z+5], tip, 2.0);
            // Isolator am Auslegerende (Stummel + haengende Kugel)
            translate([sgn*arm, 0, z]) cylinder(h = 5, d = 3, $fn = 6);
            translate([sgn*arm, 0, z-5]) sphere(d = 4);
        }
    }
    // Spitze
    translate([0, 0, h]) cylinder(h = 16, d1 = 5, d2 = 0.6, $fn = 4);
    translate([0, 0, h]) cube([2*topw+2, 1.5, 1.5], center = true);
}

// ============================ AUSKRAGENDES HOCHHAUS ===============
// Sci-Fi-Turm mit auskragendem Obergeschoss (braucht Stuetzen).
module cantilever_tower() {
    w = 34; d = 28;
    // Schaft
    difference() {
        cube([w, d, 90]);
        translate([wall, wall, -1]) cube([w-2*wall, d-2*wall, 90]);
    }
    // auskragendes Obergeschoss (ragt seitlich heraus -> Support)
    translate([-14, -6, 70])
        difference() {
            cube([w+28, d+12, 22]);
            translate([wall, wall, -1]) cube([w+28-2*wall, d+12-2*wall, 22]);
        }
    // Dachaufbau + schraege Antenne
    translate([0, 0, 92]) cube([w, d, 8]);
    translate([w/2, d/2, 100]) rotate([0, 20, 0]) cylinder(h = 30, d1 = 3, d2 = 0.5, $fn = 4);
}

// ============================ AUSGABE =============================
if (show == "cooling_tower")      cooling_tower();
else if (show == "reactor")       reactor_dome();
else if (show == "reactor_spire") reactor_spire();
else if (show == "chimney")       chimney();
else if (show == "tank")          tank();
else if (show == "power_plant")   power_plant();
else if (show == "pylon")         power_pylon();
else if (show == "cantilever_tower") cantilever_tower();
else {
    cooling_tower();
    translate([75, 0, 0])  reactor_spire();
    translate([130, 0, 0]) chimney();
    translate([165, 0, 0]) tank();
    translate([240, 0, 0]) power_pylon();
    translate([320, 0, 0]) cantilever_tower();
}
