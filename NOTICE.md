# NOTICE

本仓库是一个**非官方**的第三方工具，与 fischertechnik GmbH、beemo GmbH 及其关联公司
**没有任何隶属、赞助或背书关系**。

## 1. 项目包含什么

- 本项目作者编写的代码与文档（MIT，见 [LICENSE](LICENSE)）。
- `src/ftgateway/data/block-catalog.json`、`block-schema.json`：块的结构性元数据。

## 2. 数据文件从哪来

这两个 JSON 是在**用户本机已安装的 ROBO Pro Coding 6.5.4 应用**中，由 `bridge/dumpblocks.js`
读取该应用自身已加载的 Blockly 注册表后导出的，内容包括：

- 块类型标识（如 `motor_set_speed`）、输入名（如 `DO`、`speed`）、字段名
  （如 `instance_name_0`）——这些属于**接口/互操作性信息**；
- 块的界面标题与生成的 Python 片段——这些是**该应用的输出内容**。

数据文件的用途仅为：让第三方工具能正确生成与校验 `.ft` 工程（互操作性），
以及教学与研究。

**本项目不包含**：官方软件本体、安装程序、可执行文件、固件、图片/图标/字体素材、
语言包，也不包含任何反编译得到的源代码。

## 3. 权利与使用条件

- 上述元数据中的界面文案、生成代码与产品名称，权利归 fischertechnik GmbH / beemo GmbH
  及其许可方所有；本项目的 MIT 许可**不覆盖**这些内容，也不随之授予任何再分发许可。
- 如果你是权利人并希望移除这些数据文件，请开 issue，我们会在下一次提交中删除；
  工具链在缺少这两个文件时仍可运行（`ftg verify` 会降级为只做结构与语法检查）。
- 使用者可以随时自行重新生成这些文件（`node bridge/dumpblocks.js`），或直接删除。

## 4. 商标

「fischertechnik」「ROBO Pro Coding」「ROBO TXT」「TXT」等名称与标识是其各自所有人的商标。
本仓库仅在**描述性**意义上使用这些名称来说明兼容对象，不主张任何商标权。

## 5. 使用风险

本工具会读写你本机的工程文件，并可通过调试接口驱动 ROBO Pro Coding 应用。
请在你自己拥有或获授权的设备与工程上使用；对因使用本工具造成的任何数据丢失、
设备损坏或保修失效，作者不承担责任。运行前请备份工程。

## 6. 第三方组件

- Blockly — Apache License 2.0，© Google LLC（本项目不打包其代码，仅通过应用运行时使用）。
- Python 标准库 — PSF License。
