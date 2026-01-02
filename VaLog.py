#!/usr/bin/env python3
"""
VaLog 静态博客生成器 - 完整版（包含部署）
版本: 2.0
功能：生成 + 部署
"""

import os
import sys
import json
import yaml
import re
import markdown
import requests
import time
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin

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
            
            # Markdown转HTML
            html_content = markdown.markdown(content, extensions=['extra'])
            
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
            articles_data.append({
                "id": article["id"],
                "title": article["title"],
                "tags": article["tags"],
                "verticalTitle": article["verticalTitle"],
                "date": article["date"],
                "content": [article["summary"]],
                "url": article["url"],
                "gradient": article["gradient"]
            })
        
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
            menu_items_data.append({
                "tag": menu_item.get("tag", ""),
                "display": menu_item.get("display", ""),
                "url": "#"
            })
        
        self.base_data = {
            "blog": blog_info,
            "articles": articles_data,
            "specials": specials_data,
            "menu_items": menu_items_data
        }
        
        with open("base.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(self.base_data, f, allow_unicode=True)
        
        print("base.yaml 生成完成")
    
    def generate_home_page(self):
        """生成主页"""
        if not os.path.exists("template/home.html"):
            print("错误: template/home.html 不存在")
            return
        
        os.makedirs(self.docs_dir, exist_ok=True)
        
        with open("template/home.html", "r", encoding="utf-8") as f:
            template = f.read()
        
        # 替换基本内容
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
        
        # 注入数据
        articles_json = json.dumps(self.base_data['articles'], ensure_ascii=False, indent=2)
        specials_json = json.dumps(self.base_data['specials'], ensure_ascii=False, indent=2)
        menu_items_json = json.dumps(self.base_data['menu_items'], ensure_ascii=False, indent=2)
        
        js_section = f"""// ==================== 数据与状态管理 ====================
const blogData = {{
  articles: {articles_json},
  specials: {specials_json}
}};

const menuItems = {menu_items_json};"""
        
        # 替换 JavaScript 部分
        js_start = "// ==================== 数据与状态管理 ===================="
        if js_start in template:
            parts = template.split(js_start, 1)
            template = parts[0] + js_section + parts[1][parts[1].find(';'):]
        
        with open(f"{self.docs_dir}/index.html", "w", encoding="utf-8") as f:
            f.write(template)
        
        print("主页生成完成")
    
    def generate_article_pages(self):
        """生成文章页"""
        if not os.path.exists("template/article.html"):
            print("错误: template/article.html 不存在")
            return
        
        os.makedirs(f"{self.docs_dir}/article", exist_ok=True)
        
        with open("template/article.html", "r", encoding="utf-8") as f:
            template = f.read()
        
        blog_info = self.base_data['blog']
        
        for article in self.articles:
            html = template
            
            # 替换元数据
            html = html.replace("{{ article.title }} - {{ blog.name }}", 
                              f"{article['title']} - {blog_info['name']}")
            html = html.replace("<title>Article</title>", 
                              f"<title>{article['title']} - {blog_info['name']}</title>")
            html = html.replace('href="{{ blog.favicon }}"', 
                              f'href="{blog_info["favicon"]}"')
            
            # 替换内容
            html = html.replace("{{ blog.name }}", blog_info['name'])
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
                f.write(f)
        
        print(f"文章页生成完成: {len(self.articles)} 个文件")
    
    def copy_static_resources(self):
        """复制静态资源"""
        static_src = "static"
        static_dst = f"{self.docs_dir}/static"
        
        if os.path.exists(static_src):
            if os.path.exists(static_dst):
                shutil.rmtree(static_dst)
            shutil.copytree(static_src, static_dst)
            print(f"静态资源复制完成")
        else:
            print(f"警告: 静态资源目录不存在")
            os.makedirs(static_dst, exist_ok=True)
    
    def deploy_to_github_pages(self):
        """部署到GitHub Pages"""
        print("\n" + "="*50)
        print("开始部署到 GitHub Pages")
        print("="*50)
        
        # 检查是否在 GitHub Actions 环境中
        if not self.github_token or not self.github_repo:
            print("警告: 未检测到 GitHub 环境变量")
            print("请在 GitHub Actions 中运行此脚本以自动部署")
            print("或手动将 docs/ 目录推送到仓库的 gh-pages 分支")
            return False
        
        try:
            # 设置 git 配置
            subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
            subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions"], check=True)
            
            # 切换到 gh-pages 分支或创建它
            try:
                subprocess.run(["git", "checkout", "gh-pages"], capture_output=True)
            except:
                subprocess.run(["git", "checkout", "--orphan", "gh-pages"], check=True)
                subprocess.run(["git", "rm", "-rf", "."], capture_output=True)
            
            # 复制 docs 目录内容到根目录
            if os.path.exists(self.docs_dir):
                for item in os.listdir(self.docs_dir):
                    src = os.path.join(self.docs_dir, item)
                    dst = os.path.join(".", item)
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
            
            # 添加文件并提交
            subprocess.run(["git", "add", "."], check=True)
            
            # 检查是否有更改
            result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if not result.stdout.strip():
                print("没有更改需要提交")
                return True
            
            subprocess.run(["git", "commit", "-m", f"Deploy VaLog blog - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"], check=True)
            
            # 推送到 gh-pages 分支
            repo_url = f"https://x-access-token:{self.github_token}@github.com/{self.github_repo}.git"
            subprocess.run(["git", "push", repo_url, "gh-pages", "--force"], check=True)
            
            print("="*50)
            print("部署成功！")
            print(f"博客地址: https://{self.github_repo.split('/')[0]}.github.io/{self.github_repo.split('/')[1]}/")
            print("="*50)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"部署失败: {e}")
            print("输出:", e.output.decode() if e.output else "无输出")
            return False
    
    def deploy_manual_instructions(self):
        """显示手动部署说明"""
        print("\n" + "="*50)
        print("手动部署说明")
        print("="*50)
        
        if self.github_repo:
            username = self.github_repo.split('/')[0]
            repo_name = self.github_repo.split('/')[1]
            blog_url = f"https://{username}.github.io/{repo_name}/"
            
            print(f"1. 将 docs/ 目录推送到 GitHub")
            print(f"2. 访问 https://github.com/{self.github_repo}/settings/pages")
            print(f"3. 设置 Source 为: Branch: main, Folder: /docs")
            print(f"4. 点击 Save")
            print(f"5. 等待几分钟，访问: {blog_url}")
            print(f"\n或使用以下命令手动部署到 gh-pages 分支:")
            print(f"""
git checkout --orphan gh-pages
git rm -rf .
cp -r docs/* .
git add .
git commit -m "Deploy blog"
git push origin gh-pages --force
            """)
        else:
            print("1. 将 docs/ 目录上传到你的静态托管服务")
            print("2. 配置域名或访问地址")
            print("\n本地预览命令:")
            print(f"cd docs && python -m http.server 8000")
            print("然后在浏览器中访问: http://localhost:8000")
    
    def generate_blog(self):
        """生成博客"""
        print("="*50)
        print("开始生成博客")
        print("="*50)
        
        self.process_issues()
        self.generate_base_yaml()
        self.generate_home_page()
        self.generate_article_pages()
        self.copy_static_resources()
        
        print("\n博客生成完成！")
        print(f"生成的文件在: {self.docs_dir}/")
        print("\n文件结构:")
        subprocess.run(["find", self.docs_dir, "-type", "f"], check=False)
    
    def run(self, deploy_mode="auto"):
        """
        运行主流程
        
        参数:
            deploy_mode: 部署模式
                - "auto": 自动部署到 GitHub Pages
                - "manual": 只生成不部署，显示部署说明
                - "generate": 只生成博客
        """
        # 生成博客
        self.generate_blog()
        
        # 部署
        if deploy_mode == "auto":
            success = self.deploy_to_github_pages()
            if not success:
                self.deploy_manual_instructions()
        elif deploy_mode == "manual":
            self.deploy_manual_instructions()
        # "generate" 模式只生成不部署

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="VaLog 博客生成器")
    parser.add_argument("--deploy", choices=["auto", "manual", "generate"], 
                       default="generate", help="部署模式 (默认: generate)")
    
    args = parser.parse_args()
    
    generator = VaLogGenerator("config.yml")
    generator.run(deploy_mode=args.deploy)

if __name__ == "__main__":
    main()