#!/usr/bin/env python3
"""
VaLog 静态博客生成器 - 完整版（包含部署）
版本: 4.0
功能：生成 + 部署 + GitHub Actions 集成
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
        
    def load_config(self, path: str) -> Dict:
        """加载配置文件"""
        if not os.path.exists(path):
            print(f"错误: 配置文件 {path} 不存在")
            sys.exit(1)
            
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        return config
    
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
            created_at = issue["created_at"][:10]
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
            html_content = markdown.markdown(content, extensions=['extra', 'codehilite'])
            
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
                "gradient": ["#e74c3c", "#c0392b"]
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
    
    def generate_home_page(self):
        """生成主页"""
        if not os.path.exists("template/home.html"):
            print("错误: template/home.html 不存在")
            return
        
        os.makedirs(self.docs_dir, exist_ok=True)
        
        with open("template/home.html", "r", encoding="utf-8") as f:
            template = f.read()
        
        blog_name = self.config['blog']['name']
        blog_description = self.config['blog']['description']
        avatar_url = self.config['blog']['avatar']
        favicon_url = self.config['blog']['favicon']
        
        template = template.replace("<title>VaLog</title>", f"<title>{blog_name}</title>")
        template = template.replace('href="favicon.ico"', f'href="{favicon_url}"')
        template = template.replace('src="Url"', f'src="{avatar_url}"')
        template = template.replace('<div class="mobile-title">VaLog</div>', f'<div class="mobile-title">{blog_name}</div>')
        template = template.replace('<h2>Welcome</h2>', f'<h2>{blog_name}</h2>')
        template = template.replace('<p>Introduction</p>', f'<p>{blog_description}</p>')
        
        articles_json = json.dumps(self.base_data['articles'], ensure_ascii=False, indent=2)
        specials_json = json.dumps(self.base_data['specials'], ensure_ascii=False, indent=2)
        menu_items_json = json.dumps(self.base_data['menu_items'], ensure_ascii=False, indent=2)
        
        js_section = f"""// ==================== 数据与状态管理 ====================
const blogData = {{
  articles: {articles_json},
  specials: {specials_json}
}};

