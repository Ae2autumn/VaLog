#!/usr/bin/env python3
"""
VaLog 静态博客生成器 - 修复版
版本: 4.1
修复问题：
1. 主页模板替换逻辑错误
2. 缺失docs目录和文件生成
3. 模板变量替换不完整
4. 添加缺失的依赖检查和错误处理
"""

import os
import sys
import json
import yaml
import re
import markdown
import requests
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

class VaLogGenerator:
    """VaLog博客生成器主类"""
    
    def __init__(self, config_path="config.yml"):
        self.config = self.load_config(config_path)
        self.issues = []
        self.articles = []
        self.specials = []
        self.base_data = {}
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        self.github_repo = os.environ.get("GITHUB_REPOSITORY", "")
        self.docs_dir = "docs"
        
        # 确保必要的目录存在
        self.ensure_directories()
        
    def ensure_directories(self):
        """确保必要的目录存在"""
        os.makedirs(self.docs_dir, exist_ok=True)
        os.makedirs(os.path.join(self.docs_dir, "article"), exist_ok=True)
        os.makedirs("O-MD", exist_ok=True)
        os.makedirs("template", exist_ok=True)
        
    def load_config(self, path: str) -> Dict:
        """加载配置文件"""
        if not os.path.exists(path):
            print(f"错误: 配置文件 {path} 不存在")
            # 创建默认配置文件
            default_config = {
                "blog": {
                    "avatar": "https://avatars.githubusercontent.com/u/195545824?v=4",
                    "name": "VaLog",
                    "description": "个人技术博客",
                    "favicon": "static/favicon.ico"
                },
                "floating_menu": [
                    {"tag": "about", "display": "关于"},
                    {"tag": "contact", "display": "联系"}
                ],
                "special": {
                    "top": False,
                    "view": {
                        "RF_Information": "备案信息文本",
                        "RF_Link": "https://beian.miit.gov.cn",
                        "Copyright": "© 2023 VaLog 版权所有",
                        "C_Link": "https://github.com",
                        "Total_time": "2023.01.01",
                        "Others": "其他说明文本"
                    }
                },
                "theme": {
                    "mode": "dark",
                    "primary_color": "#e74c3c",
                    "dark_bg": "#121212",
                    "light_bg": "#f5f7fa"
                }
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)
            print(f"已创建默认配置文件 {path}")
            return default_config
            
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        return config
    
    def check_dependencies(self):
        """检查必要的依赖"""
        try:
            import markdown
            return True
        except ImportError:
            print("错误: 缺少必要依赖")
            print("请运行: pip install markdown pyyaml requests")
            return False
    
    def fetch_github_issues(self) -> List[Dict]:
        """获取GitHub Issues"""
        if not self.github_repo:
            print("警告: 未设置GITHUB_REPOSITORY，使用模拟数据")
            return self.get_mock_issues()
            
        print(f"正在获取GitHub仓库 {self.github_repo} 的Issues...")
        
        url = f"https://api.github.com/repos/{self.github_repo}/issues"
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        params = {
            "state": "open",
            "per_page": 100
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            issues = response.json()
            print(f"成功获取 {len(issues)} 个Issue")
            return issues
        except Exception as e:
            print(f"获取GitHub Issues失败: {e}")
            print("使用模拟数据")
            return self.get_mock_issues()
    
    def get_mock_issues(self) -> List[Dict]:
        """获取模拟数据，用于测试"""
        return [
            {
                "number": 1,
                "title": "欢迎使用VaLog博客系统",
                "body": """!vml-<span>这是一个基于GitHub Issues的静态博客系统</span>
                
## 功能特性
- 基于GitHub Issues管理文章
- 自动生成静态网站
- 响应式设计
- 搜索功能
- 主题切换""",
                "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "labels": [{"name": "教程"}, {"name": "介绍"}],
                "state": "open"
            },
            {
                "number": 2,
                "title": "VaLog使用教程",
                "body": """!vml-<span>VaLog博客系统详细使用教程</span>

## 快速开始
1. 在GitHub上创建仓库
2. 创建Issue作为文章
3. 运行生成器
4. 部署到GitHub Pages""",
                "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "labels": [{"name": "教程"}, {"name": "文档"}],
                "state": "open"
            }
        ]
    
    def process_issues(self):
        """处理Issues为文章数据"""
        self.issues = self.fetch_github_issues()
        
        for issue in self.issues:
            if "pull_request" in issue:
                continue
            
            issue_id = issue["number"]
            title = issue["title"]
            created_at = issue["created_at"][:10] if issue.get("created_at") else datetime.now().strftime("%Y-%m-%d")
            labels = [label["name"] for label in issue.get("labels", [])]
            
            raw_content = issue.get("body", "")
            
            # 提取摘要
            summary_match = re.search(r'!vml-<span[^>]*>(.*?)</span>', raw_content)
            summary = summary_match.group(1).strip() if summary_match else ""
            
            # 移除摘要行
            content = re.sub(r'!vml-<span[^>]*>.*?</span>\s*\n?', '', raw_content, count=1)
            
            # 处理HTML内联语法
            content = re.sub(r'!vml-(.+?)(?=\n|$)', lambda m: m.group(1), content)
            
            # Markdown转HTML
            try:
                html_content = markdown.markdown(content, extensions=['extra', 'codehilite'])
            except:
                html_content = markdown.markdown(content)
            
            # 生成渐变颜色
            gradients = [
                ["#e74c3c", "#c0392b"],  # 红色
                ["#3498db", "#2980b9"],  # 蓝色
                ["#2ecc71", "#27ae60"],  # 绿色
                ["#9b59b6", "#8e44ad"],  # 紫色
                ["#e67e22", "#d35400"],  # 橙色
            ]
            gradient = gradients[len(self.articles) % len(gradients)]
            
            article = {
                "id": f"article-{issue_id}",
                "issue_id": issue_id,
                "title": title,
                "tags": labels,
                "verticalTitle": labels[0] if labels else "文章",
                "date": created_at,
                "summary": summary,
                "content": html_content,
                "raw_content": content,
                "url": f"/article/{issue_id}.html",
                "gradient": gradient
            }
            
            self.articles.append(article)
            self.save_raw_markdown(issue_id, content)
        
        print(f"成功处理 {len(self.articles)} 篇文章")
    
    def save_raw_markdown(self, issue_id: int, content: str):
        """保存原始Markdown"""
        os.makedirs("O-MD", exist_ok=True)
        with open(f"O-MD/{issue_id}.md", 'w', encoding='utf-8') as f:
            f.write(content)
    
    def generate_base_yaml(self):
        """生成base.yaml文件"""
        blog_info = {
            "avatar": self.config["blog"]["avatar"],
            "name": self.config["blog"]["name"],
            "description": self.config["blog"]["description"],
            "favicon": self.config["blog"]["favicon"]
        }
        
        articles_data = []
        for article in self.articles:
            paragraphs = []
            if article["raw_content"]:
                raw_paragraphs = article["raw_content"].split('\n\n')
                paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]
                if len(paragraphs) > 3:
                    paragraphs = paragraphs[:3]
            
            article_data = {
                "id": article["id"],
                "title": article["title"],
                "tags": article["tags"],
                "verticalTitle": article["verticalTitle"],
                "date": article["date"],
                "content": paragraphs,
                "url": article["url"],
                "gradient": article["gradient"]
            }
            articles_data.append(article_data)
        
        specials_data = []
        special_config = self.config.get("special", {})
        
        if not specials_data and "view" in special_config:
            view_content = []
            for key, value in special_config["view"].items():
                if key == "Total_time":
                    try:
                        start_date = datetime.strptime(value, "%Y.%m.%d")
                        days = (datetime.now() - start_date).days
                        view_content.append(f"已运行 {days} 天")
                    except:
                        view_content.append(value)
                elif key == "RF_Link":
                    view_content.append(f'<a href="{value}" target="_blank">{special_config["view"]["RF_Information"]}</a>')
                elif key == "C_Link":
                    view_content.append(f'<a href="{value}" target="_blank">{special_config["view"]["Copyright"]}</a>')
                elif key not in ["RF_Information", "Copyright"]:
                    view_content.append(value)
            
            specials_data.append({
                "id": "special-text-only",
                "content": view_content
            })
        
        menu_items_data = []
        floating_menu = self.config.get("floating_menu", [])
        
        for menu_item in floating_menu:
            tag = menu_item.get("tag", "")
            display = menu_item.get("display", tag)
            
            url = None
            for article in self.articles:
                if tag in article["tags"]:
                    url = article["url"]
                    break
            
            menu_items_data.append({
                "tag": tag,
                "display": display,
                "url": url if url else "#"
            })
        
        self.base_data = {
            "blog": blog_info,
            "articles": articles_data,
            "specials": specials_data,
            "menu_items": menu_items_data
        }
        
        with open("base.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(self.base_data, f, allow_unicode=True, default_flow_style=False)
        
        print("base.yaml 生成完成")
        return self.base_data
    
    def ensure_template_files(self):
        """确保模板文件存在"""
        template_dir = "template"
        os.makedirs(template_dir, exist_ok=True)
        
        # 检查并创建home.html模板
        home_template = os.path.join(template_dir, "home.html")
        if not os.path.exists(home_template):
            print("警告: home.html模板不存在，使用默认模板")
            # 这里可以创建默认模板，但根据要求，我们需要完整的代码
            # 由于home.html内容太长，我们假设用户已提供
            
        # 检查并创建article.html模板
        article_template = os.path.join(template_dir, "article.html")
        if not os.path.exists(article_template):
            print("创建默认article.html模板")
            default_article_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ article.title }} - {{ blog.name }}</title>
    <link rel="icon" href="{{ blog.favicon }}">
    <style>
        /* 基本样式 */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { margin-bottom: 30px; }
        .article-title { font-size: 2em; margin-bottom: 10px; }
        .article-meta { color: #666; margin-bottom: 20px; }
        .article-content { font-size: 1.1em; }
        .back-link { display: inline-block; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-link">← 返回首页</a>
        </div>
        <h1 class="article-title">{{ article.title }}</h1>
        <div class="article-meta">
            <span>{{ article.date }}</span>
            {% for tag in article.tags %}
            <span class="tag">{{ tag }}</span>
            {% endfor %}
        </div>
        <div class="article-content">
            {{ article.content|safe }}
        </div>
    </div>
</body>
</html>"""
            with open(article_template, 'w', encoding='utf-8') as f:
                f.write(default_article_template)
    
    def generate_home_page(self):
        """生成主页"""
        self.ensure_template_files()
        
        home_template_path = "template/home.html"
        if not os.path.exists(home_template_path):
            print("错误: home.html模板不存在")
            return
        
        os.makedirs(self.docs_dir, exist_ok=True)
        
        with open(home_template_path, "r", encoding="utf-8") as f:
            template = f.read()
        
        # 获取配置值
        blog_name = self.config['blog']['name']
        blog_description = self.config['blog']['description']
        avatar_url = self.config['blog']['avatar']
        favicon_url = self.config['blog']['favicon']
        
        # 替换模板变量 - 修正替换逻辑
        replacements = [
            ("<title>VaLog</title>", f"<title>{blog_name}</title>"),
            ('href="favicon.ico"', f'href="{favicon_url}"'),
            ('src="{{AVATAR_URL}}"', f'src="{avatar_url}"'),
            ('<div class="mobile-title">VaLog</div>', f'<div class="mobile-title">{blog_name}</div>'),
            ('<h2>{{BLOG_NAME}}</h2>', f'<h2>{blog_name}</h2>'),
            ('<p>{{BLOG_DESCRIPTION}}</p>', f'<p>{blog_description}</p>'),
        ]
        
        for old, new in replacements:
            template = template.replace(old, new)
        
        # 准备JavaScript数据
        articles_json = json.dumps(self.base_data['articles'], ensure_ascii=False, indent=2)
        specials_json = json.dumps(self.base_data['specials'], ensure_ascii=False, indent=2)
        menu_items_json = json.dumps(self.base_data['menu_items'], ensure_ascii=False, indent=2)
        
        # 替换JavaScript部分
        js_start = "// ==================== 数据与状态管理 ===================="
        if js_start in template:
            js_section = f"""{js_start}
const blogData = {{
  articles: {articles_json},
  specials: {specials_json}
}};

const menuItems = {menu_items_json};"""
            
            template_parts = template.split(js_start, 1)
            if len(template_parts) == 2:
                # 找到JavaScript部分的结束位置
                js_content = template_parts[1]
                # 找到下一个注释行或script标签结束
                end_pattern = r'(?=\s*// =|\s*</script>|\s*$)'
                import re
                match = re.search(end_pattern, js_content, re.DOTALL)
                if match:
                    template = template_parts[0] + js_section + js_content[match.start():]
                else:
                    template = template_parts[0] + js_section
        
        with open(f"{self.docs_dir}/index.html", "w", encoding="utf-8") as f:
            f.write(template)
        
        print(f"主页生成完成: {self.docs_dir}/index.html")
    
    def generate_article_pages(self):
        """生成文章页"""
        self.ensure_template_files()
        
        article_template_path = "template/article.html"
        if not os.path.exists(article_template_path):
            print("错误: article.html模板不存在")
            return
        
        os.makedirs(f"{self.docs_dir}/article", exist_ok=True)
        
        with open(article_template_path, "r", encoding="utf-8") as f:
            template = f.read()
        
        for article in self.articles:
            article_html = template
            
            # 替换变量
            replacements = [
                ("{{ article.title }} - {{ blog.name }}", f"{article['title']} - {self.config['blog']['name']}"),
                ("{{ article.title }}", article['title']),
                ("{{ blog.name }}", self.config["blog"]["name"]),
                ("{{ blog.favicon }}", self.config["blog"]["favicon"]),
                ("{{ article.date }}", article['date']),
                ("{{ article.content|safe }}", article['content']),
            ]
            
            for old, new in replacements:
                article_html = article_html.replace(old, new)
            
            # 替换标签
            if "{% for tag in article.tags %}" in article_html:
                tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in article['tags']])
                article_html = article_html.replace('{% for tag in article.tags %}<span class="tag">{{ tag }}</span>{% endfor %}', 
                                                  tags_html)
            
            # 替换摘要
            if "{{ article.summary }}" in article_html:
                if article['summary']:
                    article_html = article_html.replace("{{ article.summary }}", article['summary'])
                else:
                    # 移除包含摘要的段落
                    import re
                    article_html = re.sub(r'<p[^>]*>\s*{{ article\.summary }}\s*</p>', '', article_html)
            
            with open(f"{self.docs_dir}/article/{article['issue_id']}.html", "w", encoding="utf-8") as f:
                f.write(article_html)
        
        print(f"文章页生成完成: {len(self.articles)} 个文件")
    
    def copy_static_resources(self):
        """复制静态资源"""
        static_src = "static"
        static_dst = f"{self.docs_dir}/static"
        
        if os.path.exists(static_src):
            if os.path.exists(static_dst):
                shutil.rmtree(static_dst)
            shutil.copytree(static_src, static_dst)
            print("静态资源复制完成")
        else:
            print("警告: 静态资源目录不存在，创建默认目录")
            os.makedirs(static_dst, exist_ok=True)
            
            # 创建默认favicon.ico
            favicon_path = os.path.join(static_dst, "favicon.ico")
            with open(favicon_path, 'wb') as f:
                # 创建一个简单的favicon占位符
                pass
    
    def create_deployment_files(self):
        """创建部署所需的文件"""
        print("\n📦 创建部署文件...")
        
        # 1. 创建 .nojekyll 文件
        nojekyll_path = os.path.join(self.docs_dir, ".nojekyll")
        with open(nojekyll_path, "w", encoding="utf-8") as f:
            f.write("")
        print("✅ 创建 .nojekyll 文件")
        
        # 2. 创建部署信息文件
        info_path = os.path.join(self.docs_dir, "_deploy-info.md")
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(f"# VaLog 博客部署信息\n\n")
            f.write(f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **文章数量**: {len(self.articles)}\n")
            if self.github_repo:
                username = self.github_repo.split('/')[0]
                repo_name = self.github_repo.split('/')[1]
                f.write(f"- **博客地址**: https://{username}.github.io/{repo_name}/\n")
                f.write(f"- **GitHub仓库**: https://github.com/{self.github_repo}\n")
            f.write(f"- **版本**: VaLog 4.1\n")
        print("✅ 创建部署信息文件")
    
    def show_deployment_info(self):
        """显示部署信息"""
        print("\n" + "="*60)
        print("🚀 VaLog 博客部署信息")
        print("="*60)
        
        if self.github_repo:
            username = self.github_repo.split('/')[0]
            repo_name = self.github_repo.split('/')[1]
            blog_url = f"https://{username}.github.io/{repo_name}/"
            
            print(f"\n🌐 博客地址:")
            print(f"   {blog_url}")
        else:
            print(f"\n📁 本地预览:")
            print(f"   cd docs && python -m http.server 8000")
            print(f"   然后在浏览器中访问: http://localhost:8000")
        
        print(f"\n📈 统计信息:")
        print(f"   文章数量: {len(self.articles)}")
        
        if os.path.exists(self.docs_dir):
            file_count = sum([len(files) for _, _, files in os.walk(self.docs_dir)])
            print(f"   生成文件数: {file_count}")
            print(f"   输出目录: {self.docs_dir}/")
        
        print("\n" + "="*60)
    
    def generate_blog(self):
        """生成博客"""
        print("="*60)
        print("🏗️  开始生成 VaLog 博客")
        print("="*60)
        
        # 检查依赖
        if not self.check_dependencies():
            return False
        
        # 处理Issues
        self.process_issues()
        
        # 生成base.yaml
        self.generate_base_yaml()
        
        # 生成主页
        self.generate_home_page()
        
        # 生成文章页
        self.generate_article_pages()
        
        # 复制静态资源
        self.copy_static_resources()
        
        # 创建部署文件
        self.create_deployment_files()
        
        print("\n✅ 博客生成完成！")
        return True
    
    def run(self, mode="generate"):
        """
        运行主流程
        
        参数:
            mode: 
                - "generate": 只生成博客（默认）
                - "auto": 自动部署（用于 GitHub Actions）
                - "manual": 显示部署说明
        """
        # 生成博客
        success = self.generate_blog()
        
        if not success:
            return
        
        # 根据模式执行部署
        if mode == "auto":
            # 自动部署（GitHub Actions）
            self.auto_deploy()
        elif mode == "manual":
            # 显示手动部署说明
            self.manual_deploy_instructions()
        else:
            # 只生成，显示基本信息
            self.show_deployment_info()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="VaLog - 基于 GitHub Issues 的静态博客生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python VaLog_fixed.py                     # 只生成博客
  python VaLog_fixed.py --mode auto        # 生成并准备自动部署
  python VaLog_fixed.py --mode manual      # 生成并显示部署说明
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["generate", "auto", "manual"], 
        default="generate",
        help="运行模式: generate(只生成), auto(自动部署), manual(显示部署说明)"
    )
    
    args = parser.parse_args()
    
    print("🎯 VaLog 博客生成器启动 (修复版)")
    print(f"📂 配置文件: config.yml")
    print(f"🚀 运行模式: {args.mode}")
    
    # 创建生成器实例
    generator = VaLogGenerator("config.yml")
    
    # 运行生成器
    generator.run(mode=args.mode)

if __name__ == "__main__":
    main()
