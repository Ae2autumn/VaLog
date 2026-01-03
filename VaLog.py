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
        # 1. 自动获取仓库信息 (优先读取环境变量，本地运行则手动提示)
        self.repo = os.getenv('GITHUB_REPOSITORY')
        if not self.repo:
            # 这里的 fallback 仅用于你本地测试，Actions 运行时会自动填充
            self.repo = "YourName/YourRepo" 
        
        # 2. 加载用户配置
        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError(f"找不到配置文件: {CONFIG_FILE}")
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 3. 确保目录存在
        os.makedirs(os.path.join(OUTPUT_DIR, "article"), exist_ok=True)

    def fetch_issues(self):
        """从 GitHub 获取数据"""
        # 自动识别仓库，不再从 config.yml 读取
        url = f"https://api.github.com/repos/{self.repo}/issues"
        headers = {}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"
        
        params = {'state': 'open', 'sort': 'created'}
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 抓取失败: {e}")
            return []

    def parse_issue(self, issue):
        """解析文章"""
        tags = [label['name'] for label in issue['labels']]
        # 开启 toc 扩展以支持标题锚点
        content_html = markdown.markdown(issue['body'], extensions=['extra', 'codehilite', 'toc'])
        summary_text = issue['body'].split('\n')[0][:80]
        
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
        
        # 逻辑：判定 Special
        special_cfg = self.config.get('special', {})
        use_special_top = special_cfg.get('top', False)

        for issue in issues:
            if 'pull_request' in issue: continue
            data = self.parse_issue(issue)
            
            # 如果配置开启且含有 special 标签
            if use_special_top and "special" in data['tags']:
                specials.append({
                    "title": data['title'],
                    "content": data['summary'],
                    "url": data['url']
                })
            else:
                articles.append(data)

        # 默认备选 Special 信息
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

        # --- 菜单验证逻辑 (重点) ---
        final_menu = []
        for item in self.config.get('floating_menu', []):
            target_tag = item.get('tag')
            # 根据标签匹配最新文章链接
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

        print(f"🚀 生成成功！仓库: {self.repo} | 文章数: {len(articles)}")

if __name__ == "__main__":
    VaLogGenerator().generate()