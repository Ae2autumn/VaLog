import os
import yaml
import requests
import markdown
from jinja2 import Template
from datetime import datetime

# ==================== 路径配置 ====================
CONFIG_FILE = "config.yml"
TEMPLATE_DIR = "template"
HOME_TEMPLATE = os.path.join(TEMPLATE_DIR, "home.html")
ARTICLE_TEMPLATE = os.path.join(TEMPLATE_DIR, "article.html")
OUTPUT_DIR = "docs"

class VaLogGenerator:
    def __init__(self):
        # 1. 加载配置
        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError(f"找不到配置文件: {CONFIG_FILE}")
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 校验关键配置（防止 KeyError）
        if 'github' not in self.config:
            # 如果 config 里没写，可以尝试从环境变量读取，或手动在此补全
            self.config['github'] = {'repo': os.getenv('GITHUB_REPOSITORY', '你的用户名/仓库名')}
        
        # 2. 确保目录存在
        os.makedirs(os.path.join(OUTPUT_DIR, "article"), exist_ok=True)

    def fetch_issues(self):
        """从 GitHub 获取 Issue 数据"""
        repo = self.config['github']['repo']
        url = f"https://api.github.com/repos/{repo}/issues"
        headers = {}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"
        
        params = {'state': 'open', 'sort': 'created'}
        response = requests.get(url, params=params, headers=headers)
        if response.status_code != 200:
            print(f"警告: 无法获取数据 ({response.status_code})")
            return []
        return response.json()

    def parse_issue(self, issue):
        """解析 Issue 为文章对象"""
        tags = [label['name'] for label in issue['labels']]
        # 启用 toc 扩展以自动生成标题 ID（侧边菜单需要）
        content_html = markdown.markdown(issue['body'], extensions=['extra', 'codehilite', 'toc'])
        summary_text = issue['body'].split('\n')[0][:80] # 截取首行作为摘要
        
        return {
            "id": str(issue['number']),
            "title": issue['title'],
            "tags": tags,
            "date": issue['created_at'].split('T')[0],
            "content_html": content_html,
            "summary": [summary_text],
            "url": f"article/{issue['number']}.html"
        }

    def generate(self):
        issues = self.fetch_issues()
        articles = []
        specials = []
        
        # 逻辑配置
        special_cfg = self.config.get('special', {})
        use_special_top = special_cfg.get('top', False)

        for issue in issues:
            if 'pull_request' in issue: continue
            data = self.parse_issue(issue)
            
            # 验证是否为 Special 文章
            if use_special_top and "special" in data['tags']:
                specials.append({
                    "title": data['title'] if data['title'].lower() != "special" else "",
                    "content": data['summary'],
                    "url": data['url']
                })
            else:
                articles.append(data)

        # 如果没有 Special 文章，使用 config 里的 view 填充
        if not specials:
            v = special_cfg.get('view', {})
            specials.append({
                "title": "Information",
                "content": [v.get('RF_Information', ''), v.get('Copyright', ''), f"Since {v.get('Total_time','')}"],
                "url": v.get('RF_Link', '#')
            })

        # --- 渲染详情页 ---
        with open(ARTICLE_TEMPLATE, 'r', encoding='utf-8') as f:
            article_tpl = Template(f.read())
        
        for art in articles:
            rendered = article_tpl.render(article=art, config=self.config)
            with open(os.path.join(OUTPUT_DIR, art['url']), 'w', encoding='utf-8') as f:
                f.write(rendered)

        # --- 菜单验证逻辑 ---
        final_menu = []
        for item in self.config.get('floating_menu', []):
            target_tag = item.get('tag')
            # 查找带有该 tag 的文章路径
            match = next((a for a in articles if target_tag in a['tags']), None)
            final_menu.append({
                "display": item.get('display'),
                "link": f"{match['url']}" if match else "#"
            })

        # --- 渲染首页 ---
        with open(HOME_TEMPLATE, 'r', encoding='utf-8') as f:
            home_tpl = Template(f.read())
        
        final_home = home_tpl.render(
            articles=articles,
            specials=specials,
            menu_items=final_menu,
            config=self.config
        )
        
        with open(os.path.join(OUTPUT_DIR, "index.html"), 'w', encoding='utf-8') as f:
            f.write(final_home)

        print(f"✅ 执行完毕！已生成 {len(articles)} 篇文章，请查看 docs/ 目录。")

if __name__ == "__main__":
    VaLogGenerator().generate()