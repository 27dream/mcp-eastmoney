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
    Tool(
        name="get_stock_quote",
        description=(
            "获取A股个股实时行情（价格、涨跌幅、成交量、换手率、市盈率等）。"
            "Get real-time quote for an A-share stock — price, change %, volume, "
            "turnover rate, P/E. 数据来源东方财富，延迟约15分钟。"
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
    Tool(
        name="get_kline",
        description=(
            "获取个股K线数据（日/周/月/分钟级）。Historical K-line data — daily, "
            "weekly, monthly, or intraday (5/15/30/60 min). 用于趋势分析、回测、技术指标计算。"
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
