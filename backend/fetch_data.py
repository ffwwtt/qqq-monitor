"""
QQQ 预警看板 - 数据采集与综合评分引擎
================================================
功能：
1. 从 yfinance 拉取价格、波动率、信用债 ETF 数据
2. 从 FRED 拉取宏观经济指标 (可选)
3. 计算 4 层信号评分
4. 输出 JSON 供前端读取
================================================
用法:
    python fetch_data.py          # 不使用 FRED
    python fetch_data.py YOUR_FRED_API_KEY  # 使用 FRED 拉取宏观

定时执行 (Linux/Mac crontab, 每5分钟):
    */5 9-16 * * 1-5 cd /path/to/backend && python fetch_data.py
"""
import sys
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# -------------------- 配置区 --------------------

# 拉取的 ticker (Yahoo 代码)
TICKERS = {
    # 第1层 价格-动量
    "QQQ":    "QQQ",      # Nasdaq 100 ETF
    "SPY":    "SPY",      # S&P 500
    "RSP":    "RSP",      # 等权 S&P 500 (用来看宽度)
    "QQEW":   "QQEW",     # 等权 Nasdaq 100

    # 第2层 波动率-情绪
    "VIX":    "^VIX",     # 股市恐慌指数
    "VIX3M":  "^VIX3M",   # 3个月VIX
    "VIX9D":  "^VIX9D",   # 9日VIX
    "VVIX":   "^VVIX",    # 波动率的波动率
    "MOVE":   "^MOVE",    # 债市波动率 (注意: Yahoo 上可能缺失，会自动跳过)
    "SKEW":   "^SKEW",    # 偏度指数

    # 第3层 内部结构 (用ETF间比率近似宽度)
    "MAGS":   "MAGS",     # Magnificent 7 ETF

    # 第4层 宏观-信用
    "HYG":    "HYG",      # 高收益债
    "JNK":    "JNK",      # 高收益债 (替代)
    "TLT":    "TLT",      # 20年+国债
    "IEF":    "IEF",      # 7-10年国债
    "LQD":    "LQD",      # 投资级信用债
    "SHY":    "SHY",      # 1-3年国债
    "DXY":    "DX-Y.NYB", # 美元指数
    "GLD":    "GLD",      # 黄金
}

# 评分阈值
THRESHOLDS = {
    "VIX_LOW": 15,       # VIX < 此值 = 极度平静
    "VIX_NORMAL": 20,    # VIX < 此值 = 正常
    "VIX_HIGH": 25,      # VIX > 此值 = 警惕
    "VIX_PANIC": 30,     # VIX > 此值 = 恐慌
    "VIX_RATIO_NORMAL": 0.92,   # VIX/VIX3M < 此值 = 健康 contango
    "VIX_RATIO_WARN": 0.95,     # VIX/VIX3M 接近 1 = 警惕
    "VIX_RATIO_PANIC": 1.0,     # > 1 = backwardation 倒挂
    "MOVE_LOW": 90,
    "MOVE_NORMAL": 110,
    "MOVE_HIGH": 130,
    "VVIX_NORMAL": 90,
    "VVIX_HIGH": 110,
}


# -------------------- 数据拉取 --------------------

def fetch_ticker(symbol: str, period: str = "300d") -> pd.DataFrame:
    """单个 ticker 拉取，失败返回空 DataFrame"""
    try:
        df = yf.Ticker(symbol).history(period=period, auto_adjust=False)
        if df.empty:
            print(f"  ⚠️  {symbol}: 无数据")
            return pd.DataFrame()
        return df
    except Exception as e:
        print(f"  ❌ {symbol}: {e}")
        return pd.DataFrame()


def compute_metrics(df: pd.DataFrame) -> dict | None:
    """从单只标的的 K 线计算所需指标"""
    if df.empty or len(df) < 200:
        return None

    close = df["Close"]
    latest = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) >= 2 else latest

    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1])

    # 200日均线斜率 (20天变化)
    sma200_slope = (
        float(close.rolling(200).mean().iloc[-1]) -
        float(close.rolling(200).mean().iloc[-20])
    ) if len(close) >= 220 else 0.0

    # RSI(14)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = float((100 - (100 / (1 + rs))).iloc[-1])

    # 距离 200SMA 的百分比
    dist_sma200_pct = (latest / sma200 - 1) * 100 if sma200 > 0 else 0

    return {
        "price": round(latest, 2),
        "change_pct": round((latest / prev - 1) * 100, 2) if prev else 0,
        "sma20": round(sma20, 2),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "sma200_slope_up": sma200_slope > 0,
        "above_sma200": latest > sma200,
        "above_sma50": latest > sma50,
        "golden_cross": sma50 > sma200,  # 50>200 = 金叉态
        "dist_sma200_pct": round(dist_sma200_pct, 2),
        "rsi14": round(rsi, 1),
    }


