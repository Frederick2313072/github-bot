# GitHub-飞书机器人

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-username/github-bot)

基于 Serverless 云函数的 GitHub-飞书机器人，实现 GitHub 事件自动推送到飞书群聊。

## 🚀 项目概述

本项目使用 Vercel + Python Flask 搭建中间服务，作为 GitHub 和飞书之间的桥梁：

```
GitHub Events → Vercel 云函数 → 飞书群聊
```

**核心功能**：接收 GitHub 的数据 → 翻译成飞书的格式 → 发送给飞书机器人

## ✨ 功能特性

### 支持的事件类型
- 🔄 **Push 事件** - 代码推送通知，显示分支、提交详情、变更链接
- 🐛 **Issues 事件** - Issue 创建/关闭/修改，显示标题、状态、描述
- 🔀 **Pull Request 事件** - PR 创建/合并/关闭，显示分支信息和描述
- 🎉 **Release 事件** - 版本发布通知，显示版本号和发布说明

### 消息特性
- 📱 **精美卡片格式** - 飞书原生卡片消息，支持宽屏显示
- 🎨 **智能颜色主题** - 不同事件类型使用不同颜色
- 🔗 **操作按钮** - 直接跳转到 GitHub 查看详情
- 🔒 **安全验证** - 支持 GitHub 和飞书的双重签名验证

## 💡 为什么选择云函数？

- **无需管理服务器**：只需上传代码，平台自动运行和扩展
- **按需付费，成本极低**：代码仅在事件推送时运行，个人使用几乎零成本
- **部署快速简单**：与 GitHub 仓库关联，git push 即可部署

## 📁 项目结构

```
GitHub-bot/
├── api/
│   └── index.py          # 核心云函数文件
├── requirements.txt      # Python 依赖
├── vercel.json          # Vercel 配置
├── env.example          # 环境变量模板
├── 部署指南.md           # 详细部署说明
├── README.md            # 项目说明
└── .gitignore           # Git 忽略文件
```

## 🚀 快速开始

### 1. 准备工作

- GitHub 账号
- Vercel 账号（用 GitHub 账号注册）
- 飞书群聊管理权限

### 2. 一键部署

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-username/github-bot)

或者手动部署：

1. **Fork 本项目**到你的 GitHub
2. **在 Vercel 中导入项目**
3. **配置环境变量**（至少需要 `FEISHU_WEBHOOK_URL`）
4. **部署完成**，获取 Vercel URL

### 3. 创建飞书机器人

1. 在飞书群中添加"自定义机器人"
2. 复制生成的 Webhook URL
3. （可选）开启"签名校验"增强安全性

### 4. 配置 GitHub Webhook

1. 进入要监控的仓库 Settings → Webhooks
2. 添加 Webhook，Payload URL 填入你的 Vercel URL
3. Content type 选择 `application/json`
4. 选择需要的事件类型
5. （可选）设置 Secret 增强安全性

## 🔧 环境变量配置

| 变量名 | 必填 | 说明 | 示例值 |
|--------|------|------|--------|
| `FEISHU_WEBHOOK_URL` | ✅ | 飞书机器人 Webhook URL | `https://open.feishu.cn/open-apis/bot/v2/hook/xxx` |
| `GITHUB_SECRET` | ❌ | GitHub Webhook 签名密钥 | `your_github_secret` |
| `FEISHU_SECRET` | ❌ | 飞书机器人签名密钥 | `your_feishu_secret` |

## 📱 消息效果预览

### Push 事件
```
🚀 [用户名/仓库名] 代码推送
分支: main
推送人: 张三
提交数量: 2

提交详情:
- a1b2c3d: 修复登录bug - 张三
- e4f5g6h: 添加新功能 - 李四

[查看变更] [访问仓库]
```

### Issues 事件
```
🐛 [用户名/仓库名] Issue 创建
标题: 登录页面显示异常
操作人: 张三
Issue #: 123

描述: 在某些浏览器中登录页面样式显示异常...

[查看 Issue]
```

## 🛠 本地开发

```bash
# 克隆项目
git clone https://github.com/your-username/github-bot.git
cd github-bot

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp env.example .env
# 编辑 .env 文件，填入你的配置

# 启动服务
python api/index.py
```

## 📚 详细文档

- [部署指南.md](./部署指南.md) - 完整的部署步骤和配置说明
- [env.example](./env.example) - 环境变量配置模板

## 🔒 安全特性

- **双重签名验证**：支持 GitHub 和飞书的签名验证
- **环境变量管理**：敏感信息通过环境变量安全存储
- **错误处理**：完善的异常处理和日志记录
- **健康检查**：提供状态检查接口便于监控

## 🚀 技术栈

- **后端**：Python + Flask
- **部署**：Vercel Serverless Functions
- **集成**：GitHub Webhooks + 飞书自定义机器人
- **安全**：HMAC 签名验证

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## ⭐ 支持项目

如果这个项目对你有帮助，请给它一个星标 ⭐

## 📞 联系方式

如有问题或建议，欢迎：
- 提交 [Issue](https://github.com/your-username/github-bot/issues)
- 发起 [Discussion](https://github.com/your-username/github-bot/discussions)
