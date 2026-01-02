# VaLog 博客系统

基于 GitHub Issues 的静态博客生成系统，自动生成响应式博客网站，部署到 GitHub Pages。

## 特性

- 🚀 基于 GitHub Issues 管理内容
- 📱 响应式移动端设计
- 🎨 自定义主题颜色
- 🔍 内置客户端搜索
- 📁 自动生成静态页面
- 🔄 自动同步更新
- 🎯 Special卡片系统
- 🌓 深色/浅色主题

## 快速开始

### 1. 创建仓库
1. Fork 或创建新的 GitHub 仓库
2. 确保仓库为公开仓库

### 2. 配置仓库
1. 在仓库设置中启用 GitHub Pages
2. 选择 `gh-pages` 分支作为发布源
3. 添加 `GITHUB_TOKEN` 权限（默认已存在）

### 3. 添加配置文件
将提供的 `config.yml` 文件放入仓库根目录，并根据需要修改配置。

### 4. 添加模板文件
创建 `template/` 目录，并添加以下文件：
- `home.html` - 主页模板
- `article.html` - 文章页模板

### 5. 添加静态资源
创建 `static/` 目录，添加以下文件：
- `avatar.png` - 博客头像
- `favicon.ico` - 网站图标
- `custom/custom.css` - 自定义样式（可选）
- `custom/custom.js` - 自定义脚本（可选）

### 6. 创建文章
在 GitHub Issues 中创建新的 Issue：
- 标题：文章标题
- 内容：使用 Markdown 编写文章内容
- 标签：添加文章标签（如：技术、教程、随笔等）

### 7. 触发生成
系统会在以下情况自动生成博客：
- 推送代码到 main 分支
- 创建、编辑、关闭、重新开启、添加标签、移除标签 Issue
- 每6小时自动运行
- 手动触发工作流

## 配置文件说明

### config.yml
主配置文件，包含博客基本信息、菜单配置、主题设置等。

### base.yaml
自动生成的数据文件，包含文章数据、菜单项等，不应手动修改。

## 目录结构
```txt
.github/workflows/
└── VaLog.yml                   # GitHub Actions工作流

config.yml                     # 用户配置文件
base.yaml                      # 内部数据文件（自动生成）
VaLog.py                       # 主生成脚本（单文件）
requirements.txt               # Python依赖

template/                      # HTML模板
├── home.html                  # 主页模板（完整代码）
└── article.html               # 文章页模板（完整代码）

docs/                          # 生成目录（GitHub Pages）
├── index.html                 # 主页（生成）
├── article/                   # 文章目录
└── favicon.ico

O-MD/                          # 原始Markdown缓存
└── articles.json              # 文章状态记录

static/                        # 静态资源
├── avatar.png                # 头像
├── favicon.ico               # 图标
└── custom/                   # 用户自定义
      ├── custom.css
      └── custom.js

README.md                      # 项目说明
LICENSE                        # 许可证
.gitignore                     # Git忽略
```
