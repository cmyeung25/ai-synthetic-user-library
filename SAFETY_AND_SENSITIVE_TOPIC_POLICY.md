# Safety And Sensitive Topic Policy

## 1. 核心原則

1. 反映現實，不放大偏見
2. 描述風險，不生成歧視性 targeting 建議
3. 敏感屬性只用於 context 與 audit，不用於排除客群
4. 高風險領域必須加強 warning
5. 所有最終輸出都必須保留 synthetic-only disclaimer

## 2. Sensitive Topic Auditor 範圍

Auditor 必須檢查：

1. discrimination risk
2. stereotype risk
3. political sensitivity
4. privacy risk
5. inclusion risk
6. manipulation risk
7. accessibility risk
8. cultural risk
9. high-stakes decision risk
10. reporting risk

## 3. 禁止輸出

以下類型不得出現在 final report：

- 某族群不會買，所以不要服務他們
- 某政治立場更值得針對
- 低收入人士不適合做客戶
- 某性別、年齡、地區、身份有固定行為

## 4. 允許輸出格式

允許輸出為：

- 哪些 persona 對 fairness 有疑慮
- 哪些文案容易造成標籤化
- 哪些資料收集要求可能過度侵入
- 哪些定位方式可能帶來政治或品牌風險
- 下一步真人訪談該驗證什麼

## 5. 高風險領域規則

若 brief 涉及以下領域，report 必須額外標示：

- medical
- legal
- financial
- education
- parenting

並加上：

- 不可當成專業建議
- 必須補上真人測試與合規審查
- synthetic users 對高風險決策的參考權重應降低

## 6. Persona 使用規則

- 不可用敏感欄位直接做 discriminatory filtering
- `metaphysical_profile` 不可作決策依據
- persona 的敏感層只用於 response nuance 與 risk surfacing

## 7. 報告強制 Disclaimer

所有 final report 必須包含以下文字：

> 此結果只屬 AI pre-validation，不應取代真人訪談、真實市場測試、專業意見或合規審查。

## 8. 稽核與覆核

建議每次 run 生成：

- auditor findings
- forbidden-output scan result
- final disclaimer presence check

若 audit 失敗或有高風險訊號未分類，report 狀態應標為 `needs_human_review`。
