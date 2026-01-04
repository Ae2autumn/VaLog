import os, re, json, yaml, requests, markdown
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# ==================== 环境路径配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yml")
TEMPLATE_DIR = os.path.join(BASE_DIR, "template")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
ARTICLE_DIR = os.path.join(DOCS_DIR, "article")
OMD_DIR = os.path.join(BASE_DIR, "O-MD")
OMD_JSON = os.path.join(OMD_DIR, "articles.json")
BASE_YAML_OUT = os.path.join(BASE_DIR, "base.yaml")

# 确保必要目录存在
os.makedirs(ARTICLE_DIR, exist_ok=True)
os.makedirs(OMD_DIR, exist_ok=True)

class VaLogGenerator:
    def __init__(self):
        # 1. 加载 config.yml
        if not os.path.exists(CONFIG_PATH):
            raise FileNotFoundError(f"未找到配置文件: {CONFIG_PATH}")
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}

        # 2. 加载增量缓存
        self.cache = {}
        if os.path.exists(OMD_JSON):
            try:
                with open(OMD_JSON, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except: self.cache = {}

        # 3. 初始化 Jinja2 环境
        # 标准环境用于文章页 (使用 {{ }})
        self.article_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        
        # 定制环境用于首页 (使用 ${ }$ 匹配你的 HTML)
        self.home_env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            variable_start_string='${',
            variable_end_string='}$'
        )

    def extract_summary(self, body):
        """提取第一个 !vml- 中的 <span> 内容，返回列表以对齐 JS renderArticles"""
        match = re.search(r'^!vml-.*?<span[^>]*>(.*?)</span>', body, re.MULTILINE | re.DOTALL)
        content = match.group(1).strip() if match else ""
        return [content] if content else ["No summary available."]

    def process_body(self, body):
        """渲染 Markdown 供文章页展示"""
        processed = re.sub(r'!vml-(.+?)(?=\n|$)', lambda m: m.group(1), body)
        return markdown.markdown(processed, extensions=['extra', 'fenced_code', 'tables'])

    def run(self):
        repo = os.getenv("REPO")
        token = os.getenv("GITHUB_TOKEN")
        if not repo or not token:
            print("Error: Environment variables REPO or GITHUB_TOKEN not found.")
            return

        headers = {"Authorization": f"token {token}"}
        resp = requests.get(f"https://api.github.com/repos/{repo}/issues?state=open", headers=headers)
        resp.raise_for_status()
        issues = [i for i in resp.json() if not i.get("pull_request")]

        all_articles = []
        specials = []
        new_cache = {}

        # 预备 Context
        blog_cfg = self.config.get('blog', {})
        theme_cfg = self.config.get('theme', {})
        special_cfg = self.config.get('special', {})
        # 合并对象供文章页模板使用 blog.theme.mode 访问
        article_blog_payload = {**blog_cfg, "theme": theme_cfg}

        for issue in issues:
            iid = str(issue['number'])
            updated_at = issue['updated_at']
            body = issue['body'] or ""
            tags = [l['name'] for l in issue['labels']]
            
            summary_list = self.extract_summary(body)
            html_content = self.process_body(body)
            
            article_data = {
                "id": iid,
                "title": issue['title'],
                "date": issue['created_at'][:10],
                "tags": tags,
                "content": summary_list, # 对齐 home.html 中的 article.content.map
                "url": f"article/{iid}.html",
                "verticalTitle": tags[0] if tags else "Blog"
            }

            # 增量渲染文章页
            if iid not in self.cache or self.cache[iid] != updated_at:
                print(f"Generating Article: {iid}")
                tmpl = self.article_env.get_template("article.html")
                rendered = tmpl.render(
                    article={**article_data, "content": html_content}, 
                    blog=article_blog_payload
                )
                with open(os.path.join(ARTICLE_DIR, f"{iid}.html"), "w", encoding="utf-8") as f:
                    f.write(rendered)
                with open(os.path.join(OMD_DIR, f"{iid}.md"), "w", encoding="utf-8") as f:
                    f.write(body)

            all_articles.append(article_data)
            new_cache[iid] = updated_at
            if "special" in tags:
                specials.append(article_data)

        # 写入缓存和 base.yaml
        with open(OMD_JSON, 'w', encoding='utf-8') as f:
            json.dump(new_cache, f, indent=2, ensure_ascii=False)

        base_data = {
            "blog": article_blog_payload,
            "articles": all_articles,
            "specials": specials,
            "floating_menu": self.config.get('floating_menu', [])
        }
        with open(BASE_YAML_OUT, 'w', encoding='utf-8') as f:
            yaml.dump(base_data, f, allow_unicode=True, sort_keys=False)

        # 生成首页
        self.generate_index(all_articles, specials)

    def generate_index(self, articles, specials):
        home_tmpl_path = os.path.join(TEMPLATE_DIR, "home.html")
        if not os.path.exists(home_tmpl_path): return

        tmpl = self.home_env.get_template("home.html")
        
        # 对齐 home.html 中的所有占位符
        context = {
            # 基础信息
            "BLOG_NAME": self.config.get('blog', {}).get('name', 'VaLog'),
            "BLOG_DESCRIPTION": self.config.get('blog', {}).get('description', ''),
            "BLOG_AVATAR": self.config.get('blog', {}).get('avatar', ''),
            "BLOG_FAVICON": self.config.get('blog', {}).get('favicon', ''),
            
            # 主题状态
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