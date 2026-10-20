# step-language

把纯文本流程，编译成一个手机能用、离线也能看的交互式指南。

[在线介绍页](https://geno1024-aigc.github.io/step-language/) ·
[交互示例](https://geno1024-aigc.github.io/step-language/example/) ·
[English](README.md)

`step-language` 是一个用于分步流程的小型 DSL 与静态站点编译器。用 `.step` 文件描述步骤，
加入勾选项、判断分支、提示、图片和代码块，编译器会生成一个独立的 HTML 页面：没有框架、
没有外部字体、没有运行时依赖。图片保持外链并懒加载，所以托管成本低，慢网络下也能快速打开。

编译器只使用 Python 标准库；生成的页面只使用原生 CSS 和 JavaScript。

> 本项目的代码、运行时、文档和示例 100% 由 AI 生成。

## 功能

- **分支流程** — 用 `?` 提问，用 `* 选项 -> 步骤` 把不同答案带到不同步骤，用 `done` 结束。
- **进度保留** — 勾选状态写入 `localStorage`，按文档 ID 和版本隔离；更新 `@version` 即可重置。
- **默认响应式** — 桌面端显示步骤侧栏，手机端使用抽屉目录，也支持键盘左右键翻页。
- **低流量** — 8 步示例约 54 KB HTML，gzip 后约 14.4 KB；图片使用懒加载，首屏不会下载无关图片。
- **阅读舒适** — 自动/浅色/深色主题、打印全部步骤、代码复制、步骤直达链接、重置进度。
- **默认安全** — 文本会 HTML 转义，内嵌 JSON 无法逃逸 `script` 标签，`javascript:` 等危险
  URL 会被拒绝。
- **无需构建工具链** — 只需要 Python 3.10+ 和浏览器。

## 快速开始

```bash
git clone https://github.com/Geno1024-AIGC/step-language.git
cd step-language

python3 -m steplang check examples/repair-computer.step --strict
python3 -m steplang build examples/repair-computer.step -o dist/repair.html
python3 -m steplang serve examples
```

打开 <http://127.0.0.1:8000/> 可以浏览会实时编译的示例目录。生成的 `dist/repair.html`
是一个独立页面，可以放到任意静态托管上。

如果希望直接使用 `steplang` / `stepc` 命令：

```bash
python3 -m pip install -e .
steplang guide
```

## 一个小的 `.step` 文件

```step
@title 电脑无法开机排查
@description 从供电到显示信号的简短排查
@id repair-computer
@version 1.0.0
@lang zh-CN
@start safety
@accent #2563eb

== safety | 安全准备
- [ ] 关闭电源并拔掉电源线
- [ ] 拔掉所有 USB 和外设
> 拆机前先触摸接地的金属机箱，释放静电。
! 若闻到焦味或看到电容鼓包，立即停止并送修。

@time 约 2 分钟
-> power

== power | 检查供电链路
? 按下电源键后，是否有灯光、声音或风扇转动？
* 有反应 -> display
* 完全无反应 -> cable
* 不确定 -> observe

== cable | 检查电源线与适配器
- 换一个已知正常的插座
- 换一根电源线或同规格适配器
? 更换后能开机吗？
* 能 -> display
* 仍不能 -> service

== display | 检查显示输出
- 确认显示器电源与输入源
- 重新插拔视频线
? 仍然没有画面吗？
* 是 -> service
* 否，已能进入系统 -> done

== service | 送修建议
记录电脑型号、故障表现和已经尝试过的步骤。
```

运行 `python3 -m steplang guide` 查看完整速查表，或直接打开
[交互示例](https://geno1024-aigc.github.io/step-language/example/)。

## 示例

- [电脑无法开机排查](https://geno1024-aigc.github.io/step-language/example/)
- [重装 Windows 系统](https://geno1024-aigc.github.io/step-language/reinstall-windows/)

两个页面都由 `examples/` 中的 `.step` 文件生成。

## 语法速览

| 结构 | 写法 |
| --- | --- |
| 元数据 | `@title`、`@description`、`@id`、`@version`、`@lang`、`@accent`、`@start` |
| 步骤 | `== step-id \| 步骤标题` |
| 列表 / 勾选 | `- 项目`、`- [ ] 待办`、`- [x] 已完成` |
| 提示 / 警告 | `> 提示`、`! 警告` |
| 时间 / 图片 | `@time 约 5 分钟`、`@img images/photo.jpg \| 图片说明` |
| 问题 / 分支 | `? 问题`、`* 选项 -> 步骤`、`* 完成 -> done` |
| 跳转 | `-> 步骤`；不写则按文档顺序继续 |
| 代码 | 围栏代码块 |
| 行内格式 | `**粗体**`、`` `代码` ``、`[文字](https://example.com)` |

`check --strict` 会把不可达步骤、空步骤、自循环等警告视为失败。
重复步骤 ID、未知跳转目标和危险 URL 始终是错误。

## CLI

| 命令 | 用途 |
| --- | --- |
| `python3 -m steplang build FILE [-o OUT]` | 把一个 `.step` 文件编译成独立 HTML 页面。 |
| `python3 -m steplang check FILE [--strict]` | 只解析和校验，不写文件。 |
| `python3 -m steplang serve [DIR] [--port N]` | 启动目录服务，按需编译 `.step` 文件并启用 gzip。 |
| `python3 -m steplang guide` | 输出简短的 DSL 速查表。 |

## GitHub Pages

`.github/workflows/pages.yml` 中的 `Deploy Pages` 工作流会运行测试、构建两个示例、复制
`web/` 中的介绍页，并通过 GitHub Actions 部署 `_site/`。

- 介绍页：<https://geno1024-aigc.github.io/step-language/>
- 电脑排查示例：<https://geno1024-aigc.github.io/step-language/example/>
- 重装 Windows 示例：<https://geno1024-aigc.github.io/step-language/reinstall-windows/>

如果 fork 了本项目，需要在 **Settings → Pages → Build and deployment → Source** 中选择一次
**GitHub Actions**，然后推送到 `master`。

## 开发

```bash
python3 -m unittest discover -s tests -t .
node --check steplang/assets/app.js   # 可选，安装 Node.js 时
```

## 目录

```text
steplang/              编译器包
steplang/assets/       生成页面的 CSS 和 JavaScript
examples/              示例流程与图片
web/                   GitHub Pages 介绍页源码
tests/                 unittest 测试
.github/workflows/     Pages 部署工作流
```
