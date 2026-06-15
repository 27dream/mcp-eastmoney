# 推广文案合集

仓库：https://github.com/27dream/mcp-eastmoney

---

## 1️⃣ V2EX（节点：分享创造 share）

**标题**：
```
[分享] mcp-eastmoney：让 Claude / Cursor 直接查 A 股的开源 MCP Server
```

**正文**：
```
做了个小工具：mcp-eastmoney，基于 Model Context Protocol 把东方财富的免费公开 API 接进 Claude Desktop / Cursor / Cline 等任何 MCP 客户端。

🔗 https://github.com/27dream/mcp-eastmoney

直接用自然语言问 AI："茅台现在多少钱？"、"今天主力净流入排前 10 是哪些？"、"宁德时代最近 30 天的 K 线"，AI 自己调工具拿真实数据。

特性：
- 完全免费，不需要任何 API Key（用东财公开延时接口 push2delay.eastmoney.com）
- 全 A 股覆盖（沪深京），返回中文字段
- 9 个工具：行情、搜索、主力资金排名、板块资金流、K 线…
- Python + 官方 MCP SDK，一行命令跑：uvx mcp-eastmoney

为什么做这个：搜了一圈 awesome-mcp-servers，国外 finance 分类里有 Polymarket、Binance、yfinance，但 A 股几乎没有，干脆自己写一个。

仓库刚发，欢迎 issue 提需求 / star 鼓励一下 🙏
```

---

## 2️⃣ 即刻

```
做了个开源小工具：mcp-eastmoney 🇨🇳

让 Claude / Cursor 直接查 A 股，免 API Key、开箱即用。

直接问："茅台多少钱""今天主力买了啥""宁德时代K线"——AI 自己调工具拿真实数据。

国内首个东方财富 MCP Server，希望能帮到玩 AI + 炒股的朋友们 🚀

https://github.com/27dream/mcp-eastmoney
```

附图：assets/demo.png

---

## 3️⃣ Twitter / X（中英双发）

**英文版**（主推）：
```
🇨🇳 Just shipped mcp-eastmoney — an MCP server that lets Claude / Cursor query China A-share stocks in real time.

✨ Free public APIs, no API key
✨ 9 tools: quotes, capital flow, K-line, sector flow…
✨ uvx mcp-eastmoney to run

Built for the underserved Chinese market 📈

github.com/27dream/mcp-eastmoney
```

**中文转推**：
```
做了个 MCP Server：mcp-eastmoney 🇨🇳

让 Claude 直接查 A 股，免 API Key，9 个工具开箱即用。

国外有 Polymarket / Binance / yfinance MCP，但 A 股一片空白，自己来填坑了 🛠️

github.com/27dream/mcp-eastmoney
```

---

## 4️⃣ 小红书

**标题**：
```
我用 AI 自己写了个炒股小工具｜开源
```

**正文**：
```
最近发现 Claude Desktop 支持 MCP 协议（就是给 AI 装"插件"），可以让它直接访问外部数据。

国外已经有人写了 MCP 接 Polymarket、币安行情，但 A 股一个都没有 😅

干脆自己写了一个：mcp-eastmoney
- 接东方财富免费公开接口
- 9 个工具：实时行情 / 搜股票 / 主力资金 / 板块资金流 / K 线
- 装上以后直接对 Claude 说："茅台现在多少钱？"它就给我答案

完全开源 MIT 协议，已经传 GitHub：
🔗 27dream/mcp-eastmoney

也提交 PR 到 awesome-mcp-servers（9w star 那个）了 🤞

#开源 #AI工具 #MCP #股票 #ClaudeAI #程序员
```

附图：assets/demo.png（已嵌入 README 头部）

---

## 5️⃣ Reddit r/ClaudeAI / r/LocalLLaMA / r/mcp

```
Title: [Open Source] mcp-eastmoney — MCP Server for China A-share stocks (free, no API key)

Body:

Hey folks, just released mcp-eastmoney — an MCP server that brings China's stock market data to Claude / Cursor / any MCP client.

GitHub: https://github.com/27dream/mcp-eastmoney

Why I built it:
The MCP ecosystem has great finance servers (yfinance, Polymarket, Binance), but A-share data was a blind spot. China is the world's 2nd largest stock market — felt worth filling.

How it works:
- Wraps Eastmoney's public delayed quote APIs (push2delay.eastmoney.com) — no API key needed
- 9 MCP tools: real-time quotes, stock search, main capital flow ranking, sector flow, K-line history, etc.
- Returns Chinese financial fields (主力净流入, 涨停板, 换手率) which most international APIs don't have

Install:
uvx mcp-eastmoney

Then add to claude_desktop_config.json and ask: "What's the main capital inflow ranking today?" — Claude calls the tool and explains.

Open to feedback / PRs / issues. Cheers!
```

---

## 📋 发布检查清单

- [ ] 截图 demo.png 已传到仓库（assets/demo.png）✅
- [ ] README 头部贴图 ✅
- [ ] awesome-mcp-servers PR #7979 已开，已回复 emoji 检查的误报 ✅
- [ ] V2EX 发布
- [ ] 即刻发布
- [ ] Twitter / X 发布
- [ ] 小红书发布
- [ ] （可选）Reddit r/ClaudeAI 发布
- [ ] （可选）Glama.ai 提交以加速 awesome PR 合并

---

## 🎯 第一周目标

- 100-300 stars
- awesome-mcp-servers PR 合并
- 至少 1-2 个 issue / PR 反馈
