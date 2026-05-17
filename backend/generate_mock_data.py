"""
模拟数据生成器 - 仅用于演示/测试
在沙箱或没有网络环境时生成一份示例 JSON

使用方法:
    python generate_mock_data.py

会生成 ../data/dashboard.json 供前端测试
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import random
import math


def generate_history(base_price: float, days: int = 120, volatility: float = 0.015) -> list:
    """生成模拟K线历史"""
    prices = [base_price]
    for _ in range(days - 1):
        # 略带上升偏置的随机游走
        change = random.gauss(0.0005, volatility)
        prices.append(prices[-1] * (1 + change))

    history = []
    today = datetime.now()
    for i, p in enumerate(prices):
        date = today - timedelta(days=days - 1 - i)
        # 简单 SMA 计算
        sma50 = sum(prices[max(0, i-49):i+1]) / min(50, i+1) if i >= 0 else None
        sma200 = sum(prices[max(0, i-199):i+1]) / min(200, i+1) if i >= 50 else None
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "close": round(p, 2),
            "sma50": round(sma50, 2) if sma50 else None,
            "sma200": round(sma200, 2) if sma200 else None,
        })
    return history


def main():
    random.seed(42)

    # 模拟当前各指标
    data = {
        "QQQ": {
            "price": 612.50, "change_pct": 1.23,
            "sma20": 605.20, "sma50": 598.40, "sma200": 565.30,
            "sma200_slope_up": True, "above_sma200": True, "above_sma50": True,
            "golden_cross": True, "dist_sma200_pct": 8.35, "rsi14": 62.4,
        },
        "SPY": {
            "price": 595.30, "change_pct": 0.85,
            "sma20": 590.00, "sma50": 585.00, "sma200": 560.00,
            "sma200_slope_up": True, "above_sma200": True, "above_sma50": True,
            "golden_cross": True, "dist_sma200_pct": 6.30, "rsi14": 58.2,
        },
        "RSP": {
            "price": 185.40, "change_pct": 0.45,
            "sma20": 184.20, "sma50": 183.50, "sma200": 178.00,
            "sma200_slope_up": True, "above_sma200": True, "above_sma50": True,
            "golden_cross": True, "dist_sma200_pct": 4.16, "rsi14": 53.8,
        },
        "QQEW": {
            "price": 142.10, "change_pct": 0.32,
            "sma20": 141.00, "sma50": 140.50, "sma200": 135.00,
            "sma200_slope_up": True, "above_sma200": True, "above_sma50": True,
            "golden_cross": True, "dist_sma200_pct": 5.26, "rsi14": 52.1,
        },
        "VIX": {
            "price": 17.85, "change_pct": -2.15,
            "sma20": 18.50, "sma50": 19.20, "sma200": 17.80,
            "sma200_slope_up": False, "above_sma200": True, "above_sma50": False,
            "golden_cross": True, "dist_sma200_pct": 0.28, "rsi14": 42.5,
        },
        "VIX3M": {
            "price": 19.65, "change_pct": -0.85,
            "sma20": 20.10, "sma50": 20.50, "sma200": 19.50,
            "sma200_slope_up": True, "above_sma200": True, "above_sma50": False,
            "golden_cross": True, "dist_sma200_pct": 0.77, "rsi14": 45.0,
        },
        "VVIX": {
            "price": 88.30, "change_pct": -1.20,
            "sma20": 90.50, "sma50": 92.30, "sma200": 95.00,
            "sma200_slope_up": False, "above_sma200": False, "above_sma50": False,
            "golden_cross": False, "dist_sma200_pct": -7.05, "rsi14": 38.2,
        },
        "MOVE": {
            "price": 97.50, "change_pct": -1.80,
            "sma20": 100.20, "sma50": 102.50, "sma200": 105.00,
            "sma200_slope_up": False, "above_sma200": False, "above_sma50": False,
            "golden_cross": False, "dist_sma200_pct": -7.14, "rsi14": 40.5,
        },
        "MAGS": {
            "price": 68.20, "change_pct": 1.65,
            "sma20": 67.00, "sma50": 65.50, "sma200": 60.00,
            "sma200_slope_up": True, "above_sma200": True, "above_sma50": True,
            "golden_cross": True, "dist_sma200_pct": 13.67, "rsi14": 65.0,
        },
        "HYG": {
            "price": 80.45, "change_pct": 0.15,
            "sma20": 80.20, "sma50": 80.10, "sma200": 79.50,
            "sma200_slope_up": True, "above_sma200": True, "above_sma50": True,
            "golden_cross": True, "dist_sma200_pct": 1.19, "rsi14": 54.5,
        },
        "JNK": {
            "price": 96.92, "change_pct": 0.10,
            "sma20": 96.80, "sma50": 96.50, "sma200": 95.80,
            "sma200_slope_up": True, "above_sma200": True, "above_sma50": True,
            "golden_cross": True, "dist_sma200_pct": 1.17, "rsi14": 53.0,
        },
        "TLT": {
            "price": 91.20, "change_pct": -0.45,
            "sma20": 92.50, "sma50": 93.00, "sma200": 95.00,
            "sma200_slope_up": False, "above_sma200": False, "above_sma50": False,
            "golden_cross": False, "dist_sma200_pct": -4.00, "rsi14": 41.2,
        },
        "IEF": {
            "price": 95.80, "change_pct": -0.20,
            "sma20": 96.20, "sma50": 96.50, "sma200": 97.20,
            "sma200_slope_up": False, "above_sma200": False, "above_sma50": False,
            "golden_cross": False, "dist_sma200_pct": -1.44, "rsi14": 44.8,
        },
        "LQD": {
            "price": 108.50, "change_pct": -0.18,
            "sma20": 108.80, "sma50": 109.00, "sma200": 109.50,
            "sma200_slope_up": False, "above_sma200": False, "above_sma50": False,
            "golden_cross": False, "dist_sma200_pct": -0.91, "rsi14": 46.0,
        },
        "SHY": {
            "price": 82.50, "change_pct": -0.05,
            "sma20": 82.55, "sma50": 82.60, "sma200": 82.80,
            "sma200_slope_up": False, "above_sma200": False, "above_sma50": False,
            "golden_cross": False, "dist_sma200_pct": -0.36, "rsi14": 47.5,
        },
        "DXY": {
            "price": 104.20, "change_pct": 0.35,
            "sma20": 103.80, "sma50": 103.50, "sma200": 102.50,
            "sma200_slope_up": True, "above_sma200": True, "above_sma50": True,
            "golden_cross": True, "dist_sma200_pct": 1.66, "rsi14": 56.5,
        },
        "GLD": {
            "price": 285.50, "change_pct": -0.80,
            "sma20": 286.20, "sma50": 285.00, "sma200": 270.00,
            "sma200_slope_up": True, "above_sma200": True, "above_sma50": True,
            "golden_cross": True, "dist_sma200_pct": 5.74, "rsi14": 55.0,
        },
    }

    ratios = {
        "VIX_VIX3M": round(data["VIX"]["price"] / data["VIX3M"]["price"], 3),
        "VIX_in_backwardation": False,
        "HYG_IEF": round(data["HYG"]["price"] / data["IEF"]["price"], 4),
        "JNK_TLT": round(data["JNK"]["price"] / data["TLT"]["price"], 4),
        "QQQ_QQEW": round(data["QQQ"]["price"] / data["QQEW"]["price"], 4),
        "MAGS_RSP": round(data["MAGS"]["price"] / data["RSP"]["price"], 4),
    }

    scoring = {
        "total_score": 9,
        "regime": "看多",
        "position_suggestion": "QQQ 80% + TQQQ 10% + 现金 10%",
        "color": "success",
        "layers": {
            "layer1_price": {
                "score": 4, "name": "价格-动量", "max": 4,
                "details": [
                    "✅ QQQ 在 200SMA 上方且向上 (+2)",
                    "✅ 50SMA > 200SMA 金叉态 (+1)",
                    "✅ RSI 62.4 健康看多 (+1)",
                ]
            },
            "layer2_volatility": {
                "score": 3, "name": "波动率-情绪", "max": 5,
                "details": [
                    "✅ VIX 17.9 正常 (+1)",
                    "✅ VIX/VIX3M 0.908 contango (+1)",
                    "✅ MOVE 98 平静 (+1)",
                ]
            },
            "layer3_structure": {
                "score": 2, "name": "内部结构", "max": 3,
                "details": [
                    "✅ SPY+RSP 均在 200SMA 上方 (+1)",
                    "✅ Nasdaq 内部宽度健康 (+1)",
                ]
            },
            "layer4_macro": {
                "score": 2, "name": "宏观-信用", "max": 3,
                "details": [
                    "✅ HYG 在 50SMA 上方: 信用健康 (+1)",
                    "✅ JNK 在 200SMA 上方 (+1)",
                ]
            },
        }
    }

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_mock": True,
        "data": data,
        "ratios": ratios,
        "scoring": scoring,
        "history": {
            "QQQ": generate_history(565, 120, 0.012),
            "VIX": generate_history(18, 120, 0.04),
        },
        "fred": {
            "T10Y2Y": {"name": "10年-2年期限利差", "value": 0.51, "date": "2026-05-16"},
            "DGS10": {"name": "10年期国债收益率", "value": 4.30, "date": "2026-05-16"},
            "DGS2": {"name": "2年期国债收益率", "value": 3.79, "date": "2026-05-16"},
            "UNRATE": {"name": "失业率", "value": 4.1, "date": "2026-04-01"},
        }
    }

    out_path = Path(__file__).parent.parent / "data" / "dashboard.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ 模拟数据已生成: {out_path}")
    print(f"📊 综合评分: {scoring['total_score']} ({scoring['regime']})")


if __name__ == "__main__":
    main()
