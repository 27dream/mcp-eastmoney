# 🤖 Claude Desktop × mcp-eastmoney 集成完整教程

把 mcp-eastmoney 接到 Claude Desktop，5 分钟搞定。

## 🚀 步骤

### 1️⃣ 安装 uv（如果你还没有）

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2️⃣ 配置 Claude Desktop

打开配置文件：

| 系统 | 路径 |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

把 [`claude_desktop_config.json`](claude_desktop_config.json) 的内容粘进去（如果已有 `mcpServers` 节点，合并 `eastmoney` 字段即可）：

```json
{
  "mcpServers": {
    "eastmoney": {
      "command": "uvx",
      "args": ["mcp-eastmoney"]
    }
  }
}
```

### 3️⃣ 重启 Claude Desktop

关闭 Claude Desktop **整个进程**（不是关窗口），再打开。在对话框右下角看到 🔧 工具图标，点开能看到 5 个工具：
- `get_stock_quote`
- `search_stock`
- `main_fund_rank`
- `sector_fund_flow`
- `get_kline`

## 🎯 试一试这些 prompts

### 行情查询
```
茅台现在多少钱？
宁德时代今天涨了多少？
查一下 002594 的实时行情。
```

### 主力资金
```
今天主力净流入排前 10 是哪些股？
科创板今天主力流入最多的 5 只股票。
```

### 板块热力
```
今天哪些行业板块涨得最好？
概念板块资金流向排前 20 给我看看。
```

### K 线分析
```
帮我分析一下贵州茅台最近 60 天的趋势。
600519 最近 30 天 K 线，给个技术分析。
```

### 组合任务（让 Claude 自己组合工具）
```
我想买"AI 算力"概念里主力资金最猛的票，帮我筛选一下。
→ Claude 会自动调 sector_fund_flow + main_fund_rank + get_stock_quote 串起来
```

## 🐛 常见问题

**Q: 重启后看不到工具？**
- 检查 `uvx --version` 能正常运行
- 看 Claude Desktop 日志：`~/Library/Logs/Claude/mcp-server-eastmoney.log`（macOS）
- 试试改用绝对路径：`"command": "/Users/xxx/.local/bin/uvx"`

**Q: 提示 "Connection closed"？**
- 多半是网络问题。东方财富 push2delay 接口偶尔抽风，过几秒重试

**Q: 想改用本地开发版？**
```json
{
  "mcpServers": {
    "eastmoney": {
      "command": "python",
      "args": ["-m", "mcp_eastmoney"],
      "cwd": "/path/to/your/mcp-eastmoney"
    }
  }
}
```

## 🔌 其他客户端

- **Cursor**：见 [`cursor_mcp_config.json`](cursor_mcp_config.json)，配置位置 `~/.cursor/mcp.json`
- **Cline (VS Code)**：扩展设置里搜 `cline.mcpServers`，结构同上
- **Continue.dev**：`~/.continue/config.yaml` 加 `mcpServers` 节点

---

⭐ 觉得有用请去 [GitHub](https://github.com/27dream/mcp-eastmoney) 给个 star！
