# Python文件与实现接口

当前`expansion/scripts/`提供8个已有源码文件，详细说明见`docs/modules/`。`future/`中的.py路径是后续交付位置；这些文件大多尚不存在，不能当作可调用模块。

## 资产工厂

推荐签名`build(builder, instance) -> None`。instance至少包括id、asset_id、district、location、rotation、params、seed、variant。factory负责创建自己的root、几何与socket；它不写磁盘、不联网、不清空场景、不改全局随机状态。

使用`builder.root()`注册唯一实例，`box/cylinder/roof/mesh`追加局部几何，`socket()`注册接口。root.location已是世界坐标时，所有子几何位置都是局部坐标。自定义网格通过mesh顶点和面数组提交，材质键必须已在注册表存在。

## 文件顶部说明模板

写清：本文件实现哪个任务；输入参数是什么；利用bpy/data mesh/曲线/实例/节点的哪种机制；生成顺序；输出哪些对象与连接点；依赖什么；没有实现什么。避免只有“生成模型”四个字。

## 未来派发器

S12将新增`future/systems/assembly_handoff.py`负责按asset_id选已实现工厂，并消费锁定版本产物。当前build_world仍调用粗粒度家族模块；细化资产不会因为新文件放进目录就自动出现，必须在新派发器显式登记映射。不要在本轮声称已支持动态发现插件。

## 模块责任

配置层描述世界；工厂层生成资产；布局层给实例位置；组装层连接资产；Blender适配层把结构写成数据块；输出层保存版本。一个文件不承担整个项目全部职责。公共函数的参数/返回值在说明中列出，未满足输入应报告缺失而非随机猜测。

当前固定色块由kernel.PALETTE定义，只有12键。未来M01–M16是精细材质任务，与色块槽的对应写在catalog/materials.json；实施S04后再接入，不要直接使用未知材质键导致框架失败。
