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

# 默认模板文件名
DEFAULT_ARTICLE_TEMPLATE = "article.html"
DEFAULT_HOME_TEMPLATE = "home.html"

# 创建必要的目录
os.makedirs(ARTICLE_DIR, exist_ok=True)
os.makedirs(OMD_DIR, exist_ok=True)

class VaLogGenerator:
    def __init__(self):
        print("初始化VaLog生成器...")
        
        # 加载配置文件
        if not os.path.exists(CONFIG_PATH):
            print(f"警告: 配置文件不存在: {CONFIG_PATH}")
            self.config = {}
        else:
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
                print(f"配置文件加载成功: {CONFIG_PATH}")
            except Exception as e:
                print(f"配置文件加载失败: {e}")
                self.config = {}
        
        # 从配置中读取模板文件名，如果没有配置则使用默认值
        self.article_template_name = self.config.get('templates', {}).get('VaLog-default-article', DEFAULT_ARTICLE_TEMPLATE)
        self.home_template_name = self.config.get('templates', {}).get('VaLog-default-index', DEFAULT_HOME_TEMPLATE)
        
        print(f"文章模板: {self.article_template_name}")
        print(f"首页模板: {self.home_template_name}")
        
        # 加载缓存
        self.cache = {}
        if os.path.exists(OMD_JSON):
            try:
                with open(OMD_JSON, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                print(f"缓存加载成功，条目数: {len(self.cache)}")
            except Exception as e:
                print(f"缓存加载失败: {e}")
                self.cache = {}
        else:
            print("无缓存文件，将创建新缓存")
        
        # 创建模板环境
        if not os.path.exists(TEMPLATE_DIR):
            print(f"错误: 模板目录不存在: {TEMPLATE_DIR}")
            raise FileNotFoundError(f"模板目录不存在: {TEMPLATE_DIR}")
        
        print(f"模板目录: {TEMPLATE_DIR}")
        self.env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        print("Jinja2环境初始化完成")

    def extract_metadata_and_body(self, body):
        """准确提取元数据并在渲染前将其从正文中彻底移除"""
        if not body:
            return {
                "summary": ["暂无简介"],
                "vertical_title": "",
                "body": ""
            }
            
        lines = body.split('\n')
        summary = ["暂无简介"]
        vertical_title = ""
        
        # 定义需要跳过的行索引
        meta_indices = []
        
        # 1. 检查第一行是否为摘要元数据
        if len(lines) > 0 and lines[0].strip().startswith('!vml-'):
            match = re.search(r'<span[^>]*>(.*?)</span>', lines[0])
            if match:
                summary = [match.group(1).strip()]
                meta_indices.append(0) # 记录该行需要被移除
        
        # 2. 检查第二行是否为垂直标题元数据
        if len(lines) > 1 and lines[1].strip().startswith('!vml-'):
            match = re.search(r'<span[^>]*>(.*?)</span>', lines[1])
            if match:
                vertical_title = match.group(1).strip()
                meta_indices.append(1) # 记录该行需要被移除
        
        # 3. 过滤正文：只排除那些被确认为元数据的行
        content_lines = [
            line for i, line in enumerate(lines) 
            if i not in meta_indices
        ]
        
        return {
            "summary": summary,
            "vertical_title": vertical_title,
            "body": "\n".join(content_lines).strip()
        }

    def process_body(self, body):
        """处理正文，转换为HTML（这里接收的是已经移除了元数据的正文）"""
        if not body:
            return ""
        
        # 调试信息
        print(f"处理正文，原始长度: {len(body)} 字符")
        if len(body) > 0:
            print(f"前200字符预览: {repr(body[:200])}")
        
        try:
            # 使用 nl2br 扩展来自动处理换行
            html_content = markdown.markdown(
                body, 
                extensions=[
                    'extra',          # 包括表格、脚注等
                    'fenced_code',    # 代码块
                    'tables',         # 表格支持
                    'nl2br',          # 自动将换行转换为 <br>
                    'sane_lists',     # 更智能的列表处理
                ],
                output_format='html5'
            )
            
            # 确保代码块有正确的CSS类
            html_content = re.sub(
                r'<pre><code(?!\s*class=)',
                '<pre><code class="language-plaintext"',
                html_content
            )
            
            # 调试转换结果
            print(f"转换后HTML长度: {len(html_content)} 字符")
            if len(html_content) > 0:
                print(f"HTML前200字符预览: {repr(html_content[:200])}")
            
            # 检查是否包含必要的HTML标签
            if '<p>' not in html_content and '</p>' not in html_content:
                print("警告: Markdown转换后没有段落标签，尝试手动处理")
                # 如果没有段落标签，手动处理
                paragraphs = []
                for para in body.split('\n\n'):
                    if para.strip():
                        # 将段落内的换行转换为 <br>
                        para_html = para.replace('\n', '<br>\n')
                        paragraphs.append(f'<p>{para_html}</p>')
                html_content = '\n\n'.join(paragraphs)
            
            return html_content
        except Exception as e:
            print(f"Markdown转换错误: {e}")
            import traceback
            traceback.print_exc()
            
            # 应急处理：手动处理换行
            print("使用应急处理方案")
            paragraphs = []
            for para in body.split('\n\n'):
                if para.strip():
                    # 将段落内的换行转换为 <br>
                    para_html = para.replace('\n', '<br>\n')
                    paragraphs.append(f'<p>{para_html}</p>')
            
            return '\n\n'.join(paragraphs) if paragraphs else ""

    def run(self):
        print("开始运行生成器...")
        
        # 获取环境变量
        repo = os.getenv("REPO")
        token = os.getenv("GITHUB_TOKEN")
        
        if not repo:
            print("错误: REPO环境变量未设置")
            return
        
        if not token:
            print("错误: GITHUB_TOKEN环境变量未设置")
            return
        
        print(f"GitHub仓库: {repo}")
        print(f"Token长度: {len(token)}")
        
        # 设置请求头
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # 获取GitHub Issues
        print("获取GitHub Issues...")
        try:
            url = f"https://api.github.com/repos/{repo}/issues?state=open&per_page=100"
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            issues = response.json()
            print(f"获取到 {len(issues)} 个issue")
        except requests.exceptions.RequestException as e:
            print(f"GitHub API请求失败: {e}")
            return
        except Exception as e:
            print(f"处理Issues时出错: {e}")
            return
        
        # 过滤掉Pull Request
        issues = [i for i in issues if not i.get("pull_request")]
        print(f"过滤后文章数量: {len(issues)}")
        
        all_articles = []
        specials = []
        new_cache = {}

        blog_cfg = self.config.get('blog', {})
        theme_cfg = self.config.get('theme', {})
        special_cfg = self.config.get('special', {})
        
        # 获取特殊标签配置
        special_top_enabled = special_cfg.get('top', True)
        special_tags = self.config.get('special_tags', [])
        
        print("开始处理文章...")
        for i, issue in enumerate(issues, 1):
            try:
                iid = str(issue['number'])
                updated_at = issue['updated_at']
                body = issue.get('body', '') or ''
                tags = [label['name'] for label in issue.get('labels', [])]
                
                print(f"\n处理文章 {i}/{len(issues)}: #{iid} - {issue['title']}")
                print(f"  标签: {tags}")
                
                # 提取元数据和正文（这里会分离元数据和正文）
                metadata = self.extract_metadata_and_body(body)
                
                # 垂直标题优先级：元数据中的垂直标题 > 文章标题 > "Blog"
                vertical_title = metadata["vertical_title"] or issue['title'] or "ABlog"
                
                # 检查是否需要更新
                need_update = iid not in self.cache or self.cache[iid] != updated_at
                
                # 处理正文内容
                processed_content = self.process_body(metadata["body"])
                
                article_data = {
                    "id": iid,
                    "title": issue['title'],
                    "date": issue['created_at'][:10] if issue.get('created_at') else "",
                    "tags": tags,
                    "content": processed_content,  # 使用处理后的HTML内容
                    "raw_content": metadata["body"],  # 保留原始内容用于调试
                    "url": f"article/{iid}.html",
                    "verticalTitle": vertical_title,
                    "summary": metadata["summary"]
                }
                
                if need_update:
                    print(f"  需要更新: {need_update}")
                    
                    # 获取文章模板
                    try:
                        tmpl = self.env.get_template(self.article_template_name)
                    except Exception as e:
                        print(f"  模板加载失败: {e}")
                        # 使用简单模板作为备选
                        article_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{article_data['title']}</title>
    <style>
        .content {{
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.8;
        }}
        .content p {{
            margin-bottom: 1.5em;
        }}
    </style>
</head>
<body>
    <h1>{article_data['title']}</h1>
    <p>日期: {article_data['date']}</p>
    <p>标签: {', '.join(article_data['tags'])}</p>
    <div class="content">{processed_content}</div>
</body>
</html>"""
                    else:
                        # 渲染文章页面
                        article_html = tmpl.render(
                            article=article_data, 
                            blog={**blog_cfg, "theme": theme_cfg}
                        )
                    
                    # 保存文章HTML
                    article_path = os.path.join(ARTICLE_DIR, f"{iid}.html")
                    with open(article_path, "w", encoding="utf-8") as f:
                        f.write(article_html)
                    print(f"  已生成: {article_path}")
                    
                    # 备份原始Markdown（包含元数据）
                    md_path = os.path.join(OMD_DIR, f"{iid}.md")
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(body)
                    print(f"  已备份: {md_path}")
                
                # 检查是否为特殊文章
                is_special = False

                if 'special' in tags:
                    is_special = True
                    print(f"  标记为特殊文章 (special标签)")
                
                # 检查配置的特殊标签
                elif special_top_enabled and 'top' in tags:
                    is_special = True
                    print(f"  标记为特殊文章 (top标签)")
                
                # 检查其他特殊标签
                for tag in special_tags:
                    if tag in tags:
                        is_special = True
                        print(f"  标记为特殊文章 ({tag}标签)")
                        break
                
                # 对于文章列表，使用摘要
                list_article_data = {
                    "id": iid,
                    "title": issue['title'],
                    "date": issue['created_at'][:10] if issue.get('created_at') else "",
                    "tags": tags,
                    "content": metadata["summary"],  # 列表使用摘要
                    "url": f"article/{iid}.html",
                    "verticalTitle": vertical_title
                }
                
                if is_special:
                    # 如果是特殊文章，只添加到specials列表
                    specials.append(list_article_data)
                else:
                    # 如果不是特殊文章，添加到all_articles列表
                    all_articles.append(list_article_data)
                
                # 更新缓存
                new_cache[iid] = updated_at
                    
            except Exception as e:
                print(f"  处理文章时出错: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n普通文章: {len(all_articles)} 篇")
        print(f"特殊文章: {len(specials)} 篇")
        print(f"文章处理完成，总计: {len(all_articles) + len(specials)} 篇")
        
        # 保存缓存
        try:
            with open(OMD_JSON, 'w', encoding='utf-8') as f:
                json.dump(new_cache, f, indent=2, ensure_ascii=False)
            print(f"缓存已保存: {OMD_JSON}")
        except Exception as e:
            print(f"缓存保存失败: {e}")
        
        # 如果special数组为空，使用配置信息填充
        if not specials and special_cfg.get('view'):
            view = special_cfg.get('view', {})
            
            # 计算运行天数
            run_date_str = view.get('Total_time', '2026.01.01')
            try:
                run_date = datetime.strptime(run_date_str, '%Y.%m.%d')
                days_running = (datetime.now() - run_date).days
                days_text = f"运行天数: {days_running} 天"
            except:
                days_text = "运行天数: 计算中..."
            
            # 创建默认的特殊文章
            default_special = {
                "id": "0",
                "title": "",
                "date": "",
                "tags": [],
                "content": [
                    view.get('RF_Information', ''),
                    view.get('Copyright', ''),
                    days_text,
                    view.get('Others', '')
                ],
                "url": "",
                "verticalTitle": "Special"
            }
            specials.append(default_special)
            print("已使用配置信息填充special数组")
        
        # 生成 base.yaml
        try:
            base_data = {
                "blog": {**blog_cfg, "theme": theme_cfg}, 
                "articles": all_articles, 
                "specials": specials, 
                "floating_menu": self.config.get('floating_menu', []),
                "special_config": special_cfg
            }
            with open(BASE_YAML_OUT, 'w', encoding='utf-8') as f:
                yaml.dump(base_data, f, allow_unicode=True, sort_keys=False)
            print(f"base.yaml 已生成: {BASE_YAML_OUT}")
        except Exception as e:
            print(f"base.yaml 生成失败: {e}")
        
        # 生成首页
        self.generate_index(all_articles, specials)
        
        print("\n生成器运行完成！")

    def generate_index(self, articles, specials):
        print("生成首页...")
        
        # 使用配置的首页模板文件名
        home_tmpl_path = os.path.join(TEMPLATE_DIR, self.home_template_name)
        if not os.path.exists(home_tmpl_path):
            print(f"错误: 首页模板不存在: {home_tmpl_path}")
            return
        
        try:
            # 使用配置的首页模板文件名
            tmpl = self.env.get_template(self.home_template_name)
            
            context = {
                "BLOG_NAME": self.config.get('blog', {}).get('name', 'VaLog'),
                "SPECIAL_NAME": self.config.get('blog', {}).get('sname', 'Special'),
                "BLOG_DESCRIPTION": self.config.get('blog', {}).get('description', ''),
                "BLOG_AVATAR": self.config.get('blog', {}).get('avatar', ''),
                "BLOG_FAVICON": self.config.get('blog', {}).get('favicon', ''),
                "THEME_MODE": self.config.get('theme', {}).get('mode', 'dark'),
                "PRIMARY_COLOR": self.config.get('theme', {}).get('primary_color', '#e74c3c'),
                "TOTAL_TIME": self.config.get('special', {}).get('view', {}).get('Total_time', '2023.01.01'),
                "ARTICLES_JSON": json.dumps(articles, ensure_ascii=False),
                "SPECIALS_JSON": json.dumps(specials, ensure_ascii=False),
                "MENU_ITEMS_JSON": json.dumps(self.config.get('floating_menu', []), ensure_ascii=False),
                "SPECIAL_TAGS": self.config.get('special_tags', ''),
            }
            
            rendered = tmpl.render(**context)
            
            index_path = os.path.join(DOCS_DIR, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(rendered)
            
            print(f"首页已生成: {index_path}")
            print(f"首页大小: {len(rendered)} 字节")
            
        except Exception as e:
            print(f"首页生成失败: {e}")
            import traceback
            traceback.print_exc()

def main():
    print("=" * 50)
    print("VaLog Generator 启动")
    print(f"工作目录: {os.getcwd()}")
    print(f"Python版本: {os.sys.version}")
    print("=" * 50)
    
    try:
        generator = VaLogGenerator()
        generator.run()
        print("=" * 50)
        print("VaLog Generator 完成")
        print("=" * 50)
    except Exception as e:
        print(f"生成器运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1  # 返回错误代码
    
    return 0  # 成功

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)