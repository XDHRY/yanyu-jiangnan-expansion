# nature · 后续实现目录

 本轮只建立目录和任务说明。本目录中尚无资产实现文件，不能将文件名清单当作已经生成的模型。
 每个模型依照[Python契约](../../docs/03_python_contract.md)新增一个工厂文件，入口为`build(builder, instance)`。
 本分类任务如下；打开任务文件复制主提示词即可开始。

 | 任务 | 目标Python文件 | 资产 |
 |---|---|---|
 | [A073](../../tasks/assets/A073.md) | `willow_tree.py` | 岸边垂柳 |
| [A074](../../tasks/assets/A074.md) | `bamboo_cluster.py` | 竹丛母体 |
| [A075](../../tasks/assets/A075.md) | `old_plum.py` | 古梅 |
| [A076](../../tasks/assets/A076.md) | `cypress_tree.py` | 寺前古柏 |
| [A077](../../tasks/assets/A077.md) | `reeds_patch.py` | 溪边芦苇 |
| [A078](../../tasks/assets/A078.md) | `lotus_patch.py` | 池中荷叶 |
| [A079](../../tasks/assets/A079.md) | `moss_patch.py` | 苔藓斑块 |
| [A080](../../tasks/assets/A080.md) | `bank_grass.py` | 河滩草丛 |
| [A081](../../tasks/assets/A081.md) | `tea_row.py` | 茶树行 |
| [A082](../../tasks/assets/A082.md) | `rice_paddy.py` | 水稻田块 |
| [A083](../../tasks/assets/A083.md) | `scholar_rock.py` | 太湖石 |
| [A084](../../tasks/assets/A084.md) | `shore_rocks.py` | 岸边乱石组 |

 工厂只向当前builder写入本资产的网格和连接点。不要清空Blender场景、保存全局主文件、修改其他资产、下载外部资源或暗中更改全局随机种子。共享的新工具另写在本扩建目录内，并由相关任务明确引用。
