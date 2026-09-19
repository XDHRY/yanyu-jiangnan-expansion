# environment · 后续实现目录

 本轮只建立目录和任务说明。本目录中尚无资产实现文件，不能将文件名清单当作已经生成的模型。
 每个模型依照[Python契约](../../docs/03_python_contract.md)新增一个工厂文件，入口为`build(builder, instance)`。
 本分类任务如下；打开任务文件复制主提示词即可开始。

 | 任务 | 目标Python文件 | 资产 |
 |---|---|---|
 | [A085](../../tasks/assets/A085.md) | `stone_paving.py` | 青石铺路 |
| [A086](../../tasks/assets/A086.md) | `mud_transition.py` | 泥地过渡 |
| [A087](../../tasks/assets/A087.md) | `courtyard_drain.py` | 院内排水沟 |
| [A088](../../tasks/assets/A088.md) | `pond_edge.py` | 园林池岸 |
| [A089](../../tasks/assets/A089.md) | `stepping_stones.py` | 汀步石组 |
| [A090](../../tasks/assets/A090.md) | `hillside_stairs.py` | 坡地台阶 |
| [A091](../../tasks/assets/A091.md) | `distant_hills.py` | 山林远景 |
| [A092](../../tasks/assets/A092.md) | `ground_mist.py` | 低雾体积 |
| [A093](../../tasks/assets/A093.md) | `eaves_rain.py` | 檐下雨线 |
| [A094](../../tasks/assets/A094.md) | `water_ripples.py` | 水面涟漪 |
| [A095](../../tasks/assets/A095.md) | `night_lighting.py` | 夜景光组 |
| [A096](../../tasks/assets/A096.md) | `camera_route.py` | 镜头路线 |

 工厂只向当前builder写入本资产的网格和连接点。不要清空Blender场景、保存全局主文件、修改其他资产、下载外部资源或暗中更改全局随机种子。共享的新工具另写在本扩建目录内，并由相关任务明确引用。
