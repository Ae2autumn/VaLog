import os
import re
import json
import yaml
import requests
import markdown
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from typing import Dict, List, Optional, Any

# ==================== 目录路径（严格对齐目录树） ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yml")
TEMPLATE_DIR = os.path.join(BASE_DIR, "template")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
ARTICLE_DIR = os.path.join(DOCS_DIR, "article")
O_MD_DIR = os.path.join(BASE_DIR, "O-MD")
STATIC_DIR = os.path.join(BASE_DIR, "static")
BASE_YAML_PATH = os.path.join(BASE_DIR, "base.yaml")

# 确保目录存在
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(ARTICLE_DIR, exist_ok=True)
os.makedirs(O_MD_DIR, exist_ok=True)


# ==================== 工具函数 ====================
def read_config(path: str) -> Dict[str, Any]:
    """读取config.yml配置文件"""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def validate_config(config: Dict[str, Any]) -> List[str]:
    """验证配置文件（按用户提供的config.yml字段对齐）"""
    errors = []
    # 1. 浮动菜单数量（≤10）
    floating_menu = config.get('floating_menu', [])
    if len(floating_menu) > 10:
        errors.append("浮动菜单不能超过10个")
    # 2. 主题模式（dark/light）
    theme_mode = config.get('theme', {}).get('mode', 'dark')
    if theme_mode not in ['dark', 'light']:
        errors.append("theme.mode 必须是 'dark' 或 'light'")
    # 3. 颜色格式（#xxxxxx）
    color_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')
    primary_color = config.get('theme', {}).get('primary_color', '#e74c3c')
    if not color_pattern.match(primary_color):
        errors.append(f"primary_color 格式错误: {primary_color}")
    # 4. Total_time格式（yyyy.mm.dd）
    total_time = config.get('special', {}).get('view', {}).get('Total_time', '')
    time_pattern = re.compile(r'^\d{4}\.\d{2}\.\d{2}$')
    if total_time and not time_pattern.match(total_time):
        errors.append(f"special.view.Total_time 格式错误（需yyyy.mm.dd）: {total_time}")
    return errors

def fetch_issues_from_github(repo: str, token: str) -> List[Dict[str, Any]]:
    """从GitHub API获取Issues（含标签、创建时间）"""
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    issues = []
    page = 1
    per_page = 100
    while True:
        url = f"https://api.github.com/repos/{repo}/issues?state=all&page={page}&per_page={per_page}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        page_issues = response.json()
        if not page_issues:
            break
        # 过滤无标签的Issues（可选，按需求）
        issues.extend([
            {
                "number": issue["number"],
                "title": issue["title"],
                "body": issue["body"] or "",
                "created_at": issue["created_at"],
                "labels": [{"name": label["name"]} for label in issue["labels"]]
            }
            for issue in page_issues if not issue.get("pull_request")  # 排除PR
        ])
        page += 1
    return issues

def extract_summary(content: str) -> str:
    """提取摘要：第一个!vml-行中第一个<span>内容（规格2.2）"""
    vml_match = re.search(r'^!vml-.+$', content, re.MULTILINE)
    if not vml_match:
        return ""
    vml_line = vml_match.group(0)
    span_match = re.search(r'<span[^>]*>(.*?)</span>', vml_line)
    return span_match.group(1).strip() if span_match else ""

def extract_vertical_title(content: str) -> str:
    """提取垂直标题：所有!vml-行中第二个<span>内容，无则用文章标题（补充规则）"""
    vml_lines = re.findall(r'^!vml-.+$', content, re.MULTILINE)
    all_spans = []
    for line in vml_lines:
        spans = re.findall(r'<span[^>]*>(.*?)</span>', line)
        all_spans.extend(spans)
    return all_spans[1].strip() if len(all_spans) >= 2 else ""  # 取第二个span

def process_html_inline(content: str) -> str:
    """处理!vml-开头的HTML内联语法（规格6.1）"""
    return re.sub(r'!vml-(.+?)(?=\n|$)', lambda m: m.group(1), content)

def markdown_to_html(md_content: str) -> str:
    """Markdown转HTML（简化版，保留段落结构）"""
    return markdown.markdown(md_content, extensions=['extra'])

