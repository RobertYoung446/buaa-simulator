"""Generate the first playable-scale graybox without modifying the OSM maps.

Run from any directory: python generate_graybox.py
The scene definitions below are the editable source; TMJ, SVG and PNG are outputs.
"""

from collections import deque
from html import escape
import json
from pathlib import Path
import struct
import zlib


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "灰盒" / "旧版草稿"
TILE = 32
REACH = 40  # Player center to an interaction anchor, in scene pixels.

# Tile IDs are deliberately shared by outdoor and indoor TMJ files.
TILES = {
    1: ("草地", "#b9c9a7"),
    2: ("绿篱", "#789987"),
    3: ("主路", "#d6d2c7"),
    4: ("辅路", "#e8dfca"),
    5: ("宿舍体块", "#8d9ab0"),
    6: ("教学楼体块", "#8d9ab0"),
    7: ("食堂体块", "#8d9ab0"),
    8: ("活动室体块", "#8d9ab0"),
    9: ("墙", "#5e6c76"),
    10: ("宿舍地面", "#e5ddd0"),
    11: ("教室地面", "#e6e4db"),
    12: ("活动室地面", "#deded4"),
    13: ("木家具", "#bd967b"),
    14: ("软家具", "#b7a5a0"),
    15: ("器材", "#8ba6a4"),
    16: ("地标体块", "#a798a6"),
    17: ("门口", "#efb66d"),
    18: ("花坛", "#a9b894"),
    19: ("碰撞标记", "#d66f67"),
}


def rect(grid, x, y, w, h, tile):
    for row in range(y, y + h):
        for col in range(x, x + w):
            if not (0 <= row < len(grid) and 0 <= col < len(grid[0])):
                raise ValueError(f"rectangle outside map: {(x, y, w, h)}")
            grid[row][col] = tile


def feature(fid, label, x, y, w, h, tile, *, action=None, anchor=None,
            target=None, target_spawn=None):
    return dict(id=fid, label=label, x=x, y=y, w=w, h=h, tile=tile,
                action=action, anchor=anchor, target=target,
                target_spawn=target_spawn)


def campus():
    w, h = 46, 30
    ground = [[1] * w for _ in range(h)]
    scenery = [[0] * w for _ in range(h)]
    blocked = [[0] * w for _ in range(h)]
    for r in [(7, 12, 33, 3), (7, 10, 2, 3), (23, 10, 2, 4),
              (27, 14, 2, 14), (19, 25, 10, 2), (19, 26, 20, 2),
              (38, 24, 2, 4),
              (38, 10, 2, 3)]:
        rect(ground, *r, 3)
    rect(ground, 14, 15, 16, 4, 4)  # Small orientation plaza.
    rect(ground, 27, 15, 2, 13, 3)
    for r in [(2, 15, 7, 3), (32, 15, 5, 3), (3, 26, 7, 2)]:
        rect(ground, *r, 18)
    buildings = [
        feature("dorm", "宿舍", 3, 3, 9, 7, 5,
                action="进入宿舍", anchor=(7, 9), target="dorm_room",
                target_spawn=(5, 7)),
        feature("teaching", "教学楼", 18, 3, 12, 7, 6,
                action="进入公共教室", anchor=(23, 9), target="classroom",
                target_spawn=(7, 9)),
        feature("museum", "航空航天博物馆\n辨识地标", 34, 3, 9, 7, 16),
        feature("dining", "食堂\n首版外观", 14, 19, 10, 6, 7,
                action="查看食堂", anchor=(19, 24)),
        feature("club", "社团活动室", 34, 19, 9, 6, 8,
                action="进入活动室", anchor=(38, 24), target="club_room",
                target_spawn=(7, 9)),
    ]
    for b in buildings:
        rect(scenery, b["x"], b["y"], b["w"], b["h"], b["tile"])
        rect(blocked, b["x"], b["y"], b["w"], b["h"], 1)
        if b["action"]:
            ax, ay = b["anchor"]
            rect(scenery, ax, ay, 2, 1, 17)
    for r in [(2, 15, 7, 3), (32, 15, 5, 3), (3, 26, 7, 2)]:
        rect(blocked, *r, 1)
    return dict(id="campus", title="学院路 · 迎新灰盒区块", width=w, height=h,
                ground=ground, scenery=scenery, blocked=blocked,
                features=buildings, spawn=(7, 11), floor="户外",
                note="位置关系参考学院路校园资料；步行距离与入口为玩法压缩，非实测平面图。")


