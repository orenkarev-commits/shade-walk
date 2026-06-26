#!/usr/bin/env python3
"""
proxy.py — Rothschild Shade Walk · TLV GIS Height Proxy
=========================================================
Bridges the browser app to the Tel Aviv municipal GIS server.
Needed because gisn.tel-aviv.gov.il doesn't send CORS headers,
and serves data in EPSG:2039 (Israeli TM) not WGS84.

INSTALL:
    pip install flask requests pyproj flask-cors

RUN:
    python proxy.py

Then in the app → GIS Connect tab → click "Connect to GIS proxy".
The app will call http://localhost:5001/heights and populate
all building heights from official TLV cadastral data.

ENDPOINTS:
    GET /heights          — heights for Rothschild bbox
    GET /heights?bbox=... — custom bbox in EPSG:2039
    GET /status           — GIS server status check
"""

import sys
import json
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False
    print("WARNING: pyproj not installed. Coordinates won't be converted.")
    print("Install with: pip install pyproj")

app = Flask(__name__)
CORS(app)  # Allow browser requests from file:// and localhost

# ── TLV GIS CONFIG ──────────────────────────────────────────────────
# TA/5500 building height plan — layer ID TBD (server intermittent)
# When the server is live, find the גובה בינוי layer ID from:
# https://gisn.tel-aviv.gov.il/arcgis/rest/services/WM/TA5500WM/MapServer/layers
# Current candidates: check layers near ID 130–145

GIS_BASE = "https://gisn.tel-aviv.gov.il/arcgis/rest/services/WM/TA5500WM/MapServer"
LAYER_ID = 136  # UPDATE THIS when you confirm the גובה בינוי layer ID

# Rothschild Boulevard bounding box in EPSG:2039 (Israeli Transverse Mercator)
# SW corner → NE corner: from Neve Tzedek to Habima
ROTHSCHILD_BBOX_2039 = "178100,663600,178900,666300"

# k_gova grade → approximate height in metres
# Grade is a planning zone classification from TA/5500
GRADE_TO_METRES = {
    1:  6,   # up to 2 floors
    2:  9,   # 3 floors
    3: 12,   # 4 floors
    4: 16,   # 5 floors
    5: 20,   # 6-7 floors
    6: 28,   # 8-9 floors
    7: 36,   # 10+ floors
}

# Coordinate transformer: EPSG:2039 → WGS84
if HAS_PYPROJ:
    transformer = Transformer.from_crs("EPSG:2039", "EPSG:4326", always_xy=True)


def itm_to_wgs84(x, y):
    """Convert Israeli TM (EPSG:2039) coordinates to WGS84 lat/lon."""
    if HAS_PYPROJ:
        lon, lat = transformer.transform(x, y)
        return round(lat, 6), round(lon, 6)
    # Rough approximation if pyproj not available
    # NOT accurate — install pyproj for production use
    lat = (y - 614000) / 111320 + 31.0
    lon = (x - 178000) / (111320 * 0.857) + 34.77
    return round(lat, 5), round(lon, 5)


def ring_to_wgs84(ring):
    """Convert a polygon ring from EPSG:2039 to WGS84."""
    return [list(itm_to_wgs84(pt[0], pt[1])) for pt in ring]


# ── ROUTES ──────────────────────────────────────────────────────────

@app.route("/status")
def status():
    """Check if TLV GIS server is reachable."""
    try:
        r = requests.get(
            f"{GIS_BASE}?f=json",
            timeout=5
        )
        return jsonify({
            "gis_reachable": r.status_code == 200,
            "status_code": r.status_code,
            "layer_url": f"{GIS_BASE}/{LAYER_ID}"
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"gis_reachable": False, "error": str(e)}), 503


