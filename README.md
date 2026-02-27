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

## 部署指南

### 1. 服务器部署

#### 使用 Docker 部署

```bash
# 1. 克隆代码到服务器
git clone https://github.com/COFFER-S/multimedia-bot-service.git
cd multimedia-bot-service

# 2. 创建环境变量文件
cat > .env << 'EOF'
GITLAB_TOKEN=your_gitlab_token_here
GITLAB_URL=https://gitlab.espressif.cn:6688
WEBHOOK_SECRET=your_webhook_secret_here
PORT=8080
LOG_LEVEL=INFO
EOF

# 3. 构建并运行
docker build -t gitlab-backport-bot .
docker run -d \
  --name backport-bot \
  --restart unless-stopped \
  -p 8080:8080 \
  --env-file .env \
  gitlab-backport-bot

# 4. 查看日志
docker logs -f backport-bot
```

#### 使用 Docker Compose 部署

```bash
# 1. 克隆代码
git clone https://github.com/COFFER-S/multimedia-bot-service.git
cd multimedia-bot-service

# 2. 编辑 docker-compose.yml (已预配置好)
# 3. 编辑 .env 文件设置环境变量

# 4. 启动服务
docker-compose up -d

# 5. 查看日志
docker-compose logs -f
```

#### 使用 systemd 部署 (裸机部署)

```bash
# 1. 安装依赖
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

# 2. 创建用户
sudo useradd -r -s /bin/false backport-bot

# 3. 克隆代码
sudo mkdir -p /opt/backport-bot
sudo chown backport-bot:backport-bot /opt/backport-bot
cd /opt/backport-bot
git clone https://github.com/COFFER-S/multimedia-bot-service.git .

# 4. 创建虚拟环境
sudo -u backport-bot python3 -m venv venv
sudo -u backport-bot ./venv/bin/pip install -r requirements.txt

# 5. 创建环境变量文件
sudo -u backport-bot tee /opt/backport-bot/.env << 'EOF'
GITLAB_TOKEN=your_gitlab_token_here
GITLAB_URL=https://gitlab.espressif.cn:6688
WEBHOOK_SECRET=your_webhook_secret_here
PORT=8080
LOG_LEVEL=INFO
EOF

# 6. 创建 systemd 服务
sudo tee /etc/systemd/system/backport-bot.service << 'EOF'
[Unit]
Description=GitLab Backport Bot Service
After=network.target

[Service]
Type=simple
User=backport-bot
Group=backport-bot
WorkingDirectory=/opt/backport-bot
Environment=PATH=/opt/backport-bot/venv/bin
EnvironmentFile=/opt/backport-bot/.env
ExecStart=/opt/backport-bot/venv/bin/python -m app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 7. 启动服务
sudo systemctl daemon-reload
sudo systemctl enable backport-bot
sudo systemctl start backport-bot

# 8. 查看状态
sudo systemctl status backport-bot
sudo journalctl -u backport-bot -f
```

### 2. 内网穿透

如果你的服务器没有公网 IP，可以使用以下内网穿透方案：

#### 方案一：frp (推荐用于生产)

frp 是一个高性能的内网穿透工具。

**服务器端 (有公网 IP) 配置：**

```bash
# 1. 下载 frp
wget https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_amd64.tar.gz
tar -xzf frp_0.52.3_linux_amd64.tar.gz
cd frp_0.52.3_linux_amd64

# 2. 配置 frps.toml
cat > frps.toml << 'EOF'
bindPort = 7000
auth.method = "token"
auth.token = "your_secure_token_here"

# Dashboard (optional)
webServer.addr = "0.0.0.0"
webServer.port = 7500
webServer.user = "admin"
webServer.password = "your_dashboard_password"
EOF

# 3. 启动服务
./frps -c frps.toml

# 或使用 systemd
sudo tee /etc/systemd/system/frps.service << 'EOF'
[Unit]
Description=FRP Server
After=network.target

[Service]
Type=simple
ExecStart=/opt/frp/frps -c /opt/frp/frps.toml
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

**客户端 (内网服务器) 配置：**

```bash
# 1. 下载 frp
wget https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_amd64.tar.gz
tar -xzf frp_0.52.3_linux_amd64.tar.gz
cd frp_0.52.3_linux_amd64

# 2. 配置 frpc.toml
cat > frpc.toml << 'EOF'
serverAddr = "your_public_server_ip"
serverPort = 7000
auth.method = "token"
auth.token = "your_secure_token_here"

[[proxies]]
name = "backport-bot"
type = "http"
localIP = "127.0.0.1"
localPort = 8080
customDomains = ["backport.yourdomain.com"]

# 如果使用 HTTP Basic Auth
# httpUser = "admin"
# httpPassword = "your_password"
EOF

# 3. 启动客户端
./frpc -c frpc.toml

# 或使用 systemd
sudo tee /etc/systemd/system/frpc.service << 'EOF'
[Unit]
Description=FRP Client
After=network.target

[Service]
Type=simple
ExecStart=/opt/frp/frpc -c /opt/frp/frpc.toml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

#### 方案二：Cloudflare Tunnel (推荐用于快速测试)

Cloudflare Tunnel 提供免费的内网穿透服务。

