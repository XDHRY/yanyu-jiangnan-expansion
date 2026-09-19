# 任务总索引

共148项：96资产 + 12区域 + 16材质 + 12系统 + 12组装套件。以下均是实施规格，当前统一标为planned。

先读[总指导](MASTER_GUIDE.md)与[接手模板](HANDOFF.md)。机器可读依赖见[catalog/task_graph.json](catalog/task_graph.json)。

## 公共系统

| 任务 | 名称 | 依赖 |
|---|---|---|
| [S01](tasks/systems/S01_water_network.md) | 统一水系与岸线 | S02, S03 |
| [S02](tasks/systems/S02_coordinates.md) | 尺度、原点和坐标 | 无 |
| [S03](tasks/systems/S03_sockets.md) | 连接点与模块拼装 | S02 |
| [S04](tasks/systems/S04_material_registry.md) | 材质和贴图协议 | S02 |
| [S05](tasks/systems/S05_weather_hooks.md) | 雨雾风的接入接口 | S03, S04 |
| [S06](tasks/systems/S06_lod_instancing.md) | 实例、LOD与性能边界 | S03, S04 |
| [S07](tasks/systems/S07_uv_textures.md) | UV、纹理密度与通道 | S04 |
| [S08](tasks/systems/S08_collision_navigation.md) | 通行、碰撞和功能净空 | S02, S03 |
| [S09](tasks/systems/S09_spatial_placement.md) | 摆放、留白与避让 | S02, S03, S08 |
| [S10](tasks/systems/S10_camera_review.md) | 镜头与成果展示 | S09 |
| [S11](tasks/systems/S11_legacy_adapter.md) | 旧庭院只读接入 | S02, S03, S09 |
| [S12](tasks/systems/S12_assembly_handoff.md) | 分任务交付和全景组装 | S01, S03, S04, S06, S08, S09, S10, S11 |

## 资产 · architecture

| 任务 | 资产 | 标称尺寸/米 | 目标Python文件 |
|---|---|---|---|
| [A001](tasks/assets/A001.md) | 临河民居 | 12.8×10×8 | `future/architecture/waterside_house.py` |
| [A002](tasks/assets/A002.md) | 商铺排屋 | 12.8×10×9 | `future/architecture/shop_front.py` |
| [A003](tasks/assets/A003.md) | 竹海客栈 | 64×50×12 | `future/architecture/bamboo_inn.py` |
| [A004](tasks/assets/A004.md) | 书香宅院 | 48×36×9 | `future/architecture/scholar_house.py` |
| [A005](tasks/assets/A005.md) | 沿街茶肆 | 16×12×9 | `future/architecture/tea_house.py` |
| [A006](tasks/assets/A006.md) | 巷口酒楼 | 22×16×12 | `future/architecture/wine_tavern.py` |
| [A007](tasks/assets/A007.md) | 布行染坊 | 18×14×8 | `future/architecture/cloth_shop.py` |
| [A008](tasks/assets/A008.md) | 沿河药铺 | 12.8×12×8 | `future/architecture/apothecary.py` |
| [A009](tasks/assets/A009.md) | 客栈后厨 | 16×12×7 | `future/architecture/inn_kitchen.py` |
| [A010](tasks/assets/A010.md) | 河运仓房 | 22×16×8 | `future/architecture/riverside_warehouse.py` |
| [A011](tasks/assets/A011.md) | 木作工棚 | 20×14×7 | `future/architecture/carpenter_workshop.py` |
| [A012](tasks/assets/A012.md) | 窑场棚屋 | 22×18×9 | `future/architecture/kiln_shed.py` |
| [A013](tasks/assets/A013.md) | 山门 | 24×12×12 | `future/architecture/temple_gate.py` |
| [A014](tasks/assets/A014.md) | 寺院正殿 | 32×24×15 | `future/architecture/main_hall.py` |
| [A015](tasks/assets/A015.md) | 讲堂 | 28×16×9 | `future/architecture/lecture_hall.py` |
| [A016](tasks/assets/A016.md) | 藏书楼 | 24×16×12 | `future/architecture/library_house.py` |
| [A017](tasks/assets/A017.md) | 临水亭 | 10×10×8 | `future/architecture/water_pavilion.py` |
| [A018](tasks/assets/A018.md) | 沿岸曲廊 | 24×3.2×4.8 | `future/architecture/covered_corridor.py` |
| [A019](tasks/assets/A019.md) | 街角戏台 | 20×14×10 | `future/architecture/opera_stage.py` |
| [A020](tasks/assets/A020.md) | 水关门楼 | 26×16×15 | `future/architecture/water_gate.py` |
| [A021](tasks/assets/A021.md) | 石基望楼 | 24×20×20 | `future/architecture/watch_tower.py` |
| [A022](tasks/assets/A022.md) | 茶田农舍 | 14×10×7 | `future/architecture/farm_house.py` |
| [A023](tasks/assets/A023.md) | 修船长棚 | 30×16×10 | `future/architecture/boat_shed.py` |
| [A024](tasks/assets/A024.md) | 竹林山居 | 16×12×8 | `future/architecture/bamboo_retreat.py` |

