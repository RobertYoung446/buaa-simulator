# 北航三校区三维地图

基于 Three.js 的交互校园微缩模型，包含学院路、沙河与杭州国际校园。真实地图轮廓作为底图，重点建筑按公开照片、校区图及设计资料单独建模。普通建筑仍为简化体量，并非逐栋测绘复原。

- [学院路校区](https://mrroam.github.io/buaa-xueyuan-campus-3d/?campus=xueyuan)
- [沙河校区](https://mrroam.github.io/buaa-xueyuan-campus-3d/?campus=shahe)
- [杭州国际校园](https://mrroam.github.io/buaa-xueyuan-campus-3d/?campus=hangzhou)

## 使用

直接打开根目录 `index.html` 即可离线使用，或通过网页左侧切换校区。支持旋转、缩放、平移、建筑名称搜索、楼体点选、俯视、环游、三种光照、截图及 GeoJSON 下载。杭州可隐藏飞翔屋顶，查看 C1—C9 内部组团。

## 本地构建

需要 Node.js，首次运行 `npm ci`，随后运行 `npm run build`。产物为根目录和 `dist/` 下的自包含 `index.html`，无需后台、地图密钥或外部模型请求。GitHub Pages 从 `main` 分支根目录发布。

## 文件

| 文件 | 内容 |
| --- | --- |
| `src/entry.js` | 校区入口与可分享的查询参数 |
| `src/app.js` | 已有学院路场景 |
| `src/new-campuses.js` | 沙河、杭州共用的场景与交互 |
| `src/campus-models.js` | 图书馆、曲面屋顶、场馆、院落等模型 |
| `data/*.geojson` | 地图要素、补绘轮廓、模型类型及来源 |
| `data/*source.osm` | 原始地图响应，保留复核依据 |
| `沙河与杭州建模说明.md` | 数据依据、精度和当前局限 |

## 复用于其他学校

先核查校园范围和地图覆盖，再处理建筑外环、内院与楼体分区。不要同时拉高整体轮廓与其内部楼座，也不要把悬空屋顶当成落地建筑。地图遗漏处可参照有使用依据的校区平面图配准补绘，但须标记来源与估算精度。地标应补查建成照片、平剖面与已公布尺寸，再写独立几何模型。最后对照俯视图、近景、手机视图检查，并合并静态几何以控制渲染开销。

地图来源：© OpenStreetMap contributors，使用 [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)。第三方建筑照片仅作为参考，未打包到网页；其版权归原作者。Three.js 许可证见 `THREE-LICENSE.txt`。
