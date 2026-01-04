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

        # 统一使用标准的 Jinja2 语法 {{ VAR }}
        self.env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    def extract_metadata_and_body(self, body):
        """提取摘要、垂直标题并移除元数据行"""
        lines = body.split('\n')
        summary = []
        vertical_title = ""
        content_lines = []
        
        # 处理前两行元数据
        if len(lines) > 0 and lines[0].startswith('!vml-'):
            # 提取第一行的摘要
            match = re.search(r'<span[^>]*>(.*?)</span>', lines[0])
            if match:
                summary = [match.group(1).strip()]
            else:
                summary = ["暂无简介"]
        else:
            summary = ["暂无简介"]
            
        if len(lines) > 1 and lines[1].startswith('!vml-'):
            # 提取第二行的垂直标题
            match = re.search(r'<span[^>]*>(.*?)</span>', lines[1])
            if match:
                vertical_title = match.group(1).strip()
        
        # 从第三行开始是正文（跳过前两行元数据行）
        content_lines = lines[2:] if len(lines) > 2 else []
        
        return {
            "summary": summary,
            "vertical_title": vertical_title,
            "body": "\n".join(content_lines)
        }

    def process_body(self, body):
        """处理正文，移除元数据行并转换为HTML"""
        # 移除所有以!vml-开头的行（元数据行）
        lines = body.split('\n')
        content_lines = [line for line in lines if not line.startswith('!vml-')]
        processed_body = "\n".join(content_lines)
        return markdown.markdown(processed_body, extensions=['extra', 'fenced_code', 'tables'])

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

        blog_cfg = self.config.get('blog', {})
        theme_cfg = self.config.get('theme', {})
        special_cfg = self.config.get('special', {})
        
        # 获取特殊标签配置（优先级: top > special > 用户自定义）
        special_tags_config = self.config.get('special_tags', [])
        special_tags = []
        
        # 如果top配置为true，则添加top标签
        if special_cfg.get('top', True):
            special_tags.append('top')
        
        # 添加special标签
        special_tags.append('special')
        
        # 添加用户自定义标签
        if special_tags_config:
            special_tags.extend(special_tags_config)
        
        for issue in issues:
            iid = str(issue['number'])
            updated_at = issue['updated_at']
            body = issue['body'] or ""
            tags = [l['name'] for l in issue['labels']]
            
            # 提取元数据和正文
            metadata = self.extract_metadata_and_body(body)
            
            # 垂直标题优先级：元数据中的垂直标题 > 文章标题 > "Blog"
            vertical_title = metadata["vertical_title"] or issue['title'] or "Blog"
            
            article_data = {
                "id": iid,
                "title": issue['title'],
                "date": issue['created_at'][:10],
                "tags": tags,
                "content": metadata["summary"],  # 主页摘要
                "url": f"article/{iid}.html",
                "verticalTitle": vertical_title
            }

            if iid not in self.cache or self.cache[iid] != updated_at:
                # 生成文章页 - 使用处理后的正文
                tmpl = self.env.get_template("article.html")
                rendered = tmpl.render(
                    article={**article_data, "content": self.process_body(metadata["body"])}, 
                    blog={**blog_cfg, "theme": theme_cfg}
                )
                with open(os.path.join(ARTICLE_DIR, f"{iid}.html"), "w", encoding="utf-8") as f:
                    f.write(rendered)
                with open(os.path.join(OMD_DIR, f"{iid}.md"), "w", encoding="utf-8") as f:
                    f.write(body)

            all_articles.append(article_data)
            new_cache[iid] = updated_at
            
            # 判断是否为特殊文章（检查标签是否包含特殊标签）
            is_special = False
            for tag in tags:
                if tag in special_tags:
                    is_special = True
                    break
            
            if is_special:
                specials.append(article_data)

        with open(OMD_JSON, 'w', encoding='utf-8') as f:
            json.dump(new_cache, f, indent=2, ensure_ascii=False)

        # 如果special数组为空，使用配置信息填充
        if not specials and special_cfg.get('view'):
            view = special_cfg.get('view', {})
            # 创建默认的特殊文章
            default_special = {
                "id": "0",
                "title": "",
                "date": "",
                "tags": [],
                "content": [
                    view.get('RF_Information', ''),
                    view.get('Copyright', ''),
                    f"运行天数: 计算中...",
                    view.get('Others', '')
                ],
                "url": "",
                "verticalTitle": "Special"
            }
            specials.append(default_special)

        # 生成 base.yaml 以供同步
        base_data = {
            "blog": {**blog_cfg, "theme": theme_cfg}, 
            "articles": all_articles, 
            "specials": specials, 
            "floating_menu": self.config.get('floating_menu', []),
            "special_config": special_cfg
        }
        with open(BASE_YAML_OUT, 'w', encoding='utf-8') as f:
            yaml.dump(base_data, f, allow_unicode=True, sort_keys=False)

        self.generate_index(all_articles, specials)

    def generate_index(self, articles, specials):
        home_tmpl_path = os.path.join(TEMPLATE_DIR, "home.html")
        if not os.path.exists(home_tmpl_path): 
            print(f"警告: 模板文件 {home_tmpl_path} 不存在")
            return
        
        tmpl = self.env.get_template("home.html")
        
        context = {
            "BLOG_NAME": self.config.get('blog', {}).get('name', 'VaLog'),
            "BLOG_DESCRIPTION": self.config.get('blog', {}).get('description', ''),
            "BLOG_AVATAR": self.config.get('blog', {}).get('avatar', ''),
            "BLOG_FAVICON": self.config.get('blog', {}).get('favicon', ''),
            "THEME_MODE": self.config.get('theme', {}).get('mode', 'dark'),
            "PRIMARY_COLOR": self.config.get('theme', {}).get('primary_color', '#e74c3c'),
            "TOTAL_TIME": self.config.get('special', {}).get('view', {}).get('Total_time', '2023.01.01'),
            # 这里需要注意：JavaScript 中需要 JSON 字符串，所以保留 json.dumps
            "ARTICLES_JSON": json.dumps(articles, ensure_ascii=False),
            "SPECIALS_JSON": json.dumps(specials, ensure_ascii=False),
            "MENU_ITEMS_JSON": json.dumps(self.config.get('floating_menu', []), ensure_ascii=False)
        }

        rendered = tmpl.render(**context)
        with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(rendered)
        
        print(f"已生成首页: {os.path.join(DOCS_DIR, 'index.html')}")
        print(f"文章总数: {len(articles)}, 特殊文章数: {len(specials)}")

if __name__ == "__main__":
    VaLogGenerator().run()