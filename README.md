# TikTok 数据抓取与分析工具

自动抓取 TikTok 账号和话题数据，通过 DeepSeek AI 进行趋势分析，并推送到飞书群。附带可视化数据看板。

## 功能

- **账号数据抓取** — 基于 Apify API 获取 TikTok 账号的粉丝数、点赞数、视频数等精确数据
- **话题数据抓取** — 基于 TikHub API 获取话题标签的播放量、视频数
- **定时追踪** — 对预设账号/话题进行每日追踪，保存到 CSV 文件
- **AI 趋势分析** — 调用 DeepSeek 对比日环比/3日/周/月四个时间窗口，生成中文数据点评
- **飞书推送** — 将每日报告自动推送到飞书群
- **可视化看板** — 基于 Chart.js 的交互式数据大盘，展示账号和话题的趋势图

## 项目结构

```
├── main.py               # 主入口，支持命令行模式
├── tiktok_scraper.py     # 数据抓取核心（Apify + TikHub）
├── analysis.py           # DeepSeek AI 趋势分析模块
├── config.py             # 配置文件
├── send_report.example.sh # 飞书推送脚本（模板）
├── dashboard.html        # 可视化数据看板
├── tracking_data.csv     # 账号追踪数据
├── tracking_hashtags.csv # 话题追踪数据
└── requirements.txt      # Python 依赖
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/as167888/tiktok-scraper.git
cd tiktok-scraper
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env 填入你的 API 密钥
```

需要申请以下 API：
- [Apify](https://console.apify.com/account#/integrations) — 获取 `APIFY_API_TOKEN`
- [TikHub](https://tikhub.io) — 获取 `TIKHUB_API_KEY`（可选，用于话题数据）
- [DeepSeek](https://platform.deepseek.com/api_keys) — 获取 `DEEPSEEK_API_KEY`（可选，用于 AI 分析）

### 4. 运行

```bash
# 自动模式：抓取预设账号和话题，保存到 CSV 并运行 AI 分析
python main.py

# 查询单个账号
python main.py account heartopia_en

# 查询单个话题
python main.py hashtag heartopia

# 同时查询账号和话题
python main.py both heartopia_en heartopia

# 追踪模式（追加到 CSV）
python main.py track
python main.py track_hashtags

# AI 趋势分析
python main.py analyze
```

### 5. 飞书推送（可选）

```bash
cp send_report.example.sh send_report.sh
# 编辑 send_report.sh 填入飞书应用凭证
bash send_report.sh
```

### 6. 可视化看板

直接在浏览器中打开 `dashboard.html`，或通过 GitHub Pages 访问：

**https://as167888.github.io/tiktok-scraper/dashboard.html**

看板包含三个标签页：
- **账号数据** — 各账号粉丝/点赞/视频数趋势图，支持按账号筛选
- **话题数据** — 各话题播放量/视频数趋势图，支持按话题筛选
- **原始数据** — CSV 数据的完整表格展示

## 定时运行

推荐使用 cron 设置每日自动运行：

```bash
# 每天早上 8:07 运行
7 8 * * * cd /path/to/tiktok-scraper && bash send_report.sh >> report.log 2>&1
```

## 技术栈

- **Apify API** — TikTok 账号数据（novi/tiktok-user-info-api）
- **TikHub API** — TikTok 话题标签数据
- **DeepSeek API** — AI 趋势分析与点评
- **飞书 IM API** — 消息推送
- **Chart.js** — 前端可视化图表

## License

MIT
