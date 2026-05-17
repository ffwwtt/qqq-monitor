# QQQ 预警看板 v2 - 云端版

实战版 QQQ 涨跌预警分析系统。基于 4 层信号体系自动评分,关键时刻自动通知,免费云端部署。

## ✨ 功能

### 核心
- **4 层信号自动评分** - 价格 / 波动率 / 内部结构 / 宏观信用
- **综合分数 -12 ~ +12** - 映射到 6 档仓位建议
- **17 个关键指标实时拉取** - QQQ / VIX / VIX3M / MOVE / HYG / TLT / JNK / DXY / GLD 等
- **关键比率自动计算** - VIX/VIX3M, HYG/IEF, JNK/TLT, QQQ/QQEW
- **历史走势图** - QQQ 价格+均线, VIX 走势
- **FRED 宏观集成** - 期限利差、CPI、失业率等

### v2 新增 🆕
- **🔔 5 大触发器预警系统** - TQQQ 入场 / 第一道警报 / 确认转熊 / 抄底信号 / 滞胀避险
- **📧 多渠道通知** - 邮件 / Telegram / 企业微信 / Discord / Slack
- **☁️ GitHub Actions 自动跑** - 每 15 分钟自动更新数据并检查预警
- **🌐 GitHub Pages 一键部署** - 永久免费, 全球访问
- **📱 PWA 支持** - 加到手机主屏幕像 App 一样使用
- **🎯 智能去重** - 同一预警 6 小时内不重发, 避免轰炸

## 📁 目录结构

```
qqq_dashboard_v2/
├── backend/
│   ├── fetch_data.py          # 数据拉取 + 评分
│   ├── check_alerts.py        # 🆕 预警检测 + 多渠道通知
│   ├── generate_mock_data.py  # 测试用模拟数据
│   └── requirements.txt
├── frontend/
│   ├── index.html             # 看板页面
│   ├── style.css              # 金融终端风格
│   ├── app.js                 # 渲染逻辑
│   ├── manifest.json          # 🆕 PWA 配置
│   └── icon.svg               # 🆕 App 图标
├── data/
│   ├── dashboard.json         # 看板数据
│   └── alert_state.json       # 🆕 预警状态持久化
├── .github/workflows/
│   ├── update-data.yml        # 🆕 定时拉数据+发预警
│   └── deploy-pages.yml       # 🆕 自动部署看板
├── README.md                  # 本文档
└── DEPLOY.md                  # ⭐ 完整云端部署指南
```

## 🚀 两种使用方式

### 方式 A: 本地跑 (5 分钟上手)

```bash
cd backend
pip install -r requirements.txt

# 拉真实数据
python fetch_data.py YOUR_FRED_KEY  # FRED key 可选

# 测试预警引擎
python check_alerts.py

# 启动看板
cd ..
python -m http.server 8000
# 浏览器打开 http://localhost:8000/frontend/
```

### 方式 B: 部署到云端 (推荐, 永久免费) ⭐

详见 **[DEPLOY.md](DEPLOY.md)** - 完整步骤指南, 包括:
- GitHub 仓库设置 (5 分钟)
- GitHub Pages 配置 (3 分钟)
- 邮件 / Telegram / 企业微信 通知接入 (5 分钟)
- PWA 加到手机主屏幕 (1 分钟)

部署后效果:
- 看板地址: `https://YOUR_USERNAME.github.io/qqq-monitor/`
- 每 15 分钟自动更新
- 触发预警时邮件/Telegram 推送
- 完全 0 成本

## 📊 评分系统

| 综合分数 | 状态 | 仓位 |
|---------|------|------|
| ≥ +7 | 极度看多 | QQQ 70% + TQQQ 30% |
| +4 ~ +6 | 看多 | QQQ 80% + TQQQ 10% + 现金 10% |
| +1 ~ +3 | 偏多观察 | QQQ 60% + 现金 40% |
| -2 ~ 0 | 中性 | QQQ 40% + 现金 60% |
| -5 ~ -3 | 减仓防御 | QQQ 20% + 现金 60% + TLT 20% |
| ≤ -6 | 重度防御 | 现金 70% + SHY 20% + GLD 10% |

## 🔔 5 大预警触发器

| 触发器 | 触发条件 | 建议操作 |
|--------|----------|----------|
| 🚀 TQQQ 入场 | QQQ>200SMA + 金叉 + VIX<18 + contango + HYG强 | 建立 TQQQ 核心仓位 |
| ⚠️ 第一道警报 | VIX/VIX3M 快速上升 / MOVE>120 / QQQ vs QQEW 背离 | 减半 TQQQ + 买 put 保险 |
| 🔴 确认转熊 | 跌破 200SMA + 死叉 + VIX 倒挂 + HYG 走弱 | 清空 TQQQ, QQQ 降至 30% |
| 💰 抄底信号 | VIX 见顶回落 + backwardation hook + HYG 企稳 | 分 3 批建仓 QQQ |
| 🚨 滞胀避险 | JNK跌 + TLT 更跌 + MOVE>130 + DXY 急涨 | 完全清仓股票转避险 |

另外还有 **评分状态切换** 提醒 (如 "看多 → 中性")。

## 📱 移动端预览

部署后, 手机 Safari/Chrome 打开看板, 加到主屏幕即可像 App 一样使用:
- 全屏体验, 无浏览器地址栏
- 自定义 QQQ 烛台图标
- 离线可看上次数据 (浏览器缓存)

## 📜 许可

MIT - 自由使用、修改、商用。

## ⚠️ 免责声明

本工具仅供研究学习, **不构成投资建议**。投资有风险, 决策需谨慎。
