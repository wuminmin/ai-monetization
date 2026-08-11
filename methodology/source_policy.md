# 来源政策

## 可信度分级

| 等级 | 定义 | 示例 |
|------|------|------|
| A | 厂商官方定价页、监管文件、财报、模型卡 | AWS pricing page, PLDT 财报, OpenRouter model description |
| B | 可靠研究机构完整报告 | MarketsandMarkets, Mordor Intelligence |
| C | 媒体报道、搜索结果摘要 | 行业新闻, LinkedIn 分析 |
| D | 内部估算或未验证假设 | PUE 估算, 空闲功耗估算 |
| E | 纯假设（无外部来源） | 利用率假设 |

## 规则
- 每个关键数据点必须在 sources.csv 中有 claim_id
- 来源 URL、published_at、accessed_at 必填
- D 级和 E 级数据在报告中必须标注为"估算"或"假设"
- 不使用"实时校准"等表述；明确标注为"截至 YYYY-MM-DD 的数据快照"
- 竞品价格必须记录 provider、route、region、pricing_type
