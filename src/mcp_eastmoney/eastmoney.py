"""Eastmoney HTTP client — wraps push2delay.eastmoney.com (free, no API key)."""
from __future__ import annotations

import httpx
from typing import Any

# Free public endpoints — no API key required
QUOTE_HOST = "https://push2delay.eastmoney.com"
KLINE_HOST = "https://push2his.eastmoney.com"
SEARCH_HOST = "https://searchadapter.eastmoney.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

# ---- helpers ----------------------------------------------------------------

def market_prefix(code: str) -> str:
    """Return 0 (深市) or 1 (沪市) prefix for a 6-digit A-share code."""
    code = code.strip()
    if code.startswith(("60", "68", "11", "13", "5")):
        return "1"  # 沪市 主板/科创/转债/ETF
    return "0"  # 深市 主板/创业板/北交所


def _safe(v: Any, default: float = 0.0) -> float:
    """Eastmoney returns '-' for halted stocks; coerce safely."""
    try:
        f = float(v)
        return default if f != f else f  # NaN check
    except (TypeError, ValueError):
        return default


def _fmt_money(v: float) -> str:
    """Format CNY amount: 亿 / 万 / raw."""
    if abs(v) >= 1e8:
        return f"{v/1e8:.2f}亿"
    if abs(v) >= 1e4:
        return f"{v/1e4:.2f}万"
    return f"{v:.2f}"


# ---- HTTP client ------------------------------------------------------------

