#!/usr/bin/env python3
"""
VaLog 静态博客生成器 - 单文件实现
基于 GitHub Issues 的静态博客生成系统
版本: 修正版
"""

import os
import sys
import json
import yaml
import re
import markdown
import requests
import time
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
        
    def load_config(self, path: str) -> Dict:
        """加载配置文件"""
        if not os.path.exists(path):
            print(f"错误: 配置文件 {path} 不存在")
            sys.exit(1)
            
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        # 验证配置
        errors = self.validate_config(config)
        if errors:
            print("配置错误:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
            
        return config
    
    def validate_config(self, config: Dict) -> List[str]:
        """验证配置文件"""
        errors = []
        
        # 浮动菜单数量验证
        floating_menu = config.get('floating_menu', [])
        if len(floating_menu) > 10:
            errors.append("浮动菜单不能超过10个")
        
        # 主题模式验证
        theme_mode = config.get('theme', {}).get('mode', 'dark')
        if theme_mode not in ['dark', 'light']:
            errors.append("theme.mode 必须是 'dark' 或 'light'")
        
        # 颜色格式验证
        import re
        color_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')
        
        primary_color = config.get('theme', {}).get('primary_color', '#e74c3c')
        if not color_pattern.match(primary_color):
            errors.append(f"primary_color 格式错误: {primary_color}")
        
        return errors
    
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
                "body": """!vml-<span>这是一个基于GitHub Issues的静态博客系统，自动生成响应式博客网站</span>
                
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
                "created_at": "2023-10-01T10:00:00Z",
                "labels": [{"name": "教程"}, {"name": "介绍"}],
                "state": "open"
            },
            {
                "number": 2,
                "title": "如何编写博客文章",
                "body": """!vml-<span>学习如何使用Markdown和特殊语法编写VaLog博客文章</span>
                
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
                "created_at": "2023-10-02T14:30:00Z",
                "labels": [{"name": "教程"}, {"name": "markdown"}],
                "state": "open"
            }
        ]
    
    def process_html_inline(self, content: str) -> str:
        """处理!vml-开头的HTML内联语法"""
        pattern = r'!vml-(.+?)(?=\n|$)'
        def replace_html(match):
            return match.group(1)  # 直接输出HTML，不转义
        return re.sub(pattern, replace_html, content)
    
    def extract_summary(self, content: str) -> str:
        """提取摘要（新逻辑）"""
        # 查找第一个!vml-开头的行
        vml_pattern = r'!vml-(.+)'
        match = re.search(vml_pattern, content)
        if not match:
            return ""  # 没有找到，摘要为空
        
        vml_line = match.group(1)
        # 提取<span>标签内容
        span_pattern = r'<span[^>]*>(.*?)</span>'
        span_match = re.search(span_pattern, vml_line)
        if span_match:
            return span_match.group(1).strip()
        return ""
    
    def process_issue_content(self, content: str) -> Tuple[str, str]:
        """处理Issue内容，返回处理后的内容和摘要"""
        # 提取摘要
        summary = self.extract_summary(content)
        
        # 处理HTML内联语法
        processed_content = self.process_html_inline(content)
        
        # 移除!vml-摘要行
        processed_content = re.sub(r'!vml-<span[^>]*>.*?</span>\s*\n?', '', processed_content, count=1)
        
        return processed_content, summary
    
    def process_issues(self):
        """处理Issues为文章数据"""
        self.issues = self.fetch_github_issues()
        
        for issue in self.issues:
            # 跳过pull request
            if "pull_request" in issue:
                continue
            
            issue_id = issue["number"]
            title = issue["title"]
            created_at = issue["created_at"][:10]  # 只取日期部分
            labels = [label["name"] for label in issue.get("labels", [])]
            
            # 处理内容
            raw_content = issue.get("body", "")
            content, summary = self.process_issue_content(raw_content)
            
            # Markdown转HTML
            html_content = markdown.markdown(content, extensions=['extra', 'codehilite'])
            
            # 生成文章数据
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
            
            # 保存原始Markdown
            self.save_raw_markdown(issue_id, content)
        
        print(f"成功处理 {len(self.articles)} 篇文章")
    
    def save_raw_markdown(self, issue_id: int, content: str):
        """保存原始Markdown到O-MD目录"""
        os.makedirs("O-MD", exist_ok=True)
        filepath = f"O-MD/{issue_id}.md"
        
        with open(filepath, 'w', encoding='utf-8') as f:
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
                # 简单按空行分割
                raw_paragraphs = article["raw_content"].split('\n\n')
                paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]
                if len(paragraphs) > 3:  # 只取前3段作为预览
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
        
        # 检查是否有置顶文章
        if special_config.get("top", False):
            # 所有置顶文章放入Special
            for article in self.articles:
                if "top" in article["tags"] or "special" in article["tags"]:
                    special_data = {
                        "id": f"special-{article['issue_id']}",
                        "title": article["title"],
                        "tags": article["tags"],
                        "content": [article["summary"]] if article["summary"] else ["暂无简介"],
                        "url": article["url"],
                        "gradient": article["gradient"]
                    }
                    specials_data.append(special_data)
        else:
            # 只有special标签的文章放入Special
            for article in self.articles:
                if "special" in article["tags"]:
                    special_data = {
                        "id": f"special-{article['issue_id']}",
                        "title": article["title"],
                        "tags": article["tags"],
                        "content": [article["summary"]] if article["summary"] else ["暂无简介"],
                        "url": article["url"],
                        "gradient": article["gradient"]
                    }
                    specials_data.append(special_data)
        
        # 如果没有Special文章，添加仅文本模式
        if not specials_data and "view" in special_config:
            view_content = []
            for key, value in special_config["view"].items():
                if key == "Total_time":
                    # 计算运行天数
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
                "url": url
            })
        
        # 构建完整数据
        self.base_data = {
            "blog": blog_info,
            "articles": articles_data,
            "specials": specials_data,
            "menu_items": menu_items_data
        }
        
        # 保存到文件 - 修复目录创建问题
        with open("base.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(self.base_data, f, allow_unicode=True, default_flow_style=False)
        
        print("base.yaml 生成完成")
    
    def generate_home_page(self):
        """生成主页（使用占位符替换）"""
        if not os.path.exists("template/home.html"):
            print("错误: template/home.html 不存在")
            return
        
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
        os.makedirs("docs", exist_ok=True)
        with open("docs/index.html", "w", encoding="utf-8") as f:
            f.write(template)
        
        print("主页生成完成: docs/index.html")
    
    def generate_article_pages(self):
        """生成文章页（使用Jinja2）"""
        if not os.path.exists("template/article.html"):
            print("错误: template/article.html 不存在")
            return
        
        try:
            from jinja2 import Environment, FileSystemLoader
        except ImportError:
            print("警告: 未安装Jinja2，使用简单模板替换")
            return self.generate_article_pages_simple()
        
        env = Environment(loader=FileSystemLoader('template'))
        template = env.get_template('article.html')
        
        for article in self.articles:
            # 准备文章数据
            article_data = {
                'blog': self.config['blog'],
                'article': article
            }
            
            # 渲染模板
            html = template.render(**article_data)
            
            # 写入文件
            output_path = f"docs/article/{article['issue_id']}.html"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
        
        print(f"文章页生成完成: {len(self.articles)} 个文件")
                
    def generate_article_pages_simple(self):
        """备用：简单的文章页生成"""
        if not os.path.exists("template/article.html"):
            print("错误: template/article.html 不存在")
            return
        
        with open("template/article.html", "r", encoding="utf-8") as f:
            template_content = f.read()
        
        # 读取base.yaml数据以获取博客信息
        if os.path.exists("base.yaml"):
            with open("base.yaml", "r", encoding="utf-8") as f:
                base_data = yaml.safe_load(f)
                blog_info = base_data.get("blog", {})
        else:
            blog_info = {
                "name": self.config["blog"]["name"],
                "favicon": self.config["blog"]["favicon"]
            }
        
        for article in self.articles:
            html = template_content
            
            # 替换文档标题
            html = html.replace("{{ article.title }} - {{ blog.name }}", 
                              f"{article['title']} - {blog_info.get('name', 'VaLog')}")
            html = html.replace("<title>Article</title>", 
                              f"<title>{article['title']} - {blog_info.get('name', 'VaLog')}</title>")
            
            # 替换favicon
            html = html.replace('href="{{ blog.favicon }}"', 
                              f'href="{blog_info.get("favicon", "favicon.ico")}"')
            
            # 替换博客名称
            html = html.replace("{{ blog.name }}", blog_info.get("name", "VaLog"))
            
            # 替换文章标题
            html = html.replace("{{ article.title }}", article['title'])
            
            # 替换文章摘要
            if article['summary']:
                html = html.replace("{{ article.summary }}", article['summary'])
            else:
                # 移除摘要部分
                html = re.sub(r'<p class="summary">\s*{{ article\.summary }}\s*</p>', '', html)
            
            # 替换文章日期
            html = html.replace("{{ article.date }}", article['date'])
            
            # 替换文章标签
            if article['tags']:
                tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in article['tags']])
                html = html.replace('{% for tag in article.tags %}<span class="tag">{{ tag }}</span>{% endfor %}', 
                                  tags_html)
            else:
                # 移除标签部分
                html = re.sub(r'<div class="tags">\s*{% for tag in article.tags %}<span class="tag">{{ tag }}</span>{% endfor %}\s*</div>', 
                            '<div class="tags"></div>', html)
            
            # 替换文章内容
            html = html.replace("{{ article.content|safe }}", article['content'])
            
            # 写入文件
            output_path = f"docs/article/{article['issue_id']}.html"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
    
    def run(self):
        """主运行流程"""
        print("=" * 50)
        print("VaLog 博客生成器启动")
        print("=" * 50)
        
        # 1. 处理Issues
        self.process_issues()
        
        # 2. 生成base.yaml
        self.generate_base_yaml()
        
        # 3. 生成主页
        self.generate_home_page()
        
        # 4. 生成文章页
        self.generate_article_pages()
        
        # 5. 复制静态资源
        self.copy_static_resources()
        
        print("=" * 50)
        print("VaLog 博客生成完成")
        print("=" * 50)
    
    def copy_static_resources(self):
        """复制静态资源到docs目录"""
        static_src = "static"
        static_dst = "docs/static"
        
        if os.path.exists(static_src):
            import shutil
            if os.path.exists(static_dst):
                shutil.rmtree(static_dst)
            shutil.copytree(static_src, static_dst)
            print(f"静态资源复制完成: {static_src} -> {static_dst}")
        else:
            print(f"警告: 静态资源目录 {static_src} 不存在")
            # 创建必要的目录结构
            os.makedirs(static_dst, exist_ok=True)
            
            # 创建默认头像
            try:
                from PIL import Image, ImageDraw, ImageFont
                img = Image.new('RGB', (200, 200), color='#e74c3c')
                d = ImageDraw.Draw(img)
                
                # 尝试加载字体，如果失败则使用默认
                try:
                    font = ImageFont.truetype("arial.ttf", 80)
                except:
                    font = ImageFont.load_default()
                
                d.text((100, 100), "V", fill='white', font=font, anchor='mm')
                img.save(f"{static_dst}/avatar.png")
                print("创建默认头像: docs/static/avatar.png")
            except ImportError:
                print("警告: PIL未安装，无法创建默认头像")
            except Exception as e:
                print(f"警告: 创建默认头像失败: {e}")
        
        # 复制favicon
        favicon_src = self.config['blog']['favicon']
        if favicon_src and os.path.exists(favicon_src):
            import shutil
            favicon_dst = os.path.join("docs", os.path.basename(favicon_src))
            shutil.copy2(favicon_src, favicon_dst)
            print(f"favicon复制完成: {favicon_src} -> {favicon_dst}")

def main():
    """主函数"""
    generator = VaLogGenerator("config.yml")
    generator.run()

if __name__ == "__main__":
    main()
