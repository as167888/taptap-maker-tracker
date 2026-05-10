# TapTap Maker Tracker

TapTap "制造"标签游戏数据追踪系统 —— 自动化爬取、存储、展示 TapTap 平台上所有使用"TapTap制造"标签的游戏信息。

## 项目概述

本项目实现对 [TapTap 制造标签页](https://www.taptap.cn/tag/TapTap%E5%88%B6%E9%80%A0) 下所有游戏的自动化数据采集，涵盖：

- **游戏发现**：遍历 50 页标签列表，提取所有游戏的名称和详情页链接
- **详情采集**：逐款抓取每款游戏的发布日期、下载量、关注量、评分、评价数量
- **数据持久化**：SQLite 数据库存储，支持增量更新和爬取状态追踪
- **可视化展示**：自动生成可排序、可筛选的 HTML 数据报告

## 项目结构

```
maker/
├── main.py                    # 主入口：全流程调度 + 交互式菜单
├── init_db.py                 # 数据库初始化、CRUD 操作、状态管理
├── db_query.py                # 交互式数据库查询浏览工具
├── import_links.py            # 链接导入工具（支持 txt/csv/xlsx）
├── taptap_games.db            # SQLite 数据库（运行时生成）
├── 1.爬取带TapTap制造tag的游戏/
│   └── taptap_spider.py       # 阶段1：列表页爬虫
├── 2.爬取TapTap制造的游戏详细信息/
│   └── taptap_mk_detail.py    # 阶段2：详情页爬虫
├── 3.生成网站发布页面/
│   └── generate_html.py       # 阶段3：HTML 报告生成
└── export/                    # 带时间戳的导出备份
```

## 数据流程

```
[TapTap 制造标签页]
        │
        ▼
  taptap_spider.py          ← 爬取 50 页列表，提取名称 + 链接
        │
        ▼
  taptap_game_list.xlsx     ← 中间产物：游戏列表
        │
        ▼
  sync_from_xlsx()          ← 新增链接写入 SQLite（URL 去重）
        │
        ▼
  taptap_mk_detail.py       ← 逐款爬取详情（JSON-LD + Nuxt 数据）
        │
        ▼
  taptap_game_detail.xlsx   ← 中间产物：完整数据
        │
        ▼
  generate_html.py          ← 生成可排序 HTML 报告
        │
        ▼
  taptap_maker_result.html  ← 最终产出
```

## 数据库设计

**games 表**（SQLite）：

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

**状态流转**：
```
0 (待抓取) ──成功──▶ 1 (已抓取)
     │
     └──失败/404──▶ -1 (已跳过)
```

## 核心模块

### main.py
全流程调度器，提供交互式菜单：
- `1` 启动全流程（链接爬取 → 数据库同步 → 详情爬取 → HTML 生成）
- `2` 浏览数据库详细数据（分页、筛选、排序）
- `3` 手动导入外部链接文件

### init_db.py
数据库核心模块，提供：
- `init_db()` — 建表 + 兼容性迁移（自动补列）
- `get_pending_games()` — 获取待抓取队列
- `update_game_detail()` — 写入抓取结果
- `mark_game_skipped()` — 标记失败记录（404 / 解析错误）
- `reset_all_pending()` — 重置全量待抓取状态
- `sync_from_xlsx()` — 从爬虫 xlsx 同步新链接

### taptap_spider.py（阶段1）
- 遍历 TapTap 制造标签页 1-50 页
- 解析 `div.app-title` 提取游戏名称（`meta[itemprop=name]`）和链接
- 输出去重后的 Excel 游戏列表
- 礼貌爬取：每次请求间隔 1.5 秒

### taptap_mk_detail.py（阶段2）
- 从数据库读取待抓取队列（`detail_fetched = 0`）
- 使用 `?os=android` 参数请求移动端页面
- 双路径数据提取：
  - **JSON-LD**（`VideoGame` schema）：名称、发布日期、下载量、评分、评价数
  - **Nuxt State**（`#__NUXT_DATA__`）：关注量
- 异常处理：404 → 标记跳过；网络错误 → 标记跳过
- 随机延迟 1-3 秒

### generate_html.py（阶段3）
- 读取 Excel 数据生成美观的 HTML 报告
- 表头点击排序（数字/文本混合排序，正确处理"未找到"等非数值）
- 响应式设计，支持移动端查看
- 自动生成带日期的动态标题

### db_query.py
交互式终端数据库浏览器，支持：
- 按状态筛选（全部/已抓/待抓/跳过）
- 多字段排序（ID/名称/下载量/关注/评分/发布日期）
- 分页浏览（每页 20 条）

## 快速开始

### 环境要求

- Python 3.8+
- 依赖库：`requests`, `beautifulsoup4`, `pandas`, `openpyxl`

```bash
pip install requests beautifulsoup4 pandas openpyxl
```

### 使用方式

**全流程一键启动**：
```bash
python main.py
# 选择 1 → 自动完成：爬链接 → 爬详情 → 生成 HTML
```

**仅爬取游戏链接**：
```bash
cd "1.爬取带TapTap制造tag的游戏"
python taptap_spider.py
```

**仅爬取游戏详情**（基于数据库已有链接）：
```bash
cd "2.爬取TapTap制造的游戏详细信息"
python taptap_mk_detail.py
```

**浏览数据库**：
```bash
python db_query.py
```

**手动导入链接**：
```bash
python import_links.py 链接文件.xlsx
```

## 数据示例

最终生成的 HTML 报告包含以下维度：

| 游戏名称 | 游戏链接 | 发布日期 | 下载量 | 关注量 | 评分 | 评价数量 |
|---------|---------|---------|-------|-------|------|---------|
| 示例游戏 | 点击访问 | 2024-01-15 | 10000 | 500 | 8.5 | 1200 |

## 设计要点

- **增量更新**：新链接自动入库去重，已爬取的不会重复请求
- **容错机制**：404 下线游戏标记跳过不再重试，网络异常自动跳过继续
- **全量重新抓取**：每次运行全流程会重置所有游戏为待抓取状态，确保数据是最新的
- **数据完整性**：非数值字段（如"未找到"）在排序时自动处理，不会导致排序错乱
