"""Build the outdoor Xueyuan Road graybox from the archived 2D map.

This script crops source tiles and SVG geometry without changing their shapes.
It deliberately does not create indoor maps, entrances, or gameplay collision.
"""

from copy import deepcopy
from hashlib import sha1
from html import escape
import json
from pathlib import Path
import re
import struct
import zlib


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "地图数据" / "二维版本"
OUT = ROOT / "灰盒"
REPO = "https://github.com/RobertYoung446/buaa-simulator"
REPO_COMMIT = "59df24233b64aa0b463fde531ac87051556c5a08"
TILE = 32
ORIGIN_X, ORIGIN_Y = 55, 39
WIDTH, HEIGHT = 64, 42

# Stable IDs from xueyuan.map.json. These are landmarks, not verified doors.
LANDMARKS = [
    ("xueyuan/way/88777864", "北航图书馆"),
    ("xueyuan/way/190430062", "8公寓"),
    ("xueyuan/way/190427801", "7公寓"),
    ("xueyuan/way/190427995", "东区食堂"),
    ("xueyuan/way/190444425", "北京航空航天博物馆"),
    ("xueyuan/way/190444424", "第九馆 / 逸夫楼"),
]


def git_blob_sha(path):
    # The source repository marks text files eol=lf in .gitattributes.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def properties(**items):
    return [{"name": key, "type": "bool" if isinstance(value, bool) else
             "int" if isinstance(value, int) else "string", "value": value}
            for key, value in items.items()]


def points(coords):
    if coords and isinstance(coords[0], (int, float)):
        yield coords
    else:
        for item in coords:
            yield from points(item)


def bounds(feature):
    pts = list(points(feature["geometry"]["coordinates"]))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def polygon_path(feature):
    geometry = feature["geometry"]
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError(f"Expected polygon: {feature['id']}")
    return " ".join(" ".join("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in ring) + " Z"
                              for ring in polygon)
                    for polygon in polygons)


def crop_layer(layer):
    result = deepcopy(layer)
    src_width = layer["width"]
    data = layer["data"]
    result["width"], result["height"] = WIDTH, HEIGHT
    result["data"] = [data[y * src_width + x]
                      for y in range(ORIGIN_Y, ORIGIN_Y + HEIGHT)
                      for x in range(ORIGIN_X, ORIGIN_X + WIDTH)]
    return result


def make_tmj(selected):
    source_tmj_path = SOURCE / "xueyuan.tmj"
    source = json.loads(source_tmj_path.read_text(encoding="utf-8"))
    assert source["tilewidth"] == TILE and source["tileheight"] == TILE
    assert ORIGIN_X + WIDTH <= source["width"] and ORIGIN_Y + HEIGHT <= source["height"]
    objects = []
    for index, (source_id, label) in enumerate(LANDMARKS, 1):
        x0, y0, x1, y1 = bounds(selected[source_id])
        x, y = (x0 + x1) / 2 - ORIGIN_X * TILE, (y0 + y1) / 2 - ORIGIN_Y * TILE
        assert 0 <= x < WIDTH * TILE and 0 <= y < HEIGHT * TILE, source_id
        objects.append({"id": index, "name": label, "type": "source_landmark",
                        "point": True, "x": round(x, 3), "y": round(y, 3),
                        "width": 0, "height": 0, "visible": True,
                        "properties": properties(sourceFeatureId=source_id,
                                                 sourceCategory=selected[source_id]["category"],
                                                 entranceVerified=False)})
    layers = [crop_layer(source["layers"][0]), crop_layer(source["layers"][1]),
              {"id": 3, "name": "source_landmarks", "type": "objectgroup",
               "draworder": "topdown", "visible": True, "opacity": 1,
               "x": 0, "y": 0, "objects": objects}]
    tileset = deepcopy(source["tilesets"][0])
    tileset["image"] = "../地图数据/二维版本/tiles.png"
    result = deepcopy(source)
    result.update(width=WIDTH, height=HEIGHT, layers=layers,
                  nextlayerid=4, nextobjectid=len(objects) + 1,
                  tilesets=[tileset],
                  properties=properties(sceneId="xueyuan_outdoor_source_crop",
                                        sourceRepo=REPO, sourceCommit=REPO_COMMIT,
                                        sourceTmjBlob=git_blob_sha(source_tmj_path),
                                        sourceMapBlob=git_blob_sha(SOURCE / "xueyuan.map.json"),
                                        sourceSvgBlob=git_blob_sha(SOURCE / "xueyuan.svg"),
                                        sourceTileX=ORIGIN_X, sourceTileY=ORIGIN_Y,
                                        metersPerSourceTile=8,
                                        collisionStatus="source draft; not gameplay verified",
                                        attribution="© OpenStreetMap contributors · ODbL 1.0"))
    (OUT / "campus.tmj").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def make_svg(selected):
    source_svg = (SOURCE / "xueyuan.svg").read_text(encoding="utf-8")
    x, y, w, h = ORIGIN_X * TILE, ORIGIN_Y * TILE, WIDTH * TILE, HEIGHT * TILE
    opening = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}" '
               f'width="{w}" height="{h}" role="img" aria-label="学院路二维数据局部灰盒">')
    svg, replacements = re.subn(r"<svg\b[^>]*>", opening, source_svg, count=1)
    assert replacements == 1
    outlines = ['<g id="source-landmark-outlines" fill="none" stroke="#ed7047" stroke-width="6" stroke-linejoin="round">']
    for source_id, label in LANDMARKS:
        outlines.append(f'<path d="{polygon_path(selected[source_id])}"><title>{escape(label)} · {escape(source_id)}</title></path>')
    outlines.append('</g>')
    svg = svg.replace('</svg>', '\n'.join(outlines) + '\n</svg>', 1)
    (OUT / "campus.svg").write_text(svg, encoding="utf-8")


