import os, re, json, yaml, requests, markdown
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# ==================== 环境配置 ====================
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

        # 3. 初始化 Jinja2 (用于文章页)
        self.env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    def extract_summary(self, body):
        """规格 2.2: 提取第一个 !vml- 中的 <span> 内容"""
        match = re.search(r'^!vml-.*?<span[^>]*>(.*?)</span>', body, re.MULTILINE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def process_body(self, body):
        """规格 6.1: 转换 !vml- 语法并渲染 Markdown"""
        # 将 !vml- 后面的内容直接作为 HTML 提取出来
        processed = re.sub(r'!vml-(.+?)(?=\n|$)', lambda m: m.group(1), body)
        # 渲染为 HTML
        return markdown.markdown(processed, extensions=['extra', 'fenced_code', 'tables'])

    def run(self):
        repo = os.getenv("REPO")
        token = os.getenv("GITHUB_TOKEN")
        if not repo or not token:
            print("错误: 请设置环境变量 REPO 和 GITHUB_TOKEN")
            return

        headers = {"Authorization": f"token {token}"}
        
        # 获取 Issue 列表
        api_url = f"https://api.github.com/repos/{repo}/issues?state=open"
        resp = requests.get(api_url, headers=headers)
        resp.raise_for_status()
        issues = [i for i in resp.json() if not i.get("pull_request")]

        all_articles = []
        specials = []
        new_cache = {}

        # 构造符合模板要求的 blog 字典 (合并 theme)
        blog_payload = self.config.get('blog', {}).copy()
        blog_payload['theme'] = self.config.get('theme', {})

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

            # --- 增量渲染文章页 ---
            if iid not in self.cache or self.cache[iid] != updated_at:
                print(f"正在更新文章: {iid}")
                tmpl = self.env.get_template("article.html")
                # 注入 article 和合并后的 blog
                rendered = tmpl.render(
                    article={**article_data, "content": html_content}, 
                    blog=blog_payload
                )
                # 写入文件
                with open(os.path.join(ARTICLE_DIR, f"{iid}.html"), "w", encoding="utf-8") as f:
                    f.write(rendered)
                # 备份 Markdown
                with open(os.path.join(OMD_DIR, f"{iid}.md"), "w", encoding="utf-8") as f:
                    f.write(body)

            all_articles.append(article_data)
            new_cache[iid] = updated_at
            
            if "special" in tags:
                specials.append(article_data)

        # 4. 写入增量缓存 JSON
        with open(OMD_JSON, 'w', encoding='utf-8') as f:
            json.dump(new_cache, f, indent=2, ensure_ascii=False)

        # 5. 写入 base.yaml (解决 Actions 找不到文件的错误)
        base_yaml_data = {
            "blog": blog_payload,
            "articles": all_articles,
            "specials": specials,
            "floating_menu": self.config.get('floating_menu', [])
        }
        with open(BASE_YAML_OUT, 'w', encoding='utf-8') as f:
            yaml.dump(base_yaml_data, f, allow_unicode=True, sort_keys=False)

        # 6. 生成首页 (字符串占位符注入)
        self.generate_index(all_articles, specials)
        print("构建完成！")

    def generate_index(self, articles, specials):
        home_tmpl_path = os.path.join(TEMPLATE_DIR, "home.html")
        if not os.path.exists(home_tmpl_path):
            print("警告: 未找到首页模板 home.html")
            return
            
        with open(home_tmpl_path, "r", encoding="utf-8") as f:
            html = f.read()

        # 对齐注入点格式
        replacements = {
            "${ARTICLES_JSON}$": json.dumps(articles, ensure_ascii=False),
            "${SPECIALS_JSON}$": json.dumps(specials, ensure_ascii=False),
            "${MENU_ITEMS_JSON}$": json.dumps(self.config.get('floating_menu', []), ensure_ascii=False),
            "${PRIMARY_COLOR}$": self.config.get('theme', {}).get('primary_color', '#e74c3c'),
            "${TOTAL_TIME}$": self.config.get('special', {}).get('view', {}).get('Total_time', '2023.01.01')
        }

        for placeholder, value in replacements.items():
            html = html.replace(placeholder, str(value))

        with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

if __name__ == "__main__":
    VaLogGenerator().run()