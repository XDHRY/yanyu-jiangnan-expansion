# 二期接口与文件职责总表

## 五种工作类型

| 类型 | 拟定公开入口 | 输入 | 输出 | 禁止隐藏的职责 |
|---|---|---|---|---|
| geometry | build(builder, instance) | 宿主、参数、根变换、seed | 本任务网格和socket | 不能自行改地区布局或保存旧场景 |
| assembly | assemble(context, spec) | 已交付资产版本与功能区域 | 实例、摆放、连接表 | 不复制所有资产内部建模代码 |
| shader | make_material(context, spec) | 材质ID、真实尺度、遮罩来源 | 材质、通道清单、响应参数 | 不声称不存在的贴图已经生成 |
| data | resolve(context, spec) | schema与明确字段 | 结果manifest、缺失与版本变化 | 不按模糊同名对象猜输入 |
| scene | compose(context, spec) | 地区、套件、机位与天气 | 场景片段和来源记录 | 不用概念图替代模型和真实渲染 |

这五个入口是未来代码应采用的接口，不是当前已实现的API。现有一期builder只支持有限的体块数据；曲线、节点、UV、层级、动画等新能力需由接手者明确增加适配。

## 统一数据包

实例至少传task_id、asset_id、instance_id、district_id、host_task、host_instance、source_version、parameters、seed、variant和transform。transform要声明local或world，以及地区中心是否已合成。任何对象的局部Z=0含义必须由宿主定义，不能把地面、水面、床面、甲板和屋面混作同一层。

几何端口：name、type、position_local、direction_local、units、tolerance_m、compatible_families、owner、resolved。非几何端口：field、dtype、unit、range、default、missing_behavior、schema_version。未测量的端口标unresolved，不填假坐标。

## 所有权与收口

| 场景关系 | 宿主拥有 | 二期任务拥有 | 下游消费 |
|---|---|---|---|
| 梁柱与屋顶 | 一期柱网/屋面轮廓 | AD局部节点、收口、变体 | 建筑装配 |
| 房间与家具 | 外墙、门窗洞、楼层标高 | IN布局及内部家具/通行约束 | 室内外连接SI06 |
| 船与岸 | 船根、水位、码头位置 | WH内壳、支承、泊靠与局部波 | 水岸组装 |
| 生产与生活工位 | 房间/院落地坪和主路 | CP/DL具体工具、接触、使用状态 | 区域叙事 |
| 植被与地形 | 地面、水深、路径遮罩 | VE骨架、叶簇、密度/季节 | 植被装配与LOD |
| 材质与几何 | 稳定材质ID、UV/几何字段 | MW遮罩、通道、响应 | S04/S05适配 |
| 数据与产物 | 真实任务版本 | SI注册、解析、追溯、缺失报告 | 全景装配 |
| 叙事片段 | 真实可用资产 | ST摆放、机位和情境关系 | 地区细化总装 |

## 与一期共存

MANIFEST只追加二期任务。DEPENDENCIES中旧ID指一期原有任务；P2-ID指本批新任务。related_phase1是细化对象或参考，不等于父任务已经完成，也不自动意味着整体父资产必须全部完成后才能先做局部。具体最低宿主输入在各任务接口节说明。

注册器未来显式读取一期与二期目录，不能因为文件夹多了就假定自动接入。保留旧代码、资产数据库、贴图与Jiangnan.blend；D07接入以S11/P2-SI15的真实测量为准。
