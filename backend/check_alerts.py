"""
QQQ 预警引擎 - 关键时刻不会错过
================================================
检测 5 个核心触发器，状态变化时发出通知。
================================================

触发器列表:
1. TQQQ 入场      (从非看多 → 看多)
2. 第一道警报      (健康 → 出现裂痕)
3. 确认转熊        (中性 → 减仓/防御)
4. 抄底信号        (恐慌见底 → 反弹机会)
5. 滞胀紧急避险    (滞胀模式触发)

支持的通知渠道:
- Email (SMTP, 任何邮箱)
- Telegram Bot
- 企业微信 Webhook
- Discord Webhook
- Slack Webhook
- 控制台输出 (默认)

用法:
    python check_alerts.py
    python check_alerts.py --config alerts.yaml  # 自定义配置

环境变量配置 (GitHub Actions secrets):
    SMTP_HOST, SMTP_USER, SMTP_PASS, ALERT_EMAIL
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    WECOM_WEBHOOK_URL
    DISCORD_WEBHOOK_URL
    SLACK_WEBHOOK_URL
"""
import os
import json
import sys
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from urllib import request as urlrequest, error as urlerror


# -------------------- 状态持久化 --------------------

STATE_FILE = Path(__file__).parent.parent / "data" / "alert_state.json"


