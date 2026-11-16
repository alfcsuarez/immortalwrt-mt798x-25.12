# MTK Wi-Fi 7 离线资料与知识库

本目录保存用户指定仓库的 19 份 PDF 原件，共 721 页，并提供逐份分析、按物理页检索的文本/OCR 索引和当前源码锚点。导入日期：2026-11-16。

上游固定为 [benboguan/immortalwrt-mt799x@38666f1d](https://github.com/benboguan/immortalwrt-mt799x/tree/38666f1d78047eb78036fa4d2b7b96880cefcaa3/package/mtk/pdf)。原件未修改，`manifest.json` 记录每份 PDF 的 SHA-256、上游 Git blob SHA-1、URL、页数及对应分析。原文件中的版权、标记和条款原样保留，本目录不为这些资料重新授予软件许可证。

## 入口

- [逐份知识索引与适用性](knowledge/README.md)：19 篇分析、帮助程度和使用边界。
- [本项目的应用结论](knowledge/applicability.md)：当前 WEXT/BE14 架构与文档的对应关系、可改进项及尚未验证项。
- [源码锚点](knowledge/source-map.json)：当前源包应用 38 个 mt_wifi7 补丁后的关键参数/符号位置。
- [离线归档清单](source-cache.json)：`dl` 的 14 个上游条目逐项取舍与哈希，另记录保留的现有构建输入。
- [Wi-Fi SDK 技能](../../../.agents/skills/mtk-wifi7-sdk/SKILL.md)与[源码缓存技能](../../../.agents/skills/mtk-sdk-source-reference/SKILL.md)：供后续任务按需读取资料。

## 检索与校验

在仓库根目录运行，工具只使用 Python 3 标准库，不连接设备或执行文档命令：

```sh
python3 scripts/mtk-sdk-reference.py verify
python3 scripts/mtk-sdk-reference.py search 'VOW_Airtime_Fairness_En'
python3 scripts/mtk-sdk-reference.py search 'MAP_HOSTAPD_SUPPORT' --doc multi-ap
python3 scripts/mtk-sdk-reference.py page airtime 14
python3 scripts/mtk-sdk-reference.py page multi-ap 281
python3 scripts/mtk-sdk-reference.py archive-list mt799x_20250613-415824.tar.xz --match pp_cmd
python3 scripts/mtk-sdk-reference.py archive-search mt799x_20250613-415824.tar.xz UniCmdPPCapCtrl
```

`knowledge/pages.jsonl` 覆盖所有 721 个物理页，保留原始提取文本；37 页另附截图 OCR。`ocr_text_unverified` 明确表示未经逐字保证的识别结果。命令、单位、位号、符号和表格需回原图及当前代码核对；目录标题的页码、文档页脚与物理页不要混用。无搜索结果也不证明图片中没有该内容。

索引由 `pdftotext -layout` 按换页符分割，部分图片以 pdftoppm 渲染后用 tesseract（eng）补充。它是检索材料，不是固件认可的命令清单。后续重建索引时保留物理页边界、更新 manifest 哈希，并再次执行完整校验。

## 当前项目基线与效果边界

分析对照源提交 `3bda8cd5e751a651ef4a71a6077eeb90b315f088`。当时私有构建选择 OSAL/WEXT，关闭 driver 与 OSAL 的 cfg80211；BE14 使用 20260721 板卡固件，内核已升级到 6.12.117。builder 的实际 defconfig 与源码中的示例 defconfig 可能不同，使用知识前重新确认。

资料多数是 2023 年应用说明，另有跨平台 Multi-AP 草案。不能将 MT7996/BE19000 的 4 streams、菜单名字、寄存器或实验参数直接用于 MT7990/BE14。主机配置成功、命令返回、固件接受和实际功能效果要分别证明。

本次新增目录没有 package Makefile 或设备启动入口；PDF/索引/技能不被安装到固件镜像。新增的 10 个 `dl` 参考归档也没有被新运行时包选用。现有正常运行固件、当前 Wi-Fi 源包/哈希、配置及调度策略没有因为资料入库而切换。

重启与 SFP 偶发故障依当前用户要求暂缓。保留相关架构知识不意味着已定位或验证这些故障，也不触发重启、工厂校准或设备寄存器实验。
