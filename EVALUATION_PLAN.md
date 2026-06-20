# Evaluation Plan

## 1. 評估目標

POC 的評估不是看回答像不像聊天，而是看整個 engine 是否：

- 一致
- 有區辨度
- 可重跑
- 可追溯
- 能發現安全風險
- 能輸出對 founder 有用的下一步

## 2. 評估面向

| 面向 | 問題 | 方法 |
| --- | --- | --- |
| Persona consistency | 同一 persona 重跑是否自洽 | seeded rerun + rubric review |
| Persona differentiation | 不同 persona 是否真的有不同反應 | pairwise comparison |
| Sampling diversity | panel 是否覆蓋預期人群 | distribution checks |
| Report completeness | 報告章節是否完整 | template assertions |
| Auditor recall | 明顯風險是否能被抓到 | adversarial fixtures |
| Stability | 同 brief 同 seed 是否相對穩定 | golden runs |
| Founder usefulness | founder 是否能據此採取下一步 | human scoring |

## 3. 自動化測試

### Unit tests

- schema validation
- ID generation
- sampling filters
- prompt loading
- report section rendering

### Integration tests

- sample brief -> sample panel -> mock responses -> report
- seeded run reproducibility
- run archive completeness

### Safety tests

- forbidden phrases scan
- high-stakes disclaimer insertion
- auditor category coverage

## 4. 人工評分 Rubric

每份 report 可用 1 到 5 分評估：

1. 是否準確理解 founder concept
2. objections 是否具體
3. triggers 是否有啟發性
4. risk observations 是否安全且可行
5. next-step validation plan 是否可執行

## 5. Golden Fixture 策略

建立少量固定測試 brief：

- B2B SaaS
- consumer subscription
- privacy-sensitive product
- politically sensitive wording case
- budget-constrained audience case

每次修改 prompt 或 sampling logic，都跑固定 fixture 做 diff。

## 6. POC Gate

在進入下一里程碑前，至少應通過：

- same seed 可重建同一 panel
- report 章節完整
- auditor 能抓出預設風險樣本
- run archive 無缺檔
- forbidden-output 測試為零
