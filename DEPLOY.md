# 🚀 部署到云端 - 完整步骤指南

让 QQQ 看板**完全免费、永久在线**，手机也能随时打开。

---

## 总体架构

```
┌─────────────────────────────────────────┐
│  您的 GitHub 仓库                         │
│  ├─ frontend/  (HTML/CSS/JS)             │
│  ├─ backend/   (Python 脚本)              │
│  ├─ data/      (自动生成的 JSON)          │
│  └─ .github/workflows/                   │
│      ├─ update-data.yml   每15分钟运行    │
│      └─ deploy-pages.yml  自动部署        │
└──────────┬──────────────────────────────┘
           │
           ├── GitHub Actions 自动跑 Python
           │      ├─ 拉数据 / 算评分
           │      ├─ 检测预警
           │      └─ 发邮件/Telegram 通知
           │
           └── GitHub Pages 自动部署看板
                  └─ https://YOUR_NAME.github.io/qqq-monitor
                       ↑ 手机/电脑随时打开
```

**总成本: 0 元** (GitHub 个人账户对公开仓库免费提供这些服务)

---

## 第 1 步: 准备 GitHub 仓库

### 1.1 注册 GitHub (已有可跳过)

打开 <https://github.com>，免费注册账号。

### 1.2 创建新仓库

1. 点击右上角 `+` → `New repository`
2. **Repository name**: `qqq-monitor` (或您喜欢的名字)
3. **Public** ✅ (公开 - 才能用 GitHub Pages 免费托管)
4. **不要** 勾选 "Add a README file"
5. 点击 `Create repository`

### 1.3 把代码推上去

在您本地解压的 `qqq_dashboard/` 目录里：

```bash
cd qqq_dashboard

git init
git add .
git commit -m "Initial: QQQ monitor MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/qqq-monitor.git
git push -u origin main
```

