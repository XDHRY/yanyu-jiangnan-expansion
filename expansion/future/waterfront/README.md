# waterfront · 后续实现目录

 本轮只建立目录和任务说明。本目录中尚无资产实现文件，不能将文件名清单当作已经生成的模型。
 每个模型依照[Python契约](../../docs/03_python_contract.md)新增一个工厂文件，入口为`build(builder, instance)`。
 本分类任务如下；打开任务文件复制主提示词即可开始。

 | 任务 | 目标Python文件 | 资产 |
 |---|---|---|
 | [A041](../../tasks/assets/A041.md) | `canal_arch_bridge.py` | 跨渠石拱桥 |
| [A042](../../tasks/assets/A042.md) | `timber_bridge.py` | 木梁小桥 |
| [A043](../../tasks/assets/A043.md) | `stone_dock.py` | 青石水埠 |
| [A044](../../tasks/assets/A044.md) | `stone_quay.py` | 石砌驳岸 |
| [A045](../../tasks/assets/A045.md) | `slipway.py` | 下水坡道 |
| [A046](../../tasks/assets/A046.md) | `sluice_gate.py` | 简式水闸 |
| [A047](../../tasks/assets/A047.md) | `awning_boat.py` | 乌篷船 |
| [A048](../../tasks/assets/A048.md) | `cargo_barge.py` | 平底货船 |
| [A049](../../tasks/assets/A049.md) | `bamboo_raft.py` | 竹木小筏 |
| [A050](../../tasks/assets/A050.md) | `mooring_bollard.py` | 系缆柱组 |
| [A051](../../tasks/assets/A051.md) | `bamboo_flume.py` | 引水竹槽 |
| [A052](../../tasks/assets/A052.md) | `ferry_shelter.py` | 桥头候船棚 |

 工厂只向当前builder写入本资产的网格和连接点。不要清空Blender场景、保存全局主文件、修改其他资产、下载外部资源或暗中更改全局随机种子。共享的新工具另写在本扩建目录内，并由相关任务明确引用。
