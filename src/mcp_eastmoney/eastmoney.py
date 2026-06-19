"""Eastmoney HTTP client — wraps push2delay.eastmoney.com (free, no API key)."""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

import httpx

# Free public endpoints — no API key required
QUOTE_HOST = "https://push2delay.eastmoney.com"
KLINE_HOST = "https://push2his.eastmoney.com"
SEARCH_HOST = "https://searchadapter.eastmoney.com"
EX_HOST = "https://push2ex.eastmoney.com"

# Fallback K-line source (Sina, reliable outside China)
SINA_KLINE = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

# ---- helpers ----------------------------------------------------------------


def market_prefix(code: str) -> str:
    """Return 0 (深市) or 1 (沪市) prefix for a 6-digit A-share code.
    Also supports 116 (港股), 105 (美股)."""
    code = code.strip()
    if code.startswith(("60", "68", "11", "13", "5")):
        return "1"  # 沪市主板/科创/转债/ETF
    return "0"  # 深市主板/创业板/北交所


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


# ---- MACD helper (纯本地计算，无需额外依赖) ----


def _calc_ema(values: list[float], period: int) -> list[float]:
    """Exponential Moving Average."""
    ema: list[float] = []
    multiplier = 2.0 / (period + 1)
    for i, v in enumerate(values):
        if i == 0:
            ema.append(v)
        else:
            ema.append((v - ema[-1]) * multiplier + ema[-1])
    return ema


def calc_macd(closes: list[float], fast=12, slow=26, signal=9) -> list[dict]:
    """Calculate MACD line, signal line, and histogram."""
    if len(closes) < slow:
        return []
    ema_fast = _calc_ema(closes, fast)
    ema_slow = _calc_ema(closes, slow)
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
    signal_line = _calc_ema(macd_line, signal)
    hist = [macd_line[i] - signal_line[i] for i in range(len(closes))]
    out = []
    for i in range(len(closes)):
        out.append({
            "macd": round(macd_line[i], 4),
            "signal": round(signal_line[i], 4),
            "histogram": round(hist[i], 4),
        })
    return out


def calc_kdj(highs: list[float], lows: list[float], closes: list[float], period=9) -> list[dict]:
    """Calculate KDJ (Stochastic oscillator)."""
    if len(closes) < period:
        return []
    out = []
    k = 50.0
    d = 50.0
    for i in range(len(closes)):
        if i >= period - 1:
            hh = max(highs[i - period + 1:i + 1])
            ll = min(lows[i - period + 1:i + 1])
        else:
            hh = max(highs[:i + 1])
            ll = min(lows[:i + 1])
        rsv = 0.0
        if hh != ll:
            rsv = (closes[i] - ll) / (hh - ll) * 100
        k = 2.0 / 3 * k + 1.0 / 3 * rsv
        d = 2.0 / 3 * d + 1.0 / 3 * k
        j = 3 * k - 2 * d
        out.append({"k": round(k, 2), "d": round(d, 2), "j": round(j, 2)})
    return out


