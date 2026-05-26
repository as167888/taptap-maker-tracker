# TapTap Maker 游戏数据追踪系统

自动化爬取、存储、展示 TapTap 平台上所有使用"TapTap 制造"标签的游戏信息，并生成可排序的数据报告页面。

## 项目概述

TapTap 的[TapTap 制造](https://www.taptap.cn/tag/TapTap%E5%88%B6%E9%80%A0)标签汇集了大量开发者使用 TapTap 服务制作的游戏。本项目实现了对这些游戏的**全流程自动化追踪**：

- **游戏发现**：遍历标签列表页，提取所有游戏名称和详情页链接
- **详情采集**：逐款抓取每款游戏的发布日期、下载量、关注量、评分、评价数量
- **数据持久化**：SQLite 数据库存储，支持增量更新和爬取状态追踪
- **可视化展示**：自动生成带排序功能的 HTML 数据报告，可通过 GitHub Pages 发布

## 项目结构

```
maker/
├── main.py                          # 主入口：全流程调度 + 参数化运行 + 交互式菜单
├── init_db.py                       # 数据库核心：建表、CRUD、状态管理
├── db_query.py                      # 交互式数据库浏览器（分页/筛选/排序）
├── import_links.py                  # 链接导入工具（支持 txt/csv/xlsx）
├── 1.爬取带TapTap制造tag的游戏/
│   └── taptap_spider.py             # 阶段1：列表页爬虫（50页）
├── 2.爬取TapTap制造的游戏详细信息/
│   └── taptap_mk_detail.py          # 阶段2：详情页爬虫
├── 3.生成网站发布页面/
│   └── generate_html.py             # 阶段3：HTML 报告生成器
├── export/                          # 输出目录（所有生成文件存放于此）
├── docs/                            # GitHub Pages 发布目录
│   └── index.html                   # 最新数据报告页面
└── taptap_games.db                  # SQLite 数据库（运行时自动生成）
```

## 数据流程

```
TapTap 制造标签页 (50页)
        │
        ▼
  taptap_spider.py           ← 爬取游戏名称 + 详情页链接
        │
        ▼
  [export/*_game_list.xlsx]  ← 游戏列表
        │
        ▼
  sync_from_xlsx()           ← 新链接写入 SQLite（URL 去重）
        │
        ▼
  taptap_mk_detail.py        ← 逐款爬取详情（JSON-LD + Nuxt 数据）
        │
        ▼
  [export/*_game_detail.xlsx] ← 完整数据
        │
        ▼
  generate_html.py           ← 生成可排序 HTML 报告，剔除名称爬取失败的游戏
        │
        ▼
  [export/*_result.html]     ← 最终报告
  [docs/index.html]          ← GitHub Pages 发布副本
```

## 数据库设计

### games 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT | 游戏名称 |
| url | TEXT UNIQUE | 详情页链接（去重键） |
| published_date | TEXT | 发布日期 |
| downloads | TEXT | 下载量 |
| followers | TEXT | 关注量 |
| rating | TEXT | 评分 |
| rating_count | TEXT | 评价数量 |
| detail_fetched | INTEGER | 爬取状态：0=待抓, 1=已抓, -1=跳过 |
| created_at | TIMESTAMP | 入库时间 |
| detail_updated_at | TIMESTAMP | 详情抓取时间 |

### 状态流转

```
0 (待抓取) ──成功──▶ 1 (已抓取)
     │
     └──失败/404──▶ -1 (已跳过)
```

## 快速开始

### 环境要求

- Python 3.8+
- 依赖库：

```bash
pip install requests beautifulsoup4 pandas openpyxl
```

### 使用方式

**参数化运行（推荐，适合自动化）**：

```bash
# 非交互模式：一键执行全流程
python main.py --full
```

**交互式菜单**：

```bash
python main.py
#  1. 启动全流程（爬取链接 → 详情 → HTML）
#  2. 查看数据库详细数据
#  3. 导入链接文件到数据库
#  4. 查看爬取历史记录
#  0. 退出
```

**单独运行各阶段**：

```bash
# 仅爬取游戏链接
cd "1.爬取带TapTap制造tag的游戏" && python taptap_spider.py

# 仅爬取游戏详情（需数据库中有链接）
cd "2.爬取TapTap制造的游戏详细信息" && python taptap_mk_detail.py
```

## GitHub Pages 发布

全流程运行后，最新的数据报告会自动复制到 `docs/index.html`。按以下步骤启用 GitHub Pages：

1. 在 GitHub 仓库页面进入 **Settings → Pages**
2. **Source** 选择 **Deploy from a branch**
3. **Branch** 选择 `master`，文件夹选择 `/docs`
4. 点击 **Save**

稍等片刻后，页面将在 `https://as167888.github.io/taptap-maker-tracker/` 可用。

## 数据示例

最终生成的 HTML 报告包含以下维度，支持点击表头排序：

| 游戏名称 | 游戏链接 | 发布日期 | 下载量 | 关注量 | 评分 | 评价数量 |

## 设计要点

- **失败名称过滤**：发布页面自动剔除游戏名称为"获取失败"或"未找到"的记录，确保报告干净
- **增量去重**：新链接通过 URL 自动入库去重，已爬取的不会重复请求
- **容错机制**：404/网络错误自动标记跳过，不影响后续游戏
- **双路径数据提取**：JSON-LD 提取游戏基础信息，Nuxt 状态提取关注量，互补覆盖
- **全量重抓**：每次全流程将所有游戏重置为待抓取，确保数据最新
- **输出集中管理**：所有生成文件统一存放在 `export/` 目录，不留根目录杂物
- **参数化运行**：`--full` 标志支持非交互模式，可直接接入定时任务或 CI/CD
