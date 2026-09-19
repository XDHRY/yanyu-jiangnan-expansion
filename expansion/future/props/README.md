# props · 后续实现目录

 本轮只建立目录和任务说明。本目录中尚无资产实现文件，不能将文件名清单当作已经生成的模型。
 每个模型依照[Python契约](../../docs/03_python_contract.md)新增一个工厂文件，入口为`build(builder, instance)`。
 本分类任务如下；打开任务文件复制主提示词即可开始。

 | 任务 | 目标Python文件 | 资产 |
 |---|---|---|
 | [A053](../../tasks/assets/A053.md) | `market_stall.py` | 街市摊架 |
| [A054](../../tasks/assets/A054.md) | `woven_basket.py` | 竹编货篮 |
| [A055](../../tasks/assets/A055.md) | `wooden_crate.py` | 叠放木箱 |
| [A056](../../tasks/assets/A056.md) | `cloth_sack.py` | 麻布货包 |
| [A057](../../tasks/assets/A057.md) | `paper_lantern.py` | 檐下灯笼 |
| [A058](../../tasks/assets/A058.md) | `riverside_lamp.py` | 临河灯架 |
| [A059](../../tasks/assets/A059.md) | `inn_banner.py` | 客栈酒旗 |
| [A060](../../tasks/assets/A060.md) | `tea_table.py` | 木茶案 |
| [A061](../../tasks/assets/A061.md) | `wood_bench.py` | 长条凳 |
| [A062](../../tasks/assets/A062.md) | `inn_counter.py` | 客栈柜台 |
| [A063](../../tasks/assets/A063.md) | `wood_bed.py` | 木床榻 |
| [A064](../../tasks/assets/A064.md) | `wine_jar.py` | 陶酒坛 |
| [A065](../../tasks/assets/A065.md) | `water_bucket.py` | 供水木桶 |
| [A066](../../tasks/assets/A066.md) | `stone_well.py` | 石井井栏 |
| [A067](../../tasks/assets/A067.md) | `kitchen_stove.py` | 灶台锅具 |
| [A068](../../tasks/assets/A068.md) | `fishing_net_rack.py` | 河岸晾网架 |
| [A069](../../tasks/assets/A069.md) | `cloth_drying_rack.py` | 晒布架 |
| [A070](../../tasks/assets/A070.md) | `editable_sign_text.py` | 匾额文字层 |
| [A071](../../tasks/assets/A071.md) | `wood_handcart.py` | 手推木车 |
| [A072](../../tasks/assets/A072.md) | `bamboo_broom.py` | 竹制扫帚 |

 工厂只向当前builder写入本资产的网格和连接点。不要清空Blender场景、保存全局主文件、修改其他资产、下载外部资源或暗中更改全局随机种子。共享的新工具另写在本扩建目录内，并由相关任务明确引用。
