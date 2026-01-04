import os, re, json, yaml, requests, markdown
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# ==================== 路径配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yml")
TEMPLATE_DIR = os.path.join(BASE_DIR, "template")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
ARTICLE_DIR = os.path.join(DOCS_DIR, "article")
OMD_DIR = os.path.join(BASE_DIR, "O-MD")
OMD_JSON = os.path.join(OMD_DIR, "articles.json")
BASE_YAML_OUT = os.path.join(BASE_DIR, "base.yaml")

os.makedirs(ARTICLE_DIR, exist_ok=True)
os.makedirs(OMD_DIR, exist_ok=True)

class VaLogGenerator:
    def __init__(self):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}
        
        self.cache = {}
        if os.path.exists(OMD_JSON):
            try:
                with open(OMD_JSON, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except: self.cache = {}

        # 首页专用环境：对齐你的 ${VAR}$ 语法
        self.home_env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            variable_start_string='${',
            variable_end_string='}$',
            autoescape=False
        )
        # 文章页专用环境：保持默认 {{ var }}
        self.article_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    def extract_summary(self, body):
        match = re.search(r'^!vml-.*?<span[^>]*>(.*?)</span>', body, re.MULTILINE | re.DOTALL)
        content = match.group(1).strip() if match else ""
        return [content] if content else ["暂无简介"]

    def process_body(self, body):
        processed = re.sub(r'!vml-(.+?)(?=\n|$)', lambda m: m.group(1), body)
        return markdown.markdown(processed, extensions=['extra', 'fenced_code', 'tables'])

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

        # 准备数据层级
        blog_cfg = self.config.get('blog', {})
        theme_cfg = self.config.get('theme', {})
        special_cfg = self.config.get('special', {})
        
        for issue in issues:
            iid = str(issue['number'])
            updated_at = issue['updated_at']
            body = issue['body'] or ""
            tags = [l['name'] for l in issue['labels']]
            
            article_data = {
                "id": iid,
                "title": issue['title'],
                "date": issue['created_at'][:10],
                "tags": tags,
                "content": self.extract_summary(body),
                "url": f"article/{iid}.html",
                "verticalTitle": tags[0] if tags else "Blog"
            }

            if iid not in self.cache or self.cache[iid] != updated_at:
                tmpl = self.article_env.get_template("article.html")
                # 传入合并后的 blog 字典，以适配 article.html 中的 blog.theme.mode
                rendered = tmpl.render(
                    article={**article_data, "content": self.process_body(body)}, 
                    blog={**blog_cfg, "theme": theme_cfg}
                )
                with open(os.path.join(ARTICLE_DIR, f"{iid}.html"), "w", encoding="utf-8") as f:
                    f.write(rendered)
                with open(os.path.join(OMD_DIR, f"{iid}.md"), "w", encoding="utf-8") as f:
                    f.write(body)

            all_articles.append(article_data)
            new_cache[iid] = updated_at
            if "special" in tags:
                specials.append(article_data)

        # 写回缓存
        with open(OMD_JSON, 'w', encoding='utf-8') as f:
            json.dump(new_cache, f, indent=2, ensure_ascii=False)

        # 生成首页
        self.generate_index(all_articles, specials)

    def generate_index(self, articles, specials):
        home_tmpl_path = os.path.join(TEMPLATE_DIR, "home.html")
        if not os.path.exists(home_tmpl_path): return
        
        tmpl = self.home_env.get_template("home.html")
        
        # --- 变量对齐区：严格按照你的 home.html 占位符命名 ---
        context = {
            # 基本信息
            "BLOG_NAME": self.config.get('blog', {}).get('name', 'VaLog'),
            "BLOG_DESCRIPTION": self.config.get('blog', {}).get('description', ''),
            "BLOG_AVATAR": self.config.get('blog', {}).get('avatar', ''),
            "BLOG_FAVICON": self.config.get('blog', {}).get('favicon', ''),
            
            # 主题与运行时间
            "THEME_MODE": self.config.get('theme', {}).get('mode', 'dark'),
            "PRIMARY_COLOR": self.config.get('theme', {}).get('primary_color', '#e74c3c'),
            "TOTAL_TIME": self.config.get('special', {}).get('view', {}).get('Total_time', '2023.01.01'),
            
            # JSON 数据流
            "ARTICLES_JSON": json.dumps(articles, ensure_ascii=False),
            "SPECIALS_JSON": json.dumps(specials, ensure_ascii=False),
            "MENU_ITEMS_JSON": json.dumps(self.config.get('floating_menu', []), ensure_ascii=False)
        }

        rendered = tmpl.render(**context)
        with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(rendered)

if __name__ == "__main__":
    VaLogGenerator().run()