def calc_ma(closes: list[float], periods: list[int]) -> dict[str, list[float | None]]:
    """Simple Moving Averages for given periods."""
    result: dict[str, list[float | None]] = {}
    for p in periods:
        key = f"MA{p}"
        vals: list[float | None] = []
        for i in range(len(closes)):
            if i < p - 1:
                vals.append(None)
            else:
                vals.append(round(sum(closes[i - p + 1:i + 1]) / p, 2))
        result[key] = vals
    return result


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

    async def _get_text(self, url: str) -> str:
        r = await self._client.get(url)
        r.raise_for_status()
        return r.text

    # ---- 1. 实时行情 ----
    async def get_quote(self, code: str, secid_prefix: str | None = None) -> dict:
        """Real-time quote for a single stock. Supports A-share,港股,美股."""
        if secid_prefix:
            prefix = secid_prefix
        else:
            prefix = market_prefix(code)
        url = (
            f"{QUOTE_HOST}/api/qt/stock/get?secid={prefix}.{code}"
            "&fields=f43,f44,f45,f46,f47,f48,f57,f58,f60,f62,f168,f169,f170,f50,f71,f152"
        )
        d = (await self._get(url)).get("data") or {}
        if not d:
            return {"error": f"未找到 {code}"}
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

    # ---- 4. K线（带新浪兜底） ----
    async def get_kline(self, code: str, period: str = "daily", limit: int = 30,
                        secid_prefix: str | None = None) -> dict:
        """Historical K-line. 支持A股/港股/美股. 自动fallback到新浪(当push2his不通时)。"""
        klt_map = {
            "daily": 101, "weekly": 102, "monthly": 103,
            "5min": 5, "15min": 15, "30min": 30, "60min": 60,
        }
        klt = klt_map.get(period, 101)
        prefix = secid_prefix if secid_prefix else market_prefix(code)

        # 优先：push2his (东财)
        url = (
            f"{KLINE_HOST}/api/qt/stock/kline/get?secid={prefix}.{code}"
            f"&klt={klt}&fqt=1&end=20500101&lmt={limit}"
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        )

        # 港股/美股不走新浪fallback（新浪只有A股）
        is_foreign = secid_prefix in ("116", "105")

        try:
            data = (await self._get(url)).get("data") or {}
            klines = data.get("klines") or []
            if klines:
                return self._parse_klines(data, code, period)
        except Exception:
            if is_foreign:
                # 港股/美股无fallback
                return {"code": code, "name": "", "period": period, "klines": [],
                        "error": "push2his不可达"}

        # fallback: 新浪日K (仅A股，仅日线)
        if not is_foreign and period in ("daily", "5min", "15min", "30min", "60min"):
            try:
                return await self._sina_kline(code, period, limit)
            except Exception:
                pass

        return {"code": code, "name": "", "period": period, "klines": [],
                "error": "所有K线数据源均不可用"}

    def _parse_klines(self, data: dict, code: str, period: str) -> dict:
        """Parse eastmoney kline response into structured data."""
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
            "code": data.get("code") or code,
            "name": data.get("name") or "",
            "period": period,
            "klines": rows,
        }

    async def _sina_kline(self, code: str, period: str, limit: int) -> dict:
        """Fallback K-line from Sina Finance. 仅A股."""
        scale_map = {"daily": 240, "5min": 5, "15min": 15, "30min": 30, "60min": 60}
        scale = scale_map.get(period, 240)
        prefix = "sh" if code.startswith(("60", "68")) else "sz"
        url = (
            f"{SINA_KLINE}?symbol={prefix}{code}"
            f"&scale={scale}&ma=no&datalen={limit}"
        )
        text = await self._get_text(url)
        rows = json.loads(text)
        parsed = []
        prev_close = None
        for i, r in enumerate(rows):
            close = float(r["close"])
            if prev_close is None:
                change_pct = 0.0
            else:
                change_pct = round((close - prev_close) / prev_close * 100, 2)
            parsed.append({
                "date": r["day"],
                "open": float(r["open"]),
                "close": close,
                "high": float(r["high"]),
                "low": float(r["low"]),
                "volume": int(float(r["volume"]) / 100),  # 股→手
                "amount": "",
                "amplitude": 0.0,
                "change_pct": change_pct,
                "change": round(close - prev_close, 2) if prev_close else 0.0,
                "turnover": 0.0,
            })
            prev_close = close
        return {
            "code": code,
            "name": "",
            "period": period,
            "klines": parsed,
        }

    # ---- 5. 股票搜索 ----
    async def search(self, keyword: str, limit: int = 10) -> list[dict]:
        """Search A-share stocks by name / code / pinyin."""
        url = (
            f"{SEARCH_HOST}/api/suggest/get?input={keyword}&type=14"
            f"&token=D43BF722C8E33BDC906FB84D85E326E8&count={limit}"
        )
        r = await self._client.get(url)
        try:
            text = r.text.strip()
            if text.startswith("("):
                text = text[1:-1]
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

    # =====================================================================
    #  NEW: 6. 北向资金 (north-bound capital flow)
    # =====================================================================
    async def north_bound_flow(self, days: int = 5) -> dict:
        """北向资金流向数据（北向合计 + 沪股通 + 深股通明细）。

        返回每日买入/卖出/净额。secid=1 获取全量数据。
        """
        url = (
            f"{QUOTE_HOST}/api/qt/kamt.kline/get?klt=101&lmt={days}"
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56&secid=1"
        )
        data = (await self._get(url)).get("data") or {}

        def parse(raw: list[str]) -> list[dict]:
            out = []
            for v in raw:
                parts = v.split(",")
                if len(parts) < 4:
                    continue
                out.append({
                    "date": parts[0],
                    "buy": float(parts[1]),
                    "sell": float(parts[2]),
                    "net": float(parts[3]),
                })
            return out

        return {
            "north_bound_total": parse(data.get("n2s", [])),         # 北向合计
            "south_bound_total": parse(data.get("s2n", [])),         # 南向合计
            "hk2sh": parse(data.get("hk2sh", [])),                    # 港股通(沪)
            "sh2hk": parse(data.get("sh2hk", [])),                    # 沪股通
            "hk2sz": parse(data.get("hk2sz", [])),                    # 港股通(深)
            "sz2hk": parse(data.get("sz2hk", [])),                    # 深股通
        }

    # =====================================================================
    #  NEW: 7. 龙虎榜 - 涨停池 (limit-up pool / dragon pool)
    # =====================================================================
    async def limit_up_pool(self,
                            date_str: str | None = None,
                            limit: int = 50,
                            sort: str = "fbt:asc") -> dict:
        """获取当日涨停板股票池（龙虎榜数据）。"""
        if date_str is None:
            date_str = date.today().strftime("%Y%m%d")
        url = (
            f"{EX_HOST}/getTopicZTPool"
            f"?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
            f"&Pageindex=0&pagesize={limit}&sort={sort}&date={date_str}"
        )
        raw = (await self._get(url)).get("data") or {}
        pool = raw.get("pool") or []
        out = []
        for p in pool:
            zttj = p.get("zttj") or {}
            out.append({
                "code": p.get("c"),
                "name": p.get("n"),
                "price": _safe(p.get("p")) / 1000 if p.get("p") else 0.0,
                "change_pct": round(_safe(p.get("zdp")), 2),
                "board_count": p.get("lbc", 0),
                "break_count": p.get("zbc", 0),
                "first_seal_time": str(p.get("fbt", "")).zfill(6),
                "last_seal_time": str(p.get("lbt", "")).zfill(6),
                "seal_fund": _fmt_money(_safe(p.get("fund"))),
                "amount": _fmt_money(_safe(p.get("amount"))),
                "industry": p.get("hybk", ""),
                "total_days": zttj.get("days", 0),
                "total_boards": zttj.get("ct", 0),
                "market_cap": _fmt_money(_safe(p.get("ltsz"))),
                "turnover_rate": round(_safe(p.get("hs")), 2),
            })
        return {"date": date_str, "total": raw.get("count", len(out)), "stocks": out}

    # =====================================================================
    #  NEW: 8. 技术指标 (MA / MACD / KDJ)
    # =====================================================================
    async def technical_indicators(self, code: str, period: str = "daily",
                                   limit: int = 120) -> dict:
        """获取个股K线 + 计算技术指标 (MA, MACD, KDJ)。"""
        kdata = await self.get_kline(code, period, limit)
        if not kdata.get("klines"):
            return kdata

        closes = [k["close"] for k in kdata["klines"]]
        highs = [k["high"] for k in kdata["klines"]]
        lows = [k["low"] for k in kdata["klines"]]

        ma = calc_ma(closes, [5, 10, 20, 30, 60])
        macd = calc_macd(closes)
        kdj = calc_kdj(highs, lows, closes)

        result_rows = []
        for i, k in enumerate(kdata["klines"]):
            row = dict(k)
            for mk, mv in ma.items():
                if i < len(mv):
                    row[mk] = mv[i]
            if i < len(macd):
                row["macd"] = macd[i]
            if i < len(kdj):
                row["kdj"] = kdj[i]
            result_rows.append(row)

        return {
            "code": kdata["code"],
            "name": kdata["name"],
            "period": period,
            "source": kdata.get("source", "eastmoney"),
            "klines": result_rows,
        }

    # =====================================================================
    #  NEW: 9. 港股 / 美股实时行情
    # =====================================================================
    async def hk_us_quote(self, code: str, market: str = "hk") -> dict:
        """获取港股或美股实时行情。market: hk(港股) / us(美股)"""
        prefix = "116" if market == "hk" else "105"
        return await self.get_quote(code, secid_prefix=prefix)

    async def hk_us_kline(self, code: str, market: str = "hk",
                          period: str = "daily", limit: int = 30) -> dict:
        """获取港股/美股K线数据。"""
        prefix = "116" if market == "hk" else "105"
        return await self.get_kline(code, period, limit, secid_prefix=prefix)
