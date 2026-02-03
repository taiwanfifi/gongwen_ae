# Paper 2: Structured Bottleneck Improves Factual Fidelity in Government Document Generation

## 論文資訊

- **目標會議**: ACL / EMNLP / NAACL
- **類型**: Long Paper (8 pages)
- **核心貢獻**: 證明結構化中間表示（AE）比端到端生成（Direct）更能保持內容忠實度

---

## Abstract (約 250 字)

Large Language Models can generate fluent government documents, but often introduce hallucinated facts or omit critical details. We hypothesize that a **structured bottleneck**—forcing the model to explicitly extract facts before generation—improves factual fidelity.

We compare two approaches for Taiwan government document generation:
- **AutoEncoder (AE) path**: Extract structured Content JSON → Generate document
- **Direct path**: Generate document directly from topic description

On N=20 documents, AE achieves significantly higher content preservation (0.66 vs 0.35, p<0.001) and overall quality (0.86 vs 0.79, p<0.001). We also demonstrate high cycle consistency (content similarity = 0.965), indicating minimal information loss through the bottleneck.

Our findings suggest that **explicit fact extraction** acts as a guardrail against hallucination, with implications for high-stakes document generation domains.

---

## 1. Introduction (1.5 pages)

### 1.1 The Hallucination Problem in Document Generation
- LLM 生成公文時容易「自由發揮」
- 加入原文沒有的事實（hallucination）
- 遺漏關鍵細節（omission）
- 在政府公文場景下，這是不可接受的

### 1.2 Hypothesis: Structured Bottleneck as Guardrail
- **核心假說**: 強迫模型先提取結構化事實，再基於事實生成，可以減少幻覺
- 類比：人類寫報告時，先列出要點，再擴寫，比直接寫更不容易遺漏

### 1.3 Research Questions
1. AE 路徑是否比 Direct 路徑更能保持內容忠實度？
2. 結構化中間表示的資訊損失有多大（循環一致性）？
3. 這種優勢是否達到統計顯著？

### 1.4 Contributions
1. 提出「結構化瓶頸」假說，解釋為什麼 AE 優於 Direct
2. 設計公平比較實驗（Direct 也經過 Encoder 評估）
3. 在 N=20 樣本上達到 p<0.001 的統計顯著性
4. 展示循環一致性 > 0.96，證明瓶頸的資訊損失很小

---

## 2. Related Work (1 page)

### 2.1 Hallucination in LLM Generation
- 幻覺的類型：intrinsic vs extrinsic
- 現有緩解方法：retrieval augmentation, chain-of-thought
- 與本文差異：我們用**結構化中間表示**作為約束

### 2.2 Structured Generation
- JSON-mode, function calling
- 與本文差異：我們不只是輸出格式化，而是用結構作為**中間表示**

### 2.3 AutoEncoder for Text
- VAE for text, discrete autoencoders
- 與本文差異：我們的 latent space 是**符號化**的（JSON），不是向量

---

## 3. Method (2 pages)

### 3.1 Problem Setup
- 輸入：主題描述 + 格式規則
- 輸出：完整公文
- 評估：與 ground truth 比較內容保留度

### 3.2 Two Generation Paths

**AE Path (Structured Bottleneck)**:
```
Topic + Rules → Generate Content JSON → Generate Document
                      ↓
              Explicit fact extraction
              (entities, events, actions)
```

**Direct Path (End-to-End)**:
```
Topic + Rules → Generate Document directly
                      ↓
              LLM freely generates content
```

### 3.3 Why AE Should Be Better (Hypothesis)
1. **Explicit Fact Anchoring**: Content JSON 明確列出所有事實，Decoder 必須使用
2. **Reduced Freedom**: Direct 可以自由發揮，AE 被結構約束
3. **Verifiable Intermediate**: Content JSON 可以被檢查，錯誤可以在中間階段發現

### 3.4 Fair Comparison Design
- 問題：AE 有 ground truth Content，Direct 沒有，這公平嗎？
- 解決：Direct 生成的公文也經過 Encoder 提取 Content，再與 ground truth 比較
- 這樣兩條路徑用相同標準評估

### 3.5 Cycle Consistency Test
```
Original → Encode → (C₁, R₁) → Decode → Reconstructed → Re-Encode → (C₂, R₂)

Measure: similarity(C₁, C₂), similarity(R₁, R₂)
```
- 如果循環一致性高，說明 AE 的資訊損失小
- 如果低，說明 bottleneck 太緊，丟失資訊

