#!/usr/bin/env python3

import os
import sys
import json
import yaml
import hashlib
import re
import markdown
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin
import html
import time


class VaLogGenerator:
    """VaLog 博客生成器主类"""
    
    def __init__(self, config_path: str = "config.yml"):
        self.config_path = config_path
        self.config = self.load_config()
        self.issues = []
        self.articles = []
        self.specials = []
        self.base_data = {}
        
        # 初始化目录
        self.init_directories()
    
    def init_directories(self):
        """初始化必要的目录结构"""
        directories = [
            "docs/article",
            "template",
            "static/custom",
            "O-MD"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 验证配置
            errors = self.validate_config(config)
            if errors:
                print("配置错误:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)
            
            return config
        except FileNotFoundError:
            print(f"错误: 配置文件 {self.config_path} 不存在")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"错误: 配置文件格式错误: {e}")
            sys.exit(1)
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """验证配置文件"""
        errors = []
        
        # 浮动菜单数量验证
        floating_menu = config.get('floating_menu', [])
        if len(floating_menu) > 10:
            errors.append("浮动菜单不能超过10个")
        
        # 特殊卡片配置验证
        special_config = config.get('special', {})
        if not isinstance(special_config.get('top', False), bool):
            errors.append("special.top 必须是布尔值")
        
        # 主题配置验证
        theme_config = config.get('theme', {})
        if theme_config.get('mode') not in ['default', 'light']:
            errors.append("theme.mode 必须是 'default' 或 'light'")
        
        return errors
    
    def safe_fetch_issues(self) -> List[Dict[str, Any]]:
        """安全的GitHub API调用，获取issues"""
        try:
            return self.fetch_issues()
        except Exception as e:
            print(f"GitHub API错误: {e}")
            # 使用本地缓存
            return self.load_cached_issues()
    
    def fetch_issues(self) -> List[Dict[str, Any]]:
        """从GitHub获取issues"""
        github_token = os.environ.get('GITHUB_TOKEN')
        repo = os.environ.get('GITHUB_REPOSITORY')
        
        if not repo:
            # 从当前git仓库获取
            try:
                import subprocess
                result = subprocess.run(
                    ['git', 'remote', 'get-url', 'origin'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    remote_url = result.stdout.strip()
                    # 解析仓库名
                    if 'github.com' in remote_url:
                        repo = remote_url.replace('https://github.com/', '').replace('.git', '').strip()
            except:
                pass
        
        if not repo:
            print("错误: 无法确定GitHub仓库")
            sys.exit(1)
        
        headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        all_issues = []
        page = 1
        per_page = 100
        
        while True:
            url = f'https://api.github.com/repos/{repo}/issues'
            params = {
                'state': 'open',
                'page': page,
                'per_page': per_page
            }
            
            print(f"获取第 {page} 页issues...")
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                print(f"GitHub API错误: {response.status_code}")
                print(response.text[:200])
                break
            
            issues = response.json()
            if not issues:
                break
            
            all_issues.extend(issues)
            
            if len(issues) < per_page:
                break
            
            page += 1
            time.sleep(0.5)  # 避免频率限制
        
        return all_issues
    
    def load_cached_issues(self) -> List[Dict[str, Any]]:
        """从本地缓存加载issues"""
        cache_file = Path("O-MD/articles.json")
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                return cached_data.get('issues', [])
            except:
                pass
        return []
    
    def process_html_inline(self, content: str) -> str:
        """处理!vml-开头的HTML内联语法"""
        pattern = r'!vml-(.+?)(?=\n|$)'
        
        def replace_html(match):
            return match.group(1)  # 直接输出HTML，不转义
        
        return re.sub(pattern, replace_html, content, flags=re.DOTALL)
    
    def extract_summary(self, content: str, max_length: int = 100) -> str:
        """提取文章摘要"""
        # 去除Markdown标题、日期、标签等元数据
        lines = content.split('\n')
        content_lines = []
        
        for line in lines:
            # 跳过空行和元数据行
            if not line.strip():
                continue
            if line.startswith('#') or line.startswith('日期:') or line.startswith('标签:'):
                continue
            content_lines.append(line)
        
        full_content = ' '.join(content_lines)
        
        # 处理HTML内联语法
        full_content = self.process_html_inline(full_content)
        
        # Markdown转HTML
        html_content = markdown.markdown(full_content)
        
        # 去除HTML标签获取纯文本
        text_content = re.sub(r'<[^>]+>', '', html_content)
        
        # 截取摘要
        if len(text_content) > max_length:
            summary = text_content[:max_length] + '...'
        else:
            summary = text_content
        
        return summary
    
    def generate_vertical_title(self, title: str, tags: List[str]) -> str:
        """生成垂直标题"""
        if not title or len(title) < 2:
            if tags:
                return tags[0][:4] if len(tags[0]) > 4 else tags[0]
            return "Blog"
        
        # 提取前4个字符
        vertical = title[:4]
        return vertical
    
    def generate_gradient(self, index: int) -> List[str]:
        """生成渐变颜色"""
        gradients = [
            ["#e74c3c", "#c0392b"],  # 红色
            ["#3498db", "#2980b9"],  # 蓝色
            ["#2ecc71", "#27ae60"],  # 绿色
            ["#9b59b6", "#8e44ad"],  # 紫色
            ["#1abc9c", "#16a085"],  # 青色
        ]
        
        return gradients[index % len(gradistics)]
    
    def process_issues(self):
        """处理issues为文章数据"""
        issues = self.safe_fetch_issues()
        self.issues = issues
        
        # 分类issues
        github_pinned = []
        tag_pinned = []
        specials = []
        normal_articles = []
        
        for issue in issues:
            issue_number = issue['number']
            title = issue['title']
            created_at = issue['created_at']
            labels = [label['name'] for label in issue.get('labels', [])]
            body = issue['body'] or ''
            
            # 检查是否为GitHub置顶
            if 'pinned' in labels:
                github_pinned.append(issue)
            # 检查是否为标签置顶
            elif 'top' in labels:
                tag_pinned.append(issue)
            # 检查是否为special
            elif 'special' in labels:
                specials.append(issue)
            else:
                normal_articles.append(issue)
        
        # 处理置顶逻辑
        if self.config.get('special', {}).get('top', False):
            # 所有置顶文章放入Special
            all_pinned = github_pinned + tag_pinned
            for issue in all_pinned:
                specials.append(issue)
        else:
            # 最多1个GitHub置顶文章
            if len(github_pinned) > 1:
                print("警告: 检测到多个GitHub置顶文章，但配置只允许1个")
                github_pinned = github_pinned[:1]
            
            # 将GitHub置顶文章放到普通列表顶部
            if github_pinned:
                normal_articles = github_pinned + normal_articles
        
        # 处理普通文章
        for issue in normal_articles:
            article = self.process_article(issue, is_special=False)
            if article:
                self.articles.append(article)
        
        # 处理特殊文章
        for issue in specials:
            article = self.process_article(issue, is_special=True)
            if article:
                self.specials.append(article)
        
        # 保存文章数据到缓存
        self.save_articles_cache()
    
    def process_article(self, issue: Dict[str, Any], is_special: bool = False) -> Optional[Dict[str, Any]]:
        """处理单个issue为文章数据"""
        try:
            issue_number = issue['number']
            title = issue['title']
            created_at = issue['created_at']
            labels = [label['name'] for label in issue.get('labels', [])]
            body = issue['body'] or ''
            
            # 去除pinned、top、special标签
            labels = [label for label in labels if label not in ['pinned', 'top', 'special']]
            
            # 解析日期
            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = date_obj.strftime('%Y-%m-%d')
            
            # 生成摘要
            summary = self.extract_summary(body)
            
            # 处理内容
            processed_body = self.process_html_inline(body)
            html_content = markdown.markdown(processed_body)
            
            # 分割为段落
            paragraphs = re.split(r'</p>\s*<p>|</p>\s*<p[^>]*>', html_content)
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            
            # 如果没有段落，使用整个内容
            if not paragraphs:
                paragraphs = [html_content]
            
            # 生成垂直标题
            vertical_title = self.generate_vertical_title(title, labels)
            
            # 生成文章ID
            article_id = f"article-{issue_number}"
            
            # 生成URL
            url = f"/article/{issue_number}.html"
            
            # 生成渐变颜色
            gradient = self.generate_gradient(len(self.articles))
            
            article_data = {
                'id': article_id,
                'title': title,
                'tags': labels,
                'verticalTitle': vertical_title,
                'date': date_str,
                'content': paragraphs,
                'url': url,
                'gradient': gradient
            }
            
            # 如果是special文章，调整结构
            if is_special:
                article_data['id'] = f"special-{issue_number}"
                article_data['url'] = f"https://github.com/issues/{issue_number}"
            
            # 保存原始Markdown
            self.save_original_markdown(issue_number, body)
            
            return article_data
            
        except Exception as e:
            print(f"处理文章 {issue.get('number', 'unknown')} 时出错: {e}")
            return None
    
    def save_original_markdown(self, issue_number: int, content: str):
        """保存原始Markdown到缓存"""
        md_file = Path(f"O-MD/{issue_number}.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def save_articles_cache(self):
        """保存文章数据到缓存"""
        cache_data = {
            'issues': self.issues,
            'articles': self.articles,
            'specials': self.specials,
            'timestamp': datetime.now().isoformat()
        }
        
        cache_file = Path("O-MD/articles.json")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    def generate_base_yaml(self):
        """生成base.yaml文件"""
        # 准备基础数据
        base_data = {
            'blog': {
                'avatar': self.config['blog'].get('avatar', 'static/avatar.png'),
                'name': self.config['blog']['name'],
                'description': self.config['blog']['description']
            },
            'articles': self.articles,
            'specials': self.specials,
            'menu_items': []
        }
        
        # 处理浮动菜单
        floating_menu_config = self.config.get('floating_menu', [])
        for menu_item in floating_menu_config:
            tag = menu_item.get('tag')
            display = menu_item.get('display')
            
            # 查找对应标签的文章
            url = None
            for article in self.articles:
                if tag in article.get('tags', []):
                    url = article['url']
                    break
            
            base_data['menu_items'].append({
                'tag': tag,
                'display': display,
                'url': url
            })
        
        # 写入base.yaml
        with open('base.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(base_data, f, allow_unicode=True, default_flow_style=False)
        
        self.base_data = base_data
        print("base.yaml 生成完成")
    
    def generate_home_page(self):
        """生成主页"""
        template_file = Path("template/home.html")
        if not template_file.exists():
            print(f"错误: 主页模板文件不存在: {template_file}")
            return
        
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 转义特殊字符
        def escape_for_js(value):
            if isinstance(value, str):
                return html.escape(value)
            elif isinstance(value, list):
                return [escape_for_js(item) for item in value]
            elif isinstance(value, dict):
                return {k: escape_for_js(v) for k, v in value.items()}
            else:
                return value
        
        # 准备模板数据
        template_data = {
            'blog': self.base_data['blog'],
            'theme': self.config.get('theme', {}),
            'menu_items': self.base_data['menu_items'],
            'articles': [escape_for_js(article) for article in self.articles],
            'specials': [escape_for_js(special) for special in self.specials]
        }
        
        # 渲染模板
        from jinja2 import Template
        
        template = Template(template_content)
        rendered_content = template.render(**template_data)
        
        # 写入生成的文件
        output_file = Path("docs/index.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(rendered_content)
        
        print(f"主页生成完成: {output_file}")
    
    def generate_article_pages(self):
        """生成文章页"""
        template_file = Path("template/article.html")
        if not template_file.exists():
            print(f"错误: 文章页模板文件不存在: {template_file}")
            return
        
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        from jinja2 import Template
        template = Template(template_content)
        
        # 为每篇文章生成页面
        for article in self.articles:
            # 准备文章数据
            article_data = {
                'article': article,
                'blog': {
                    'name': self.config['blog']['name'],
                    'description': self.config['blog']['description']
                },
                'theme': self.config.get('theme', {})
            }
            
            # 渲染模板
            rendered_content = template.render(**article_data)
            
            # 写入文件
            output_file = Path(f"docs/article/{article['id'].replace('article-', '')}.html")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(rendered_content)
            
            print(f"文章页生成完成: {output_file}")
    
    def calculate_run_days(self) -> int:
        """计算运行天数"""
        total_time = self.config.get('special', {}).get('view', {}).get('Total_time', '2023.01.01')
        try:
            start_date = datetime.strptime(total_time, '%Y.%m.%d')
            current_date = datetime.now()
            delta = current_date - start_date
            return delta.days
        except:
            return 0
    
    def run(self):
        """主运行流程"""
        print("开始生成VaLog博客...")
        
        # 1. 获取和处理issues
        print("正在获取GitHub Issues...")
        self.process_issues()
        
        # 2. 生成base.yaml
        print("正在生成base.yaml...")
        self.generate_base_yaml()
        
        # 3. 生成主页
        print("正在生成主页...")
        self.generate_home_page()
        
        # 4. 生成文章页
        print("正在生成文章页...")
        self.generate_article_pages()
        
        print("VaLog博客生成完成！")
        print(f"生成文章总数: {len(self.articles)}")
        print(f"生成特殊卡片数: {len(self.specials)}")


if __name__ == "__main__":
    generator = VaLogGenerator()
    generator.run()
