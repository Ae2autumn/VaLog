# VaLog 博客系统

📝 项目简介

VaLog 是一个基于 GitHub Issues 的现代化静态博客生成系统。它利用 GitHub 的生态，将 Issues 自动转换为美观的博客网站，并部署到 GitHub Pages。无需数据库，无需服务器，只需一个 GitHub 账户即可拥有功能完整的个人博客。

✨ 核心特性

🚀 极简部署

· 零服务器成本：完全运行在 GitHub 生态系统
· 一键部署：配置完成后，发布文章只需创建 GitHub Issue
· 自动更新：通过 GitHub Actions 自动构建和部署

📱 现代化设计

· 响应式布局：完美适配桌面、平板和手机
· 暗黑/明亮双主题：支持主题切换，护眼舒适
· 渐变色彩系统：自动为每篇文章生成独特渐变背景
· 流畅动画：精心设计的交互动效

🔧 强大功能

· 客户端搜索：无需后端服务，直接在浏览器中搜索文章
· 智能摘要：自动从文章中提取摘要内容
· 标签系统：完善的分类和标签管理
· 特殊卡片：支持置顶文章和自定义展示卡片
· 浮动菜单：可自定义的快捷导航菜单

🏗️ 系统架构

```
GitHub Issues (数据源)
        ↓
GitHub Actions (自动构建)
        ↓
VaLog.py (生成引擎)
        ↓
静态HTML文件
        ↓
GitHub Pages (部署)
```

📂 项目结构

```
├── .github/workflows/    # GitHub Actions 工作流
├── docs/                 # 生成的网站文件（GitHub Pages）
├── template/             # HTML 模板文件
├── static/               # 静态资源文件
├── O-MD/                 # 原始 Markdown 缓存
├── config.yml            # 用户配置文件
├── base.yaml             # 自动生成的数据文件
├── VaLog.py              # 主生成脚本
└── requirements.txt      # Python 依赖
```

⚙️ 快速开始

1. 创建仓库

1. Fork 或创建新的 GitHub 仓库
2. 启用 GitHub Pages（设置 → Pages → Source: gh-pages branch）

2. 基础配置

1. 复制 config.yml 到仓库根目录
2. 修改配置文件中的个人信息：

```yaml
blog:
  avatar: "static/avatar.png"
  name: "你的博客名称"
  description: "博客描述"
  favicon: "static/favicon.ico"
```

3. 添加模板文件

将 template/ 目录和模板文件复制到仓库中：

· home.html - 主页模板
· article.html - 文章页模板

4. 设置工作流

将 .github/workflows/VaLog.yml 复制到仓库，系统会自动运行。

5. 开始写作

1. 在 Issues 中创建新 Issue
2. 使用 Markdown 格式编写内容
3. 添加标签进行分类
4. 提交 Issue，系统自动构建网站

🎨 高级配置

主题自定义

```yaml
theme:
  mode: "dark"            # dark 或 light
  primary_color: "#e74c3c" # 主题主色调
  dark_bg: "#121212"      # 暗色背景
  light_bg: "#f5f7fa"     # 亮色背景
```

浮动菜单

```yaml
floating_menu:
  - tag: "about"
    display: "关于"
  - tag: "project"
    display: "项目"
```

Special 卡片

· 显示置顶文章或特殊内容
· 支持仅文本模式显示备案信息等

📝 写作指南

基础格式

· 标题：Issue 标题作为文章标题
· 标签：使用 Issue Labels 作为文章标签
· 内容：使用标准的 GitHub Flavored Markdown

特殊语法

```markdown
!vml-<span>这是文章的摘要，会显示在卡片中</span>

这里是文章的正文内容...

## 二级标题

- 列表项
- 另一个列表项

`代码片段`

![图片描述](图片链接)
```

摘要提取

· 系统会自动提取第一个 !vml-<span> 中的内容作为摘要
· 如果没有找到，摘要区域将不会显示

🔍 搜索功能

· 内嵌客户端搜索，无需额外配置
· 支持标题、标签、内容全文搜索
· 实时显示搜索结果

📱 移动端优化

· 完全响应式设计
· 触摸友好的交互元素
· 移动端专属的导航菜单

🛠️ 开发者说明

本地开发

1. 安装依赖：

```bash
pip install -r requirements.txt
```

1. 配置环境变量：

```bash
export GITHUB_TOKEN=your_token
export GITHUB_REPO=username/repo
```

1. 运行生成器：

```bash
python VaLog.py
```

自定义扩展

· 模板修改：编辑 template/ 中的 HTML 文件,或者使用提供的额外模板

API 集成

· 使用 GitHub REST API 获取 Issues 数据
· 支持 GitHub App 或 Personal Access Token 认证

🚨 注意事项

1. GitHub API 限制：注意 API 请求频率限制
2. 文件路径：所有链接路径基于 docs/ 目录
3. 缓存机制：系统会缓存 Markdown 文件，避免重复处理
4. 特殊字符：避免在 Issue 标题中使用特殊字符

🔄 更新与维护

自动更新

· 每次 Issue 创建、修改或标签变更都会触发自动构建
· 支持手动触发工作流

数据备份

· 原始 Markdown 文件保存在 O-MD/ 目录
· 文章状态记录在 articles.json

📄 许可证

本项目采用 MIT 许可证 - 详见 LICENSE 文件。

🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来改进项目：

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

📞 支持与反馈

· 问题反馈：GitHub Issues
· 功能建议：通过 Issues 提交
· 文档改进：欢迎提交 Pull Request

🌟 致谢

感谢所有为项目做出贡献的开发者，以及使用 VaLog 的博主们！

---

开始你的博客之旅吧！只需一个 GitHub 账户，即可拥有专业的个人博客系统。

✨ VaLog - Write with Issues, Publish with Pages ✨