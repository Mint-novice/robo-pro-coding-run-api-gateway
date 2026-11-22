# ROBO Pro Coding Run API Gateway

> 慧鱼（fischertechnik）ROBO Pro Coding（TXT 4.0）工程的 API 式网关：读、写、生成、校验、直接驱动。

读写、生成、校验、**驱动** 慧鱼（fischertechnik）ROBO Pro Coding 的 `.ft` 工程文件。

- `.ft` 就是 ZIP：JSON 元数据 + Blockly XML + Python，可以不打开软件直接读写。
- 内置 **314 个块**的完整字典（输入名 / 字段名 / 官方生成的 Python），
  从软件本体提取：`src/ftgateway/data/block-schema.json`。
- `bridge/` 提供 CDP 桥：在运行中的软件里打开工程、读工作区、让软件自己生成代码。
- 一条命令生成常见程序：电机常转、LED 闪烁、LED 常亮、纯 Python 工程。

## 交给 AI 智能体用

克隆仓库后，对智能体说一句就行（Claude Code / Cursor / Codex / Cline 都行）：

> 把 `https://github.com/your-name/robo-pro-coding-run-api-gateway` 克隆下来，
> 读 `AGENTS.md`，然后用 `ftg` 帮我生成并校验慧鱼工程。

`AGENTS.md` 就是给它的契约：容器格式、可用命令、两个会静默搞坏工程的坑、以及每次改完
必须跑的校验流程。块的行为不靠模型猜——`src/ftgateway/data/` 里 314 个块的字典就是
事实来源。

机器要求：

* Python 3.9+（无第三方依赖）
* 可选，仅当需要“让软件打开工程 / 截图”时：Windows + 已安装 ROBO Pro Coding
  （`bridge/launch.ps1`）

如果你的智能体支持 skill，把自带的那个装上，就能按名字（`fischertechnik-ft`）触发：

```powershell
.\skills\install-skill.ps1              # 装到 %USERPROFILE%\.claude\skills
```

```bash
./skills/install-skill.sh               # 装到 ~/.claude/skills
```

开局先让它自检：

```bash
ftg --version && ftg verify examples/motor-run.ft --strict
```

## 安装

```bash
git clone https://github.com/your-name/robo-pro-coding-run-api-gateway.git
cd ftg
pip install -e .
ftg --help
```

零第三方依赖，Python 3.9+。

## 命令行

```powershell
ftg gen motor-run --name Motor_Run --speed 512   # 生成：M1 电机一直转
ftg gen led-blink --name LED_Blink --hold 1      # 生成：M1 上的 LED 一秒一闪
ftg verify examples\motor-run.ft --strict        # 静态校验
ftg info examples\motor-run.ft                   # 结构 + 元数据 + 块列表
ftg extract a.ft out\ ; ftg pack out\ b.ft       # 解包 / 打包
ftg blocks motor                                 # 搜块字典
```

`verify` 会检查：容器、元数据、主文件与 `mode/name` 是否匹配、XML 合法性、
**每个块的语句输入名**、块类型是否在官方清单里、每个 `.py` 能否编译。

## Python API

```python
from ftgateway import build_motor_run, verify
from ftgateway.blocks import ProjectBuilder

build_motor_run("Motor_Run", speed=512).save("Motor_Run.ft")
print(verify("Motor_Run.ft", strict=True))

b = ProjectBuilder("Conveyor")
b.add_motor("M1")
b.motor("M1", speed=300)
b.wait(2)
b.motor_off("M1")
b.build().save("Conveyor.ft")
```

## 桥接（直接驱动软件）

软件是 Electron，带 `--remote-debugging-port` 启动后可用 CDP 脚本化：

```powershell
.\bridge\launch.ps1 -Port 9334      # 自动清 ELECTRON_RUN_AS_NODE + 独立 profile
$env:CDP_PORT = 9334
node bridge\cdp.js eval "document.body.innerText"
node bridge\setfile.js examples\motor-run.ft     # 在软件里打开工程（不弹系统对话框）
node bridge\verify_in_app.js ctrl.blockly main.blockly   # 用软件自己的 Blockly 复核
node bridge\dumpblocks.js blocks.json            # 软件升级后刷新块字典
```

关键点：软件的“加载项目 → 下一步”最后是网页里的 `<input type=file>`，
用 `DOM.setFileInputFiles` 直接喂文件即可，绕开系统文件对话框。

## 两个最贵的坑

1. **`loop_endless` 的语句输入名是 `DO`，不是 `statement`。**
   写错时 Blockly 会静默丢弃里面的块——UI 上就是空循环，没有任何报错。
   `ftg verify` 会拦这种文件。
2. **引脚实例名是 `<控制器id>-<引脚块id>`。**
   电机块的 `instance_name_0` 必须与 `lib/controller.blockly` 里 `Motor-0`
   上挂的硬件块 id 一致，否则下拉退回 `-`，生成代码变成 `-.set_speed(...)`。

这两条都固化进了 `src/ftgateway/blocks.py` 和 `src/ftgateway/verify.py`。

## 已验证到什么程度

| 层次 | 证据 |
|---|---|
| 容器/元数据 | 单元测试 + extract/pack 往返 |
| 块 XML | 软件内自己的 Blockly 解析通过 |
| 生成的 Python | 软件的 `pythonGenerator` 现场产出 |
| 实机 | TXT 4.0，M1 电机持续转、LED 闪烁 |

## 法律声明

本项目是**非官方**第三方工具，与 fischertechnik GmbH、beemo GmbH 无隶属、赞助或背书关系。

* 本项目自写的代码与文档为 MIT 许可（见 [LICENSE](LICENSE)）。
* `src/ftgateway/data/*.json` 是从本机已安装应用导出的**互操作性元数据**（块标识、输入名、
  字段名，以及各块生成的代码片段）。界面文案与生成内容的权利归其所有人，MIT 许可**不覆盖**
  这些内容，也不授予再分发权。来源与删除方式见 [NOTICE.md](NOTICE.md)。
* 不包含软件本体、安装包、固件、素材、字体或语言包。
* 产品名称与商标归各自所有人，此处仅用于说明兼容性。
* 通过桥接驱动你本机的应用与工程，风险自负；使用前请备份 `.ft` 文件。

## 局限

- 桥接部分面向 Windows（软件是 Electron，CLI 部分跨平台）。
- 上传/运行到 TXT 仍需在软件里点一下（路线图里有 `ftg upload`）。
- 块字典是 ROBO Pro Coding 6.5.x 的快照，升级后用 `bridge/dumpblocks.js` 重新导出。
- 与 fischertechnik 官方无关，风险自负。

## 许可

MIT。
