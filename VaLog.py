#!/usr/bin/env python3
"""
VaLog 静态博客生成器 - 完整版
版本: 3.0
功能：生成 + 部署
"""

import os
import sys
import json
import yaml
import re
import markdown
import requests
import shutil
from datetime import datetime
from typing import Dict, List, Any, Tuple

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
- 主题切换

## 使用说明
1. 创建GitHub Issues作为博客文章
2. 系统自动生成静态网站
3. 部署到GitHub Pages""",
                "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "labels": [{"name": "教程"}, {"name": "介绍"}],
                "state": "open"
            },
            {
                "number": 2,
                "title": "如何编写博客文章",
                "body": """!vml-<span>学习如何使用Markdown和特殊语法编写博客文章</span>
                
## Markdown语法
支持标准的Markdown语法：
- 标题
- 列表
- 代码块
- 链接
- 图片

## 特殊语法
使用 !vml- 开头可以内联HTML

示例:
!vml-<span style="color: red;">这是红色文本</span>""",
                "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "labels": [{"name": "教程"}, {"name": "markdown"}],
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
                "gradient": ["#e74c3c", "#c0392b"]  # 默认渐变颜色
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
        # 准备博客基础信息
        blog_info = {
            "avatar": self.config["blog"]["avatar"],
            "name": self.config["blog"]["name"],
            "description": self.config["blog"]["description"],
            "favicon": self.config["blog"]["favicon"]
        }
        
        # 准备文章数据
        articles_data = []
        for article in self.articles:
            # 将HTML内容分割为段落
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
        
        # 准备Special卡片数据
        specials_data = []
        special_config = self.config.get("special", {})
        
        # 如果没有Special文章，添加仅文本模式
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
        
        # 准备浮动菜单数据
        menu_items_data = []
        floating_menu = self.config.get("floating_menu", [])
        
        for menu_item in floating_menu:
            tag = menu_item.get("tag", "")
            display = menu_item.get("display", tag)
            
            # 查找是否有对应标签的文章
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
        
        # 构建完整数据
        self.base_data = {
            "blog": blog_info,
            "articles": articles_data,
            "specials": specials_data,
            "menu_items": menu_items_data
        }
        
        # 保存到文件
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
        
        # 替换基础信息占位符
        blog_name = self.config['blog']['name']
        blog_description = self.config['blog']['description']
        avatar_url = self.config['blog']['avatar']
        favicon_url = self.config['blog']['favicon']
        
        # 替换文档标题
        template = template.replace("<title>VaLog</title>", 
                                   f"<title>{blog_name}</title>")
        
        # 替换meta描述
        template = template.replace('content="VaLog"', 
                                   f'content="{blog_name}"')
        
        # 替换favicon
        template = template.replace('href="favicon.ico"', 
                                   f'href="{favicon_url}"')
        
        # 替换头像URL
        template = template.replace('src="Url"', 
                                   f'src="{avatar_url}"')
        
        # 替换移动端标题
        template = template.replace('<div class="mobile-title">VaLog</div>', 
                                   f'<div class="mobile-title">{blog_name}</div>')
        
        # 替换顶部卡片内容
        template = template.replace('<h2>Welcome</h2>', 
                                   f'<h2>{blog_name}</h2>')
        template = template.replace('<p>Introduction</p>', 
                                   f'<p>{blog_description}</p>')
        
        # 替换JavaScript数据部分
        articles_json = json.dumps(self.base_data['articles'], ensure_ascii=False, indent=2)
        specials_json = json.dumps(self.base_data['specials'], ensure_ascii=False, indent=2)
        menu_items_json = json.dumps(self.base_data['menu_items'], ensure_ascii=False, indent=2)
        
        # 查找并替换JavaScript数据部分
        js_start = "// ==================== 数据与状态管理 ===================="
        template_parts = template.split(js_start, 1)
        if len(template_parts) == 2:
            new_js_section = f"""// ==================== 数据与状态管理 ====================
const blogData = {{
  articles: {articles_json},
  specials: {specials_json}
}};

