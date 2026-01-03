import os
import yaml
import requests
import markdown
from jinja2 import Template
from datetime import datetime

# ==================== 配置区 ====================
CONFIG_FILE = "config.yml"
HOME_TEMPLATE = "home.html"
ARTICLE_TEMPLATE = "article.html"
OUTPUT_DIR = "dist"

# ==================== 核心逻辑 ====================
class VaLogGenerator:
    def __init__(self):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 确保输出目录存在
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
        if not os.path.exists(f"{OUTPUT_DIR}/article"):
            os.makedirs(f"{OUTPUT_DIR}/article")

    def fetch_issues(self):
        """从 GitHub API 获取 Issues"""
        url = f"https://api.github.com/repos/{self.config['github']['repo']}/issues"
        params = {'state': 'open', 'creator': self.config['github']['repo'].split('/')[0]}
        # 如果需要私有库或提高配率，可在此处添加 Token 验证
        response = requests.get(url, params=params)
        return response.json()

    def parse_issue(self, issue):
        """解析单条 Issue 数据"""
        tags = [label['name'] for label in issue['labels']]
        content_html = markdown.markdown(issue['body'], extensions=['extra', 'codehilite', 'toc'])
        
        # 提取第一行作为简介（去除 Markdown 标记）
        raw_body = issue['body'].split('\n')[0][:100]
        
        return {
            "id": str(issue['number']),
            "title": issue['title'],
            "tags": tags,
            "date": issue['created_at'].split('T')[0],
            "content_raw": issue['body'],
            "content_html": content_html,
            "summary": [raw_body], # 适配 home.html 的数组格式
            "url": f"article/{issue['number']}.html"
        }

    def generate(self):
        issues = self.fetch_issues()
        articles = []
        specials = []
        
        # 特殊标签逻辑配置
        special_tag = self.config['logic']['special_tag']
        menu_tag_mapping = self.config['floating_menu']

        for issue in issues:
            if 'pull_request' in issue: continue
            
            data = self.parse_issue(issue)
            
            # 1. 判定是否为 Special (置顶/特殊展示)
            if special_tag in data['tags']:
                # 如果只有内容没有标题，触发模板的“仅文本模式”
                specials.append({
                    "id": data['id'],
                    "title": data['title'] if data['title'].lower() != "special" else "",
                    "tags": [t for t in data['tags'] if t != special_tag],
                    "content": data['summary'],
                    "url": data['url']
                })
            else:
                articles.append(data)

        # 2. 渲染文章详情页
        with open(ARTICLE_TEMPLATE, 'r', encoding='utf-8') as f:
            article_tpl = Template(f.read())

        for art in articles:
            rendered_art = article_tpl.render(
                article=art,
                config=self.config
            )
            with open(f"{OUTPUT_DIR}/{art['url']}", 'w', encoding='utf-8') as f:
                f.write(rendered_art)

        # 3. 处理动态菜单链接
        # 逻辑：遍历 config 中的菜单，如果其 display 名称对应一个标签，则自动链接到该标签下的最新文章
        final_menu = []
        for item in menu_tag_mapping:
            target_tag = item['display']
            # 寻找带有该标签的第一篇文章
            match = next((a for a in articles if target_tag in a['tags']), None)
            final_menu.append({
                "display": item['display'],
                "link": match['url'] if match else "#"
            })

        # 4. 渲染首页
        with open(HOME_TEMPLATE, 'r', encoding='utf-8') as f:
            # 预处理：将静态占位符替换为 Jinja2 变量
            home_html = f.read().replace('src="Url"', 'src="{{ config.me.avatar }}"')
            home_html = home_html.replace('VaLog', '{{ config.blog.title }}')
            home_html = home_html.replace('Introduction', '{{ config.blog.description }}')
            home_tpl = Template(home_html)

        final_home = home_tpl.render(
            articles=articles,
            specials=specials,
            menu_items=final_menu,
            config=self.config
        )
        
        with open(f"{OUTPUT_DIR}/index.html", 'w', encoding='utf-8') as f:
            f.write(final_home)

        print(f"✅ 生成成功！共 {len(articles)} 篇文章，{len(specials)} 个特殊卡片。")

if __name__ == "__main__":
    VaLogGenerator().generate()