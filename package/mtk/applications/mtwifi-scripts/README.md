# MTK cfg80211 / ucode 无线框架（开发中）

此包提供可选的 netifd ucode 后端，依赖 WiFi7 与 OSAL 同时启用 cfg80211。
当前私有固件的默认 WEXT 配置没有切换；本次提交保存开发进度，不代表可直接交付的生产固件。

## 已实现

- 现有无线配置只补充 `devname`、`phy`、`path` 元数据，保留段名、SSID、密码、信道和加密方式。
- 按 L1 profile 区分独立无线设备与频段别名，避免重复生成 6 GHz 设备。
- 先校验配置，再生成文件；配置文件使用 0600 权限与原子替换。
- `.dat` 多文件事务支持失败回滚；通过文件锁串行处理共享配置和 WPS 映射。
- 统一使用 procd 管理的 wpad，通过 ubus 添加、删除 AP，不按无线设备重复启动 hostapd。
- 不自动卸载驱动、递归执行 Wi-Fi 启动，也不启动或停止 EasyMesh/WAPP 服务。
- 6 GHz 检查 WPA3/OWE 与 PMF；结构性驱动参数变更明确返回需要重启。

`mtwifi-scripts` 与 `wifi-scripts`、`mtwifi-cfg` 互斥。原生 `iwinfo` 命令和 `luci-app-mtk` 菜单包继续保留。

## 云电脑验证进度

2026-11-16：

- 109 项原生 ucode / UCI / 文件系统回归通过，包含三频配置、AP 配置生成、失败回滚、重复加载、netifd 成功通知及配置迁移。
- 可选 hostapd 补丁共 246 个，完整严格回放通过（`--fuzz=0`）。
- 原生 hostapd、wpa_supplicant 与最终 wpad multicall 编译、链接通过。
- ARM64 GCC 14.3 / musl 的 json-c、zlib、libubox、ubus、UCI、libnl-tiny、ucode、udebug 和 OpenSSL 3.5.9 编译通过。

尚未完成 ARM64 wpad、cfg80211 / OSAL / WiFi7 整体编译及设备回归。
cfg80211 构建当前停在现有 mac80211 补丁
`390-wifi-mac80211-notify-driver-on-airtime-weight-change.patch` 的上下文不匹配；此次没有跳过该检查或修改生产配置。

没有进行 GitHub CI 验证。实机 AP/STA 关联、跨频 MLO、吞吐和重启行为尚未验证。

运行脚本回归：

```sh
python3 scripts/test-mtwifi-ucode.py --prefix /path/to/native/ucode/install --output results.json
```

测试使用真实 ucode、UCI 与文件系统；无线能力和守护进程回复使用固定测试数据，不执行无线硬件命令。

## 来源

参考 `benboguan/immortalwrt-mt799x` 的 `openwrt-25.12-mtwifi` 分支，
固定版本 `38666f1d78047eb78036fa4d2b7b96880cefcaa3`。
保留源文件版权声明；hostapd 使用本仓库现有补丁作为基线，按需适配 ucode 与 HE/EHT 配置支持。
