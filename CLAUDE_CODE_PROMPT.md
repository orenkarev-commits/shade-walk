# Shade Walk — Rothschild Boulevard, Tel Aviv
## Complete Claude Code Handoff Prompt

---

## WHAT THIS IS

A web app for a parent (architect, Tel Aviv) to find the shadiest path to walk a baby stroller along Rothschild Boulevard. It works like SunSeekr.com (London sun-seeker app) but inverted — instead of finding the sunniest route, we find the shadiest.

The core visual is a **full-screen dark map** with the pedestrian route drawn as a thick coloured line. Each segment of the route is coloured by shade intensity in real time:
- **Deep green** = dense shade (safe for baby)
- **Yellow/orange** = partial shade
- **Red** = full sun exposure (cross-street gaps, avoid lingering)

The time slider and season selector recalculate everything live using real astronomical sun math for 32.07°N (Tel Aviv).

**Reference:** [SunSeekr](https://www.sunseekr.com) — same concept, opposite purpose.

---

## CURRENT STATE (what exists)

A working prototype in a single `index.html` file. It has:
- ✅ Full-screen Leaflet map with CartoDB Dark tiles
- ✅ Correct astronomical sun math for Tel Aviv 32.07°N
- ✅ Colour-coded route segments (shade intensity → colour)
- ✅ Building shadow geometry from real OSM footprints (Overpass API POST)
- ✅ Tree canopy overlays with directional shadow cast
- ✅ Cross-street exposure markers (yellow dots)
- ✅ Time slider (6am–7pm, 30-min steps) + season selector
- ✅ Bottom stats card (shade %, best window, sun altitude)
- ✅ POI markers (benches, water fountains)
- ✅ Floating glass-morphism UI panels

**What's broken / not yet right:**
- ❌ Route walkway coordinates need to be more precisely aligned to the actual left-side pedestrian promenade of Rothschild Boulevard (currently approximated from OSM centreline with a fixed offset)
- ❌ Tree canopy positions need to snap to the real boulevard promenade geometry, not hardcoded lat bands
- ❌ Building heights are mostly estimated — need to connect to TLV GIS or allow manual entry per building
- ❌ No backend — building heights and route geometry are all client-side

---

## TECH STACK TO USE IN CLAUDE CODE

Build this as a **proper web app** with:

```
/
├── index.html          (single entry point)
├── src/
│   ├── main.js         (app bootstrap)
│   ├── map.js          (Leaflet map init + layer management)
│   ├── sun.js          (astronomical sun position math)
│   ├── shade.js        (shade calculation engine)
│   ├── route.js        (route geometry + colour rendering)
│   ├── buildings.js    (OSM Overpass fetch + height DB)
│   ├── data/
│   │   ├── centreline.json   (exact OSM nodes for Rothschild)
│   │   ├── trees.json        (tree segments with density/height)
│   │   ├── heights.json      (manual building height overrides)
│   │   └── pois.json         (benches, water, stops)
├── style.css
├── proxy/
│   ├── proxy.py        (Flask proxy for TLV GIS building heights)
│   └── requirements.txt
└── README.md
```

Use **Vite** for bundling. No React needed — vanilla JS is fine and faster for a map app.

---

## DETAILED SPECIFICATIONS

### 1. MAP

- **Library:** Leaflet.js 1.9.4
- **Tiles:** CartoDB Dark (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`)
- **Center:** `[32.0625, 34.7750]`
- **Default zoom:** 16 (shows full boulevard)
- **Zoom control:** bottom-right
- **The map must be full-screen** (`position: fixed; inset: 0`). All UI floats on top. This is non-negotiable — the map IS the app.

---

### 2. ROUTE GEOMETRY

The route is Rothschild Boulevard's **left-side pedestrian promenade** (walking south from Habima to Neve Tzedek, the left side is the west/NW side).

**Real centreline nodes** (from OSM way 154741757, verified against satellite):
```javascript
const CENTRELINE = [
  [32.06820, 34.77793],  // Habima square (NW / north end)
  [32.06817, 34.77792],
  [32.06672, 34.77746],  // After Allenby crossing
  [32.06667, 34.77745],
  [32.06662, 34.77743],
  [32.06593, 34.77720],  // Balfour area
  [32.06547, 34.77671],  // Shenkin junction
  [32.06543, 34.77667],
  [32.06438, 34.77557],  // Brenner / Independence Hall
  [32.06350, 34.77483],
  [32.06250, 34.77400],  // Herzl
  [32.06150, 34.77320],  // Ahad Ha'am
  [32.06050, 34.77240],
  [32.05950, 34.77170],  // Shadal
  [32.05860, 34.77110],
  [32.05770, 34.77050],  // Florentin
  [32.05660, 34.76990],
  [32.05560, 34.76940],
  [32.05490, 34.76910],  // Neve Tzedek (SE / south end)
];
```

**Left-side walkway offset:** Rothschild runs at ~225° (NE→SW). The left pedestrian promenade is ~8 metres NW of the centreline. Offset each node by approximately:
- `dLat = +0.000055` (northward)
- `dLon = -0.000040` (westward)

**In Claude Code:** fetch the actual OSM way geometry at boot using Overpass to get precise node coordinates, then apply the offset. Don't hardcode if you can get live data.

---

### 3. TREE SEGMENTS

The boulevard has a planted median with ficus trees. Canopy data from site survey (Oren Yudilevitch, architect):

```javascript
const TREE_SEGS = [
  // [startNodeIdx, endNodeIdx, density, heightMetres, label]
  [0,  2,  'trimmed', 12, 'Habima end'],           // Well-trimmed 12m, narrow canopy spread
  [2,  4,  'dense',   12, 'Allenby–Gruzenberg'],   // Dense ficus 12m
  [4,  6,  'dense',   12, 'Café zone'],             // Densest section
  [6,  8,  'sparse',   9, 'Balfour–Shenkin'],      // WEAKEST: sparse 9m trees only
  [8,  10, 'dense',   12, 'Shenkin–Brenner'],
  [10, 12, 'dense',   12, 'Independence Hall'],    // Tallest ficus, best canopy
  [12, 14, 'medium',  12, 'Herzl–Ahad Ha\'am'],
  [14, 16, 'medium',  12, 'Southern stretch'],
  [16, 18, 'sparse',  12, 'Near Neve Tzedek'],
];
```

**Canopy opacity by density:**
- `dense` → 0.62 opacity
- `medium` → 0.43
- `trimmed` → 0.27 (12m height but tight spread — less coverage than dense)
- `sparse` → 0.20

---

### 4. CROSS-STREETS (all fully exposed — no shade when crossing)

```javascript
const CROSS_STREETS = [
  { nodeIdx: 2,  name: 'Allenby' },
  { nodeIdx: 3,  name: 'Gruzenberg' },
  { nodeIdx: 5,  name: 'Balfour' },
  { nodeIdx: 6,  name: 'Shenkin' },
  { nodeIdx: 8,  name: 'Brenner' },
  { nodeIdx: 9,  name: 'Herzl' },
  { nodeIdx: 11, name: "Ahad Ha'am" },
  { nodeIdx: 13, name: 'Shadal' },
  { nodeIdx: 15, name: 'Florentin' },
];
```

Render as yellow dots on the walkway. Tooltip: "⚠ Fully exposed — cross quickly."

---

### 5. POIs (benches and water)

```javascript
const POIS = [
  { nodeIdx: 4,  type: 'bench', label: 'Benches — café zone' },
  { nodeIdx: 5,  type: 'water', label: 'Water fountain' },
  { nodeIdx: 9,  type: 'bench', label: 'Independence Hall benches' },
  { nodeIdx: 11, type: 'water', label: 'Water fountain' },
  { nodeIdx: 13, type: 'bench', label: 'Seating area' },
  { nodeIdx: 15, type: 'bench', label: 'Rest stop' },
];
```

---

### 6. SUN MATH

Astronomical solar position for **Tel Aviv, 32.07°N**. This is the core engine — everything else depends on it.

```javascript
function getSun(hourDecimal, season) {
  // Declination by season (approximate)
  const declDeg = { summer: 23.5, spring: 10, autumn: 5, winter: -23.5 }[season];
  const decl = declDeg * Math.PI / 180;
  const lat  = 32.07 * Math.PI / 180;
  const ha   = (hourDecimal - 12) * 15 * Math.PI / 180; // hour angle

  const sinAlt = Math.sin(lat) * Math.sin(decl) + Math.cos(lat) * Math.cos(decl) * Math.cos(ha);
  const altRad = Math.asin(Math.max(-0.15, sinAlt));
  const altDeg = altRad * 180 / Math.PI;

  const cosAz = (Math.sin(decl) - Math.sin(lat) * sinAlt) / (Math.cos(lat) * Math.cos(altRad));
  let azDeg = Math.acos(Math.max(-1, Math.min(1, cosAz))) * 180 / Math.PI;
  if (hourDecimal > 12) azDeg = 360 - azDeg;

  return {
    alt:       Math.round(altDeg * 10) / 10,   // altitude in degrees
    az:        Math.round(azDeg),               // azimuth in degrees (N=0, E=90)
    shadowLen: altDeg > 0.3 ? 1 / Math.tan(altRad) : 30,  // shadow length multiplier (height × this = shadow length)
    aboveHorizon: altDeg > 0
  };
}
```

**Shadow casting geometry:**
```javascript
function buildingCastPoly(footprintPoly, buildingHeightM, sun) {
  if (!sun.aboveHorizon || buildingHeightM <= 0) return null;
  const az  = sun.az * Math.PI / 180;
  const MPD = 111320; // metres per degree latitude
  const latCos = Math.cos(32.07 * Math.PI / 180);
  // Shadow offset per metre of height:
  const dLat = -Math.cos(az) * buildingHeightM * sun.shadowLen / MPD;
  const dLon =  Math.sin(az) * buildingHeightM * sun.shadowLen / (MPD * latCos);
  // Combine original footprint + shifted footprint into shadow polygon
  return [...footprintPoly, ...footprintPoly.map(p => [p[0] + dLat, p[1] + dLon]).reverse()];
}
```

---

### 7. SHADE CALCULATION

Per tree segment, combine tree canopy + building shadow to produce a shade score 0→1:

```javascript
function calcShade(seg, sun) {
  // Tree canopy base shade
  const canopyOp = { dense: 0.85, medium: 0.65, trimmed: 0.40, sparse: 0.28 }[seg.density];
  const heightBonus = seg.heightM >= 12 ? 1.0 : 0.78;  // 9m trees = less coverage
  const treeShade = canopyOp * heightBonus;

  // Building shadow contribution
  // Morning (sun from ENE, az < 120°): west-flank buildings shade the left walkway heavily
  // Afternoon (sun from SW, az > 220°): east-flank buildings shade right side
  let bldgShade = 0;
  if (sun.aboveHorizon) {
    if (sun.az < 120) {
      // Best building shade window: 6am–10am
      bldgShade = Math.min(0.80, sun.shadowLen * 0.06 * (1 - sun.az / 180));
    } else if (sun.az > 220) {
      bldgShade = 0.10; // Some relief but not on the left walkway
    }
  }

  // Combined — trees and buildings compound each other
  return Math.min(1.0, treeShade * 0.7 + bldgShade * 0.5 + treeShade * bldgShade * 0.3);
}
```

**Shade → colour mapping (SunSeekr-style):**
```javascript
function shadeToColor(shade) {
  if (shade > 0.75) return '#15803d';  // deep shade — safe, go here
  if (shade > 0.55) return '#16a34a';  // good shade
  if (shade > 0.40) return '#65a30d';  // partial shade
  if (shade > 0.25) return '#ca8a04';  // patchy — caution
  if (shade > 0.12) return '#ea580c';  // mostly sun
  return '#dc2626';                     // full sun — avoid / cross-street
}
```

---

### 8. BUILDING HEIGHT DATA

**Source priority (highest wins):**
1. **TLV GIS** — `gisn.tel-aviv.gov.il/arcgis/rest/services/WM/TA5500WM/MapServer` — official cadastral heights, field `k_gova` (height grade 1–7). Needs server-side proxy due to CORS. Currently intermittent.
2. **OSM tags** — `height=` (metres) or `building:levels=` (× 3.2m per floor)
3. **Manual overrides** — stored in `data/heights.json`, keyed by OSM way ID
4. **Block estimates** — fallback by latitude band:

```javascript
const BLOCK_HEIGHTS = [
  { latN: 32.0724, latS: 32.0710, h: 18, notes: 'Near Habima, 5-6fl mixed-use' },
  { latN: 32.0710, latS: 32.0696, h: 14, notes: 'Allenby block, 4-5fl Bauhaus' },
  { latN: 32.0696, latS: 32.0680, h: 16, notes: 'Café zone, 5fl Bauhaus' },
  { latN: 32.0680, latS: 32.0662, h: 12, notes: 'Balfour–Shenkin, 4fl (surveyed)' },
  { latN: 32.0662, latS: 32.0645, h: 15, notes: 'Shenkin–Brenner' },
  { latN: 32.0645, latS: 32.0625, h: 14, notes: 'Independence Hall (surveyed)' },
  { latN: 32.0625, latS: 32.0605, h: 12, notes: 'Herzl–Ahad Ha\'am' },
  { latN: 32.0605, latS: 32.0585, h: 11, notes: 'Southern stretch' },
  { latN: 32.0585, latS: 32.0562, h: 10, notes: 'Near Neve Tzedek' },
  { latN: 32.0562, latS: 32.0540, h:  9, notes: 'Neve Tzedek end, 3fl (surveyed)' },
];
```

**TLV GIS grade → metres:**
```javascript
const GRADE_TO_M = { 1: 6, 2: 9, 3: 12, 4: 16, 5: 20, 6: 28, 7: 36 };
```

**Building footprints** come from Overpass API (POST request):
```
[out:json][timeout:30];
(way["building"](32.053,34.765,32.074,34.782););
out geom;
```

---

### 9. GIS PROXY (Python/Flask)

Build `proxy/proxy.py` — runs locally, bridges browser to TLV GIS (CORS blocked):

```python
# proxy.py
# pip install flask flask-cors requests pyproj
# python proxy.py  →  http://localhost:5001/heights

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from pyproj import Transformer

app = Flask(__name__)
CORS(app)

# EPSG:2039 (Israeli TM) → WGS84
xf = Transformer.from_crs("EPSG:2039", "EPSG:4326", always_xy=True)

GIS_BASE = "https://gisn.tel-aviv.gov.il/arcgis/rest/services/WM/TA5500WM/MapServer"
GRADE_TO_M = {1:6, 2:9, 3:12, 4:16, 5:20, 6:28, 7:36}

# Rothschild bbox in EPSG:2039
ROTHSCHILD_BBOX = "178100,663600,178900,666300"

@app.route("/heights")
def heights():
    # Find the גובה בינוי (building height) layer ID first via /layers
    # Current candidate: layer ~136 in TA5500WM service
    layer = request.args.get("layer", "136")
    r = requests.get(f"{GIS_BASE}/{layer}/query", params={
        "where": "1=1",
        "geometry": ROTHSCHILD_BBOX,
        "geometryType": "esriGeometryEnvelope",
        "outFields": "OBJECTID,k_gova",
        "returnGeometry": "true",
        "outSR": "2039",
        "f": "json"
    }, timeout=10)
    features = r.json().get("features", [])
    out = []
    for f in features:
        attrs = f["attributes"]
        geom  = f.get("geometry", {})
        grade = attrs.get("k_gova") or 3
        h     = GRADE_TO_M.get(int(grade), 12)
        lon, lat = None, None
        if "x" in geom and "y" in geom:
            lon, lat = xf.transform(geom["x"], geom["y"])
        out.append({
            "osmId": attrs["OBJECTID"],
            "h": h, "src": "gis",
            "lat": lat, "lon": lon,
            "notes": f"TLV GIS grade {grade} → {h}m"
        })
    return jsonify(out)

@app.route("/layers")
def layers():
    r = requests.get(f"{GIS_BASE}/layers?f=json", timeout=10)
    return jsonify([{"id": l["id"], "name": l["name"]} for l in r.json().get("layers", [])])

@app.route("/status")
def status():
    try:
        r = requests.get(f"{GIS_BASE}?f=json", timeout=5)
        return jsonify({"ok": r.status_code == 200})
    except:
        return jsonify({"ok": False})

if __name__ == "__main__":
    app.run(port=5001, debug=False)
```

The app calls `http://localhost:5001/heights` on startup if the GIS toggle is on. Heights populate `heightDB` keyed by OSM way ID and override block estimates.

---

### 10. UI DESIGN

Inspired by **SunSeekr + Cosmos.so**. Dark, minimal, map-forward.

**Colour palette:**
- Background: `#0d0d0d`
- Glass panels: `rgba(10,10,10,0.88)` + `backdrop-filter: blur(16px)`
- Borders: `rgba(255,255,255,0.12)`
- Text primary: `#ffffff`
- Text secondary: `rgba(255,255,255,0.5)`
- Shade good: `#15803d` → `#86efac`
- Shade bad: `#ea580c` → `#dc2626`
- Accent (cross-streets): `#fbbf24`

**Layout — everything floats over the full-screen map:**

```
┌─────────────────────────────────────────────────────┐
│  [🌿 Shade Walk]  [━━━●━━━━━━] [8:00am]  [Summer ▼]  │  ← top pill, centered
│                                                       │
│                      MAP                             │
│  ┌──────────────┐              ┌────────────────┐    │
│  │ Legend       │              │ ☀ 8:00 am      │    │  ← floating glass cards
│  │ ■ Deep shade │              │ 42° · ENE       │    │
│  │ ■ Partial    │              └────────────────┘    │
│  │ ■ Full sun ⚠ │                                    │
│  └──────────────┘                                    │
│                                                       │
│  ┌───────────────────────────────────────────────┐   │
│  │ Before 9am — long building shadows cover the  │   │  ← bottom card
│  │ full promenade. Best window of the day.       │   │
│  │ Route shade ━━━━━━━━━━━━━━━━░░░░ 78%          │   │
│  │ 7am–10am  │  142 bldgs  │  42° alt            │   │
│  └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Route rendering — this is the key visual:**
- Each tree segment = one `L.polyline` with `weight: 10`, colour from `shadeToColor()`
- Thin white underline behind each segment for visual continuity
- Yellow `L.circleMarker` at each cross-street node
- Street name labels as `L.divIcon` floating to the side
- Start/end labels: white pill at Habima, dimmer pill at Neve Tzedek

**Controls:**
- Top bar: centred pill, `border-radius: 99px`
- Time slider: `<input type="range" min="6" max="19" step="0.5">` — updates everything on `input` event
- Season: 4 pill buttons, one active at a time
- Layers: Shadows / Trees / Route / Stops toggles (optional, can be in settings panel)

---

### 11. FUNCTIONALITY TO BUILD

**Phase 1 (MVP):**
- [ ] Full-screen Leaflet map, dark tiles
- [ ] Colour-coded route on exact Rothschild walkway geometry
- [ ] Sun math + shade calculation updating live on time slider
- [ ] Building shadows from Overpass
- [ ] Cross-street yellow exposure markers
- [ ] Bottom card with tip text + shade percentage
- [ ] Works on desktop and mobile

**Phase 2:**
- [ ] Click any building → edit height panel (saves to `heights.json` locally)
- [ ] GIS proxy connection in settings
- [ ] "Best time today" recommendation
- [ ] Date picker (not just season — use real declination formula)
- [ ] Share link with time/date encoded in URL hash

**Phase 3 (future):**
- [ ] Other Tel Aviv streets (Dizengoff, Ibn Gabirol, HaYarkon)
- [ ] Route planner: A→B with shadiest path
- [ ] PWA with home screen install for mobile use while walking
- [ ] Push notification: "Now is the best time to walk today"

---

### 12. WHAT TO FIX FIRST IN CLAUDE CODE

The prototype's biggest issues, in priority order:

1. **Route geometry** — the walkway line must sit precisely on the left-side promenade of Rothschild, not floating in space. Use Overpass to fetch the actual boulevard way geometry, extract the left edge (not centreline), or use the centreline with a precisely computed perpendicular offset based on the road's actual bearing at each node.

2. **Tile loading** — use `cdnjs.cloudflare.com` for Leaflet (confirmed working). CartoDB Dark tiles confirmed working. The `invalidateSize()` call after 100ms on boot is required.

3. **Building shadows** — currently the shadow polygons look correct but overlap the route. Render order should be: tiles → building shadows → tree shade → route line → POIs → UI.

4. **Tree canopy position** — tree polygons should follow the walkway path, not be lat-band rectangles. Convert each tree segment into a buffered polyline along the actual walkway nodes.

5. **Height editor** — add a click handler on buildings that opens a floating panel to edit height + source. Persist to localStorage (or a JSON file if running with a dev server).

---

### 13. GETTING THE REAL WALKWAY GEOMETRY

The best approach in Claude Code:

```javascript
// 1. Fetch the Rothschild boulevard way from Overpass
const query = `[out:json][timeout:20];
  way["name"="שד' רוטשילד"]["highway"](32.053,34.769,32.074,34.782);
  out geom;`;

// 2. Get all geometry nodes
// Way 154741757 is one segment, there may be multiple ways making up the full boulevard

// 3. Offset the centreline to the left-side walkway
// Compute bearing at each node pair, then offset perpendicular left by 8m
function offsetPolyline(nodes, offsetMetres) {
  const MPD = 111320;
  return nodes.map((node, i) => {
    const prev = nodes[Math.max(0, i-1)];
    const next = nodes[Math.min(nodes.length-1, i+1)];
    const bearing = Math.atan2(
      (next[1] - prev[1]) * Math.cos(node[0] * Math.PI/180),
      next[0] - prev[0]
    );
    const perpLeft = bearing - Math.PI/2;
    return [
      node[0] + Math.cos(perpLeft) * offsetMetres / MPD,
      node[1] + Math.sin(perpLeft) * offsetMetres / (MPD * Math.cos(node[0] * Math.PI/180))
    ];
  });
}

// 4. Use offsetPolyline(centreline, 8) for the pedestrian walkway
// The 8m offset puts you on the left-side promenade
```

---

### 14. CONTEXT ABOUT THE USER

- **Oren** — registered architect (ARB/RIBA), 10+ years experience, Senior Architect at Roy David Architects (Tel Aviv/Berlin). Based in Tel Aviv.
- Uses this daily to walk baby daughter **Alma** in a stroller along Rothschild.
- Wants the app to eventually cover all major Tel Aviv walking streets.
- Aesthetic sensibility: precise, clean, no decorative clutter. Thinks like an urban planner — plan view, accurate geometry, shadows as cast areas.
- The canvas diagram without a real map is useless to him — it must be a real geographic map.

---

### 15. THE EXISTING index.html

Paste the full `index.html` file contents here (from the prototype). Claude Code can use this as the starting point and refactor into the proper module structure above.

[PASTE THE FULL index.html CONTENTS HERE — the file is ~730 lines]

---

## START COMMAND FOR CLAUDE CODE

```
Build the Shade Walk app for Rothschild Boulevard, Tel Aviv as described in this document. 

Start with:
1. `npm create vite@latest shade-walk -- --template vanilla`
2. Install leaflet: `npm install leaflet`
3. Set up the file structure from section 3
4. Port the existing index.html logic into modules
5. Fix the route geometry first — it must sit precisely on the left-side pedestrian promenade
6. Make it work in the browser with `npm run dev`

The most important thing: the coloured route line must be visually aligned to the actual Rothschild Boulevard left walkway on the real map. Everything else is secondary.
```