> **首次 push 提示输入密码**?
> 用 [Personal Access Token](https://github.com/settings/tokens) 替代密码:
> Settings → Developer settings → Personal access tokens → Tokens (classic)
> → Generate new token → 勾选 `repo` 权限 → 复制 token 当密码用

---

## 第 2 步: 开启 GitHub Pages

1. 仓库主页 → `Settings` → 左侧 `Pages`
2. **Source**: 选 `GitHub Actions` (重要! 不选 Deploy from a branch)
3. 保存

接下来等待几分钟，GitHub Actions 会自动构建并部署。
完成后访问: `https://YOUR_USERNAME.github.io/qqq-monitor/`

---

## 第 3 步: 配置通知 (可选但强烈推荐)

仓库 → `Settings` → 左侧 `Secrets and variables` → `Actions` → `New repository secret`

### 选项 A: 邮件通知 (推荐用 Gmail)

需要先去 [Google 账户](https://myaccount.google.com/security) 开启两步验证, 然后在 ["应用专用密码"](https://myaccount.google.com/apppasswords) 生成一个 16 位密码 (普通密码不能用)。

添加这些 secret:

| Secret 名称 | 值 | 示例 |
|-------------|-----|------|
| `SMTP_HOST` | SMTP 服务器 | `smtp.gmail.com` |
| `SMTP_PORT` | 端口 | `587` |
| `SMTP_USER` | 你的邮箱 | `you@gmail.com` |
| `SMTP_PASS` | 应用专用密码 | `abcd efgh ijkl mnop` |
| `ALERT_EMAIL` | 接收邮件的地址 | `you@gmail.com` |

**其他邮箱配置参考:**

| 邮箱 | SMTP_HOST | SMTP_PORT |
|------|-----------|-----------|
| Gmail | smtp.gmail.com | 587 |
| Outlook | smtp.office365.com | 587 |
| QQ 邮箱 | smtp.qq.com | 587 |
| 163 邮箱 | smtp.163.com | 465 |
| iCloud | smtp.mail.me.com | 587 |

### 选项 B: Telegram (推荐 - 最快最免费)

1. 打开 Telegram, 找 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` → 起个名字 → 拿到 token (形如 `123456:ABC-DEF...`)
3. 给自己发条消息给这个 bot, 然后访问:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   找到 `"chat":{"id":1234567}` 这个数字

添加 secret:

| Secret 名称 | 值 |
|-------------|-----|
| `TELEGRAM_BOT_TOKEN` | `123456:ABC-DEF...` |
| `TELEGRAM_CHAT_ID` | `1234567` |

### 选项 C: 企业微信 (国内推荐)

1. 企业微信群里 → 添加群机器人 → 复制 webhook URL
2. URL 形如 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx`

| Secret 名称 | 值 |
|-------------|-----|
| `WECOM_WEBHOOK_URL` | 完整的 webhook URL |

### 选项 D: Discord / Slack

| Secret 名称 | 值 |
|-------------|-----|
| `DISCORD_WEBHOOK_URL` | 服务器设置 → 整合 → Webhook → 复制 URL |
| `SLACK_WEBHOOK_URL` | Slack App → Incoming Webhook → URL |

### 选项 E: FRED 宏观数据 (可选)

去 <https://fred.stlouisfed.org/docs/api/api_key.html> 免费申请:

| Secret 名称 | 值 |
|-------------|-----|
| `FRED_API_KEY` | 32 位 key |

---

## 第 4 步: 启用 Actions 并首次运行

1. 仓库主页 → `Actions` 标签
2. 第一次进入会提示 "Workflows aren't being run on this forked repository"
   点击 `I understand my workflows, go ahead and enable them`
3. 左侧选 `📊 Update Dashboard Data`
4. 点击 `Run workflow` → `Run workflow` (绿色按钮) **手动触发一次**

等待 1-2 分钟, 应该看到绿色对勾。
如果失败, 点进去看日志, 大概率是某个 secret 没配置。

---

## 第 5 步: 验证

### 看板访问

`https://YOUR_USERNAME.github.io/qqq-monitor/`

### 手机加到主屏幕 (像 App 一样)

**iOS Safari**:
1. 打开看板链接
2. 点底部 `分享` 按钮
3. 选 `添加到主屏幕`

**Android Chrome**:
1. 打开看板链接
2. 右上角 `⋮` → `添加到主屏幕`

之后从主屏幕打开就是全屏 App, 无浏览器地址栏。

---

## 📅 调整刷新频率

默认配置 (`.github/workflows/update-data.yml`):

```yaml
schedule:
  - cron: '*/15 13-20 * * 1-5'   # 美股盘中 每15分钟
  - cron: '0,30 12,21 * * 1-5'   # 盘前盘后 每30分钟
  - cron: '0 22 * * 5'            # 周五收盘后总结
```

**调整建议:**

| 用法 | Cron |
|------|------|
| 每 5 分钟 (盘中) | `*/5 13-20 * * 1-5` |
| 每小时整点 | `0 13-20 * * 1-5` |
| 每天一次 | `0 21 * * 1-5` (盘后 21:00 UTC) |
| 每周一次 | `0 22 * * 5` (周五收盘) |

⚠️ **GitHub Actions 免费额度**: 公开仓库无限免费;私有仓库每月 2000 分钟。
按每 15 分钟跑 1 次、每次约 1 分钟算, 每月用量 ~700 分钟, 私有仓库也够用。

---

## 🔧 常见问题

### Q: Actions 失败提示 "Permission denied"

仓库 → Settings → Actions → General → 滚到底 `Workflow permissions`
选 ✅ `Read and write permissions` → 保存。

### Q: GitHub Pages 显示 404

确认 Settings → Pages 的 Source 选的是 **GitHub Actions** 不是 Deploy from a branch。
第一次部署需要等 2-5 分钟。

### Q: 看板能打开但数据是旧的

GitHub Pages 部署有 1-2 分钟延迟, CDN 缓存还会再延迟几分钟。强制刷新: `Ctrl+Shift+R` (Win) 或 `Cmd+Shift+R` (Mac)。

### Q: yfinance 拉数据失败

Yahoo Finance API 偶发性限流。一般几分钟后自动恢复, 不影响下一次 cron。

### Q: 不想公开代码

GitHub Pages 私有部署需要 GitHub Pro ($4/月)。
**变通方案**: 把仓库设为 Private, 用 [Cloudflare Pages](https://pages.cloudflare.com/) 部署 (永久免费且支持私有仓库)。

### Q: 想要更频繁的预警 (如 1 分钟检查一次)

GitHub Actions 最小间隔是 5 分钟。如果需要更高频, 建议:
1. 自己的 VPS (5 美元/月起)
2. Railway / Fly.io 免费层
3. 自己电脑跑 cron

---

## 🎯 进阶玩法

### 加新指标

编辑 `backend/fetch_data.py`, 在 `TICKERS` 字典加新代码:

```python
TICKERS = {
    # ...
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
}
```

然后编辑 `frontend/app.js` 的 `DISPLAY` 数组加显示项。

### 调整评分阈值

`backend/fetch_data.py` 顶部的 `THRESHOLDS` 字典。

### 加新预警触发器

`backend/check_alerts.py` 里仿照 `check_trigger_*` 函数添加新函数, 在 main() 的检测列表里注册。

### 数据用 CDN 加速

GitHub Pages 默认有 CDN, 但 data/dashboard.json 因为更新频繁不会被强缓存。
如果要进一步加速, 可以加 Cloudflare 在前面。

---

## 💎 你已经完成了!

现在您拥有了:
- ✅ 24x7 在云端跑的看板
- ✅ 每 15 分钟自动更新数据
- ✅ 关键时刻自动发预警到邮箱/手机
- ✅ 手机加到主屏幕像 App 一样用
- ✅ 全部代码版本控制
- ✅ 零持续成本

下一步可以考虑:
- 🔄 加历史回测验证策略
- 🤖 接入券商 API 实现半自动交易
- 📈 增加更多自定义指标