def room(scene_id, title, w, h, floor_tile, furniture, door_x, spawn,
         campus_spawn):
    ground = [[floor_tile] * w for _ in range(h)]
    scenery = [[0] * w for _ in range(h)]
    blocked = [[0] * w for _ in range(h)]
    for x, y, rw, rh in [(0, 0, w, 1), (0, 0, 1, h),
                         (w - 1, 0, 1, h), (0, h - 1, w, 1)]:
        rect(scenery, x, y, rw, rh, 9)
        rect(blocked, x, y, rw, rh, 1)
    rect(scenery, door_x, h - 1, 2, 1, 17)
    rect(blocked, door_x, h - 1, 2, 1, 0)
    for f in furniture:
        rect(scenery, f["x"], f["y"], f["w"], f["h"], f["tile"])
        rect(blocked, f["x"], f["y"], f["w"], f["h"], 1)
    exit_feature = feature("exit", "返回校园", door_x, h - 1, 2, 1, 17,
                           action="返回校园", anchor=(door_x, h - 1),
                           target="campus", target_spawn=campus_spawn)
    return dict(id=scene_id, title=title, width=w, height=h,
                ground=ground, scenery=scenery, blocked=blocked,
                features=furniture + [exit_feature], spawn=spawn, floor="室内",
                note="功能区与通道按 32 px 网格手工规划；家具仅作体块与交互锚点。")


SCENES = [
    campus(),
    room("dorm_room", "宿舍 · 床与工作角", 12, 10, 10, [
        feature("bed", "床", 2, 2, 2, 2, 14, action="查看床", anchor=(2, 3)),
        feature("desk", "书桌", 7, 2, 3, 2, 13, action="查看书桌", anchor=(8, 3)),
        feature("bookshelf", "书架", 2, 6, 2, 1, 13, action="查看书架", anchor=(2, 6)),
        feature("wardrobe", "衣柜", 9, 6, 1, 2, 13),
    ], 5, (5, 7), (7, 10)),
    room("classroom", "公共教室 · 课程空间", 16, 12, 11, [
        feature("board", "讲台 / 黑板", 6, 1, 4, 1, 15,
                action="查看课程板", anchor=(7, 1)),
        feature("desk_a", "课桌", 3, 4, 2, 1, 13),
        feature("desk_b", "课桌", 7, 4, 2, 1, 13),
        feature("desk_c", "课桌", 11, 4, 2, 1, 13),
        feature("desk_d", "课桌", 3, 7, 2, 1, 13),
        feature("desk_e", "课桌", 7, 7, 2, 1, 13),
        feature("desk_f", "课桌", 11, 7, 2, 1, 13),
    ], 7, (7, 9), (23, 10)),
    room("club_room", "社团活动室 · 制作与展示", 16, 12, 12, [
        feature("noticeboard", "公告板", 6, 1, 4, 1, 15,
                action="查看公告板", anchor=(7, 1)),
        feature("supply", "材料架", 2, 2, 2, 2, 13,
                action="查看材料架", anchor=(3, 3)),
        feature("display", "展示架", 12, 2, 2, 2, 13,
                action="查看展示架", anchor=(12, 3)),
        feature("workbench", "工作台", 6, 4, 4, 2, 15,
                action="使用工作台", anchor=(7, 5)),
        feature("sofa", "休息角", 2, 8, 3, 1, 14),
    ], 7, (7, 9), (38, 25)),
]


