import pandas as pd
import os
from datetime import datetime

def excel_to_html(input_file_path, output_file=None):
    """
    读取 Excel 或 CSV 并生成带有动态日期标题、居中对齐及排序功能的 HTML。
    适配 TapTap 爬虫结果数据，处理了"请求链接"列以及"未找到"等非数值文本的排序问题。
    """
    now = datetime.now()
    today_str = now.strftime("%Y年%m月%d日")

    if output_file:
        output_html_path = output_file
    else:
        time_prefix = now.strftime("%Y%m%d_%H%M%S")
        output_html_path = f"{time_prefix}_taptap_maker_result.html"

    # 动态页面标题
    page_title = f"TapTap Maker游戏数据抓取明细表（数据截至{today_str}）"

    print(f"正在读取文件: {input_file_path} ...")

    try:
        if input_file_path.endswith('.csv'):
            df = pd.read_csv(input_file_path)
        else:
            df = pd.read_excel(input_file_path)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return

    # 将"请求链接"重命名为"游戏链接"，方便后续处理和页面展示
    if '请求链接' in df.columns:
        df.rename(columns={'请求链接': '游戏链接'}, inplace=True)

    # 处理超链接
    if '游戏链接' in df.columns:
        df['游戏链接'] = df['游戏链接'].apply(
            lambda x: f'<a href="{x}" target="_blank">点击访问</a>' if pd.notnull(x) else ''
        )

    # 转换为 HTML 表格主体
    table_html = df.to_html(index=False, classes='styled-table', table_id='dataTable', escape=False)

    # HTML 模板
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{page_title}</title>
        <style>
            body {{
                font-family: 'Microsoft YaHei', sans-serif;
                background-color: #f0f2f5;
                margin: 0;
                padding: 40px 20px;
            }}
            h2 {{
                text-align: center;
                color: #1a1a1a;
                font-size: 24px;
                margin-bottom: 10px;
            }}
            .subtitle {{
                text-align: center;
                color: #666;
                margin-bottom: 30px;
                font-size: 0.9em;
            }}
            .table-container {{
                overflow-x: auto;
                background-color: #ffffff;
                border-radius: 12px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.05);
                padding: 25px;
                margin: 0 auto;
                max-width: 98%;
            }}
            .styled-table {{
                border-collapse: collapse;
                width: 100%;
                font-size: 14px;
            }}
            .styled-table thead tr {{
                background-color: #2f3542;
                color: #ffffff;
            }}
            .styled-table th,
            .styled-table td {{
                padding: 14px 10px;
                text-align: center;
                border-bottom: 1px solid #ececec;
            }}
            .styled-table th {{
                cursor: pointer;
                user-select: none;
                transition: background 0.2s;
                white-space: nowrap;
            }}
            .styled-table th:hover {{
                background-color: #57606f;
            }}
            .styled-table tbody tr:nth-of-type(even) {{
                background-color: #f8f9fa;
            }}
            .styled-table tbody tr:hover {{
                background-color: #e9ecef;
            }}
            a {{
                color: #00a8ff;
                text-decoration: none;
                font-weight: 500;
            }}
        </style>
    </head>
    <body>
        <h2>{page_title}</h2>
        <div class="subtitle">💡 点击下方表头可按该项进行升降序排列</div>

        <div class="table-container">
            {table_html}
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const table = document.getElementById('dataTable');
                const headers = table.querySelectorAll('th');
                const tbody = table.querySelector('tbody');
                let sortAsc = new Array(headers.length).fill(true);

                headers.forEach((header, index) => {{
                    header.addEventListener('click', () => {{
                        const rows = Array.from(tbody.querySelectorAll('tr'));
                        const isAscending = sortAsc[index];

                        rows.sort((rowA, rowB) => {{
                            let cellA = rowA.children[index].innerText.trim();
                            let cellB = rowB.children[index].innerText.trim();

                            // 兼容"未找到"等非数字文本，将其视为最小值(-1)处理，防止破坏排序
                            let parseValue = (val) => {{
                                if (val === '未找到' || val === '') return -1;
                                return parseFloat(val.replace(/,/g, ''));
                            }};

                            let numA = parseValue(cellA);
                            let numB = parseValue(cellB);

                            if (!isNaN(numA) && !isNaN(numB)) {{
                                return isAscending ? numA - numB : numB - numA;
                            }} else {{
                                return isAscending
                                    ? cellA.localeCompare(cellB, 'zh-CN')
                                    : cellB.localeCompare(cellA, 'zh-CN');
                            }}
                        }});

                        sortAsc[index] = !isAscending;
                        headers.forEach(th => th.innerHTML = th.innerHTML.replace(' ▲', '').replace(' ▼', ''));
                        header.innerHTML += isAscending ? ' ▲' : ' ▼';
                        tbody.append(...rows);
                    }});
                }});
            }});
        </script>
    </body>
    </html>
    """

    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_template)

    print(f"---")
    print(f"✅ 成功！网页已生成。")
    print(f"文件名称: {output_html_path}")
    print(f"文件位置: {os.path.abspath(output_html_path)}")

if __name__ == "__main__":
    excel_to_html("taptap_game_detail.xlsx", "taptap_maker_result.html")