def png_bytes(width, height, pixel):
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(pixel(x, y))
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def make_overview_png(tmj):
    # The source tile preview colors; outlines and labels remain in the SVG.
    colors = [None, (231, 225, 204), (169, 199, 141), (134, 185, 208),
              (213, 198, 176), (197, 148, 114)]
    grid = tmj["layers"][0]["data"]
    scale = 16
    def pixel(x, y):
        gid = grid[(y // scale) * WIDTH + x // scale]
        color = colors[gid]
        if x % scale == 0 or y % scale == 0:
            return tuple(max(0, c - 10) for c in color)
        return color
    (OUT / "campus-overview.png").write_bytes(
        png_bytes(WIDTH * scale, HEIGHT * scale, pixel))


def make_preview(selected):
    items = []
    for source_id, label in LANDMARKS:
        x0, y0, x1, y1 = bounds(selected[source_id])
        x = round((x0 + x1) / 2 - ORIGIN_X * TILE)
        y = round((y0 + y1) / 2 - ORIGIN_Y * TILE)
        items.append(f'<button class="place" data-x="{x}" data-y="{y}">{escape(label)}</button>')
    html = f'''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>北航模拟器 · 学院路二维数据灰盒</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f4f1e9;color:#263741;font:15px/1.6 Arial,"Microsoft YaHei",sans-serif}}
header{{padding:20px 28px;background:#263741;color:white}}h1{{margin:0;font-size:24px}}header p{{margin:4px 0 0;color:#d2dddf}}
main{{max-width:1600px;margin:auto;padding:18px 24px}}.bar{{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:12px}}
button{{border:1px solid #b6c0c1;border-radius:7px;background:#fff;padding:7px 10px;color:#263741;cursor:pointer}}
button:hover{{background:#fce5d9}}.bar label{{margin-left:auto;white-space:nowrap}}.mapbox{{height:min(72vh,960px);overflow:auto;background:#e7e1cc;border:1px solid #cbd1cc;border-radius:10px}}
.mapbox img{{display:block;max-width:none}}.details{{margin-top:14px;display:flex;flex-wrap:wrap;gap:10px}}.pill{{background:#e6e8e1;border-radius:7px;padding:6px 10px}}
p.note{{color:#58676c;margin:10px 0}}a{{color:#315f7a}}
</style>
<header><h1>学院路 · 二维数据局部灰盒</h1><p>从仓库二维地图裁出公寓区—东区食堂—图书馆—博物馆一带；橙色轮廓标出选中的源数据要素。</p></header>
<main><p><a href="试玩.html">▶ 开始校园漫步：移动、碰撞、地点切换与互动</a></p><div class="bar">{''.join(items)}<label>缩放 <input id="zoom" type="range" min="50" max="140" value="80"> <output id="value">80%</output></label></div>
<div class="mapbox" id="mapbox"><img id="map" src="campus.svg" alt="学院路校区二维数据局部灰盒"></div>
<div class="details"><span class="pill">源地图：150 × 148 格</span><span class="pill">本区块：64 × 42 格</span><span class="pill">源比例：8 米/格、32 px/格</span><span class="pill">源瓦片起点：(55, 39)</span></div>
<p class="note">道路、绿地、水体和建筑轮廓取自仓库二维数据。此页查看源地图；试玩页提供三个室外区块、轮廓碰撞与地点互动。室内设计暂缓。</p>
<p class="note">[二维数据来源] <a href="{REPO}/tree/{REPO_COMMIT}/地图数据/二维版本">RobertYoung446/buaa-simulator</a> · © OpenStreetMap contributors · <a href="https://opendatacommons.org/licenses/odbl/1-0/">ODbL 1.0</a></p></main>
<script>
const img=document.getElementById('map'),box=document.getElementById('mapbox'),zoom=document.getElementById('zoom'),value=document.getElementById('value');
function setZoom(){{img.style.width=(2048*Number(zoom.value)/100)+'px';value.textContent=zoom.value+'%';}}zoom.oninput=setZoom;setZoom();
document.querySelectorAll('.place').forEach(button=>button.onclick=()=>{{const scale=Number(zoom.value)/100;box.scrollTo({{left:Number(button.dataset.x)*scale-box.clientWidth/2,top:Number(button.dataset.y)*scale-box.clientHeight/2,behavior:'smooth'}});}});
</script></html>
'''
    (OUT / "预览.html").write_text(html, encoding="utf-8")


def main():
    OUT.mkdir(exist_ok=True)
    map_json = json.loads((SOURCE / "xueyuan.map.json").read_text(encoding="utf-8"))
    features = {f["id"]: f for f in map_json["features"]}
    selected = {}
    for source_id, label in LANDMARKS:
        feature = features[source_id]
        assert feature["properties"].get("name") == label, (source_id, label)
        selected[source_id] = feature
    tmj = make_tmj(selected)
    make_svg(selected)
    make_overview_png(tmj)
    make_preview(selected)
    print(f"Generated source-based campus crop: {WIDTH}×{HEIGHT} tiles at ({ORIGIN_X},{ORIGIN_Y})")
    print("Source TMJ Git blob:", git_blob_sha(SOURCE / "xueyuan.tmj"))
    print("Source feature Git blob:", git_blob_sha(SOURCE / "xueyuan.map.json"))


if __name__ == "__main__":
    main()
