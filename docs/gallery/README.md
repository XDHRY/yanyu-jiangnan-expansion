# 烟雨江南扩建 · 36机位 4K 最终画廊

> 3840×2160 · Cycles · 256 samples（关键 Hero 机位 384）· 16-bit PNG

当前 36 机位 4K 最终渲染工作流已经启动。由于使用 GitHub 公共 CPU runner，任务会分批排队执行。

## 最终查看位置

- 预览宣传页：[`docs/gallery/4k/README.md`](4k/README.md)
- 完整 4K 原图：仓库 **Releases** 页面
- 原图将分成 3 个 ZIP，每包 12 张，共 36 张。
- Actions artifact 同时保留单张 PNG 90 天，作为备用下载渠道。

## 渲染策略

- 分辨率：3840×2160
- 引擎：Cycles
- 普通最终机位：256 samples
- Hero 机位：384 samples
- 16-bit PNG
- 自适应采样 + 去噪
- 每个仓库最多 2 个 4K 镜头并行，允许长时间排队，避免公共 runner 被一次占满。

工作流全部完成后，此入口页会自动更新为 36 张实际预览图与精确 Release 下载链接。