def fetch_all_data() -> dict:
    """主拉取函数"""
    print("📡 开始拉取市场数据...")
    raw_data = {}

    for name, symbol in TICKERS.items():
        df = fetch_ticker(symbol)
        metrics = compute_metrics(df)
        if metrics:
            raw_data[name] = metrics
            print(f"  ✅ {name:6s} ({symbol:10s}): ${metrics['price']:>8.2f}  Δ {metrics['change_pct']:+.2f}%")
        else:
            print(f"  ⚠️  {name}: 跳过 (数据不足或拉取失败)")

    return raw_data


# -------------------- 衍生比率计算 --------------------

def compute_ratios(data: dict) -> dict:
    """计算关键比率"""
    ratios = {}

    if "VIX" in data and "VIX3M" in data:
        ratios["VIX_VIX3M"] = round(
            data["VIX"]["price"] / data["VIX3M"]["price"], 3
        )
        ratios["VIX_in_backwardation"] = ratios["VIX_VIX3M"] > THRESHOLDS["VIX_RATIO_PANIC"]

    if "HYG" in data and "IEF" in data:
        ratios["HYG_IEF"] = round(
            data["HYG"]["price"] / data["IEF"]["price"], 4
        )

    if "JNK" in data and "TLT" in data:
        ratios["JNK_TLT"] = round(
            data["JNK"]["price"] / data["TLT"]["price"], 4
        )

    if "QQQ" in data and "QQEW" in data:
        ratios["QQQ_QQEW"] = round(
            data["QQQ"]["price"] / data["QQEW"]["price"], 4
        )

    if "MAGS" in data and "RSP" in data:
        ratios["MAGS_RSP"] = round(
            data["MAGS"]["price"] / data["RSP"]["price"], 4
        )

    return ratios


# -------------------- 4 层评分系统 --------------------

def score_layer_1_price(data: dict) -> tuple[int, list]:
    """第1层：价格-动量"""
    score = 0
    details = []

    if "QQQ" not in data:
        return 0, ["QQQ 数据缺失"]

    q = data["QQQ"]

    # 信号 1: 价格 vs 200SMA
    if q["above_sma200"] and q["sma200_slope_up"]:
        score += 2
        details.append("✅ QQQ 在 200SMA 上方且向上 (+2)")
    elif q["above_sma200"]:
        score += 1
        details.append("✅ QQQ 在 200SMA 上方 (+1)")
    else:
        score -= 2
        details.append("❌ QQQ 跌破 200SMA (-2)")

    # 信号 2: 金叉态
    if q["golden_cross"]:
        score += 1
        details.append("✅ 50SMA > 200SMA 金叉态 (+1)")
    else:
        score -= 1
        details.append("❌ 50SMA < 200SMA 死叉态 (-1)")

    # 信号 3: RSI 健康度
    if 50 <= q["rsi14"] <= 70:
        score += 1
        details.append(f"✅ RSI {q['rsi14']} 健康看多 (+1)")
    elif q["rsi14"] > 80:
        score -= 1
        details.append(f"⚠️ RSI {q['rsi14']} 严重超买 (-1)")
    elif q["rsi14"] < 30:
        details.append(f"💡 RSI {q['rsi14']} 超卖区域 (0)")

    return score, details


def score_layer_2_volatility(data: dict, ratios: dict) -> tuple[int, list]:
    """第2层：波动率-情绪"""
    score = 0
    details = []

    # VIX 绝对水平
    if "VIX" in data:
        vix = data["VIX"]["price"]
        if vix < THRESHOLDS["VIX_LOW"]:
            score += 2
            details.append(f"✅ VIX {vix:.1f} 极度平静 (+2)")
        elif vix < THRESHOLDS["VIX_NORMAL"]:
            score += 1
            details.append(f"✅ VIX {vix:.1f} 正常 (+1)")
        elif vix < THRESHOLDS["VIX_HIGH"]:
            details.append(f"💡 VIX {vix:.1f} 略高 (0)")
        elif vix < THRESHOLDS["VIX_PANIC"]:
            score -= 1
            details.append(f"⚠️ VIX {vix:.1f} 偏高 (-1)")
        else:
            score -= 2
            details.append(f"❌ VIX {vix:.1f} 恐慌 (-2)")

    # VIX/VIX3M 期限结构
    if "VIX_VIX3M" in ratios:
        r = ratios["VIX_VIX3M"]
        if r < THRESHOLDS["VIX_RATIO_NORMAL"]:
            score += 1
            details.append(f"✅ VIX/VIX3M {r} contango (+1)")
        elif r < THRESHOLDS["VIX_RATIO_WARN"]:
            details.append(f"💡 VIX/VIX3M {r} (0)")
        elif r < THRESHOLDS["VIX_RATIO_PANIC"]:
            score -= 1
            details.append(f"⚠️ VIX/VIX3M {r} 接近倒挂 (-1)")
        else:
            score -= 2
            details.append(f"❌ VIX/VIX3M {r} backwardation (-2)")

    # MOVE 债市波动率
    if "MOVE" in data:
        move = data["MOVE"]["price"]
        if move < THRESHOLDS["MOVE_LOW"]:
            score += 1
            details.append(f"✅ MOVE {move:.0f} 平静 (+1)")
        elif move < THRESHOLDS["MOVE_NORMAL"]:
            details.append(f"💡 MOVE {move:.0f} (0)")
        elif move < THRESHOLDS["MOVE_HIGH"]:
            score -= 1
            details.append(f"⚠️ MOVE {move:.0f} 偏高 (-1)")
        else:
            score -= 2
            details.append(f"❌ MOVE {move:.0f} 紧张 (-2)")

    # VVIX
    if "VVIX" in data:
        vvix = data["VVIX"]["price"]
        if vvix > THRESHOLDS["VVIX_HIGH"]:
            score -= 1
            details.append(f"⚠️ VVIX {vvix:.0f} 高 (-1)")

    return score, details


