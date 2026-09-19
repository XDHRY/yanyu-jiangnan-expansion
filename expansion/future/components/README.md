# components · 后续实现目录

 本轮只建立目录和任务说明。本目录中尚无资产实现文件，不能将文件名清单当作已经生成的模型。
 每个模型依照[Python契约](../../docs/03_python_contract.md)新增一个工厂文件，入口为`build(builder, instance)`。
 本分类任务如下；打开任务文件复制主提示词即可开始。

 | 任务 | 目标Python文件 | 资产 |
 |---|---|---|
 | [A025](../../tasks/assets/A025.md) | `stone_foundation.py` | 石台基 |
| [A026](../../tasks/assets/A026.md) | `stone_steps.py` | 踏步组 |
| [A027](../../tasks/assets/A027.md) | `column_base.py` | 柱础木柱 |
| [A028](../../tasks/assets/A028.md) | `timber_beam.py` | 穿枋横梁 |
| [A029](../../tasks/assets/A029.md) | `rafter_frame.py` | 檩椽屋架 |
| [A030](../../tasks/assets/A030.md) | `gable_roof.py` | 双坡屋面 |
| [A031](../../tasks/assets/A031.md) | `hip_gable_roof.py` | 歇山屋面 |
| [A032](../../tasks/assets/A032.md) | `tile_course.py` | 瓦垄与滴水 |
| [A033](../../tasks/assets/A033.md) | `grey_brick_wall.py` | 灰砖墙段 |
| [A034](../../tasks/assets/A034.md) | `lime_wall.py` | 粉墙段 |
| [A035](../../tasks/assets/A035.md) | `moon_gate.py` | 月洞门 |
| [A036](../../tasks/assets/A036.md) | `lattice_door.py` | 格扇门 |
| [A037](../../tasks/assets/A037.md) | `shutter_window.py` | 支摘窗 |
| [A038](../../tasks/assets/A038.md) | `water_railing.py` | 临水栏杆 |
| [A039](../../tasks/assets/A039.md) | `sign_frame.py` | 门额招牌框 |
| [A040](../../tasks/assets/A040.md) | `corridor_corner.py` | 连廊转角 |

 工厂只向当前builder写入本资产的网格和连接点。不要清空Blender场景、保存全局主文件、修改其他资产、下载外部资源或暗中更改全局随机种子。共享的新工具另写在本扩建目录内，并由相关任务明确引用。