def validate():
    scenes_by_id = {s["id"]: s for s in SCENES}
    ids = set(scenes_by_id)
    for scene in SCENES:
        w, h = scene["width"], scene["height"]
        sx, sy = scene["spawn"]
        assert scene["blocked"][sy][sx] == 0, (scene["id"], "blocked spawn")
        seen = {(sx, sy)}
        queue = deque([(sx, sy)])
        while queue:
            x, y = queue.popleft()
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if (0 <= nx < w and 0 <= ny < h
                        and not scene["blocked"][ny][nx] and (nx, ny) not in seen):
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        for f in scene["features"]:
            if f["target"]:
                assert f["target"] in ids, (scene["id"], f["id"], "bad target")
                tx, ty = f["target_spawn"]
                destination = scenes_by_id[f["target"]]
                assert (0 <= tx < destination["width"] and 0 <= ty < destination["height"]
                        and not destination["blocked"][ty][tx]), (scene["id"], f["id"], "blocked arrival")
            if f["action"]:
                ax, ay = f["anchor"]
                assert 0 <= ax < w and 0 <= ay < h
                # A player can stand on the anchor or at one cardinal tile away.
                approach = [(ax, ay), (ax - 1, ay), (ax + 1, ay),
                            (ax, ay - 1), (ax, ay + 1)]
                assert any(p in seen for p in approach), (scene["id"], f["id"], "unreachable")
        assert len(seen) > 1, scene["id"]
        scene["reachableCells"] = len(seen)
        if scene["id"] == "campus":
            # The four intended door approaches must share the painted route,
            # even though players may later be allowed to cut across grass.
            route = {scene["spawn"]: 0}
            road_queue = deque([scene["spawn"]])
            while road_queue:
                x, y = road_queue.popleft()
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if (0 <= nx < w and 0 <= ny < h and (nx, ny) not in route
                            and not scene["blocked"][ny][nx]
                            and scene["ground"][ny][nx] in (3, 4)):
                        route[(nx, ny)] = route[(x, y)] + 1
                        road_queue.append((nx, ny))
            for f in scene["features"]:
                if f["action"]:
                    approach = (f["anchor"][0], f["anchor"][1] + 1)
                    assert approach in route, (f["id"], "painted route disconnected")
                    f["routeTiles"] = route[approach]


def png_bytes(width, height, rgb):
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(rgb(x, y))
    def chunk(tag, payload):
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


def make_tileset():
    colors = [rgb(TILES[i][1]) for i in range(1, 20)]
    def pixel(x, y):
        col, row = x // TILE, y // TILE
        idx = row * 5 + col
        color = colors[idx] if idx < len(colors) else (255, 255, 255)
        if x % TILE == 0 or y % TILE == 0:
            return tuple(max(0, v - 20) for v in color)
        if idx == 16 and (x % TILE in (3, 4, 27, 28)):
            return (248, 223, 176)
        return color
    (OUT / "graybox-tiles.png").write_bytes(png_bytes(5 * TILE, 4 * TILE, pixel))


