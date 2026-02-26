# GitLab Backport Bot Service - Project Structure

## 目录结构

```
multimedia-bot-service/
├── app/                              # 主应用代码
│   ├── __init__.py                   # 应用包初始化
│   ├── main.py                       # FastAPI 服务入口
│   ├── config.py                     # 配置管理
│   ├── api/                          # API 路由
│   │   ├── __init__.py
│   │   ├── health.py                 # 健康检查端点
│   │   ├── webhook.py                # GitLab Webhook 处理
│   │   └── backport.py               # Backport API 端点
│   ├── services/                     # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── gitlab_service.py         # GitLab API 封装
│   │   ├── backport_service.py       # Backport 核心逻辑
│   │   └── webhook_service.py        # Webhook 事件处理
│   └── utils/                        # 工具函数
│       ├── __init__.py
│       ├── logger.py                 # 结构化日志配置
│       └── helpers.py                # 辅助函数
├── scripts/                          # 独立脚本
│   ├── __init__.py
│   └── backport_mr.py                # 参考脚本（命令行版）
├── tests/                            # 测试代码
│   ├── __init__.py
│   ├── test_webhook.py               # Webhook 测试
│   └── test_backport.py              # Backport 测试
├── Dockerfile                        # Docker 镜像构建
├── docker-compose.yml                # Docker Compose 配置
├── requirements.txt                  # Python 依赖
├── .env.example                      # 环境变量示例
├── .gitignore                        # Git 忽略文件
├── README.md                         # 项目说明
└── PROJECT_STRUCTURE.md              # 项目结构说明（本文件）
```

## 核心功能模块

### 1. API 层 (`app/api/`)

| 文件 | 功能 | 端点 |
|------|------|------|
| `health.py` | 健康检查 | `/health/`, `/health/ready`, `/health/live` |
| `webhook.py` | GitLab Webhook 接收 | `/webhook/gitlab` |
| `backport.py` | 手动触发 Backport | `/api/backport` |

### 2. 服务层 (`app/services/`)

| 文件 | 功能 |
|------|------|
| `gitlab_service.py` | GitLab API 封装（项目、MR、分支、cherry-pick） |
| `backport_service.py` | Backport 核心逻辑（执行 cherry-pick、创建 MR） |
| `webhook_service.py` | Webhook 事件处理（MR、Push、Pipeline） |

### 3. 工具层 (`app/utils/`)

| 文件 | 功能 |
|------|------|
| `logger.py` | 结构化日志配置（structlog） |
| `helpers.py` | 辅助函数（签名验证、分支名清理等） |

## 数据流

```
GitLab Webhook → /webhook/gitlab → WebhookService
                                        ↓
                              BackportService
                                        ↓
                            GitLabService (API调用)
                                        ↓
                              创建分支 + Cherry-pick + 创建MR
```

## 配置

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `GITLAB_TOKEN` | GitLab 访问令牌 | 必需 |
| `GITLAB_URL` | GitLab 实例 URL | https://gitlab.espressif.cn:6688 |
| `WEBHOOK_SECRET` | Webhook 签名密钥 | 可选 |
| `PORT` | 服务端口 | 8080 |
| `LOG_LEVEL` | 日志级别 | INFO |

## 部署

### Docker

```bash
# 构建镜像
docker build -t gitlab-backport-bot .

# 运行容器
docker run -d \
  -p 8080:8080 \
  -e GITLAB_TOKEN=your_token \
  gitlab-backport-bot
```

### Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 开发

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export GITLAB_TOKEN=your_token

# 运行服务
python -m app.main
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_webhook.py
```

## 许可证

MIT License