## 资产 · components

| 任务 | 资产 | 标称尺寸/米 | 目标Python文件 |
|---|---|---|---|
| [A025](tasks/assets/A025.md) | 石台基 | 3.2×1.2×0.6 | `future/components/stone_foundation.py` |
| [A026](tasks/assets/A026.md) | 踏步组 | 2.8×2.4×1.2 | `future/components/stone_steps.py` |
| [A027](tasks/assets/A027.md) | 柱础木柱 | 0.65×0.65×3.8 | `future/components/column_base.py` |
| [A028](tasks/assets/A028.md) | 穿枋横梁 | 3.4×0.32×0.42 | `future/components/timber_beam.py` |
| [A029](tasks/assets/A029.md) | 檩椽屋架 | 6.4×8×3 | `future/components/rafter_frame.py` |
| [A030](tasks/assets/A030.md) | 双坡屋面 | 14.4×11.6×3 | `future/components/gable_roof.py` |
| [A031](tasks/assets/A031.md) | 歇山屋面 | 26×18×7 | `future/components/hip_gable_roof.py` |
| [A032](tasks/assets/A032.md) | 瓦垄与滴水 | 3.2×1.6×0.18 | `future/components/tile_course.py` |
| [A033](tasks/assets/A033.md) | 灰砖墙段 | 3.2×0.32×3 | `future/components/grey_brick_wall.py` |
| [A034](tasks/assets/A034.md) | 粉墙段 | 3.2×0.28×3 | `future/components/lime_wall.py` |
| [A035](tasks/assets/A035.md) | 月洞门 | 4.8×0.45×3.8 | `future/components/moon_gate.py` |
| [A036](tasks/assets/A036.md) | 格扇门 | 2.4×0.18×2.8 | `future/components/lattice_door.py` |
| [A037](tasks/assets/A037.md) | 支摘窗 | 1.6×0.24×1.8 | `future/components/shutter_window.py` |
| [A038](tasks/assets/A038.md) | 临水栏杆 | 3.2×0.18×1.05 | `future/components/water_railing.py` |
| [A039](tasks/assets/A039.md) | 门额招牌框 | 2.6×0.22×0.75 | `future/components/sign_frame.py` |
| [A040](tasks/assets/A040.md) | 连廊转角 | 6.4×6.4×5 | `future/components/corridor_corner.py` |

## 资产 · waterfront

