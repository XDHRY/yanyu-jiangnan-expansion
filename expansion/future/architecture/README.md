# architecture · 后续实现目录

 本轮只建立目录和任务说明。本目录中尚无资产实现文件，不能将文件名清单当作已经生成的模型。
 每个模型依照[Python契约](../../docs/03_python_contract.md)新增一个工厂文件，入口为`build(builder, instance)`。
 本分类任务如下；打开任务文件复制主提示词即可开始。

 | 任务 | 目标Python文件 | 资产 |
 |---|---|---|
 | [A001](../../tasks/assets/A001.md) | `waterside_house.py` | 临河民居 |
| [A002](../../tasks/assets/A002.md) | `shop_front.py` | 商铺排屋 |
| [A003](../../tasks/assets/A003.md) | `bamboo_inn.py` | 竹海客栈 |
| [A004](../../tasks/assets/A004.md) | `scholar_house.py` | 书香宅院 |
| [A005](../../tasks/assets/A005.md) | `tea_house.py` | 沿街茶肆 |
| [A006](../../tasks/assets/A006.md) | `wine_tavern.py` | 巷口酒楼 |
| [A007](../../tasks/assets/A007.md) | `cloth_shop.py` | 布行染坊 |
| [A008](../../tasks/assets/A008.md) | `apothecary.py` | 沿河药铺 |
| [A009](../../tasks/assets/A009.md) | `inn_kitchen.py` | 客栈后厨 |
| [A010](../../tasks/assets/A010.md) | `riverside_warehouse.py` | 河运仓房 |
| [A011](../../tasks/assets/A011.md) | `carpenter_workshop.py` | 木作工棚 |
| [A012](../../tasks/assets/A012.md) | `kiln_shed.py` | 窑场棚屋 |
| [A013](../../tasks/assets/A013.md) | `temple_gate.py` | 山门 |
| [A014](../../tasks/assets/A014.md) | `main_hall.py` | 寺院正殿 |
| [A015](../../tasks/assets/A015.md) | `lecture_hall.py` | 讲堂 |
| [A016](../../tasks/assets/A016.md) | `library_house.py` | 藏书楼 |
| [A017](../../tasks/assets/A017.md) | `water_pavilion.py` | 临水亭 |
| [A018](../../tasks/assets/A018.md) | `covered_corridor.py` | 沿岸曲廊 |
| [A019](../../tasks/assets/A019.md) | `opera_stage.py` | 街角戏台 |
| [A020](../../tasks/assets/A020.md) | `water_gate.py` | 水关门楼 |
| [A021](../../tasks/assets/A021.md) | `watch_tower.py` | 石基望楼 |
| [A022](../../tasks/assets/A022.md) | `farm_house.py` | 茶田农舍 |
| [A023](../../tasks/assets/A023.md) | `boat_shed.py` | 修船长棚 |
| [A024](../../tasks/assets/A024.md) | `bamboo_retreat.py` | 竹林山居 |

 工厂只向当前builder写入本资产的网格和连接点。不要清空Blender场景、保存全局主文件、修改其他资产、下载外部资源或暗中更改全局随机种子。共享的新工具另写在本扩建目录内，并由相关任务明确引用。
