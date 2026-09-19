# 机器可读规划目录

assets.json：96个资产任务；materials.json：16个材质任务；systems.json：12个系统任务；assemblies.json：12个组合任务；task_graph.json：第一波 148 项依赖。

**board.json 才是 340 卡闭环的权威状态**（planned → implemented → validated → integrated）。`sync_board.py` 生成 board、STATE.md 和第二波短卡；`check_board.py` 是 CI 门禁。

第一波 JSON 仍保留规格，不再假装全部 planned。完成状态只写 board，保持 task_id 稳定。旧 asset_db 不在本轮更新。