@app.route("/heights")
def heights():
    """
    Fetch building heights from TLV GIS for Rothschild area.
    Returns list of {osmId, h, src, lat, lon, notes} objects.
    The browser app ingests this and populates HEIGHT_DB.

    Query params:
        bbox  — optional, EPSG:2039 envelope (xmin,ymin,xmax,ymax)
        layer — optional, override GIS layer ID
    """
    bbox  = request.args.get("bbox",  ROTHSCHILD_BBOX_2039)
    layer = request.args.get("layer", str(LAYER_ID))

    url = f"{GIS_BASE}/{layer}/query"
    params = {
        "where":        "1=1",
        "geometry":     bbox,
        "geometryType": "esriGeometryEnvelope",
        "spatialRel":   "esriSpatialRelIntersects",
        "outFields":    "OBJECTID,k_gova,MaxGovaInc",
        "returnGeometry": "true",
        "outSR":        "2039",   # keep in ITM, we convert ourselves
        "f":            "json",
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if "error" in data:
            return jsonify({
                "error": "GIS returned error",
                "detail": data["error"],
                "tip": f"Check layer ID. Try: {GIS_BASE}/layers"
            }), 502

        features = data.get("features", [])
        out = []

        for feat in features:
            attrs = feat.get("attributes", {})
            geom  = feat.get("geometry", {})

            obj_id = attrs.get("OBJECTID")
            k_gova = attrs.get("k_gova") or attrs.get("MaxGovaInc") or 3
            h_m    = GRADE_TO_METRES.get(int(k_gova), 12)

            # Get centroid from geometry
            lat, lon = None, None
            if "x" in geom and "y" in geom:
                lat, lon = itm_to_wgs84(geom["x"], geom["y"])
            elif "rings" in geom and geom["rings"]:
                ring = geom["rings"][0]
                cx = sum(p[0] for p in ring) / len(ring)
                cy = sum(p[1] for p in ring) / len(ring)
                lat, lon = itm_to_wgs84(cx, cy)

            # Convert polygon rings to WGS84
            poly_wgs84 = None
            if "rings" in geom and geom["rings"]:
                poly_wgs84 = ring_to_wgs84(geom["rings"][0])

            out.append({
                "osmId":    obj_id,       # GIS OBJECTID (not OSM ID — used as key)
                "h":        h_m,
                "src":      "gis",
                "lat":      lat,
                "lon":      lon,
                "poly":     poly_wgs84,   # footprint in WGS84 for map overlay
                "k_gova":   int(k_gova),
                "notes":    f"TLV GIS TA/5500 grade {k_gova} → {h_m}m"
            })

        return jsonify(out)

    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "Cannot reach TLV GIS server",
            "url": url,
            "tip": "Server may be down (returns 503 intermittently). Try again later."
        }), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "TLV GIS request timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/layers")
def list_layers():
    """List all layers in TA5500WM to help find the correct layer ID."""
    try:
        r = requests.get(f"{GIS_BASE}/layers?f=json", timeout=10)
        data = r.json()
        layers_summary = []
        for lyr in data.get("layers", []):
            layers_summary.append({
                "id":   lyr.get("id"),
                "name": lyr.get("name"),
                "type": lyr.get("type"),
                "geom": lyr.get("geometryType"),
            })
        return jsonify({"layers": layers_summary, "total": len(layers_summary)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── MAIN ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Rothschild Shade Walk — TLV GIS Proxy")
    print("=" * 60)
    print(f"  GIS base:  {GIS_BASE}")
    print(f"  Layer ID:  {LAYER_ID}  (update if needed — run /layers to check)")
    print(f"  pyproj:    {'installed ✓' if HAS_PYPROJ else 'MISSING — install: pip install pyproj'}")
    print()
    print("  Endpoints:")
    print("    http://localhost:5001/status   — GIS server reachable?")
    print("    http://localhost:5001/layers   — list all TA5500WM layers")
    print("    http://localhost:5001/heights  — Rothschild building heights")
    print()
    print("  In the app: GIS Connect tab → click 'Connect to GIS proxy'")
    print("=" * 60)
    app.run(host="localhost", port=5001, debug=False)
