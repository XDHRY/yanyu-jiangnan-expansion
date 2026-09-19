# 江南材质 / 贴图生产线 v1

当前仓库已有 7 张 AI 生成 base-color/albedo 贴图，并已映射进 Blender。下一阶段不再把“贴一张图 + 灰度转 bump”视为完成，而是建立真正的 PBR 通道生产线。

权威材质登记表：`asset_db/materials.json`。

## 1. 文件规范

现有兼容文件继续保留：

- `textures/plaster.png`
- `textures/stone.png`
- `textures/bark.png`
- `textures/clay.png`
- `textures/wood.png`
- `textures/petal.png`
- `textures/landscape.png`

新 PBR 文件统一放入：

```text
textures/pbr/<material>/
  <material>_basecolor.png
  <material>_roughness.png
  <material>_normal.png
  <material>_height.png
  <material>_ao.png
```

可选通道：`wetness_mask`、`opacity`、`transmission_mask`。

## 2. 色彩空间

- Base Color：sRGB
- Roughness / Normal / Height / AO / Mask：Non-Color
- Normal：OpenGL (+Y) 为默认约定；如来源为 DirectX，导入时翻转 G。

## 3. AI 生成原则

生成 base color 时必须要求：

- orthographic / straight-on material scan；
- flat neutral diffuse illumination；
- no baked directional shadow；
- no glossy highlight baked in；
- seamless / tileable；
- no object silhouette；
- no text / frame / watermark；
- 材质尺度明确。

**不要让图像模型直接把错误的光照烘焙进 albedo。**

Roughness/height/normal 不应简单理解为“把彩色图转灰度就行”。第一版可以从 albedo 推导作为占位，但生产版必须针对材料物理性质二次修正。

## 4. 江南天气响应

### 雨天

- 石：粗糙度显著下降，但不应全表面镜面化；
- 瓦：朝天面更湿，檐下相对干；
- 木：颜色略深，横向端面和积水位置更明显；
- 泥：凹处形成高 wetness，凸起仍保持较高 roughness；
- 青苔：颜色变深但保持漫反射主体。

### 雾天

雾主要通过体积和空气透视表达，不应该把所有贴图直接降对比度。

### 雪天

积雪应由表面朝向、高度、遮挡和风向决定；不要直接把整张材质变白。

## 5. 第一批 PBR 升级顺序

### P0
1. `stone`：对雨景影响最大；
2. `clay`：屋面占画面面积大；
3. `wood`：亭、门、柱、家具共用；
4. `plaster`：墙面决定江南基调；
5. `bark`：近景梅树需要真实微表面。

### P1
6. `bamboo`：新资产；
7. `mud_ground`：新资产；
8. `cloth_banner`：新资产；
9. `petal`：增加 transmission / subsurface 控制。

## 6. 贴图验收

每个材质至少检查：

- 四方连续性；
- 是否含错误阴影/高光；
- 实际世界尺度是否可信；
- Base Color 是否过饱和；
- Roughness 是否与材料类别一致；
- Normal 是否有反向或强度过大；
- Height 是否造成“融化/膨胀”感；
- 雨天 wetness 是否只影响合理区域；
- 远中近三个镜头距离下都没有明显重复纹样。

## 7. 生成提示词骨架

```text
Asset type: production PBR base-color texture for <material>.
Historical grounded Jiangnan environment.
Square orthographic material scan, real-world scale <X cm/m>.
<material-specific microstructure>.
Desaturated restrained color palette.
Flat neutral diffuse cross-polarized illumination.
NO baked shadows, NO directional highlights, NO perspective.
Seamlessly tileable on all four sides.
Full bleed material only.
NO object silhouette, NO text, NO frame, NO watermark.
```

然后为每种材质追加材质物理描述，而不是追加“cinematic / masterpiece”。

## 8. 当前限制

`jiangnan.py::image_material()` 目前仍把同一 albedo 的颜色直接接到 Bump Height，这只是旧场景兼容方案。PBR 升级应新增一个独立材质加载器：优先加载 `textures/pbr/...` 的真实通道；不存在时才回退到旧 albedo。

在没有对主生成脚本完成安全拆分前，先保持兼容，不直接破坏现有 `Jiangnan.blend`。