def make_overview_png(scene):
    """Small dependency-free raster check of layout and anchor visibility."""
    w, h = scene["width"], scene["height"]
    anchors = [((f["anchor"][0] + .5) * TILE,
                (f["anchor"][1] + .5) * TILE)
               for f in scene["features"] if f["action"]]
    spawn = ((scene["spawn"][0] + .5) * TILE,
             (scene["spawn"][1] + .5) * TILE)
    palette = {i: rgb(color) for i, (_, color) in TILES.items()}
    def pixel(x, y):
        if (x - spawn[0]) ** 2 + (y - spawn[1]) ** 2 <= 9 ** 2:
            return (49, 99, 132)
        if any((x - ax) ** 2 + (y - ay) ** 2 <= 7 ** 2 for ax, ay in anchors):
            return (255, 245, 212)
        tile = scene["scenery"][y // TILE][x // TILE] or scene["ground"][y // TILE][x // TILE]
        color = palette[tile]
        if x % TILE == 0 or y % TILE == 0:
            return tuple(max(0, v - 19) for v in color)
        return color
    (OUT / f"{scene['id']}-overview.png").write_bytes(
        png_bytes(w * TILE, h * TILE, pixel))


def props(**kwargs):
    result = []
    for k, v in kwargs.items():
        if v is not None:
            result.append({"name": k, "type": "bool" if isinstance(v, bool) else "int" if isinstance(v, int) else "string", "value": v})
    return result


def tmj(scene):
    w, h = scene["width"], scene["height"]
    layers = []
    for i, (name, grid, visible) in enumerate([
        ("ground", scene["ground"], True),
        ("scenery", scene["scenery"], True),
        ("collision", [[19 if v else 0 for v in row] for row in scene["blocked"]], False),
    ], 1):
        layers.append({"id": i, "name": name, "type": "tilelayer", "width": w, "height": h,
                       "opacity": 1, "visible": visible, "x": 0, "y": 0,
                       "data": [value for row in grid for value in row]})
    objects = [{"id": 1, "name": "player_spawn", "type": "spawn", "point": True,
                "x": (scene["spawn"][0] + .5) * TILE,
                "y": (scene["spawn"][1] + .5) * TILE,
                "width": 0, "height": 0, "visible": True}]
    for i, f in enumerate(scene["features"], 2):
        p = props(stableId=f["id"], label=f["label"].replace("\n", " / "),
                  action=f["action"], targetScene=f["target"],
                  interactionRadius=REACH if f["action"] else None)
        if f["target_spawn"]:
            tx, ty = f["target_spawn"]
            p += props(targetTileX=tx, targetTileY=ty)
        if f["anchor"]:
            ax, ay = f["anchor"]
            p += props(anchorX=(ax + .5) * TILE, anchorY=(ay + .5) * TILE)
        objects.append({"id": i, "name": f["id"], "type": "entrance" if f["target"] else "interactable" if f["action"] else "landmark",
                        "x": f["x"] * TILE, "y": f["y"] * TILE,
                        "width": f["w"] * TILE, "height": f["h"] * TILE,
                        "visible": True, "properties": p})
    layers.append({"id": 4, "name": "gameplay", "type": "objectgroup", "draworder": "topdown",
                   "opacity": 1, "visible": True, "x": 0, "y": 0, "objects": objects})
    data = {"type": "map", "version": "1.10", "tiledversion": "1.11.2",
            "orientation": "orthogonal", "renderorder": "right-down", "infinite": False,
            "width": w, "height": h, "tilewidth": TILE, "tileheight": TILE,
            "nextlayerid": 5, "nextobjectid": len(objects) + 1,
            "properties": props(sceneId=scene["id"], artScale="32 px/tile",
                                interactionRadius=REACH, attribution="© OpenStreetMap contributors · ODbL 1.0" if scene["id"] == "campus" else None),
            "tilesets": [{"firstgid": 1, "name": "graybox", "tilewidth": TILE,
                          "tileheight": TILE, "columns": 5, "tilecount": 20,
                          "image": "graybox-tiles.png", "imagewidth": 5 * TILE,
                          "imageheight": 4 * TILE}],
            "layers": layers}
    (OUT / f"{scene['id']}.tmj").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def svg(scene):
    w, h = scene["width"], scene["height"]
    width, height = w * TILE, h * TILE
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{escape(scene["title"])}">',
             '<style>text{font-family:Arial,"Microsoft YaHei",sans-serif;fill:#283641} .label{font-size:16px;font-weight:700;text-anchor:middle} .small{font-size:11px;text-anchor:middle} .grid{stroke:#4f6470;stroke-opacity:.14;stroke-width:1} .door{fill:#f1b66e;stroke:#8f674c;stroke-width:2} .anchor{fill:#fff4da;stroke:#b36d3a;stroke-width:2}</style>']
    for y in range(h):
        for x in range(w):
            tile = scene["scenery"][y][x] or scene["ground"][y][x]
            parts.append(f'<rect x="{x*TILE}" y="{y*TILE}" width="{TILE}" height="{TILE}" fill="{TILES[tile][1]}"/>')
    for x in range(w + 1):
        parts.append(f'<path class="grid" d="M{x*TILE} 0V{height}"/>')
    for y in range(h + 1):
        parts.append(f'<path class="grid" d="M0 {y*TILE}H{width}"/>')
    for f in scene["features"]:
        x, y, fw, fh = (f[k] * TILE for k in ("x", "y", "w", "h"))
        if f["tile"] in (5, 6, 7, 8, 16):
            parts.append(f'<rect x="{x+5}" y="{y+5}" width="{fw-10}" height="{fh-10}" rx="9" fill="none" stroke="#657786" stroke-width="3"/>')
        elif f["tile"] in (13, 14, 15):
            parts.append(f'<rect x="{x+3}" y="{y+3}" width="{fw-6}" height="{fh-6}" rx="5" fill="none" stroke="#745f59" stroke-width="2"/>')
        if f["id"] != "exit":
            lines = f["label"].split("\n")
            cy = y + fh / 2 - (len(lines) - 1) * 9
            font_class = "small" if fw < 3 * TILE or (scene["id"] != "campus" and fw < 4 * TILE) else "label"
            for j, line in enumerate(lines):
                parts.append(f'<text class="{font_class}" x="{x+fw/2}" y="{cy+j*19+5}">{escape(line)}</text>')
        if f["action"]:
            ax, ay = f["anchor"]
            cx, cy = (ax + .5) * TILE, (ay + .5) * TILE
            if scene["id"] == "campus":
                parts.append(f'<rect class="door" x="{cx-29}" y="{(f["y"]+f["h"])*TILE-7}" width="58" height="12" rx="2"/>')
            parts.append(f'<circle class="anchor" cx="{cx}" cy="{cy}" r="7"/>')
    sx, sy = scene["spawn"]
    cx, cy = (sx + .5) * TILE, (sy + .5) * TILE
    parts.append(f'<ellipse cx="{cx}" cy="{cy+8}" rx="11" ry="5" fill="#314c67" opacity=".35"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy-6}" r="8" fill="#3b6682" stroke="#fff" stroke-width="2"/>')
    parts.append(f'<text class="small" x="{cx}" y="{cy-20}">出生点</text>')
    parts.append('</svg>')
    (OUT / f"{scene['id']}.svg").write_text("\n".join(parts), encoding="utf-8")


