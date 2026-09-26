"""Convert archived campus GeoJSON to editable 2D assets. Python 3, stdlib only."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
ATTRIBUTION = '© OpenStreetMap contributors · ODbL 1.0'
LICENSE = 'https://opendatacommons.org/licenses/odbl/1-0/'
CAMPUSES = [('xueyuan', '学院路', 'campus.geojson'),
            ('shahe', '沙河', 'shahe.geojson'),
            ('hangzhou', '杭州国际校园', 'hangzhou.geojson')]
COLORS = ['#e7e1cc', '#a9c78d', '#86b9d0', '#d5c6b0', '#c59472', '#de645e']


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def points(coords):
    if coords and isinstance(coords[0], (int, float)):
        yield coords
    else:
        for child in coords:
            yield from points(child)


def transform(coords, project):
    if coords and isinstance(coords[0], (int, float)):
        return project(coords)
    return [transform(child, project) for child in coords]


def category(p):
    if p.get('model') == 'flying-roof' or p.get('building') == 'roof':
        return 'roof'
    if p.get('building', 'no') != 'no' or p.get('building:part', 'no') != 'no':
        return 'building'
    if p.get('natural') == 'water' or p.get('water') or p.get('waterway'):
        return 'water'
    if p.get('highway'):
        return 'road'
    if p.get('leisure') or p.get('natural') in ('wood', 'scrub', 'grassland') or p.get('landuse') in ('grass', 'forest', 'meadow', 'recreation_ground'):
        return 'green'
    return 'other'


def rings_of(feature):
    g = feature['geometry']
    if g['type'] == 'Polygon':
        return [g['coordinates']]
    if g['type'] == 'MultiPolygon':
        return g['coordinates']
    return []


def inside_ring(x, y, ring):
    hit = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y):
            cross = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < cross:
                hit = not hit
    return hit


def inside_polygon(x, y, rings):
    return inside_ring(x, y, rings[0]) and not any(inside_ring(x, y, r) for r in rings[1:])


def png(path, width, height, rgb):
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)
    raw = b''.join(b'\x00' + rgb[y * width * 3:(y + 1) * width * 3] for y in range(height))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def palette_image(path, tile):
    colors = [bytes.fromhex(c[1:]) for c in COLORS]
    row = b''.join(c * tile for c in colors)
    png(path, tile * len(colors), tile, row * tile)


def convert(key, name, filename, out, meters, scale):
    source_path = ROOT / '地图数据' / 'GeoJSON' / filename
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes.decode('utf-8-sig'))
    source_features = source['features']
    campus_boundaries = [f for f in source_features if f.get('properties', {}).get('amenity') == 'university'
                         and ('北京航空航天大学' in f['properties'].get('name', '') or 'Beihang' in f['properties'].get('operator', ''))]
    all_points = [p for f in (campus_boundaries or source_features) for p in points(f['geometry']['coordinates'])]
    bounds = source.get('bbox') or [min(p[0] for p in all_points), min(p[1] for p in all_points), max(p[0] for p in all_points), max(p[1] for p in all_points)]
    west, south, east, north = bounds
    latitude = (south + north) / 2
    kx = 6378137 * math.pi / 180 * math.cos(math.radians(latitude))
    ky = 6378137 * math.pi / 180
    if not source.get('bbox') and campus_boundaries:
        west, east = west - 40 / kx, east + 40 / kx
        south, north = south - 40 / ky, north + 40 / ky
    project = lambda p: [round((p[0] - west) * kx * scale, 3), round((north - p[1]) * ky * scale, 3)]
    tile = int(round(meters * scale))
    width = math.ceil((east - west) * kx * scale / tile)
    height = math.ceil((north - south) * ky * scale / tile)
    features = []
    used_ids = set()
    for f in source_features:
        geometry = f['geometry']
        fp = list(points(geometry['coordinates']))
        if max(p[0] for p in fp) < west or min(p[0] for p in fp) > east or max(p[1] for p in fp) < south or min(p[1] for p in fp) > north:
            continue
        identity = f.get('id') or (f.get('properties', {}).get('osm_type', '') + '/' + str(f.get('properties', {}).get('osm_id', ''))).strip('/')
        if not identity:
            identity = 'derived/' + hashlib.sha256(json.dumps(f, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        if identity in used_ids:
            identity += '/' + hashlib.sha256(json.dumps(f, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
        used_ids.add(identity)
        p = f.get('properties', {})
        features.append({'id': key + '/' + identity, 'category': category(p), 'properties': p,
                         'geometry': {'type': geometry['type'], 'coordinates': transform(geometry['coordinates'], project)}})
    metadata = {'schemaVersion': 1, 'campus': key, 'name': name, 'attribution': ATTRIBUTION,
                'license': LICENSE, 'sourceFile': filename, 'sourceSHA256': hashlib.sha256(source_bytes).hexdigest(),
                'sourceMetadata': {k: v for k, v in source.items() if k != 'features'},
                'projection': {'type': 'local-equirectangular', 'originLonLat': [west, north],
                               'referenceLatitude': latitude, 'pixelsPerMeter': scale,
                               'xAxis': 'east', 'yAxis': 'south', 'units': 'pixels'},
                'widthPixels': width * tile, 'heightPixels': height * tile,
                'viewportLonLat': [west, south, east, north], 'inputFeatureCount': len(source_features),
                'extentMethod': 'source-bbox' if source.get('bbox') else 'campus-boundary-bbox-with-40m-margin',
                'grid': {'columns': width, 'rows': height, 'tilePixels': tile, 'metersPerTile': meters},
                'limitations': ['Schematic map, not pixel-art production assets.',
                                'Collision cells use polygon center sampling; thin obstacles need editing.',
                                'Unblocked does not certify walkability; entrances, walls, gates and stairs are not inferred.',
                                'Roofs are visual only; other aggregate building outlines require manual review.',
                                'Features intersecting the viewport are retained; geometries are not clipped.',
                                'Campus bounding rectangle may contain surroundings outside the actual boundary.']}
    save_json(out / f'{key}.map.json', {'metadata': metadata, 'features': features})
    ground = [1] * (width * height)
    blocked = [0] * (width * height)
    rank = {'other': 0, 'green': 1, 'water': 2, 'road': 3, 'building': 4, 'roof': 5}
    gids = {'other': 1, 'green': 2, 'water': 3, 'road': 4, 'building': 5}
    for f in sorted(features, key=lambda v: rank[v['category']]):
        cat = f['category']
        if cat == 'roof':
            continue
        for rings in rings_of(f):
            outer = rings[0]
            x0 = max(0, math.floor(min(p[0] for p in outer) / tile))
            x1 = min(width - 1, math.floor(max(p[0] for p in outer) / tile))
            y0 = max(0, math.floor(min(p[1] for p in outer) / tile))
            y1 = min(height - 1, math.floor(max(p[1] for p in outer) / tile))
            for row in range(y0, y1 + 1):
                for col in range(x0, x1 + 1):
                    if inside_polygon((col + .5) * tile, (row + .5) * tile, rings):
                        idx = row * width + col
                        ground[idx] = gids[cat]
                        if cat in ('building', 'water'):
                            blocked[idx] = 6
        g = f['geometry']
        if cat == 'road' and g['type'] in ('LineString', 'MultiLineString'):
            lines = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates']
            for line in lines:
                for a, b in zip(line, line[1:]):
                    steps = max(1, math.ceil(math.dist(a, b) / (tile / 3)))
                    for i in range(steps + 1):
                        col = math.floor((a[0] + (b[0] - a[0]) * i / steps) / tile)
                        row = math.floor((a[1] + (b[1] - a[1]) * i / steps) / tile)
                        if 0 <= col < width and 0 <= row < height:
                            ground[row * width + col] = 4
    save_json(out / f'{key}.collision.json', {'metadata': metadata, 'encoding': 'row-major, 0=unclassified/open, 1=blocked',
              'cells': [int(v != 0) for v in blocked],
              'obstacles': [{'featureId': f['id'], 'category': f['category'], 'polygons': rings_of(f)}
                            for f in features if f['category'] in ('building', 'water') and rings_of(f)]})
    props = [{'name': 'attribution', 'type': 'string', 'value': ATTRIBUTION},
             {'name': 'license', 'type': 'string', 'value': LICENSE},
             {'name': 'metersPerTile', 'type': 'float', 'value': meters}]
    tiled = {'type': 'map', 'version': '1.10', 'tiledversion': '1.10.2', 'orientation': 'orthogonal',
             'renderorder': 'right-down', 'infinite': False, 'width': width, 'height': height,
             'tilewidth': tile, 'tileheight': tile, 'nextlayerid': 4, 'nextobjectid': 1, 'properties': props,
             'tilesets': [{'firstgid': 1, 'name': 'campus-schematic', 'tilewidth': tile, 'tileheight': tile,
                          'columns': 6, 'tilecount': 6, 'image': 'tiles.png', 'imagewidth': tile * 6, 'imageheight': tile,
                          'tiles': [{'id': i, 'properties': [{'name': 'kind', 'type': 'string', 'value': n}]} for i, n in enumerate(['ground', 'green', 'water', 'road', 'building', 'blocked'])]}],
             'layers': [{'id': 1, 'name': 'ground', 'type': 'tilelayer', 'width': width, 'height': height, 'x': 0, 'y': 0, 'visible': True, 'opacity': 1, 'data': ground},
                        {'id': 2, 'name': 'collision_draft', 'type': 'tilelayer', 'width': width, 'height': height, 'x': 0, 'y': 0, 'visible': False, 'opacity': .5, 'data': blocked},
                        {'id': 3, 'name': 'gameplay_manual', 'type': 'objectgroup', 'visible': True, 'opacity': 1, 'objects': []}]}
    save_json(out / f'{key}.tmj', tiled)
    # Accurate outline preview, retaining courtyards with even-odd filling.
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width*tile} {height*tile}" width="{width*tile}" height="{height*tile}">',
           f'<title>{html.escape(name)}校园二维轮廓</title><desc>{html.escape(ATTRIBUTION)}</desc>',
           '<rect width="100%" height="100%" fill="#e7e1cc"/>']
    fill = {'other': '#e1dcc7', 'green': '#a9c78d', 'water': '#86b9d0', 'road': '#d5c6b0', 'building': '#c59472', 'roof': 'none'}
    labels = []
    for f in sorted(features, key=lambda v: rank[v['category']]):
        cat, g = f['category'], f['geometry']
        polygons = rings_of(f)
        if polygons:
            for rings in polygons:
                d = ' '.join('M' + ' L'.join(f'{x},{y}' for x, y in ring) + ' Z' for ring in rings)
                dash = ' stroke-dasharray="12 8"' if cat == 'roof' else ''
                svg.append(f'<path d="{d}" fill="{fill[cat]}" fill-rule="evenodd" stroke="#796e5f" stroke-width="2"{dash}><title>{html.escape(str(f["properties"].get("name", f["id"])))}</title></path>')
        elif g['type'] in ('LineString', 'MultiLineString') and cat in ('road', 'water'):
            lines = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates']
            for line in lines:
                d = 'M' + ' L'.join(f'{x},{y}' for x, y in line)
                svg.append(f'<path d="{d}" fill="none" stroke="{fill[cat]}" stroke-width="{4*scale if cat == "road" else 2*scale}" stroke-linecap="round"/>')
        name_label = f['properties'].get('name')
        if name_label and cat == 'building' and polygons:
            ring = polygons[0][0][:-1]
            x, y = sum(p[0] for p in ring)/len(ring), sum(p[1] for p in ring)/len(ring)
            labels.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#302d29" stroke="#fff" stroke-width="3" paint-order="stroke">{html.escape(str(name_label))}</text>')
    svg.extend(['<g id="labels">', *labels, '</g>', '</svg>'])
    (out / f'{key}.svg').write_text('\n'.join(svg), encoding='utf-8')
    # Lightweight raster of the tile draft (one tile displayed as 4x4 pixels).
    colors = [bytes.fromhex(c[1:]) for c in COLORS]
    rows = []
    for row in range(height):
        pixels = b''.join(colors[v-1] * 4 for v in ground[row * width:(row+1)*width])
        rows.extend([pixels] * 4)
    png(out / f'{key}.tiles-preview.png', width * 4, height * 4, b''.join(rows))
    return {'campus': key, 'name': name, 'features': len(features), 'columns': width, 'rows': height,
            'blockedCells': sum(v != 0 for v in blocked), 'sourceSHA256': metadata['sourceSHA256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--meters-per-tile', type=float, default=8)
    parser.add_argument('--pixels-per-meter', type=float, default=4)
    args = parser.parse_args()
    if args.meters_per_tile <= 0 or args.pixels_per_meter <= 0:
        parser.error('Scale must be positive.')
    if abs(args.meters_per_tile * args.pixels_per_meter - round(args.meters_per_tile * args.pixels_per_meter)) > 1e-6:
        parser.error('meters-per-tile * pixels-per-meter must be an integer.')
    if args.meters_per_tile * args.pixels_per_meter < 1:
        parser.error('Tile size must be at least one pixel.')
    out = ROOT / '地图数据' / '二维版本'
    out.mkdir(parents=True, exist_ok=True)
    palette_image(out / 'tiles.png', round(args.meters_per_tile * args.pixels_per_meter))
    results = [convert(key, name, filename, out, args.meters_per_tile, args.pixels_per_meter) for key, name, filename in CAMPUSES]
    save_json(out / '转换清单.json', {'schemaVersion': 1, 'attribution': ATTRIBUTION, 'license': LICENSE, 'campuses': results})
    for result in results:
        print(f'{result["name"]}: {result["features"]} features, {result["columns"]}x{result["rows"]} tiles, {result["blockedCells"]} blocked draft cells')


if __name__ == '__main__':
    main()
