import os, re, json, yaml, requests, markdown
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# ==================== 配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yml")
TEMPLATE_DIR = os.path.join(BASE_DIR, "template")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
ARTICLE_DIR = os.path.join(DOCS_DIR, "article")
OMD_DIR = os.path.join(BASE_DIR, "O-MD")
OMD_JSON = os.path.join(OMD_DIR, "articles.json")

os.makedirs(ARTICLE_DIR, exist_ok=True)
os.makedirs(OMD_DIR, exist_ok=True)

class VaLogGenerator:
    def __init__(self):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}
        self.cache = {}
        if os.path.exists(OMD_JSON):
            with open(OMD_JSON, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
        self.env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    def extract_summary(self, body):
        """规格 2.2: 提取第一个 !vml- 中的 <span> 内容"""
        match = re.search(r'^!vml-.*?<span[^>]*>(.*?)</span>', body, re.MULTILINE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def process_body(self, body):
        """规格 6.1: 处理 !vml- 语法并移除摘要行，转 HTML"""
        # 提取摘要行内容（不含!vml-前缀）用于后续处理
        # 先将所有 !vml- 语法行转换为其内部的 HTML
        processed = re.sub(r'!vml-(.+?)(?=\n|$)', lambda m: m.group(1), body)
        # 移除掉那些原本是 !vml- 的行，避免它们出现在正文渲染中（如果那是摘要的话）
        lines = processed.split('\n')
        clean_lines = [l for l in lines if not l.strip().startswith('<span')] # 假设摘要都在span里
        html = markdown.markdown('\n'.join(lines), extensions=['extra', 'fenced_code', 'tables'])
        return html

    def run(self):
        repo = os.getenv("REPO")
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Authorization": f"token {token}"}
        resp = requests.get(f"https://api.github.com/repos/{repo}/issues?state=open", headers=headers)
        resp.raise_for_status()
        issues = [i for i in resp.json() if not i.get("pull_request")]

        all_articles = []
        specials = []
        new_cache = {}

        for issue in issues:
            iid = str(issue['number'])
            updated_at = issue['updated_at']
            body = issue['body'] or ""
            tags = [l['name'] for l in issue['labels']]
            
            summary = self.extract_summary(body)
            html_content = self.process_body(body)
            
            article_data = {
                "id": iid,
                "title": issue['title'],
                "date": issue['created_at'][:10],
                "tags": tags,
                "summary": summary,
                "url": f"article/{iid}.html",
                "verticalTitle": tags[0] if tags else "Blog"
            }

            # 增量生成文章页 (Jinja2)
            if iid not in self.cache or self.cache[iid] != updated_at:
                tmpl = self.env.get_template("article.html")
                rendered = tmpl.render(article={**article_data, "content": html_content}, blog=self.config['blog'])
                with open(os.path.join(ARTICLE_DIR, f"{iid}.html"), "w", encoding="utf-8") as f:
                    f.write(rendered)
                with open(os.path.join(OMD_DIR, f"{iid}.md"), "w", encoding="utf-8") as f:
                    f.write(body)

            all_articles.append(article_data)
            new_cache[iid] = updated_at
            
            # Special 逻辑
            if "special" in tags:
                specials.append(article_data)

        # 写入缓存和 base.yaml
        with open(OMD_JSON, 'w', encoding='utf-8') as f: json.dump(new_cache, f)
        base_yaml_data = {"blog": self.config['blog'], "articles": all_articles, "specials": specials}
        with open(os.path.join(BASE_DIR, "base.yaml"), 'w', encoding='utf-8') as f:
            yaml.dump(base_yaml_data, f, allow_unicode=True)

        # 生成首页 (精准占位符替换)
        self.generate_index(all_articles, specials)

    def generate_index(self, articles, specials):
        with open(os.path.join(TEMPLATE_DIR, "home.html"), "r", encoding="utf-8") as f:
            html = f.read()

        # 严格匹配你的注入点格式
        replacements = {
            "${ARTICLES_JSON}$": json.dumps(articles, ensure_ascii=False),
            "${SPECIALS_JSON}$": json.dumps(specials, ensure_ascii=False),
            "${MENU_ITEMS_JSON}$": json.dumps(self.config.get('floating_menu', []), ensure_ascii=False),
            "${PRIMARY_COLOR}$": self.config.get('theme', {}).get('primary_color', '#e74c3c'),
            "${TOTAL_TIME}$": self.config.get('special', {}).get('view', {}).get('Total_time', '2023.01.01'),
            # 基础信息替换
            "${BLOG_NAME}$": self.config['blog']['name'],
            "${BLOG_DESCRIPTION}$": self.config['blog']['description']
        }

        for placeholder, value in replacements.items():
            html = html.replace(placeholder, str(value))

        with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

if __name__ == "__main__":
    VaLogGenerator().run()