"""End-to-end MCP protocol test — initialize + list_tools + call_tool."""
import asyncio
import json
import sys
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_eastmoney.server"],
    )
    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        tools = await session.list_tools()
        print(f"✅ Server listed {len(tools.tools)} tools:")
        for t in tools.tools:
            print(f"   - {t.name}: {t.description[:60]}")

        print("\n🔧 Calling get_stock_quote('300750')...")
        result = await session.call_tool("get_stock_quote", {"code": "300750"})
        print(result.content[0].text[:200])

        print("\n🔧 Calling main_fund_rank(limit=3)...")
        result = await session.call_tool("main_fund_rank", {"limit": 3})
        print(result.content[0].text[:300])


if __name__ == "__main__":
    asyncio.run(main())