class EastmoneyClient:
    def __init__(self, timeout: float = 10.0):
        self._client = httpx.AsyncClient(timeout=timeout, headers=HEADERS)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, url: str) -> dict:
        r = await self._client.get(url)
        r.raise_for_status()
        return r.json()

    # ---- 1. 实时行情 ----
    async def get_quote(self, code: str) -> dict:
        """Real-time quote for a single stock. Returns parsed dict."""
        m = market_prefix(code)
        url = (
            f"{QUOTE_HOST}/api/qt/stock/get?secid={m}.{code}"
            "&fields=f43,f44,f45,f46,f47,f48,f57,f58,f60,f62,f168,f169,f170,f50,f71,f152"
        )
        d = (await self._get(url)).get("data") or {}
        if not d:
            return {"error": f"未找到股票 {code}"}
        # 价格字段在东财通常需除以100（用 f152 小数位修正）
        scale = 10 ** _safe(d.get("f152"), 2)
        scale = scale or 100
        cur = _safe(d.get("f43")) / scale
        prev = _safe(d.get("f60")) / scale
        change = cur - prev
        pct = (change / prev * 100) if prev else 0.0
        return {
            "code": d.get("f57"),
            "name": d.get("f58"),
            "price": round(cur, 2),
            "change": round(change, 2),
            "change_pct": round(pct, 2),
            "open": round(_safe(d.get("f46")) / scale, 2),
            "high": round(_safe(d.get("f44")) / scale, 2),
            "low": round(_safe(d.get("f45")) / scale, 2),
            "prev_close": round(prev, 2),
            "volume": int(_safe(d.get("f47"))),
            "amount": _fmt_money(_safe(d.get("f48"))),
            "turnover_rate": round(_safe(d.get("f168")) / 100, 2),
            "pe": round(_safe(d.get("f169")) / 100, 2),
        }

    # ---- 2. 主力资金排行 ----
    async def main_fund_rank(self, limit: int = 20, market: str = "all") -> list[dict]:
        """Top stocks by main net inflow."""
        fs_map = {
            "all": "m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23,m:1+t:8",
            "sh": "m:0+t:6,m:0+t:13,m:0+t:80",
            "sz": "m:1+t:2,m:1+t:23,m:1+t:8",
            "cyb": "m:0+t:80",
            "kcb": "m:1+t:23",
        }
        fs = fs_map.get(market, fs_map["all"])
        url = (
            f"{QUOTE_HOST}/api/qt/clist/get?pn=1&pz={limit}&po=1&np=1&fltt=2&invt=2"
            f"&fid=f62&fs={fs}&fields=f12,f14,f2,f3,f62,f184,f66,f70,f76,f78"
        )
        diff = (await self._get(url)).get("data", {}).get("diff", []) or []
        out = []
        for r in diff:
            out.append({
                "code": r.get("f12"),
                "name": r.get("f14"),
                "price": _safe(r.get("f2")),
                "change_pct": _safe(r.get("f3")),
                "main_net_inflow": _fmt_money(_safe(r.get("f62"))),
                "main_net_pct": _safe(r.get("f184")),
                "super_large_net": _fmt_money(_safe(r.get("f66"))),
                "large_net": _fmt_money(_safe(r.get("f70"))),
                "medium_net": _fmt_money(_safe(r.get("f76"))),
                "small_net": _fmt_money(_safe(r.get("f78"))),
            })
        return out

    # ---- 3. 板块资金流 ----
    async def sector_fund_flow(self, kind: str = "industry", limit: int = 20) -> list[dict]:
        """Sector-level fund flow ranking. kind: industry / concept."""
        fs = "m:90+t:2" if kind == "industry" else "m:90+t:3"
        url = (
            f"{QUOTE_HOST}/api/qt/clist/get?pn=1&pz={limit}&po=1&np=1&fltt=2&invt=2"
            f"&fid=f62&fs={fs}&fields=f12,f14,f2,f3,f62,f184,f128,f136"
        )
        diff = (await self._get(url)).get("data", {}).get("diff", []) or []
        out = []
        for r in diff:
            out.append({
                "code": r.get("f12"),
                "name": r.get("f14"),
                "change_pct": _safe(r.get("f3")),
                "main_net_inflow": _fmt_money(_safe(r.get("f62"))),
                "main_net_pct": _safe(r.get("f184")),
                "leading_stock": r.get("f128") or "-",
                "leading_change_pct": _safe(r.get("f136")),
            })
        return out

    # ---- 4. K线 ----
    async def get_kline(self, code: str, period: str = "daily", limit: int = 30) -> dict:
        """Historical K-line. period: daily / weekly / monthly / 5min / 15min / 30min / 60min."""
        klt_map = {
            "daily": 101, "weekly": 102, "monthly": 103,
            "5min": 5, "15min": 15, "30min": 30, "60min": 60,
        }
        klt = klt_map.get(period, 101)
        m = market_prefix(code)
        url = (
            f"{KLINE_HOST}/api/qt/stock/kline/get?secid={m}.{code}"
            f"&klt={klt}&fqt=1&end=20500101&lmt={limit}"
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        )
        data = (await self._get(url)).get("data") or {}
        klines = data.get("klines") or []
        rows = []
        for line in klines:
            p = line.split(",")
            if len(p) < 8:
                continue
            rows.append({
                "date": p[0], "open": float(p[1]), "close": float(p[2]),
                "high": float(p[3]), "low": float(p[4]),
                "volume": int(p[5]), "amount": _fmt_money(float(p[6])),
                "amplitude": float(p[7]) if len(p) > 7 else 0.0,
                "change_pct": float(p[8]) if len(p) > 8 else 0.0,
                "change": float(p[9]) if len(p) > 9 else 0.0,
                "turnover": float(p[10]) if len(p) > 10 else 0.0,
            })
        return {
            "code": data.get("code"),
            "name": data.get("name"),
            "period": period,
            "klines": rows,
        }

    # ---- 5. 股票搜索 ----
    async def search(self, keyword: str, limit: int = 10) -> list[dict]:
        """Search A-share stocks by name / code / pinyin."""
        url = (
            f"{SEARCH_HOST}/api/suggest/get?input={keyword}&type=14"
            f"&token=D43BF722C8E33BDC906FB84D85E326E8&count={limit}"
        )
        r = await self._client.get(url)
        # Response is JSONP-ish but with cb empty it's plain JSON
        try:
            text = r.text.strip()
            if text.startswith("("):
                text = text[1:-1]
            import json
            d = json.loads(text)
        except Exception:
            return []
        items = d.get("QuotationCodeTable", {}).get("Data", []) or []
        out = []
        for it in items:
            if it.get("Classify") != "AStock":
                continue
            out.append({
                "code": it.get("Code"),
                "name": it.get("Name"),
                "pinyin": it.get("PinYin"),
                "market": it.get("SecurityTypeName"),
            })
        return out