| 任务 | 资产 | 标称尺寸/米 | 目标Python文件 |
|---|---|---|---|
| [A041](tasks/assets/A041.md) | 跨渠石拱桥 | 32×6×6 | `future/waterfront/canal_arch_bridge.py` |
| [A042](tasks/assets/A042.md) | 木梁小桥 | 12×3.2×3 | `future/waterfront/timber_bridge.py` |
| [A043](tasks/assets/A043.md) | 青石水埠 | 4×5×3 | `future/waterfront/stone_dock.py` |
| [A044](tasks/assets/A044.md) | 石砌驳岸 | 8×2.5×3 | `future/waterfront/stone_quay.py` |
| [A045](tasks/assets/A045.md) | 下水坡道 | 10×24×3 | `future/waterfront/slipway.py` |
| [A046](tasks/assets/A046.md) | 简式水闸 | 10×6×6 | `future/waterfront/sluice_gate.py` |
| [A047](tasks/assets/A047.md) | 乌篷船 | 6×2.4×2.6 | `future/waterfront/awning_boat.py` |
| [A048](tasks/assets/A048.md) | 平底货船 | 12×3.4×3 | `future/waterfront/cargo_barge.py` |
| [A049](tasks/assets/A049.md) | 竹木小筏 | 5×2.4×0.7 | `future/waterfront/bamboo_raft.py` |
| [A050](tasks/assets/A050.md) | 系缆柱组 | 2.8×0.8×1 | `future/waterfront/mooring_bollard.py` |
| [A051](tasks/assets/A051.md) | 引水竹槽 | 8×0.5×2.5 | `future/waterfront/bamboo_flume.py` |
| [A052](tasks/assets/A052.md) | 桥头候船棚 | 8×5×5 | `future/waterfront/ferry_shelter.py` |

## 资产 · props

| 任务 | 资产 | 标称尺寸/米 | 目标Python文件 |
|---|---|---|---|
| [A053](tasks/assets/A053.md) | 街市摊架 | 3.7×2.4×3 | `future/props/market_stall.py` |
| [A054](tasks/assets/A054.md) | 竹编货篮 | 0.7×0.7×0.6 | `future/props/woven_basket.py` |
| [A055](tasks/assets/A055.md) | 叠放木箱 | 1.2×0.8×0.8 | `future/props/wooden_crate.py` |
| [A056](tasks/assets/A056.md) | 麻布货包 | 0.7×0.5×0.9 | `future/props/cloth_sack.py` |
| [A057](tasks/assets/A057.md) | 檐下灯笼 | 0.6×0.6×0.85 | `future/props/paper_lantern.py` |
| [A058](tasks/assets/A058.md) | 临河灯架 | 1.2×0.5×3.6 | `future/props/riverside_lamp.py` |
| [A059](tasks/assets/A059.md) | 客栈酒旗 | 1.5×0.1×2.5 | `future/props/inn_banner.py` |
| [A060](tasks/assets/A060.md) | 木茶案 | 1.4×0.8×0.75 | `future/props/tea_table.py` |
| [A061](tasks/assets/A061.md) | 长条凳 | 1.8×0.4×0.46 | `future/props/wood_bench.py` |
| [A062](tasks/assets/A062.md) | 客栈柜台 | 3.2×0.75×1.1 | `future/props/inn_counter.py` |
| [A063](tasks/assets/A063.md) | 木床榻 | 2.2×1.4×1.1 | `future/props/wood_bed.py` |
| [A064](tasks/assets/A064.md) | 陶酒坛 | 0.65×0.65×0.85 | `future/props/wine_jar.py` |
| [A065](tasks/assets/A065.md) | 供水木桶 | 0.5×0.5×0.6 | `future/props/water_bucket.py` |
| [A066](tasks/assets/A066.md) | 石井井栏 | 2.4×2.4×2.8 | `future/props/stone_well.py` |
| [A067](tasks/assets/A067.md) | 灶台锅具 | 2.6×1.6×1.3 | `future/props/kitchen_stove.py` |
| [A068](tasks/assets/A068.md) | 河岸晾网架 | 6×1.2×3.2 | `future/props/fishing_net_rack.py` |
| [A069](tasks/assets/A069.md) | 晒布架 | 8×2.4×4.2 | `future/props/cloth_drying_rack.py` |
| [A070](tasks/assets/A070.md) | 匾额文字层 | 2×0.05×0.5 | `future/props/editable_sign_text.py` |
| [A071](tasks/assets/A071.md) | 手推木车 | 2.8×1.2×1.1 | `future/props/wood_handcart.py` |
| [A072](tasks/assets/A072.md) | 竹制扫帚 | 0.5×0.25×1.5 | `future/props/bamboo_broom.py` |