def preview_html():
    buttons = "\n".join(f'<button data-scene="{s["id"]}">{escape(s["title"])}</button>' for s in SCENES)
    notes = {s["id"]: s["note"] for s in SCENES}
    html = f'''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>北航模拟器 · 灰盒场景总览</title>
<style>
body{{margin:0;background:#f4f1e9;color:#263741;font:15px/1.6 Arial,"Microsoft YaHei",sans-serif}}
header{{padding:22px 28px;background:#263741;color:white}}h1{{margin:0;font-size:23px}}header p{{margin:4px 0 0;color:#c9d4d6}}
main{{max-width:1540px;margin:auto;padding:20px 28px}}nav{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}}
button{{border:1px solid #b6c0c1;border-radius:8px;background:white;padding:9px 13px;cursor:pointer;color:#263741}}
button.active{{background:#dce8df;border-color:#668b7d;font-weight:bold}}.frame{{background:white;border:1px solid #d6dbd4;border-radius:12px;padding:12px;overflow:auto;box-shadow:0 8px 30px #26374112}}
img{{display:block;max-width:none}}.meta{{display:flex;flex-wrap:wrap;gap:12px;margin:14px 0}}.pill{{background:#e7e9e2;border-radius:8px;padding:7px 12px}}.note{{color:#5a6970}}
</style>
<header><h1>北航模拟器 · 校园与室内灰盒</h1><p>第一步：检查空间比例、通道宽度、入口位置与交互锚点。此页不含移动逻辑。</p></header>
<main><nav>{buttons}</nav><div class="frame"><img id="map" alt="灰盒地图"></div>
<div class="meta"><span class="pill">1 格 = 32 × 32 px</span><span class="pill">角色外观 = 20 × 28 px</span><span class="pill">碰撞脚印 = 20 × 12 px</span><span class="pill">交互半径 = 40 px</span><span class="pill">门宽 = 2 格</span></div>
<p class="note" id="note"></p><p class="note">蓝点为玩家出生点；浅黄圆点为交互锚点；橙色短条为户外入口。地图可用 Tiled 打开同名 .tmj 编辑。学院路区块为玩法示意，路线和建筑体块不代表真实尺寸。</p>
<p class="note">校园方位与地标参考归档学院路地图：© OpenStreetMap contributors · <a href="https://opendatacommons.org/licenses/odbl/1-0/">ODbL 1.0</a>。</p></main>
<script>const notes={json.dumps(notes,ensure_ascii=False)};function show(id){{document.getElementById('map').src=id+'.svg';document.getElementById('note').textContent=notes[id];document.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.scene===id));}}document.querySelectorAll('button').forEach(b=>b.onclick=()=>show(b.dataset.scene));show('campus');</script></html>
'''
    (OUT / "预览.html").write_text(html, encoding="utf-8")


def main():
    OUT.mkdir(exist_ok=True)
    validate()
    make_tileset()
    for scene in SCENES:
        tmj(scene)
        svg(scene)
        make_overview_png(scene)
    preview_html()
    print("Generated:", OUT)
    for s in SCENES:
        print(f"  {s['id']}: {s['width']}×{s['height']} tiles, {s['reachableCells']} reachable from spawn")
        if s["id"] == "campus":
            print("  painted-route lengths from spawn:",
                  ", ".join(f"{f['id']}={f['routeTiles']}" for f in s["features"] if f["action"]))


if __name__ == "__main__":
    main()