const menuItems = {menu_items_json};"""
        
        js_start = "// ==================== 数据与状态管理 ===================="
        template_parts = template.split(js_start, 1)
        if len(template_parts) == 2:
            template = template_parts[0] + js_section + template_parts[1]
        
        with open(f"{self.docs_dir}/index.html", "w", encoding="utf-8") as f:
            f.write(template)
        
        print("主页生成完成")
    
    def generate_article_pages(self):
        """生成文章页"""
        if not os.path.exists("template/article.html"):
            print("错误: template/article.html 不存在")
            return
        
        try:
            from jinja2 import Environment, FileSystemLoader
            use_jinja2 = True
        except ImportError:
            use_jinja2 = False
        
        os.makedirs(f"{self.docs_dir}/article", exist_ok=True)
        
        if use_jinja2:
            env = Environment(loader=FileSystemLoader('template'))
            template = env.get_template('article.html')
            
            for article in self.articles:
                article_data = {
                    'blog': self.config['blog'],
                    'article': article
                }
                html = template.render(**article_data)
                
                with open(f"{self.docs_dir}/article/{article['issue_id']}.html", "w", encoding="utf-8") as f:
                    f.write(html)
        else:
            with open("template/article.html", "r", encoding="utf-8") as f:
                template_content = f.read()
            
            for article in self.articles:
                html = template_content
                
                html = html.replace("{{ article.title }} - {{ blog.name }}", 
                                  f"{article['title']} - {self.config['blog']['name']}")
                html = html.replace("<title>Article</title>", 
                                  f"<title>{article['title']} - {self.config['blog']['name']}</title>")
                html = html.replace('href="{{ blog.favicon }}"', 
                                  f'href="{self.config["blog"]["favicon"]}"')
                html = html.replace("{{ blog.name }}", self.config["blog"]["name"])
                html = html.replace("{{ article.title }}", article['title'])
                
                if article['summary']:
                    html = html.replace("{{ article.summary }}", article['summary'])
                else:
                    html = re.sub(r'<p class="summary">\s*{{ article\.summary }}\s*</p>', '', html)
                
                html = html.replace("{{ article.date }}", article['date'])
                
                if article['tags']:
                    tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in article['tags']])
                    html = html.replace('{% for tag in article.tags %}<span class="tag">{{ tag }}</span>{% endfor %}', 
                                      tags_html)
                
                html = html.replace("{{ article.content|safe }}", article['content'])
                
                with open(f"{self.docs_dir}/article/{article['issue_id']}.html", "w", encoding="utf-8") as f:
                    f.write(html)
        
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
            print("警告: 静态资源目录不存在")
            os.makedirs(static_dst, exist_ok=True)
    
    # ==================== 部署相关函数 ====================
    
    def create_deployment_files(self):
        """创建部署所需的文件"""
        print("\n📦 创建部署文件...")
        
        # 1. 创建 .nojekyll 文件（禁用 Jekyll）
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
            f.write(f"- **版本**: VaLog 4.0\n")
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
            
            print(f"\n🔧 GitHub Pages 设置:")
            print(f"   https://github.com/{self.github_repo}/settings/pages")
            
            print(f"\n📊 部署状态:")
            print(f"   1. 已生成博客文件到 docs/ 目录")
            print(f"   2. 已创建 .nojekyll 文件")
            print(f"   3. 请确保 GitHub Pages 设置为:")
            print(f"      - Source: GitHub Actions")
            print(f"      或")
            print(f"      - Source: Branch: main, Folder: /docs")
            
            if os.environ.get('GITHUB_ACTIONS') == 'true':
                print(f"\n🤖 检测到 GitHub Actions 环境")
                print(f"   部署将自动完成！")
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
    
    def auto_deploy(self):
        """自动部署到 GitHub Pages（在 GitHub Actions 中调用）"""
        print("\n" + "="*60)
        print("🤖 开始自动部署流程")
        print("="*60)
        
        # 创建部署文件
        self.create_deployment_files()
        
        # 检查是否在 GitHub Actions 中
        if os.environ.get('GITHUB_ACTIONS') != 'true':
            print("⚠️  警告: 不在 GitHub Actions 环境中")
            print("自动部署只能在 GitHub Actions 中运行")
            self.show_deployment_info()
            return False
        
        print("✅ 检测到 GitHub Actions 环境")
        print("✅ 部署文件已准备就绪")
        print("✅ GitHub Actions 将自动完成部署")
        
        # 显示访问地址
        if self.github_repo:
            username = self.github_repo.split('/')[0]
            repo_name = self.github_repo.split('/')[1]
            print(f"\n🌐 博客将部署到:")
            print(f"   https://{username}.github.io/{repo_name}/")
        
        print("\n⏳ 等待 GitHub Pages 部署完成...")
        print("部署通常需要 1-2 分钟")
        
        return True
    
    def manual_deploy_instructions(self):
        """显示手动部署说明"""
        print("\n" + "="*60)
        print("📖 手动部署说明")
        print("="*60)
        
        print("\n1️⃣ 推送代码到 GitHub:")
        print("   git add .")
        print("   git commit -m 'Update blog'")
        print("   git push origin main")
        
        print("\n2️⃣ 配置 GitHub Pages:")
        print("   a. 访问: https://github.com/你的用户名/你的仓库名/settings/pages")
        print("   b. 设置 Source 为 'GitHub Actions'")
        print("      - 或选择 'Deploy from a branch'")
        print("      - Branch: main, Folder: /docs")
        print("   c. 点击 Save")
        
        print("\n3️⃣ 等待部署:")
        print("   - 通常需要 1-2 分钟")
        print("   - 刷新页面查看状态")
        
        if self.github_repo:
            username = self.github_repo.split('/')[0]
            repo_name = self.github_repo.split('/')[1]
            print(f"\n4️⃣ 访问博客:")
            print(f"   https://{username}.github.io/{repo_name}/")
        
        print("\n" + "="*60)
    
    # ==================== 主流程函数 ====================
    
    def generate_blog(self):
        """生成博客"""
        print("="*60)
        print("🏗️  开始生成 VaLog 博客")
        print("="*60)
        
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
        
        print("\n✅ 博客生成完成！")
    
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
        self.generate_blog()
        
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
  python VaLog.py                     # 只生成博客
  python VaLog.py --mode auto        # 生成并准备自动部署（GitHub Actions）
  python VaLog.py --mode manual      # 生成并显示部署说明
        
在 GitHub Actions 中:
  python VaLog.py --mode auto
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["generate", "auto", "manual"], 
        default="generate",
        help="运行模式: generate(只生成), auto(自动部署), manual(显示部署说明)"
    )
    
    args = parser.parse_args()
    
    print("🎯 VaLog 博客生成器启动")
    print(f"📂 配置文件: config.yml")
    print(f"🚀 运行模式: {args.mode}")
    
    # 创建生成器实例
    generator = VaLogGenerator("config.yml")
    
    # 运行生成器
    generator.run(mode=args.mode)

if __name__ == "__main__":
    main()