def score_layer_3_structure(data: dict, ratios: dict) -> tuple[int, list]:
    """第3层：内部结构 (用 ETF 间比率近似)"""
    score = 0
    details = []

    # QQQ vs QQEW: 头重不健康
    if "QQQ_QQEW" in ratios:
        # 这里需要历史均值对比，简化版直接看绝对值
        details.append(f"💡 QQQ/QQEW = {ratios['QQQ_QQEW']:.3f}")

    # RSP vs SPY: 等权 vs 市值权 - 如果等权跑赢市值权说明宽度健康
    if "RSP" in data and "SPY" in data:
        rsp_above = data["RSP"]["above_sma200"]
        spy_above = data["SPY"]["above_sma200"]
        if rsp_above and spy_above:
            score += 1
            details.append("✅ SPY+RSP 均在 200SMA 上方 (+1)")
        elif not rsp_above and spy_above:
            score -= 1
            details.append("⚠️ SPY 强但 RSP 弱: 宽度恶化 (-1)")
        elif not rsp_above and not spy_above:
            score -= 2
            details.append("❌ SPY+RSP 均跌破 200SMA (-2)")

    # QQQ vs QQEW: 同上逻辑
    if "QQQ" in data and "QQEW" in data:
        qqq_above = data["QQQ"]["above_sma200"]
        qqew_above = data["QQEW"]["above_sma200"]
        if not qqew_above and qqq_above:
            score -= 1
            details.append("⚠️ QQQ 强但 QQEW 弱: MAG7 独涨 (-1)")
        elif qqq_above and qqew_above:
            score += 1
            details.append("✅ Nasdaq 内部宽度健康 (+1)")

    return score, details


def score_layer_4_macro(data: dict, ratios: dict) -> tuple[int, list]:
    """第4层：宏观-信用"""
    score = 0
    details = []

    # HYG/IEF 风险偏好
    if "HYG_IEF" in ratios and "HYG" in data:
        if data["HYG"]["above_sma50"]:
            score += 1
            details.append(f"✅ HYG 在 50SMA 上方: 信用健康 (+1)")
        else:
            score -= 1
            details.append(f"⚠️ HYG 跌破 50SMA: 信用走弱 (-1)")

    # JNK 趋势
    if "JNK" in data:
        if data["JNK"]["above_sma200"]:
            score += 1
            details.append("✅ JNK 在 200SMA 上方 (+1)")
        else:
            score -= 1
            details.append("❌ JNK 跌破 200SMA (-1)")

    # 美元方向 (美元急涨 = 风险资产承压)
    if "DXY" in data:
        if data["DXY"]["change_pct"] > 1.0:
            score -= 1
            details.append(f"⚠️ DXY 急涨 {data['DXY']['change_pct']:+.2f}% (-1)")

    return score, details


def compute_overall_score(data: dict, ratios: dict) -> dict:
    """综合 4 层评分"""
    s1, d1 = score_layer_1_price(data)
    s2, d2 = score_layer_2_volatility(data, ratios)
    s3, d3 = score_layer_3_structure(data, ratios)
    s4, d4 = score_layer_4_macro(data, ratios)

    total = s1 + s2 + s3 + s4

    # 仓位建议
    if total >= 7:
        regime = "极度看多"
        position = "QQQ 70% + TQQQ 30%"
        color = "success"
    elif total >= 4:
        regime = "看多"
        position = "QQQ 80% + TQQQ 10% + 现金 10%"
        color = "success"
    elif total >= 1:
        regime = "偏多观察"
        position = "QQQ 60% + 现金 40%"
        color = "info"
    elif total >= -2:
        regime = "中性"
        position = "QQQ 40% + 现金 60%"
        color = "warning"
    elif total >= -5:
        regime = "减仓防御"
        position = "QQQ 20% + 现金 60% + TLT 20%"
        color = "danger"
    else:
        regime = "重度防御"
        position = "现金 70% + SHY 20% + GLD 10%"
        color = "danger"

    return {
        "total_score": total,
        "regime": regime,
        "position_suggestion": position,
        "color": color,
        "layers": {
            "layer1_price":      {"score": s1, "name": "价格-动量",   "details": d1, "max": 4},
            "layer2_volatility": {"score": s2, "name": "波动率-情绪", "details": d2, "max": 5},
            "layer3_structure":  {"score": s3, "name": "内部结构",   "details": d3, "max": 3},
            "layer4_macro":      {"score": s4, "name": "宏观-信用",   "details": d4, "max": 3},
        }
    }