def process_articles(issues: List[Dict], config: Dict) -> Dict[str, Any]:
    """处理文章数据（含摘要、垂直标题、内容）"""
    articles = []
    specials = []
    menu_items = []

    # 1. 处理文章（含Special文章：带special标签）
    for issue in issues:
        body = issue["body"]
        tags = [label["name"] for label in issue["labels"]]
        vertical_title = extract_vertical_title(body) or issue["title"]  # 补充规则
        
        # 提取摘要（第一个!vml-的第一个<span>）
        summary = extract_summary(body)
        # 处理内容（去除!vml-行，转HTML）
        processed_body = process_html_inline(body)
        content_lines = processed_body.split("\n")
        cleaned_body = "\n".join([line for line in content_lines if not line.startswith("!vml-")])
        html_content = markdown_to_html(cleaned_body)
        
        # 组装文章数据（规格3.3）
        article = {
            "id": f"article-{issue['number']}",
            "title": issue["title"],
            "tags": tags,
            "verticalTitle": vertical_title,
            "date": issue["created_at"][:10],  # YYYY-MM-DD
            "content": [p.strip() for p in html_content.split("\n\n") if p.strip()],  # 段落数组
            "url": f"/article/{issue['number']}.html",
            "gradient": ["#e74c3c", "#c0392b"]  # 默认渐变
        }
        articles.append(article)
        
        # Special文章（带special标签）
        if "special" in tags:
            specials.append({
                "id": f"special-{issue['number']}",
                "title": issue["title"],
                "tags": tags,
                "content": article["content"],  # 复用处理后的内容
                "url": article["url"],
                "gradient": article["gradient"]
            })

    # 2. 处理浮动菜单（规格3.2）
    for item in config.get("floating_menu", []):
        # 查找带对应标签的文章（取第一篇）
        matched_article = next((a for a in articles if item["tag"] in a["tags"]), None)
        menu_items.append({
            "tag": item["tag"],
            "display": item["display"],
            "url": matched_article["url"] if matched_article else None
        })

    return {"articles": articles, "specials": specials, "menu_items": menu_items}


# ==================== 生成文件 ====================
def generate_base_yaml(config: Dict, data: Dict) -> None:
    """生成base.yaml（规格3.3结构）"""
    base_data = {
        "blog": {
            "avatar": config["blog"]["avatar"],
            "name": config["blog"]["name"],
            "description": config["blog"]["description"],
            "favicon": config["blog"]["favicon"]
        },
        "articles": data["articles"],
        "specials": data["specials"],
        "menu_items": data["menu_items"]
    }
    with open(BASE_YAML_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(base_data, f, allow_unicode=True, sort_keys=False)

def generate_home_page(template_path: str, output_path: str, data: Dict, config: Dict) -> None:
    """生成主页（占位符替换，规格5.2.1）"""
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 替换占位符（规格5.3）
    replacements = {
        "${BLOG_NAME}$": config["blog"]["name"],
        "${BLOG_FAVICON}$": config["blog"]["favicon"],
        "${BLOG_AVATAR}$": config["blog"]["avatar"],
        "${BLOG_DESCRIPTION}$": config["blog"]["description"],
        "${THEME_MODE}$": config["theme"]["mode"],
        "${ARTICLES_JSON}$": json.dumps(data["articles"], ensure_ascii=False),
        "${SPECIALS_JSON}$": json.dumps(data["specials"], ensure_ascii=False),
        "${MENU_ITEMS_JSON}$": json.dumps(data["menu_items"], ensure_ascii=False),
        "${PRIMARY_COLOR}$": config["theme"]["primary_color"],
        "${TOTAL_TIME}$": config["special"]["view"]["Total_time"]
    }
    for k, v in replacements.items():
        template = template.replace(k, v)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(template)

def generate_article_page(article: Dict, template_path: str, output_path: str, config: Dict) -> None:
    """生成文章页（Jinja2渲染，规格5.2.2）"""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("article.html")
    # 注入博客配置（供模板使用）
    blog_config = {
        "name": config["blog"]["name"],
        "favicon": config["blog"]["favicon"],
        "theme": config["theme"]
    }
    html = template.render(article=article, blog=blog_config)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)


# ==================== 主流程 ====================
def main():
    # 1. 读取配置并验证
    config = read_config(CONFIG_PATH)
    errors = validate_config(config)
    if errors:
        raise ValueError("配置错误:\n" + "\n".join(errors))
    
    # 2. 获取GitHub Issues（需secrets.GITHUB_TOKEN）
    repo = os.getenv("REPO")
    token = os.getenv("GITHUB_TOKEN")
    if not repo or not token:
        raise EnvironmentError("缺少环境变量REPO或GITHUB_TOKEN")
    issues = fetch_issues_from_github(repo, token)
    
    # 3. 处理文章数据
    data = process_articles(issues, config)
    
    # 4. 生成base.yaml
    generate_base_yaml(config, data)
    
    # 5. 生成主页（占位符替换）
    home_template = os.path.join(TEMPLATE_DIR, "home.html")
    generate_home_page(home_template, os.path.join(DOCS_DIR, "index.html"), data, config)
    
    # 6. 生成文章页（Jinja2）
    for article in data["articles"]:
        output_path = os.path.join(ARTICLE_DIR, f"{article['id'].split('-')[1]}.html")
        generate_article_page(article, os.path.join(TEMPLATE_DIR, "article.html"), output_path, config)
    
    print("✅ 生成完成！")

if __name__ == "__main__":
    main()
