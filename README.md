# 烟雨江南 · 雪月江南

> 致虚极，守静笃 —— 一庭月色，半池灯影。听雨轩前，梅枝随风。

*A fully procedural, editable Jiangnan night courtyard in Blender — moon gate, leaning plum trees, still water and a rain-listening pavilion. One script builds everything; no external game assets.*

![正面 · 烟雨](renders/01_rain_front.png)

## 这是什么

一座可步入、可停留、可整体重建的江南夜庭院，由单个 Blender Python 脚本（`jiangnan.py`，约 40KB）全参数化生成：

- **场景**：粉墙月洞门（真实贯通几何）、斜梅两株、静水池与汀步、听雨轩、石灯茶案、太湖石、云月与远山。
- **双天气一键切换**：烟雨（细雨/涟漪/湿石）与雪夜（飘雪/瓦上薄雪/残雪）互斥切换，风力 0–2 可调。
- **原生驱动动画**：4461 条驱动器，240 帧 / 24 fps，花枝摇摆、露珠随枝、雨雪下落、云移水动，无外部缓存。
- **AI 贴图**：仓库已有 7 张 albedo 贴图（粉墙/苔石/梅皮/黛瓦/老木/花瓣/远山夜景）及提示词存档；新分支正在把它们升级为可验证的 PBR 材质生产线。
- **远程 Blender CI**：GitHub Actions 使用官方 Blender 4.5.14 LTS headless 打开真实 `.blend`，检查天气、动画驱动、对象基线、贴图和法线，并自动输出低成本预览 artifact。

当前场景基线：2745 对象 / 3 机位 / 11 灯光；更详细统计与 CI 报告见 `validation/` 与 Actions artifact。

## 快速开始

1. 用 **Blender 4.5 LTS** 打开根目录 `Jiangnan.blend`，选择场景「烟雨江南 · 雪月江南」。本仓库远程 CI 固定使用 **4.5.14 LTS**。
2. 若提示禁用驱动表达式，选择信任并启用脚本自动运行。
3. 播放时间轴（1–240 帧）查看动态；在集合 `JN_00_总控` 的 `JN_总控_天气0雨1雪_风力` 上改自定义属性 `Weather`（0 雨 / 1 雪）与 `Wind`（0–2）。
4. 浏览器打开 `renders/gallery.html` 查看静帧预览页。

更多操作细节见 [docs/usage.md](docs/usage.md)。

## 重建与二次开发

```python
# 在 Blender 文本编辑器中打开 jiangnan.py 直接运行即可全量重建。
# 顶部 PARAMS 集中管理：seed / weather / wind / blossom_density /
# rain_count / snow_count / resolution / samples / stage / render / output_dir
```

- `stage` 1–5 分阶段构建（庭院→植被→雨雪→天空→灯光），调试用低 stage 更快。
- `render=True` 时构建完成后自动渲染正面、顶视、三分之四三个机位到 `renders/`。
- 输出目录默认取当前 `.blend` 所在目录（仓库内即根目录），需有 `textures/` 子目录；可用环境变量 `JN_OUT` 覆盖。

旧场景脚本契约见 [docs/development.md](docs/development.md)。新的资产工业化路线见：

- [docs/asset-pipeline.md](docs/asset-pipeline.md) — 3D 资产工厂、MVP 与 QA；
- [docs/texture-pipeline.md](docs/texture-pipeline.md) — PBR 材质/贴图生产线；
- [asset_db/assets.json](asset_db/assets.json) — 首批 20 个 P0 资产；
- [asset_db/materials.json](asset_db/materials.json) — 材质物理与天气响应清单。

## GitHub 远程调试

### 自动 CI

对 `main` 或 `ai/**` 分支 push 时，`.github/workflows/blender-ci.yml` 会：

1. 运行 `tools/validate_repo.py` 做 JSON / 文件 / Python 语法检查；
2. 下载并缓存官方 Blender 4.5.14 LTS；
3. headless 打开真正的 `Jiangnan.blend`；
4. 运行 `tools/ci_validate.py`；
5. 验证通过后用 Eevee 生成 640px 三分之四雨景预览；
6. 上传验证 JSON 与预览图为 Actions artifact。

### 手动远程出图

GitHub Actions → **Remote Render Preview** 可选择：

- 正面 / 顶视 / 三分之四；
- 雨 / 雪；
- Eevee / Cycles；
- 640 / 960 / 1280 / 1600；
- 16 / 32 / 64 / 96 samples。

适合在没有本机 Blender 的情况下反复检查远程场景。

## 目录结构

```text
├── Jiangnan.blend
├── Jiangnan.blend1
├── jiangnan.py
├── asset_db/            # 资产与材质权威 manifest
├── textures/            # 现有贴图；未来 PBR 进入 textures/pbr/
├── renders/             # 正式静帧 + gallery.html
├── validation/          # 历史统计/验证记录
├── tools/               # 仓库 QA / Blender QA / 远程预览
├── progress/            # 构建过程记录
├── docs/                # 使用、美术、开发、资产、贴图文档
└── .github/workflows/   # Blender CI 与手动远程渲染
```

## 当前状态与路线

- [x] 程序化庭院、双天气、4461 条动画驱动已形成可运行基线。
- [x] 正面烟雨静帧 `01_rain_front.png`。
- [x] GitHub 上的 Blender 4.5.14 LTS headless CI 已接通。
- [x] 首批 20 个江南竹海客栈 P0 资产进入 `asset_db/assets.json`。
- [x] 材质 PBR 升级规范进入 `asset_db/materials.json` 与 `docs/texture-pipeline.md`。
- [ ] 让新 CI 完整通过，并以它替代旧的人工验证记录作为事实来源。
- [ ] 补齐剩余正式 Cycles 机位渲染。
- [ ] 为 stone / clay / wood / plaster / bark 生成真正 roughness / normal / height / AO。
- [ ] 建第一个可批量衍生的参数化竹子资产母体。
- [ ] 建独立“江南竹海客栈”生产场景。

> 注意：`validation/validation.json` 是旧验证脚本留下的历史记录，并不代表每个后续 commit 都通过。以当前 GitHub Actions 结果为准。

完整变更记录见 [CHANGELOG.md](CHANGELOG.md)。

## 致谢与许可

- 场景与脚本由 **OpenAI Codex** 经 Blender MCP 工作流生成（2026-09-17/18），灵感方向参考《燕云十六声》与《黑神话：悟空》的美术气质；工作流参考 [newo-ether/blender-mcp](https://github.com/newo-ether/blender-mcp)、[hassledzebra/codex_blender_mcp](https://github.com/hassledzebra/codex_blender_mcp)、[PatrykIti/blender-ai-mcp](https://github.com/PatrykIti/blender-ai-mcp)。
- 本仓库为私人项目存档，未附带开源许可；如需引用请先联系所有者。
