#!/usr/bin/env python3
"""
generate_italy_map.py — Genera il partial PHP con la mappa SVG delle regioni
italiane usata dalla pagina /regioni.php (app/includes/italy-map.php).

Sorgente: GeoJSON dei confini regionali di openpolis/geojson-italy
(https://github.com/openpolis/geojson-italy, dati ISTAT, licenza CC-BY 4.0).
Il file generato è committato nel repository: questo script serve solo se si
vuole rigenerare la mappa (es. con una tolleranza di semplificazione diversa).

Uso:
    curl -L -o /tmp/italy_regions.geojson \
      https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_regions.geojson
    python tools/generate_italy_map.py /tmp/italy_regions.geojson

Proiezione equirettangolare con correzione cos(lat media); semplificazione
Ramer-Douglas-Peucker; gli anelli con area proiettata sotto soglia (isolotti
minori) vengono scartati per contenere il peso del file.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_PATH = REPO_ROOT / "app" / "includes" / "italy-map.php"

WIDTH = 600.0          # larghezza del viewBox
RDP_TOLERANCE = 0.9    # tolleranza di semplificazione (unità del viewBox)
MIN_RING_AREA = 3.0    # area minima (unità² del viewBox) per tenere un anello


def project(lon: float, lat: float, k_lon: float) -> "tuple[float, float]":
    return lon * k_lon, -lat


def rdp(points: "list[tuple[float, float]]", tol: float) -> "list[tuple[float, float]]":
    """Semplificazione Ramer-Douglas-Peucker (iterativa, per evitare limiti di ricorsione)."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        ax, ay = points[start]
        bx, by = points[end]
        dx, dy = bx - ax, by - ay
        seg_len_sq = dx * dx + dy * dy
        max_dist, max_idx = -1.0, -1
        for i in range(start + 1, end):
            px, py = points[i]
            if seg_len_sq == 0:
                dist = math.hypot(px - ax, py - ay)
            else:
                t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
                t = max(0.0, min(1.0, t))
                dist = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if dist > max_dist:
                max_dist, max_idx = dist, i
        if max_dist > tol:
            keep[max_idx] = True
            stack.append((start, max_idx))
            stack.append((max_idx, end))
    return [p for p, k in zip(points, keep) if k]


def ring_area(points: "list[tuple[float, float]]") -> float:
    area = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def path_d(rings: "list[list[tuple[float, float]]]") -> str:
    parts = []
    for ring in rings:
        cmds = [f"M{ring[0][0]:.1f} {ring[0][1]:.1f}"]
        for x, y in ring[1:]:
            cmds.append(f"L{x:.1f} {y:.1f}")
        cmds.append("Z")
        parts.append("".join(cmds))
    return "".join(parts)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    geojson = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    # Bounding box e fattori di scala
    lons, lats = [], []
    for feat in geojson["features"]:
        geom = feat["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            for ring in poly:
                for lon, lat in ring:
                    lons.append(lon)
                    lats.append(lat)
    lat_mid = (min(lats) + max(lats)) / 2
    k_lon = math.cos(math.radians(lat_mid))

    xs = [lon * k_lon for lon in lons]
    ys = [-lat for lat in lats]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    scale = WIDTH / (max_x - min_x)
    height = (max_y - min_y) * scale

    def to_view(lon: float, lat: float) -> "tuple[float, float]":
        x, y = project(lon, lat, k_lon)
        return (x - min_x) * scale, (y - min_y) * scale

    features = []
    for feat in sorted(geojson["features"], key=lambda f: f["properties"]["reg_istat_code"]):
        props = feat["properties"]
        geom = feat["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        rings = []
        for poly in polys:
            # solo l'anello esterno: i buchi sono irrilevanti a questa scala
            outer = [to_view(lon, lat) for lon, lat in poly[0]]
            simplified = rdp(outer, RDP_TOLERANCE)
            if len(simplified) >= 4 and ring_area(simplified) >= MIN_RING_AREA:
                rings.append(simplified)
        if not rings:
            continue
        features.append({
            "istat": props["reg_istat_code"],
            "name": props["reg_name"],
            "d": path_d(rings),
        })

    lines = [
        "<?php",
        "/**",
        " * Mappa SVG delle regioni italiane (partial incluso da app/views/regions.php).",
        " * FILE GENERATO da python/tools/generate_italy_map.py — non modificare a mano.",
        " * Confini: openpolis/geojson-italy (dati ISTAT), licenza CC-BY 4.0.",
        " * Ogni regione è un <path> con data-istat (codice ISTAT a 2 cifre) e",
        " * data-name; colorazione e interazione sono a carico di regions.js.",
        " */",
        "?>",
        f'<svg id="italy-map" viewBox="0 0 {WIDTH:.0f} {height:.0f}" role="img" xmlns="http://www.w3.org/2000/svg"',
        '     aria-label="Mappa dell\'Italia: scelte valide per regione">',
    ]
    for f in features:
        name = f["name"].replace('"', "&quot;")
        lines.append(
            f'  <path class="map-region" data-istat="{f["istat"]}" data-name="{name}" d="{f["d"]}"/>'
        )
    lines.append("</svg>")

    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"Scritto {OUT_PATH} ({size_kb:.0f} KB, {len(features)} regioni)")


if __name__ == "__main__":
    main()
