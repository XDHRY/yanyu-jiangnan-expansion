# 输出位置

本轮交付的是项目框架与详细任务提示词。这里尚无已经运行或验收的 `.blend`。

下一位 AI 完成对应任务后，把新产物放入新的版本子目录，例如 `v001/`。
`build_world.py` 要求目标目录尚不存在，避免覆盖此前的结果。

初版命令（在仓库根目录运行）：

```bash
python expansion/scripts/build_world.py --format obj --out expansion/generated/v001_obj
blender -b --factory-startup --python-exit-code 1 --python expansion/scripts/build_world.py -- --format blend --out expansion/generated/v001_blend
```

OBJ 为米制、Z 向上，导入 Blender 时保持 Z Up、Y Forward；材质文件必须与 OBJ 同目录。
`.blend` 输出包括区域集合、实例根节点、初版网格、连接点、材质块和总览相机。
它不包含旧庭院、不自动把旧场景导入进来，也不代表已经完成提示词中的精细模型。
