import os
import yaml
import requests
import markdown
from jinja2 import Template
from datetime import datetime

# ==================== 路径配置（适配你的结构） ====================
CONFIG_FILE = "config.yml"
TEMPLATE_DIR = "template"
HOME_TEMPLATE = os.path.join(TEMPLATE_DIR, "home.html")
ARTICLE_TEMPLATE = os.path.join(TEMPLATE_DIR, "article.html")
OUTPUT_DIR = "docs"  # 你配置的是 docs/ 用于 GitHub Pages

class VaLogGenerator:
    def __init__(self):
        # 1. 严格检查配置文件
        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError(f"❌ 找不到配置文件: {CONFIG_FILE}")
            
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
            
        if not self.config or 'github' not in self.config:
            print(f"DEBUG - 当前 config 内容: {self.config}")
            raise KeyError("❌ config.yml 格式不正确，缺少 'github' 节点。请检查缩进！")
        
        # 2. 确保输出目录存在
        os.makedirs(os.path.join(OUTPUT_DIR, "article"), exist_ok=True)

    def fetch_issues(self):
        repo = self.config['github']['repo']
        url = f"https://api.github.com/repos/{repo}/issues"
        # 增加 GitHub Token 防止 API 限制
        headers = {}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"
            
        params = {'state': 'open'}
        response = requests.get(url, params=params, headers=headers)
        if response.status_code != 200:
            raise Exception(f"❌ 无法获取 Issues: {response.text}")
        return response.json()

    def parse_issue(self, issue):
        tags = [label['name'] for label in issue['labels']]
        # 转换 Markdown
        content_html = markdown.markdown(issue['body'], extensions=['extra', 'codehilite', 'toc'])
        # 提取第一行作为简介
        summary_text = issue['body'].split('\n')[0][:100]
        
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
        
        special_tag = self.config.get('logic', {}).get('special_tag', 'special')

        for issue in issues:
            if 'pull_request' in issue: continue
            data = self.parse_issue(issue)
            
            if special_tag in data['tags']:
                specials.append({
                    "id": data['id'],
                    "title": "" if data['title'].lower() == "special" else data['title'],
                    "tags": [t for t in data['tags'] if t != special_tag],
                    "content": data['summary'],
                    "url": data['url']
                })
            else:
                articles.append(data)

        # 渲染文章页
        with open(ARTICLE_TEMPLATE, 'r', encoding='utf-8') as f:
            article_tpl = Template(f.read())

        for art in articles:
            rendered_art = article_tpl.render(article=art, config=self.config)
            with open(os.path.join(OUTPUT_DIR, art['url']), 'w', encoding='utf-8') as f:
                f.write(rendered_art)

        # 渲染首页
        with open(HOME_TEMPLATE, 'r', encoding='utf-8') as f:
            home_raw = f.read()
            # 这里的占位符替换逻辑需配合模板修改
            home_tpl = Template(home_raw)

        # 动态菜单逻辑
        final_menu = []
        for item in self.config.get('floating_menu', []):
            target = item['display']
            match = next((a for a in articles if target in a['tags']), None)
            final_menu.append({"display": target, "link": match['url'] if match else "#"})

        final_home = home_tpl.render(
            articles=articles,
            specials=specials,
            menu_items=final_menu,
            config=self.config
        )
        
        with open(os.path.join(OUTPUT_DIR, "index.html"), 'w', encoding='utf-8') as f:
            f.write(final_home)

        print(f"🚀 生成成功！输出至 {OUTPUT_DIR} 目录。")

if __name__ == "__main__":
    VaLogGenerator().generate()