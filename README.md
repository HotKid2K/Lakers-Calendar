# 🏀 湖人队中文赛程订阅日历 / Lakers CN Calendar

一个可以自己在 GitHub 托管的**中文赛程 iCalendar（ICS）**：

- 比赛标题：`湖人VS勇士` / `湖人VS快船`，无冗长前缀、表情或主客场后缀
- 比赛时间：只设置开赛时刻，例如北京时间 `10:30`，不设置结束时刻，以便日历尽量只显示一项时间；实际 `DTSTART` 使用 UTC，苹果设备按系统所在时区显示（中国大陆、台湾均为 UTC+8）
- 主客场、中文球馆、比赛链接等信息保留在事件详情中，标题统一采用“湖人VS对手”，不在标题中区分主客场
- 常规赛、后续官方发布的附加比赛、附加赛及季后赛：只要 NBA 提供比赛记录就纳入；不包含季前赛
- GitHub Actions 每 **6 小时**尝试获取最新赛程、生成日历；使用稳定比赛 UID，减少自动更新时产生重复事件的风险
- GitHub Pages 提供长期不变的在线订阅网址
- 不需要付费服务器、不需要 API Key 或第三方 Python 库

> ⚠️ 此仓库初始附有一份已有的 **2026–27赛季80场**赛程快照，用于初次上线。自动化首次成功运行后，会从 NBA 公开数据源重新生成；NBA 杯尚未决定或未公布开球时间的比赛不会猜测。NBA 公共数据源不是稳定承诺的正式开发者接口；接口异常时保留最后一次成功的文件。

## 版本说明：全中文极简版

- **日历列表**：只显示 `湖人VS勇士` 这样短标题；开赛时刻使用北京时间，例如 `10:30`，不写英文赛事前缀、长球队名称、场馆或主客场后缀。
- **赛事详情**：球馆 `直觉巨蛋`、`大通中心`、`加密网竞技场` 等中文名称；说明为 `常规赛｜湖人客场`、`北京时间：10月29日 10:30`。
- **不认识的场馆名称**：标注 `比赛场馆待确认`，避免把无法辨认的英语直接展示给订阅用户，也不乱翻译；遇到可核实的新球馆，可编辑 `scripts/update_schedule.py` 的 `ARENA_ZH`。
- **预置赛程**：保留原来的80场和事件编号，按当季球队常规主场补全中文球馆；如比赛改为中立场地，以后续自动同步的数据为准。
- **自动更新**：新增或变更比赛仍然走相同中文转换逻辑，绝不因为下一次自动同步恢复英文。
- **时区**：文件按世界协调时存储开球瞬间，苹果日历在 UTC+8 区域显示为北京时间。如果人在其他时区，需在 iPhone 日历设置中选择北京时间时区覆盖。

取消 `DTEND` 是为了尽可能只在列表显示开赛时刻，但苹果日历界面仍由 iOS 控制，不能保证它不显示时间范围。赛事链接的网址属于技术地址，不作翻译。已经订阅旧版的用户应替换仓库文件，等待日历订阅刷新。

## 一、用 GitHub 网页创建仓库（不需要命令行）

1. 登录 [github.com](https://github.com)，点击右上角 `+` → **New repository**（或直接打开 <https://github.com/new>）。
2. **Repository name** 填 `lakers-cn-calendar`；选择 **Public**；**Add a README file** 保持关闭（仓库刚创建时先不要添加其他文件）。
3. 点击 **Create repository**。
4. 把下载的本项目 ZIP 文件**解压**，进入解压后的 `lakers-cn-calendar` 文件夹。不要直接上传 ZIP。
5. 在仓库的空白初始页面点击 **uploading an existing file**；或在 `Add file` → `Upload files` 页面，把**文件夹里面的所有内容**一起拖入页面，包括 `.github` 文件夹、`scripts` 文件夹、`tests` 文件夹、`docs` 文件夹和 `README.md`。
6. 检查 GitHub 显示了 `.github/workflows/update.yml` 等完整路径，然后提交（**Commit changes**）。

## 二、启动自动更新与在线发布

1. 仓库 → **Settings** → **Pages** → **Build and deployment** → **Source** 选择 **GitHub Actions**。**不要选 Deploy from a branch**，因为本项目用自己的部署工作流更新 Pages。
2. 仓库 → **Actions** → 左边点击 **更新并发布湖人中文赛程** → **Run workflow** → 运行。首次触发通常也可能由上传工作流时的 `push` 触发。
3. 等待 `generate` 和 `deploy` 两个作业成功完成；如 GitHub 提示启用 Workflows 或允许 Pages，按页面完成设置。
4. 如果更新步骤失败但已有初始文件，脚本会保留原始赛程并尝试发布；若部署失败，去 **Actions** 打开失败的运行日志。

## 三、苹果 iPhone 订阅地址

假设 GitHub 用户名是 `USERNAME`，仓库名为 `lakers-cn-calendar`，网站为：

```text
https://USERNAME.github.io/lakers-cn-calendar/
```

永久的 ICS 订阅地址为：

```text
https://USERNAME.github.io/lakers-cn-calendar/lakers.ics
```

> `USERNAME` 必须替换为你真实的 GitHub 用户名。链接只会在你实际创建仓库并成功发布后生效。

在 iPhone「日历」App → 底部「日历」→「添加日历」→ **「添加订阅日历」** → 粘贴第二个 `.ics` 地址 → 确认。

也可以用 iPhone Safari 打开第一条网站地址，使用网页上的复制订阅地址或一键订阅按钮。

**不要下载 `.ics` 再一次性导入**；一定要添加“订阅日历”，才会根据网络上的文件更新。

## 四、数据更新机制

- **原始数据**：NBA 公开 JSON 赛程，按顺序尝试：
  - `https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json`
  - `https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json`
- 默认至少接受 `2026-27` 赛季的 50 场已确定开球时间比赛；后续新赛季公布超过该门槛时自动切换新赛季。
- **每6小时检查一次**，如果对阵和时间没变化则不重复提交；如果有修改，按同一 UID 更新事件并提升 `SEQUENCE`。
- GitHub Pages 的更新和苹果日历的再次拉取都需要时间：不是实时推送；GitHub Actions 计划任务也可能延迟，长期不活跃的公开仓库可能被 GitHub 停用计划任务（需要去 Actions 重新启用）。
- 若 NBA CDN 拒绝访问、返回旧赛季、比赛数量异常或请求中断，保留最后一次可用的 `.ics` 文件。
- 过渡时尽量复用初始快照中的事件 UID，避免首次同步后出现重复日程。
- 通知 `VALARM` 写在 ICS 中，但苹果**订阅日历**是否响铃由系统设置决定，不能保证一定提前30分钟提醒。

## 五、测试 / 手动更新

在 Python 3.9+（含 `zoneinfo`）的环境下：

```bash
python -m unittest discover -s tests -v
python scripts/update_schedule.py
```

无需 `pip install`。如果需要修改刷新频率，编辑 `.github/workflows/update.yml` 中的 `cron`。不用提供密码、GitHub Token 或其他密钥。

## 版权与说明

球迷自用项目，未获 NBA 或洛杉矶湖人队官方背书；使用的球队及赛事名称仅用于识别赛程。赛程和比赛时刻最终以 NBA 官方公告为准。