## 资产 · nature

| 任务 | 资产 | 标称尺寸/米 | 目标Python文件 |
|---|---|---|---|
| [A073](tasks/assets/A073.md) | 岸边垂柳 | 7×7×10 | `future/nature/willow_tree.py` |
| [A074](tasks/assets/A074.md) | 竹丛母体 | 5×5×9 | `future/nature/bamboo_cluster.py` |
| [A075](tasks/assets/A075.md) | 古梅 | 6×5×6 | `future/nature/old_plum.py` |
| [A076](tasks/assets/A076.md) | 寺前古柏 | 7×7×13 | `future/nature/cypress_tree.py` |
| [A077](tasks/assets/A077.md) | 溪边芦苇 | 3×3×2.5 | `future/nature/reeds_patch.py` |
| [A078](tasks/assets/A078.md) | 池中荷叶 | 4×4×1.5 | `future/nature/lotus_patch.py` |
| [A079](tasks/assets/A079.md) | 苔藓斑块 | 2×2×0.05 | `future/nature/moss_patch.py` |
| [A080](tasks/assets/A080.md) | 河滩草丛 | 2×2×0.7 | `future/nature/bank_grass.py` |
| [A081](tasks/assets/A081.md) | 茶树行 | 12×2×1.4 | `future/nature/tea_row.py` |
| [A082](tasks/assets/A082.md) | 水稻田块 | 18×12×1.2 | `future/nature/rice_paddy.py` |
| [A083](tasks/assets/A083.md) | 太湖石 | 3×2.5×4 | `future/nature/scholar_rock.py` |
| [A084](tasks/assets/A084.md) | 岸边乱石组 | 6×4×2 | `future/nature/shore_rocks.py` |

## 资产 · environment

| 任务 | 资产 | 标称尺寸/米 | 目标Python文件 |
|---|---|---|---|
| [A085](tasks/assets/A085.md) | 青石铺路 | 6×6×0.18 | `future/environment/stone_paving.py` |
| [A086](tasks/assets/A086.md) | 泥地过渡 | 6×6×0.3 | `future/environment/mud_transition.py` |
| [A087](tasks/assets/A087.md) | 院内排水沟 | 8×0.4×0.5 | `future/environment/courtyard_drain.py` |
| [A088](tasks/assets/A088.md) | 园林池岸 | 12×3×2 | `future/environment/pond_edge.py` |
| [A089](tasks/assets/A089.md) | 汀步石组 | 12×2×0.6 | `future/environment/stepping_stones.py` |
| [A090](tasks/assets/A090.md) | 坡地台阶 | 4×18×8 | `future/environment/hillside_stairs.py` |
| [A091](tasks/assets/A091.md) | 山林远景 | 720×180×140 | `future/environment/distant_hills.py` |
| [A092](tasks/assets/A092.md) | 低雾体积 | 180×160×12 | `future/environment/ground_mist.py` |
| [A093](tasks/assets/A093.md) | 檐下雨线 | 14×1×6 | `future/environment/eaves_rain.py` |
| [A094](tasks/assets/A094.md) | 水面涟漪 | 12×12×0.05 | `future/environment/water_ripples.py` |
| [A095](tasks/assets/A095.md) | 夜景光组 | 180×160×30 | `future/environment/night_lighting.py` |
| [A096](tasks/assets/A096.md) | 镜头路线 | 720×540×80 | `future/environment/camera_route.py` |

## 材质

