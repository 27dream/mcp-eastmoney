"""Live integration smoke test — hits real Eastmoney endpoints."""
import asyncio
import json
from mcp_eastmoney.eastmoney import EastmoneyClient


async def main():
    c = EastmoneyClient()
    try:
        print("=" * 60)
        print("[1/5] get_quote('300750') 宁德时代")
        print("=" * 60)
        q = await c.get_quote("300750")
        print(json.dumps(q, ensure_ascii=False, indent=2))

        print("\n" + "=" * 60)
        print("[2/5] search('宁德')")
        print("=" * 60)
        s = await c.search("宁德")
        print(json.dumps(s, ensure_ascii=False, indent=2))

        print("\n" + "=" * 60)
        print("[3/5] main_fund_rank(limit=5)")
        print("=" * 60)
        r = await c.main_fund_rank(limit=5)
        print(json.dumps(r, ensure_ascii=False, indent=2))

        print("\n" + "=" * 60)
        print("[4/5] sector_fund_flow('industry', 5)")
        print("=" * 60)
        sf = await c.sector_fund_flow("industry", 5)
        print(json.dumps(sf, ensure_ascii=False, indent=2))

        print("\n" + "=" * 60)
        print("[5/5] get_kline('600519', 'daily', 5) 茅台")
        print("=" * 60)
        k = await c.get_kline("600519", "daily", 5)
        print(json.dumps(k, ensure_ascii=False, indent=2))
    finally:
        await c.aclose()


if __name__ == "__main__":
    asyncio.run(main())
