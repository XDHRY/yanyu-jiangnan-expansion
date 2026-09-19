# 烟雨江南 · 二期细化提示词与项目职责

这批**新增200个文件**，接续一期扩建，专门供用户把细节任务逐个交给其他模型实现：180份专项细化提示词、12份区域细化总装说明、8份职责/索引/契约与机器可读目录文件。

本轮只新增文件并提交GitHub；没有改写一期文件，没有实现本批目标Python工厂，也没有运行Blender或生成模型/渲染。

## 入口

- [MASTER_PROMPT.md](MASTER_PROMPT.md)：整体接手提示词与职责边界。
- [TASK_INDEX.md](TASK_INDEX.md)：逐项任务、标题、源码目标和上游关系。
- [INTERFACE_MAP.md](INTERFACE_MAP.md)：几何、装配、材质、数据、场景五种接口。
- [IMPLEMENTATION_ORDER.md](IMPLEMENTATION_ORDER.md)：依赖与按区分批实施路线。
- [QUALITY_BAR.md](QUALITY_BAR.md)：任务细化到什么程度才算完成。
- [MANIFEST.json](MANIFEST.json)、[DEPENDENCIES.json](DEPENDENCIES.json)：机器可读目录与依赖。

## 新增内容

| 类别 | 文件数 | 位置 |
|---|---:|---|
| 建筑构造与收口 | 24 | `architecture_detail/` |
| 室内空间与可用陈设 | 24 | `interiors/` |
| 水工、船体与岸线细部 | 18 | `watercraft_hydrology/` |
| 生产工位与工序 | 24 | `craft_production/` |
| 日常生活与街巷使用 | 24 | `daily_life/` |
| 植物结构与群落 | 18 | `vegetation_ecology/` |
| 材质与旧化规则 | 18 | `materials_weathering/` |
| 项目接口与装配职责 | 18 | `scene_integration/` |
| 空间叙事与场景片段 | 12 | `environment_storytelling/` |
| 区域细化总装 | 12 | `districts/` |
| 总指导、索引与契约 | 8 | 当前目录 |

每份专项文件都包含：新增职责、一期关联、目标源码路径、完整实现提示词、部件拆解、技术路线、专属接口、材质与使用痕迹、变体、辅助提示词和具体完成标准。

一期入口仍在[原整体指导](../MASTER_GUIDE.md)和[原任务索引](../TASK_INDEX.md)。当前新增目录是附加层，不自动改写原注册表；未来由显式装配器消费。