---

## 4. Experimental Setup (1 page)

### 4.1 Dataset
- N = 20 份公文
- 通過「逆向生成」獲得 ground truth Content 和 Rules

### 4.2 Evaluation Metrics

**Primary Metrics (Content Fidelity)**:
| 指標 | 說明 |
|------|------|
| content_preservation | LLM 評審：重建公文是否保留所有事實（1-5 分） |
| content_accuracy | Embedding similarity: predicted vs ground truth Content |

**Secondary Metrics**:
| 指標 | 說明 |
|------|------|
| format_compliance | LLM 評審：格式是否正確 |
| semantic_similarity | 原文 vs 重建文的整體相似度 |
| weighted_total | 綜合加權分數 |

### 4.3 Statistical Test
- Paired t-test（每份文件都有 AE 和 Direct 兩個版本）
- 顯著性水準 α = 0.05

---

## 5. Results (1.5 pages)

### 5.1 Main Comparison: AE vs Direct

| Metric | AE | Direct | Δ | p-value |
|--------|-----|--------|---|---------|
| content_preservation | **0.66** | 0.35 | +89% | <0.001*** |
| content_accuracy | **0.90** | 0.79 | +13% | — |
| weighted_total | **0.86** | 0.79 | +9% | <0.001*** |

**Key Finding**: AE 在內容忠實度上顯著優於 Direct，且達到統計顯著（p<0.001）

### 5.2 Cycle Consistency

| Metric | Mean | Std |
|--------|------|-----|
| content_similarity | 0.965 | ±0.016 |
| rules_similarity | 0.983 | ±0.016 |

**Key Finding**: 循環一致性 > 0.96，說明結構化瓶頸的資訊損失很小

### 5.3 Error Analysis
- **AE 的錯誤類型**: 主要是 Encoder 提取不完整（可修復）
- **Direct 的錯誤類型**: 幻覺和遺漏（難以檢測和修復）

### 5.4 Trade-off: Quality vs Cost
| Path | LLM Calls | Content Preservation |
|------|-----------|---------------------|
| Direct | 1 | 0.35 |
| AE | 3 (gen + enc + dec) | 0.66 |

- AE 需要更多計算，但內容品質顯著更高
- 在高風險場景（政府公文），品質優先於成本

---

## 6. Analysis (0.5 page)

### 6.1 Why Does the Bottleneck Help?
- **Anchor Effect**: Content JSON 提供明確的事實錨點
- **Reduced Hallucination**: LLM 被限制在 Content 範圍內生成
- **Verifiable Intermediate**: 錯誤可以在 Content 階段被發現

### 6.2 Limitations
- LLM judge 的 content_preservation 評分可能有偏差
- 需要人工評審驗證

### 6.3 Generalization
- 假說應適用於其他需要高事實準確度的場景
- 如：法律文件、醫療報告、財務報表

---

## 7. Conclusion (0.5 page)

- 結構化瓶頸（AE）顯著優於端到端生成（Direct）
- 內容保留度提升 89%（p<0.001）
- 循環一致性高（>0.96），資訊損失小
- 為高風險文檔生成提供了可行方案

---

## 待補實驗清單

| 優先級 | 實驗 | 目的 |
|--------|------|------|
| P0 | 人工評審 20 篇 | 驗證 LLM judge 可靠性 |
| P1 | 細粒度指標 | Entity Recall, Date Accuracy |
| P1 | 錯誤分類 | 量化 hallucination vs omission |
| P2 | 其他領域測試 | 法律/醫療文件 |

---

## 與 Paper 1 的差異

| 面向 | Paper 1 | Paper 2 |
|------|---------|---------|
| 核心問題 | 能否解耦 Content 和 Rules？ | AE 是否優於 Direct？ |
| 實驗設計 | 消融 + 交叉重建 | AE vs Direct 比較 |
| 主要結果 | 解耦成功（消融效果顯著） | AE 顯著更好（p<0.001） |
| 貢獻類型 | 架構貢獻（新表示方法） | 實證貢獻（比較實驗） |

兩篇論文可以獨立投稿，不會重複。Paper 1 回答「如何表示」，Paper 2 回答「為什麼這樣表示更好」。