| 任务 | 名称 | 初版色块槽 |
|---|---|---|
| [M01](tasks/materials/M01_lime_plaster.md) | 旧粉墙 | `plaster` |
| [M02](tasks/materials/M02_grey_brick.md) | 青灰砖 | `stone` |
| [M03](tasks/materials/M03_roof_clay.md) | 黛瓦胎土 | `tile` |
| [M04](tasks/materials/M04_aged_timber.md) | 老木柱梁 | `timber` |
| [M05](tasks/materials/M05_paving_stone.md) | 湿青石 | `stone` |
| [M06](tasks/materials/M06_quay_stone.md) | 驳岸粗石 | `stone` |
| [M07](tasks/materials/M07_bamboo_skin.md) | 竹皮 | `bamboo` |
| [M08](tasks/materials/M08_plum_bark.md) | 梅树皮 | `timber` |
| [M09](tasks/materials/M09_undyed_cloth.md) | 粗麻布 | `cloth` |
| [M10](tasks/materials/M10_indigo_cloth.md) | 靛蓝布 | `cloth` |
| [M11](tasks/materials/M11_lantern_paper.md) | 灯笼纸 | `paper` |
| [M12](tasks/materials/M12_rough_ceramic.md) | 粗陶 | `ceramic` |
| [M13](tasks/materials/M13_forged_iron.md) | 旧锻铁 | `iron` |
| [M14](tasks/materials/M14_mud_soil.md) | 河岸湿土 | `earth` |
| [M15](tasks/materials/M15_moss_lichen.md) | 苔藓地衣 | `leaf` |
| [M16](tasks/materials/M16_leaf_atlas.md) | 植被叶卡 | `leaf` |

## 组装套件

| 任务 | 名称 | 区域 |
|---|---|---|
| [K01](tasks/assemblies/K01.md) | 商街连续铺面 | D02 |
| [K02](tasks/assemblies/K02.md) | 竹海客栈院落 | D03 |
| [K03](tasks/assemblies/K03.md) | 渔埠修船作业组 | D04 |
| [K04](tasks/assemblies/K04.md) | 桥头候船节点 | D01 |
| [K05](tasks/assemblies/K05.md) | 书院讲学院 | D05 |
| [K06](tasks/assemblies/K06.md) | 里巷共井生活组 | D06 |
| [K07](tasks/assemblies/K07.md) | 中央借景水院 | D07 |
| [K08](tasks/assemblies/K08.md) | 手作生产院 | D08 |
| [K09](tasks/assemblies/K09.md) | 田庄茶圃组合 | D09 |
| [K10](tasks/assemblies/K10.md) | 古寺山门轴线 | D10 |
| [K11](tasks/assemblies/K11.md) | 竹溪慢行路径 | D11 |
| [K12](tasks/assemblies/K12.md) | 湖心望楼远景组 | D12 |

## 区域

| 任务 | 名称 | 中心XY/米 |
|---|---|---|
| [D01](tasks/districts/D01.md) | 南市水关 | [-270, -180] |
| [D02](tasks/districts/D02.md) | 沿河商街 | [-90, -180] |
| [D03](tasks/districts/D03.md) | 竹海客栈 | [90, -180] |
| [D04](tasks/districts/D04.md) | 船坞渔埠 | [270, -180] |
| [D05](tasks/districts/D05.md) | 西园书院 | [-270, 0] |
| [D06](tasks/districts/D06.md) | 粉墙里巷 | [-90, 0] |
| [D07](tasks/districts/D07.md) | 中央水院 | [90, 0] |
| [D08](tasks/districts/D08.md) | 手工作坊 | [270, 0] |
| [D09](tasks/districts/D09.md) | 田庄茶圃 | [-270, 180] |
| [D10](tasks/districts/D10.md) | 山门古寺 | [-90, 180] |
| [D11](tasks/districts/D11.md) | 竹溪幽径 | [90, 180] |
| [D12](tasks/districts/D12.md) | 湖心望楼 | [270, 180] |
