"""Export exact outdoor polygons and named places for the browser prototype."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / '地图数据/二维版本/xueyuan.map.json').read_text(encoding='utf8'))
ox, oy = 55 * 32, 39 * 32
obstacles = []
features = {}
for f in data['features']:
    features[f['id']] = f
    g = f['geometry']
    if f['category'] not in ('building', 'water') or g['type'] not in ('Polygon', 'MultiPolygon'):
        continue
    polygons = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    for polygon in polygons:
        rings = [[[round(x-ox, 3), round(y-oy, 3)] for x, y in ring] for ring in polygon]
        xs, ys = zip(*rings[0])
        box = [min(xs), min(ys), max(xs), max(ys)]
        if box[2] >= 0 and box[0] <= 2048 and box[3] >= 0 and box[1] <= 1344:
            obstacles.append(dict(id=f['id'], kind=f['category'], box=box, rings=rings))
places = []
for fid, scene, text in [
    ('190430062', 'living', '这里是8公寓。可以从南侧道路继续走到东区食堂。'),
    ('190427801', 'living', '这里是7公寓。宿舍楼之间的小路通向校园东路。'),
    ('190427995', 'living', '这里是东区食堂。生活区的室外探索点已到达。'),
    ('88777864', 'library', '这里是北航图书馆。西侧是绿园与湖边步道。'),
    ('190444425', 'museum', '这里是北京航空航天博物馆。沿西侧道路可到第九馆。'),
    ('190444424', 'museum', '这里是第九馆 / 逸夫楼。你可以沿道路返回生活区。'),
]:
    f = features['xueyuan/way/' + fid]
    obstacle = next(o for o in obstacles if o['id'] == f['id'])
    places.append(dict(id=f['id'], name=f['properties']['name'], scene=scene,
                       box=obstacle['box'], text=text))
world = dict(width=2048, height=1344, obstacles=obstacles, places=places,
             source='RobertYoung446/buaa-simulator',
             scenes=[
                 dict(id='living', name='公寓与食堂', bounds=[0,380,1070,1344]),
                 dict(id='library', name='图书馆与绿园', bounds=[0,0,2048,730]),
                 dict(id='museum', name='博物馆周边', bounds=[850,380,2048,1344]),
             ])
(ROOT/'灰盒/world.js').write_text('globalThis.CAMPUS_WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',', ':'))+';\n',encoding='utf8')
print(f'Exported {len(obstacles)} exact collision polygons, {len(places)} landmarks, 3 outdoor scenes')