```bash
# 1. 安装 cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared

# 2. 登录并授权
cloudflared tunnel login
# 这会打开浏览器，让你选择 Cloudflare 账户和域名

# 3. 创建 tunnel
cloudflared tunnel create backport-bot
# 记录输出的 tunnel ID

# 4. 配置 tunnel
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: <your-tunnel-id>
credentials-file: /root/.cloudflared/<your-tunnel-id>.json

ingress:
  - hostname: backport.yourdomain.com
    service: http://localhost:8080
    originRequest:
      noTLSVerify: true
  - service: http_status:404
EOF

# 5. 运行 tunnel
cloudflared tunnel run backport-bot

# 或使用 systemd
sudo cloudflared service install
sudo systemctl start cloudflared
```

#### 方案三：Ngrok (适合快速测试)

Ngrok 是最简单的内网穿透方案，适合快速测试。

```bash
# 1. 下载 ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# 2. 注册并获取 authtoken (https://ngrok.com)
ngrok config add-authtoken YOUR_AUTHTOKEN

# 3. 启动隧道
ngrok http 8080

# 输出示例：
# Forwarding  https://xxxx.ngrok-free.app -> http://localhost:8080
```

然后配置 GitLab Webhook URL 为 `https://xxxx.ngrok-free.app/webhook/gitlab`

**注意事项：**
- 免费版 Ngrok 每次重启 URL 会变
- 适合测试，不建议用于生产环境

### 3. 功能验证

#### 3.1 验证服务是否正常运行

```bash
# 1. 检查健康状态
curl http://localhost:8080/health

# 期望输出：
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z"
}

# 2. 检查就绪状态
curl http://localhost:8080/health/ready

# 3. 完整健康检查
curl http://localhost:8080/health/live
```

#### 3.2 验证 Webhook 接收

使用 curl 测试 Webhook：

```bash
# 测试 Merge Request Hook
curl -X POST http://localhost:8080/webhook/gitlab \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Event: Merge Request Hook" \
  -d '{
    "object_kind": "merge_request",
    "event_type": "merge_request",
    "project": {
      "id": 1,
      "name": "Test Project",
      "path_with_namespace": "test/project"
    },
    "object_attributes": {
      "id": 1,
      "iid": 1,
      "source_branch": "feature/test",
      "target_branch": "main",
      "action": "merge",
      "labels": [{ "title": "backport-to-v1.0" }],
      "author_id": 1
    }
  }'
```

#### 3.3 验证手动 Backport API

```bash
# 测试手动触发 backport
curl -X POST http://localhost:8080/api/backport \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_token" \
  -d '{
    "project_path": "adf/multimedia/esp-gmf",
    "source_branch": "feature/test-feature",
    "target_branch": "release/v1.0",
    "continue_on_conflict": true
  }'
```

#### 3.4 在 GitLab 中配置 Webhook

1. 进入项目设置 → Webhooks
2. 配置以下参数：
   - **URL**: `https://your-public-url/webhook/gitlab`
   - **Secret Token**: 你设置的 `WEBHOOK_SECRET`
   - **Trigger**: 勾选 "Merge request events"
   - **SSL Verification**: 根据你的证书情况选择
3. 点击 "Add webhook"
4. 点击 "Test" → "Merge request events" 测试 Webhook

#### 3.5 完整的端到端测试

创建一个测试 MR 并验证 Backport 流程：

```bash
# 1. 创建测试分支
git checkout -b feature/backport-test

# 2. 做一些修改并提交
echo "# Test" >> README.md
git add README.md
git commit -m "test: Add backport test"

# 3. 推送到 GitLab
git push origin feature/backport-test

# 4. 在 GitLab 中创建 MR
# - Source: feature/backport-test
# - Target: main
# - Label: backport-to-v1.0

# 5. 合并 MR 后，观察 Webhook 是否触发
# 6. 检查 GitLab 上是否创建了新的 Backport MR
```

#### 3.6 常见问题排查

**问题1: Webhook 返回 401 Unauthorized**

```bash
# 检查 Webhook Secret 是否匹配
curl -X POST http://localhost:8080/webhook/gitlab \
  -H "X-Gitlab-Token: your_webhook_secret" \
  -d '{}'
```

**问题2: 服务无法访问**

```bash
# 检查防火墙
sudo ufw status
sudo ufw allow 8080

# 检查服务监听地址
curl http://localhost:8080/health

# 从外部测试
curl http://your-server-ip:8080/health
```

**问题3: GitLab API 访问失败**

```bash
# 测试 GitLab Token 是否有效
curl -H "PRIVATE-TOKEN: your_token" \
  https://gitlab.espressif.cn:6688/api/v4/user

# 检查网络连接
curl -v https://gitlab.espressif.cn:6688
```

**问题4: 内网穿透后 Webhook 不触发**

```bash
# 检查隧道是否正常运行
curl http://your-tunnel-url/health

# 检查 GitLab Webhook 日志 (GitLab Admin 面板)
# 查看 delivery 失败原因

# 测试从外部访问 Webhook
curl -X POST https://your-tunnel-url/webhook/gitlab \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: your_secret" \
  -d '{"test": true}'
```

### 4. 生产环境建议

#### 使用 Nginx 反向代理 (HTTPS)

```nginx
# /etc/nginx/sites-available/backport-bot
server {
    listen 80;
    server_name backport.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name backport.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/backport-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 使用 Let's Encrypt 获取免费 SSL 证书

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d backport.yourdomain.com

# 自动续期测试
sudo certbot renew --dry-run
```

#### 监控和日志

```bash
# 使用 journalctl 查看日志
sudo journalctl -u backport-bot -f

# 设置日志轮转
sudo tee /etc/logrotate.d/backport-bot << 'EOF'
/var/log/backport-bot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 backport-bot backport-bot
}
EOF
```

## License

MIT License