def load_state() -> dict:
    """加载上一次的预警状态"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 状态文件读取失败: {e}")
    return {
        "last_score": None,
        "last_regime": None,
        "last_triggers": {},
        "last_run": None,
    }


def save_state(state: dict):
    STATE_FILE.parent.mkdir(exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False, default=str)


# -------------------- 触发器检测 --------------------

def check_trigger_1_tqqq_entry(data: dict, ratios: dict, scoring: dict) -> dict | None:
    """触发器 1: TQQQ 入场信号"""
    q = data.get("QQQ", {})
    vix = data.get("VIX", {}).get("price", 99)
    vix_ratio = ratios.get("VIX_VIX3M", 1.0)
    hyg = data.get("HYG", {})

    conditions = {
        "QQQ > 200SMA": q.get("above_sma200", False),
        "金叉态 (50>200)": q.get("golden_cross", False),
        "QQQ 在 50SMA 上方": q.get("above_sma50", False),
        "VIX < 18": vix < 18,
        "VIX/VIX3M < 0.92 (健康 contango)": vix_ratio < 0.92,
        "HYG 在 50SMA 上方": hyg.get("above_sma50", False),
    }

    met = sum(1 for v in conditions.values() if v)
    if met >= 5:  # 至少满足 5/6 个
        return {
            "name": "🚀 TQQQ 入场信号",
            "severity": "bullish",
            "score_threshold_met": met,
            "conditions": conditions,
            "action": "可考虑建立 TQQQ 核心仓位，止损设在 200SMA 下方 3%",
        }
    return None


def check_trigger_2_first_warning(data: dict, ratios: dict, state: dict) -> dict | None:
    """触发器 2: 第一道警报 - 健康市场出现裂痕"""
    vix_ratio = ratios.get("VIX_VIX3M", 0)
    move = data.get("MOVE", {}).get("price")
    q = data.get("QQQ", {})

    warnings = []

    # VIX/VIX3M 3天内从 <0.9 升至 >0.95
    last_ratio = state.get("last_vix_ratio")
    if last_ratio is not None and last_ratio < 0.9 and vix_ratio > 0.95:
        warnings.append(f"VIX/VIX3M 从 {last_ratio:.3f} 升至 {vix_ratio:.3f}")

    # MOVE 突破 120
    if move is not None and move > 120:
        last_move = state.get("last_move", 0)
        if last_move <= 120:
            warnings.append(f"MOVE 突破 120 (当前 {move:.0f})")

    # QQQ 创新高但 QQEW 未创新高 (背离)
    qqew = data.get("QQEW", {})
    if q.get("dist_sma200_pct", 0) > 5 and qqew.get("dist_sma200_pct", 0) < 2:
        warnings.append(f"QQQ 强 (+{q['dist_sma200_pct']:.1f}%) 但 QQEW 弱 (+{qqew['dist_sma200_pct']:.1f}%): 头重")

    if warnings:
        return {
            "name": "⚠️ 第一道警报",
            "severity": "warning",
            "warnings": warnings,
            "action": "TQQQ 仓位减半，加买 1-2 个月 OTM put 做保险",
        }
    return None


def check_trigger_3_bear_confirmed(data: dict, ratios: dict, scoring: dict) -> dict | None:
    """触发器 3: 确认转熊"""
    q = data.get("QQQ", {})
    hyg = data.get("HYG", {})

    bear_signals = {
        "QQQ 跌破 200SMA": not q.get("above_sma200", True),
        "死叉态 (50<200)": not q.get("golden_cross", True),
        "VIX/VIX3M > 1.0 (backwardation)": ratios.get("VIX_in_backwardation", False),
        "HYG 跌破 200SMA": not hyg.get("above_sma200", True),
        "综合评分 ≤ -5": scoring.get("total_score", 0) <= -5,
    }

    met = sum(1 for v in bear_signals.values() if v)
    if met >= 2:
        return {
            "name": "🔴 确认转熊",
            "severity": "bearish",
            "conditions_met": met,
            "total_conditions": len(bear_signals),
            "signals": bear_signals,
            "action": "清空所有 TQQQ, QQQ 仓位降至 30% 以下, 部分资金转 TLT/现金",
        }
    return None


def check_trigger_4_panic_bottom(data: dict, ratios: dict, state: dict) -> dict | None:
    """触发器 4: 抄底信号 - VIX 见顶回落"""
    vix = data.get("VIX", {}).get("price", 0)
    vix_ratio = ratios.get("VIX_VIX3M", 1.0)
    hyg = data.get("HYG", {})

    last_vix = state.get("last_vix")
    last_vix_ratio = state.get("last_vix_ratio")

    if last_vix and last_vix > 30 and 20 < vix < 25:  # 钩子
        if last_vix_ratio and last_vix_ratio > 1.1 and vix_ratio < 1.0:
            return {
                "name": "💰 抄底信号 (恐慌见底)",
                "severity": "bullish",
                "details": [
                    f"VIX 从 {last_vix:.1f} 回落至 {vix:.1f}",
                    f"VIX/VIX3M 从 {last_vix_ratio:.3f} 回落至 {vix_ratio:.3f}",
                    f"HYG 企稳: {'是' if hyg.get('change_pct', 0) >= 0 else '否'}",
                ],
                "action": "分 3 批建仓 QQQ (先 1/3), 收复 50SMA 加至 2/3, 收复 200SMA 满仓",
            }
    return None


def check_trigger_5_stagflation(data: dict, ratios: dict) -> dict | None:
    """触发器 5: 滞胀紧急避险"""
    jnk = data.get("JNK", {})
    tlt = data.get("TLT", {})
    dxy = data.get("DXY", {})
    move = data.get("MOVE", {}).get("price", 0)

    # 滞胀模式: JNK跌 + JNK/TLT涨 (TLT跌得更惨) + MOVE涨
    is_stagflation = (
        jnk.get("change_pct", 0) < -0.5 and
        tlt.get("change_pct", 0) < -1.0 and
        move > 130 and
        dxy.get("change_pct", 0) > 1.0
    )

    if is_stagflation:
        return {
            "name": "🚨 滞胀紧急避险",
            "severity": "critical",
            "details": [
                f"JNK 跌 {jnk.get('change_pct', 0):.2f}%",
                f"TLT 跌 {tlt.get('change_pct', 0):.2f}% (跌得更惨)",
                f"MOVE {move:.0f} 紧张",
                f"DXY 涨 {dxy.get('change_pct', 0):+.2f}% (急涨)",
            ],
            "action": "完全清仓股票，转入短期国债 (SHY/BIL) + 美元 + 少量黄金。不要碰 TLT。",
        }
    return None


def check_score_change(scoring: dict, state: dict) -> dict | None:
    """检测综合评分跨越关键阈值"""
    cur = scoring.get("total_score", 0)
    last = state.get("last_score")

    if last is None:
        return None  # 首次运行

    THRESHOLDS = [
        (7, "极度看多"),
        (4, "看多"),
        (1, "偏多观察"),
        (-2, "中性"),
        (-5, "减仓防御"),
        (-12, "重度防御"),
    ]

    def regime_of(score):
        for t, name in THRESHOLDS:
            if score >= t:
                return name
        return "重度防御"

    cur_regime = regime_of(cur)
    last_regime = regime_of(last)

    if cur_regime != last_regime:
        # 评分方向
        direction = "↑" if cur > last else "↓"
        severity = "bullish" if cur > last else "bearish"
        return {
            "name": f"🔔 状态切换: {last_regime} → {cur_regime}",
            "severity": severity,
            "details": [
                f"综合评分: {last} → {cur} ({direction})",
                f"建议仓位: {scoring.get('position_suggestion', '--')}",
            ],
            "action": "重新评估当前组合，调整仓位",
        }
    return None


# -------------------- 通知渠道 --------------------

def format_alert_text(alerts: list, scoring: dict, timestamp: str) -> str:
    """生成纯文本预警内容"""
    lines = [
        "═══════════════════════════════",
        "  QQQ 预警通知",
        "═══════════════════════════════",
        f"时间: {timestamp}",
        f"综合评分: {scoring.get('total_score', '--')} ({scoring.get('regime', '--')})",
        f"建议仓位: {scoring.get('position_suggestion', '--')}",
        "",
    ]

    for i, alert in enumerate(alerts, 1):
        lines.append(f"─── 触发器 {i}: {alert['name']} ───")
        lines.append(f"严重等级: {alert.get('severity', 'info')}")

        if "warnings" in alert:
            for w in alert["warnings"]:
                lines.append(f"  • {w}")

        if "details" in alert:
            for d in alert["details"]:
                lines.append(f"  • {d}")

        if "conditions" in alert:
            for cond, met in alert["conditions"].items():
                mark = "✓" if met else "✗"
                lines.append(f"  {mark} {cond}")

        if "signals" in alert:
            for sig, met in alert["signals"].items():
                mark = "✓" if met else "✗"
                lines.append(f"  {mark} {sig}")

        if "action" in alert:
            lines.append("")
            lines.append(f"建议操作: {alert['action']}")
        lines.append("")

    lines.append("─" * 32)
    lines.append("本通知仅供参考，不构成投资建议。")
    return "\n".join(lines)


def format_alert_html(alerts: list, scoring: dict, timestamp: str) -> str:
    """生成 HTML 邮件正文"""
    color_map = {
        "bullish": "#4ade80",
        "bearish": "#ef4444",
        "warning": "#fbbf24",
        "critical": "#dc2626",
        "info": "#60a5fa",
    }
    regime_color = {
        "极度看多": "#4ade80", "看多": "#4ade80",
        "偏多观察": "#60a5fa", "中性": "#fbbf24",
        "减仓防御": "#ef4444", "重度防御": "#dc2626",
    }
    reg = scoring.get("regime", "--")
    score = scoring.get("total_score", "--")

    cards = []
    for alert in alerts:
        c = color_map.get(alert.get("severity", "info"), "#60a5fa")
        body_lines = []
        if "warnings" in alert:
            body_lines.extend(f"<li>{w}</li>" for w in alert["warnings"])
        if "details" in alert:
            body_lines.extend(f"<li>{d}</li>" for d in alert["details"])
        if "conditions" in alert:
            for cond, met in alert["conditions"].items():
                mark = "✅" if met else "⬜"
                body_lines.append(f"<li>{mark} {cond}</li>")
        if "signals" in alert:
            for sig, met in alert["signals"].items():
                mark = "🔴" if met else "⬜"
                body_lines.append(f"<li>{mark} {sig}</li>")
        body_html = "<ul style='margin:8px 0;padding-left:20px;'>" + "".join(body_lines) + "</ul>" if body_lines else ""
        action_html = f"<p style='margin:12px 0 0;padding:10px;background:#f5f5f4;border-radius:4px;font-size:13px;'><strong>📌 建议操作:</strong> {alert['action']}</p>" if alert.get("action") else ""
        cards.append(f"""
        <div style="margin:16px 0;border-left:4px solid {c};padding:16px;background:#fafaf9;border-radius:4px;">
            <h3 style="margin:0 0 8px;color:{c};font-size:16px;">{alert['name']}</h3>
            {body_html}
            {action_html}
        </div>
        """)

    return f"""
    <html>
    <body style="font-family: -apple-system, sans-serif; max-width:600px; margin:0 auto; padding:20px; background:#fafaf9;">
        <div style="background:white; border-radius:8px; padding:24px;">
            <h1 style="margin:0 0 16px;font-size:20px;color:#1a1a1a;">📊 QQQ 预警通知</h1>
            <div style="display:flex; gap:12px; margin-bottom:20px;">
                <div style="flex:1; padding:12px; background:#1a1a1a; color:white; border-radius:4px;">
                    <div style="font-size:11px; opacity:0.6;">综合评分</div>
                    <div style="font-size:28px; font-weight:700; color:{regime_color.get(reg, '#fbbf24')};">{'+' if isinstance(score, (int,float)) and score>0 else ''}{score}</div>
                    <div style="font-size:13px;">{reg}</div>
                </div>
                <div style="flex:2; padding:12px; background:#f5f5f4; border-radius:4px;">
                    <div style="font-size:11px; color:#999;">建议仓位</div>
                    <div style="font-size:14px; font-weight:600; margin-top:4px;">{scoring.get('position_suggestion','--')}</div>
                </div>
            </div>
            <div style="border-top:1px solid #e5e5e5; padding-top:16px;">
                <h2 style="font-size:14px;color:#666;margin:0 0 8px;">🔔 触发的预警 ({len(alerts)})</h2>
                {''.join(cards)}
            </div>
            <p style="margin-top:20px; padding-top:16px; border-top:1px solid #e5e5e5; font-size:11px; color:#999;">
                时间: {timestamp}<br>
                本通知由 QQQ Monitor 自动发送，仅供研究参考，不构成投资建议。
            </p>
        </div>
    </body>
    </html>
    """


def send_email(html_body: str, text_body: str, subject: str) -> bool:
    """通过 SMTP 发送邮件"""
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    to_email = os.getenv("ALERT_EMAIL", user)
    port = int(os.getenv("SMTP_PORT", "587"))

    if not all([host, user, password]):
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_email
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        print(f"  ✅ 邮件已发送至 {to_email}")
        return True
    except Exception as e:
        print(f"  ❌ 邮件发送失败: {e}")
        return False


def http_post_json(url: str, payload: dict) -> bool:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except Exception as e:
        print(f"  ❌ Webhook 失败: {e}")
        return False


def send_telegram(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat, "text": text, "parse_mode": "HTML"}
    ok = http_post_json(url, payload)
    if ok:
        print("  ✅ Telegram 已发送")
    return ok


def send_wecom(text: str) -> bool:
    """企业微信 Bot Webhook"""
    url = os.getenv("WECOM_WEBHOOK_URL")
    if not url:
        return False
    payload = {"msgtype": "text", "text": {"content": text}}
    ok = http_post_json(url, payload)
    if ok:
        print("  ✅ 企业微信已发送")
    return ok


def send_discord(text: str) -> bool:
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        return False
    # Discord 单条消息 2000 字符上限
    payload = {"content": f"```\n{text[:1900]}\n```"}
    ok = http_post_json(url, payload)
    if ok:
        print("  ✅ Discord 已发送")
    return ok


def send_slack(text: str) -> bool:
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return False
    payload = {"text": f"```\n{text}\n```"}
    ok = http_post_json(url, payload)
    if ok:
        print("  ✅ Slack 已发送")
    return ok


# -------------------- 主流程 --------------------

def main():
    print("=" * 50)
    print("  QQQ 预警检测引擎")
    print("=" * 50)

    # 1. 读取数据
    data_path = Path(__file__).parent.parent / "data" / "dashboard.json"
    if not data_path.exists():
        print(f"❌ 数据文件不存在: {data_path}")
        print("   请先运行 python fetch_data.py")
        sys.exit(1)

    with open(data_path, "r", encoding="utf-8") as f:
        dashboard = json.load(f)

    data = dashboard.get("data", {})
    ratios = dashboard.get("ratios", {})
    scoring = dashboard.get("scoring", {})
    timestamp = dashboard.get("timestamp", datetime.now(timezone.utc).isoformat())

    print(f"\n数据时间: {timestamp}")
    print(f"综合评分: {scoring.get('total_score')} ({scoring.get('regime')})")

    # 2. 加载状态
    state = load_state()

    # 3. 执行所有触发器检测
    print("\n🔍 检测触发器...")
    alerts = []

    for check_fn, name in [
        (lambda: check_trigger_1_tqqq_entry(data, ratios, scoring), "TQQQ 入场"),
        (lambda: check_trigger_2_first_warning(data, ratios, state), "第一道警报"),
        (lambda: check_trigger_3_bear_confirmed(data, ratios, scoring), "确认转熊"),
        (lambda: check_trigger_4_panic_bottom(data, ratios, state), "抄底信号"),
        (lambda: check_trigger_5_stagflation(data, ratios), "滞胀避险"),
        (lambda: check_score_change(scoring, state), "评分阶段切换"),
    ]:
        try:
            result = check_fn()
            if result:
                alerts.append(result)
                print(f"  🔔 [{name}] 触发: {result['name']}")
            else:
                print(f"  ✓  [{name}] 未触发")
        except Exception as e:
            print(f"  ⚠️ [{name}] 检测出错: {e}")

    # 4. 去重: 同一触发器与上次相同时不重复发送
    last_triggers = state.get("last_triggers", {})
    fresh_alerts = []
    new_triggers = {}
    for alert in alerts:
        name = alert["name"]
        # 同名触发器在 6 小时内不重发
        new_triggers[name] = datetime.now(timezone.utc).isoformat()
        if name in last_triggers:
            try:
                last_time = datetime.fromisoformat(last_triggers[name].replace("Z", "+00:00"))
                hours_since = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600
                if hours_since < 6:
                    print(f"  ⏭️ 跳过 (6小时内已发): {name}")
                    continue
            except Exception:
                pass
        fresh_alerts.append(alert)

    # 5. 发送通知
    sent_channels = []
    if fresh_alerts:
        print(f"\n📢 发送 {len(fresh_alerts)} 条新预警...")
        text = format_alert_text(fresh_alerts, scoring, timestamp)
        html = format_alert_html(fresh_alerts, scoring, timestamp)

        print("\n" + text)
        print()

        # 邮件主题: 取最严重的
        severity_rank = {"critical": 0, "bearish": 1, "warning": 2, "bullish": 3, "info": 4}
        most_severe = min(fresh_alerts, key=lambda a: severity_rank.get(a.get("severity", "info"), 99))
        subject = f"[QQQ 预警] {most_severe['name']} · 评分 {scoring.get('total_score')}"

        if send_email(html, text, subject):
            sent_channels.append("email")
        if send_telegram(text):
            sent_channels.append("telegram")
        if send_wecom(text):
            sent_channels.append("wecom")
        if send_discord(text):
            sent_channels.append("discord")
        if send_slack(text):
            sent_channels.append("slack")

        if not sent_channels:
            print("\n⚠️ 未配置任何通知渠道 (设置 SMTP/TELEGRAM/WECOM/DISCORD/SLACK 环境变量)")
        else:
            print(f"\n✅ 已通过 {len(sent_channels)} 个渠道发送: {', '.join(sent_channels)}")
    else:
        print("\n✓ 无新预警触发")

    # 6. 保存状态
    state.update({
        "last_score": scoring.get("total_score"),
        "last_regime": scoring.get("regime"),
        "last_vix": data.get("VIX", {}).get("price"),
        "last_vix_ratio": ratios.get("VIX_VIX3M"),
        "last_move": data.get("MOVE", {}).get("price"),
        "last_triggers": {**last_triggers, **new_triggers},
        "last_run": datetime.now(timezone.utc).isoformat(),
    })
    save_state(state)
    print(f"\n💾 状态已保存: {STATE_FILE}")


if __name__ == "__main__":
    main()