# -------------------- 历史快照 (供前端画走势) --------------------

def fetch_history_snapshot(symbol: str = "QQQ", days: int = 120) -> list:
    """拉取价格历史，给前端画走势图"""
    try:
        df = yf.Ticker(symbol).history(period=f"{days}d")
        if df.empty:
            return []

        # 计算 SMA
        df["sma50"] = df["Close"].rolling(50).mean()
        df["sma200"] = df["Close"].rolling(200).mean()

        history = []
        for idx, row in df.iterrows():
            history.append({
                "date": idx.strftime("%Y-%m-%d"),
                "close": round(float(row["Close"]), 2),
                "sma50": round(float(row["sma50"]), 2) if not pd.isna(row["sma50"]) else None,
                "sma200": round(float(row["sma200"]), 2) if not pd.isna(row["sma200"]) else None,
            })
        return history
    except Exception as e:
        print(f"历史数据拉取失败: {e}")
        return []


# -------------------- FRED 宏观数据 (可选) --------------------

def fetch_fred_data(api_key: str) -> dict:
    """从 FRED 拉取宏观数据，需要免费 API key"""
    try:
        from fredapi import Fred
        fred = Fred(api_key=api_key)

        series = {
            "T10Y2Y": "10年-2年期限利差",
            "DGS10": "10年期国债收益率",
            "DGS2": "2年期国债收益率",
            "UNRATE": "失业率",
            "CPIAUCSL": "CPI",
        }

        result = {}
        for code, name in series.items():
            try:
                s = fred.get_series_latest_release(code).dropna()
                if len(s) > 0:
                    result[code] = {
                        "name": name,
                        "value": round(float(s.iloc[-1]), 3),
                        "date": s.index[-1].strftime("%Y-%m-%d"),
                    }
            except Exception as e:
                print(f"FRED {code} 失败: {e}")

        return result
    except ImportError:
        print("⚠️ 未安装 fredapi，跳过宏观数据")
        return {}
    except Exception as e:
        print(f"⚠️ FRED 拉取失败: {e}")
        return {}


# -------------------- 主函数 --------------------

def main(fred_key: str | None = None):
    print("=" * 50)
    print("  QQQ 预警看板 - 数据采集")
    print(f"  时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 50)

    # 1. 拉取标的数据
    data = fetch_all_data()
    if not data:
        print("❌ 所有数据拉取失败")
        sys.exit(1)

    # 2. 计算比率
    print("\n📊 计算衍生比率...")
    ratios = compute_ratios(data)
    for k, v in ratios.items():
        print(f"  {k}: {v}")

    # 3. 综合评分
    print("\n🎯 计算综合评分...")
    scoring = compute_overall_score(data, ratios)
    print(f"  综合分数: {scoring['total_score']}")
    print(f"  状态判断: {scoring['regime']}")
    print(f"  仓位建议: {scoring['position_suggestion']}")

    # 4. 拉取历史 (供前端画图)
    print("\n📈 拉取 QQQ 历史走势...")
    history = fetch_history_snapshot("QQQ", days=120)
    vix_history = fetch_history_snapshot("^VIX", days=120)

    # 5. FRED 数据 (可选)
    fred_data = {}
    if fred_key:
        print("\n🏛️ 拉取 FRED 宏观数据...")
        fred_data = fetch_fred_data(fred_key)
        for k, v in fred_data.items():
            print(f"  {k}: {v['value']} ({v['date']})")

    # 6. 输出 JSON
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "ratios": ratios,
        "scoring": scoring,
        "history": {
            "QQQ": history,
            "VIX": vix_history,
        },
        "fred": fred_data,
    }

    # 写入 data 目录
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    output_path = data_dir / "dashboard.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n✅ 数据已写入: {output_path}")
    print(f"📊 文件大小: {output_path.stat().st_size / 1024:.1f} KB")

    return output


if __name__ == "__main__":
    fred_key = sys.argv[1] if len(sys.argv) > 1 else None
    main(fred_key)