const menuItems = {menu_items_json};"""
            template = template_parts[0] + new_js_section + template_parts[1]
        else:
            print("警告: 未找到JavaScript数据注入点，将使用默认数据")
        
        # 写入输出文件
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
            print("警告: 未安装Jinja2，使用简单模板替换")
            use_jinja2 = False
        
        os.makedirs(f"{self.docs_dir}/article", exist_ok=True)
        
        if use_jinja2:
            # 使用Jinja2模板
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
            # 使用简单模板替换
            with open("template/article.html", "r", encoding="utf-8") as f:
                template_content = f.read()
            
            for article in self.articles:
                html = template_content
                
                # 替换文档标题
                html = html.replace("{{ article.title }} - {{ blog.name }}", 
                                  f"{article['title']} - {self.config['blog']['name']}")
                html = html.replace("<title>Article</title>", 
                                  f"<title>{article['title']} - {self.config['blog']['name']}</title>")
                
                # 替换favicon
                html = html.replace('href="{{ blog.favicon }}"', 
                                  f'href="{self.config["blog"]["favicon"]}"')
                
                # 替换博客名称
                html = html.replace("{{ blog.name }}", self.config["blog"]["name"])
                
                # 替换文章标题
                html = html.replace("{{ article.title }}", article['title'])
                
                # 替换文章摘要
                if article['summary']:
                    html = html.replace("{{ article.summary }}", article['summary'])
                else:
                    html = re.sub(r'<p class="summary">\s*{{ article\.summary }}\s*</p>', '', html)
                
                # 替换文章日期
                html = html.replace("{{ article.date }}", article['date'])
                
                # 替换文章标签
                if article['tags']:
                    tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in article['tags']])
                    html = html.replace('{% for tag in article.tags %}<span class="tag">{{ tag }}</span>{% endfor %}', 
                                      tags_html)
                
                # 替换文章内容
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
    
    def create_nojekyll_file(self):
        """创建 .nojekyll 文件（禁用 Jekyll）"""
        nojekyll_path = os.path.join(self.docs_dir, ".nojekyll")
        with open(nojekyll_path, "w", encoding="utf-8") as f:
            f.write("")
        print("创建 .nojekyll 文件")
    
    def prepare_for_deployment(self):
        """准备部署文件"""
        # 创建 .nojekyll 文件
        self.create_nojekyll_file()
        
        # 显示部署信息
        if self.github_repo:
            username = self.github_repo.split('/')[0]
            repo_name = self.github_repo.split('/')[1]
            blog_url = f"https://{username}.github.io/{repo_name}/"
            
            print("\n" + "="*50)
            print("博客已准备好部署！")
            print(f"GitHub Pages 地址: {blog_url}")
            print("="*50)
            
            # 生成部署信息文件
            info_path = os.path.join(self.docs_dir, "deploy-info.txt")
            with open(info_path, "w", encoding="utf-8") as f:
                f.write(f"VaLog Blog Deployment Info\n")
                f.write("=" * 30 + "\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"仓库: {self.github_repo}\n")
                f.write(f"文章数量: {len(self.articles)}\n")
                f.write(f"访问地址: {blog_url}\n")
                f.write(f"GitHub Pages 配置: https://github.com/{self.github_repo}/settings/pages\n")
    
    def show_manual_deploy_instructions(self):
        """显示手动部署说明"""
        print("\n" + "="*50)
        print("手动部署说明")
        print("="*50)
        
        if self.github_repo:
            username = self.github_repo.split('/')[0]
            repo_name = self.github_repo.split('/')[1]
            blog_url = f"https://{username}.github.io/{repo_name}/"
            
            print(f"1. 访问: https://github.com/{self.github_repo}/settings/pages")
            print(f"2. 设置 Source 为: Branch: main, Folder: /docs")
            print(f"3. 点击 Save")
            print(f"4. 等待几分钟，访问: {blog_url}")
        else:
            print("请配置 GitHub Pages:")
            print("1. 将 docs/ 目录推送到 GitHub")
            print("2. 在仓库设置中配置 GitHub Pages")
            print("3. 选择 main 分支的 /docs 文件夹")
        
        print("\n本地预览:")
        print(f"cd {self.docs_dir} && python -m http.server 8000")
        print("然后在浏览器中访问: http://localhost:8000")
    
    def generate_blog(self):
        """生成博客"""
        print("="*50)
        print("开始生成 VaLog 博客")
        print("="*50)
        
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
    
    def run(self, deploy_mode="generate"):
        """
        运行主流程
        
        参数:
            deploy_mode: 
                - "generate": 只生成博客（默认）
                - "prepare": 生成并准备部署
                - "manual": 生成并显示部署说明
        """
        # 生成博客
        self.generate_blog()
        
        # 根据模式执行操作
        if deploy_mode == "prepare":
            # 准备部署文件
            self.prepare_for_deployment()
        elif deploy_mode == "manual":
            # 显示部署说明
            self.show_manual_deploy_instructions()
        
        # 显示统计信息
        print("\n" + "="*50)
        print("生成统计")
        print("="*50)
        print(f"📊 文章数量: {len(self.articles)}")
        print(f"📁 输出目录: {self.docs_dir}")
        
        # 显示生成的文件
        if os.path.exists(self.docs_dir):
            file_count = 0
            for root, dirs, files in os.walk(self.docs_dir):
                file_count += len(files)
            print(f"📄 生成文件数: {file_count}")
            
            # 显示主要文件
            print(f"📋 主要文件:")
            for root, dirs, files in os.walk(self.docs_dir):
                level = root.replace(self.docs_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f'{indent}{os.path.basename(root)}/')
                subindent = ' ' * 2 * (level + 1)
                for file in files[:5]:  # 只显示前5个文件
                    if not file.startswith('.'):
                        print(f'{subindent}{file}')
                if len(files) > 5:
                    print(f'{subindent}... 和其他 {len(files)-5} 个文件')
                break  # 只显示第一层

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="VaLog - 基于 GitHub Issues 的静态博客生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python VaLog.py                     # 只生成博客
  python VaLog.py --deploy prepare    # 生成并准备部署
  python VaLog.py --deploy manual     # 生成并显示部署说明
        
GitHub Actions 使用:
  python VaLog.py --deploy prepare
        """
    )
    
    parser.add_argument(
        "--deploy", 
        choices=["generate", "prepare", "manual"], 
        default="generate",
        help="部署模式: generate(只生成), prepare(准备部署), manual(显示部署说明)"
    )
    
    args = parser.parse_args()
    
    # 创建生成器实例
    generator = VaLogGenerator("config.yml")
    
    # 运行生成器
    generator.run(deploy_mode=args.deploy)

if __name__ == "__main__":
    main()