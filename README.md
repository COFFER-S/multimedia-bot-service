# GitLab Backport Bot Service

一个基于 Webhook 的 GitLab Backport 自动化服务。

## 功能

- 接收 GitLab Webhook 指令
- 自动执行 Cherry-pick 操作
- 创建 Backport Merge Request
- 处理冲突和失败情况

## 快速开始

### 使用 Docker

```bash
# 构建镜像
docker build -t gitlab-backport-bot .

# 运行容器
docker run -d \
  -p 8080:8080 \
  -e GITLAB_TOKEN=your_token \
  -e GITLAB_URL=https://gitlab.example.com \
  --name backport-bot \
  gitlab-backport-bot
```

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行服务
python app/main.py
```

## 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `GITLAB_TOKEN` | GitLab 访问令牌 | 必需 |
| `GITLAB_URL` | GitLab 实例 URL | https://gitlab.espressif.cn:6688 |
| `WEBHOOK_SECRET` | Webhook 签名密钥 | 可选 |
| `PORT` | 服务端口 | 8080 |
| `LOG_LEVEL` | 日志级别 | INFO |

## API 端点

### Webhook 接收

```http
POST /webhook/gitlab
Content-Type: application/json
X-Gitlab-Event: Merge Request Hook
X-Gitlab-Token: your_webhook_secret

{
  "object_kind": "merge_request",
  "event_type": "merge_request",
  "project": {
    "path_with_namespace": "adf/multimedia/esp-gmf"
  },
  "object_attributes": {
    "source_branch": "feature/awesome-feature",
    "target_branch": "main",
    "action": "merge",
    "labels": ["backport-to-v1.0"]
  }
}
```

### 手动触发 Backport

```http
POST /api/backport
Content-Type: application/json
Authorization: Bearer your_api_token

{
  "project_path": "adf/multimedia/esp-gmf",
  "source_branch": "feature/awesome-feature",
  "target_branch": "release/v1.0",
  "continue_on_conflict": true
}
```

## 目录结构

```
multimedia-bot-service/
├── app/                      # 主应用代码
│   ├── __init__.py
│   ├── main.py              # 服务入口
│   ├── config.py            # 配置管理
│   ├── api/                 # API 路由
│   │   ├── __init__.py
│   │   ├── webhook.py       # Webhook 处理
│   │   └── backport.py      # Backport API
│   ├── services/            # 业务逻辑
│   │   ├── __init__.py
│   │   ├── gitlab_service.py    # GitLab 交互
│   │   ├── backport_service.py  # Backport 逻辑
│   │   └── webhook_service.py   # Webhook 处理
│   └── utils/               # 工具函数
│       ├── __init__.py
│       ├── logger.py        # 日志配置
│       └── helpers.py       # 辅助函数
├── scripts/                 # 独立脚本
│   └── backport_mr.py       # 参考脚本
├── tests/                   # 测试代码
│   ├── __init__.py
│   ├── test_webhook.py
│   └── test_backport.py
├── Dockerfile               # Docker 镜像
├── docker-compose.yml       # Docker Compose 配置
├── requirements.txt         # Python 依赖
├── .env.example             # 环境变量示例
├── .gitignore
└── README.md                # 项目说明
```

## License

MIT License
