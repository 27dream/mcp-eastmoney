"""mcp-eastmoney MCP server — exposes Eastmoney A-share data as MCP tools."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .eastmoney import EastmoneyClient

app: Server = Server("mcp-eastmoney")
_client: EastmoneyClient | None = None


def _c() -> EastmoneyClient:
    global _client
    if _client is None:
        _client = EastmoneyClient()
    return _client


# ---- Tool registry ----------------------------------------------------------

TOOLS: list[Tool] = [
    # ---- 1. 实时行情 ----
    Tool(
        name="get_stock_quote",
        description=(
            "获取A股个股实时行情（价格、涨跌幅、成交量、换手率、市盈率等）。"
            "Get real-time quote for an A-share stock. 数据来源东方财富，延迟约15分钟。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "6位股票代码，如 600519（贵州茅台）、300750（宁德时代）",
                }
            },
            "required": ["code"],
        },
    ),
    # ---- 2. 股票搜索 ----
    Tool(
        name="search_stock",
        description=(
            "按名称、代码或拼音搜索A股股票。Search A-share stocks by name / code / "
            "pinyin (e.g. '宁德', 'NDSD', '300750')."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"},
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 20},
            },
            "required": ["keyword"],
        },
    ),
    # ---- 3. 主力资金排行 ----
    Tool(
        name="main_fund_rank",
        description=(
            "主力资金净流入排行榜。Top stocks ranked by main capital net inflow. "
            "可按市场过滤：all / sh(沪市) / sz(深市) / cyb(创业板) / kcb(科创板)。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                "market": {
                    "type": "string",
                    "enum": ["all", "sh", "sz", "cyb", "kcb"],
                    "default": "all",
                },
            },
        },
    ),
    # ---- 4. 板块资金流 ----
    Tool(
        name="sector_fund_flow",
        description=(
            "板块资金流向排行（行业板块或概念板块）。Sector fund flow ranking. "
            "kind: industry(行业) / concept(概念)。返回涨跌幅、主力净流入、领涨股。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["industry", "concept"], "default": "industry"},
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 50},
            },
        },
    ),
    # ---- 5. K线 ----
    Tool(
        name="get_kline",
        description=(
            "获取个股K线数据（日/周/月/分钟级）。Historical K-line. "
            "用于趋势分析、回测、技术指标计算。支持A股、港股(116.)、美股(105.)。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "6位股票代码"},
                "period": {
                    "type": "string",
                    "enum": ["daily", "weekly", "monthly", "5min", "15min", "30min", "60min"],
                    "default": "daily",
                },
                "limit": {"type": "integer", "default": 30, "minimum": 1, "maximum": 500},
            },
            "required": ["code"],
        },
    ),
    # ================================================================
    #  NEW: 6. 北向资金
    # ================================================================
    Tool(
        name="north_bound_flow",
        description=(
            "北向资金流向数据（北向合计 + 沪股通 + 深股通明细）。"
            "North-bound capital flow via Stock Connect. "
            "返回每日买入/卖出/净额，单位元。可直接判断外资动向。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "default": 5, "minimum": 1, "maximum": 30,
                         "description": "获取最近N天的北向资金数据"},
            },
        },
    ),
    # ================================================================
    #  NEW: 7. 龙虎榜 - 涨停池
    # ================================================================
    Tool(
        name="limit_up_pool",
        description=(
            "涨停板股票池（龙虎榜数据）。Today's limit-up stocks — "
            "连板数、封板时间、封板资金、炸板次数、所属行业。用于短线情绪分析。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 200,
                          "description": "返回数量"},
                "sort": {
                    "type": "string",
                    "default": "fbt:asc",
                    "description": "排序: fbt:asc(按封板时间), zdp:desc(按涨幅), lbc:desc(按连板)",
                },
            },
        },
    ),
    # ================================================================
    #  NEW: 8. 技术指标 (MA / MACD / KDJ)
    # ================================================================
    Tool(
        name="technical_indicators",
        description=(
            "计算个股技术指标：MA5/10/20/30/60 均线 + MACD (DIF/DEA/柱) + KDJ。"
            "Technical indicators — moving averages, MACD, KDJ, "
            "基于东财K线数据本地计算，无需额外API。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "6位股票代码"},
                "period": {
                    "type": "string",
                    "enum": ["daily", "weekly", "monthly"],
                    "default": "daily",
                },
                "limit": {
                    "type": "integer", "default": 120, "minimum": 60, "maximum": 500,
                    "description": "取多少根K线用于计算（建议 >= 120，长周期需更多数据）",
                },
            },
            "required": ["code"],
        },
    ),
    # ================================================================
    #  NEW: 9. 港股/美股行情
    # ================================================================
    Tool(
        name="hk_us_quote",
        description=(
            "获取港股或美股实时行情。Hong Kong / US stock real-time quote. "
            "例如 00700(腾讯)、AAPL(苹果)、TSLA(特斯拉)。数据来源于东方财富。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "股票代码，港股如 00700，美股如 AAPL"},
                "market": {
                    "type": "string",
                    "enum": ["hk", "us"],
                    "default": "hk",
                    "description": "市场: hk(港股) / us(美股)",
                },
            },
            "required": ["code"],
        },
    ),
    Tool(
        name="hk_us_kline",
        description=(
            "获取港股或美股K线数据。HK / US stock K-line. "
            "支持日/周/月线及分钟级。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "股票代码"},
                "market": {"type": "string", "enum": ["hk", "us"], "default": "hk"},
                "period": {
                    "type": "string",
                    "enum": ["daily", "weekly", "monthly", "5min", "15min", "30min", "60min"],
                    "default": "daily",
                },
                "limit": {"type": "integer", "default": 30, "minimum": 1, "maximum": 500},
            },
            "required": ["code"],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    c = _c()
    try:
        if name == "get_stock_quote":
            data = await c.get_quote(arguments["code"])
        elif name == "search_stock":
            data = await c.search(arguments["keyword"], arguments.get("limit", 10))
        elif name == "main_fund_rank":
            data = await c.main_fund_rank(
                arguments.get("limit", 20), arguments.get("market", "all")
            )
        elif name == "sector_fund_flow":
            data = await c.sector_fund_flow(
                arguments.get("kind", "industry"), arguments.get("limit", 20)
            )
        elif name == "get_kline":
            data = await c.get_kline(
                arguments["code"],
                arguments.get("period", "daily"),
                arguments.get("limit", 30),
            )
        # ---- NEW tools ----
        elif name == "north_bound_flow":
            data = await c.north_bound_flow(arguments.get("days", 5))
        elif name == "limit_up_pool":
            data = await c.limit_up_pool(
                date_str=arguments.get("date"),
                limit=arguments.get("limit", 50),
                sort=arguments.get("sort", "fbt:asc"),
            )
        elif name == "technical_indicators":
            data = await c.technical_indicators(
                arguments["code"],
                arguments.get("period", "daily"),
                arguments.get("limit", 120),
            )
        elif name == "hk_us_quote":
            data = await c.hk_us_quote(
                arguments["code"],
                arguments.get("market", "hk"),
            )
        elif name == "hk_us_kline":
            data = await c.hk_us_kline(
                arguments["code"],
                arguments.get("market", "hk"),
                arguments.get("period", "daily"),
                arguments.get("limit", 30),
            )
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error calling {name}: {e}")]

    return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
