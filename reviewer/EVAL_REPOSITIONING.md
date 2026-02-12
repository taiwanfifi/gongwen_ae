# GongWen-AE 重新定位：結構化解構評估框架

> **用途**：基於 60+ 篇文獻的調研，重新定位 GongWen-AE——
> 不是當「符號化自編碼器」，也不只是「概念瓶頸生成模型」，
> 而是一個**用結構化解構來評估公文生成品質**的 Evaluation Framework。
>
> **核心轉向**：重點從「拆/合本身」移到「用拆/合來量化品質」。
>
> **寫法**：白話、工程思維、先講道理再給名詞。

---

## 一、三秒鐘版：你到底做了什麼有價值的事？

把你的系統從頭到尾看一遍：

```
公文 ──Encode──▶ Content JSON + Rules JSON ──Decode──▶ 重建公文 ──Compare──▶ 六維分數
                                                                              ^^^^^^^^
                                                                              這裡才是重點
```

你做了一個**公文品質的多維度評估框架**——透過「先拆解、再重建、最後比較」的迂迴路線，把一份公文的品質拆成六個可獨立檢查的維度。

**這件事在學術界有名字，而且是 2023-2025 年的熱門方向。** 叫做：

### Decompose-then-Verify Evaluation（解構後驗證評估）

---

## 二、為什麼要繞路？直接打分不行嗎？

### 2.1 直接打分的問題

叫一個 LLM 看完公文後直接給一個 1-5 分，你會遇到三個問題：

| 問題 | 白話說明 | 文獻證據 |
|------|---------|---------|
| **粒度太粗** | 「3 分」到底是格式差、內容差、還是都差？你不知道 | Wang et al. (2023) 發現 ChatGPT 做 evaluator 時分數粒度極低 |
| **不可解釋** | 為什麼給 3 分？LLM 不會告訴你哪裡出了問題 | Zheng et al. (2023) 系統性研究 LLM-as-Judge 的偏差 |
| **維度糊在一起** | 一份格式完美但事實全錯的公文，和一份事實正確但格式亂七八糟的公文，可能拿到一樣的分數 | Sai et al. (2021) 證明沒有任何單一指標能同時捕捉所有品質維度 |

### 2.2 繞路的價值：把「品質」拆開來看

你的系統做了一件聰明的事——**把評估問題分解了**：

```
                    ┌─ rule_adherence      ← 格式對不對？（Regex 硬指標）
                    ├─ structural_match    ← Encoder 認得出格式嗎？
原始公文 vs 重建公文 ├─ semantic_similarity ← 整體語意有多像？（Embedding）
                    ├─ content_accuracy    ← 語意核被正確提取了嗎？（Embedding）
                    ├─ content_preservation← 內容完整嗎？（LLM Judge）
                    └─ format_compliance   ← 格式規範嗎？（LLM Judge）
```

**這就是 Decomposed Evaluation 的核心思想**——不給一個總分，而是分別回答六個獨立的問題。每個維度用最適合的方法（Regex / Embedding / LLM）去量化。

---

## 三、你的系統在文獻中的位置

### 3.1 Decompose-then-Verify 家族

2023-2025 年，NLG 評估的主流方向是「先把文本拆成小單元，再逐一驗證」：

| 方法 | 怎麼拆？ | 拆成什麼？ | 怎麼驗證？ | 會議 |
|------|---------|-----------|-----------|------|
| **FActScore** (Min et al. 2023) | 拆成原子事實 | 一句一事實的清單 | 每個事實查 Wikipedia | EMNLP 2023 |
| **SAFE** (Wei et al. 2024) | 拆成原子事實 | 事實清單 | LLM agent + Google Search | NeurIPS 2024 |
| **RAGAS** (Es et al. 2024) | 拆成 claims | claim 清單 | 每個 claim 對照 context | EACL 2024 |
| **FineSurE** (Song et al. 2024) | 拆成 keyfacts + sentences | 二層對齊表 | 事實核查 + 對齊度 | ACL 2024 |
| **QuestEval** (Scialom et al. 2021) | 拆成 QA pairs | 問答清單 | 雙向答題比對 | EMNLP 2021 |
| **CheckEval** (Kim et al. 2025) | 拆成 yes/no checklist | 二元問題清單 | 逐題回答 | EMNLP 2025 |
| **你的系統** | 拆成 Content JSON + Rules JSON | **結構化 JSON schema** | 六維度混合驗證 | — |

**你跟 FActScore/RAGAS 的差別在哪？**

- FActScore 把文本拆成**平面的事實清單**（一維）
- RAGAS 把回答拆成**claims**（一維）
- **你把公文拆成二維結構**：語義（Content）× 格式（Rules）

這個差別很重要——公文不只是「事實的集合」，它是「事實 + 呈現方式」的二維產物。FActScore 只能告訴你事實對不對，但告訴不了你格式對不對。你的框架可以。

### 3.2 Round-Trip Evaluation 家族

你的 Encode→Decode→Compare 流程，本質上是一個 **Round-Trip Evaluation**（來回評估）：

| 方法 | Round-Trip 路線 | 比較什麼？ | 結論 |
|------|----------------|-----------|------|
| **RTT for QE** (Moon et al. 2020) | 原文 → 翻譯 → 回譯 → 比較 | 原文 vs 回譯 | 用 semantic embedding 比 BLEU 好 |
| **CycleGT** (Guo et al. 2020) | 文本 → 知識圖 → 文本 → 比較 | 原文 vs 重建文本 | 圖和文本的雙向一致性 |
| **BARTScore** (Yuan et al. 2021) | 測量 P(hypothesis\|source) | 重建機率 | 機率越高品質越好 |
| **你的系統** | 公文 → JSON → 重建公文 → 比較 | 原文 vs 重建公文 | 六維度分數 |

**你跟 CycleGT 最像**——都是「結構化表示 ↔ 自然語言」的雙向來回。差別是 CycleGT 用知識三元組，你用 JSON schema。

### 3.3 Multi-Dimensional Evaluation 家族

用多個獨立維度評分，不是新概念，但你的組合方式有自己的特色：

| 框架 | 維度 | 怎麼評？ | 差異 |
|------|------|---------|------|
| **UniEval** (Zhong et al. 2022) | coherence, consistency, fluency, relevance | Boolean QA (T5) | 通用，不分 content/format |
| **G-Eval** (Liu et al. 2023) | 自定義維度 | CoT + 機率加權 | 依賴 GPT-4，粒度取決於 prompt |
| **FLASK** (Ye et al. 2023) | 12 種 fine-grained skills | 逐技能評分 | 偏向通用能力 |
| **MQM** (Lommel et al. 2014) | 100+ 錯誤類型（翻譯品質） | 人工標注 | 翻譯專用，最成熟 |
| **Prometheus** (Kim et al. 2024) | 自定義 rubric | 專門訓練的 13B evaluator | 需要自定義 rubric |
| **你的系統** | 6 維度（格式硬指標 + embedding + LLM judge） | **混合方法**：Regex + Embedding + LLM | 三種方法互補驗證 |

**你的獨特之處**：不只用一種方法評，而是**三種方法交叉驗證**：
1. **Regex（硬指標）**：rule_adherence — 有就是有、沒有就是沒有
2. **Embedding（軟指標）**：semantic_similarity, content_accuracy — 語意相似度
3. **LLM Judge（主觀指標）**：content_preservation, format_compliance — 類人判斷

大多數框架只用其中一種。三種方法的組合本身就是一個有價值的設計決策。

---

## 四、新的論文定位

### 4.1 一句話定位

```
舊定位：「我們提出了一個 Symbolic AutoEncoder，能把公文拆/合」
         → 問題：不是 AE、拆/合本身不新、證據有缺陷

新定位：「我們提出了一個結構化解構評估框架，
        用 Concept Bottleneck 的 Encode→Decode→Compare 迴路，
        實現公文生成品質的六維度可解釋評估」
         → 重點在 eval，不在 encode/decode
```

### 4.2 建議的新名稱

按適切度排序：

| 排名 | 名稱 | 優點 | 缺點 |
|------|------|------|------|
| **1** | **Schema-Grounded Decomposed Evaluation for Formal Document Generation** | 精確描述做的事；連接 decomposed eval 文獻 | 稍長 |
| 2 | **Concept Bottleneck Evaluation Framework for Government Documents** | 連接 CBM 文獻 (Koh 2020, ICML)；強調可解釋性 | CBM 原本用在分類，用在 eval 需要額外解釋 |
| 3 | **Round-Trip Structured Evaluation for Controllable Document Generation** | 強調 round-trip 核心機制；連接 CycleGT 等工作 | 「round-trip」在 NLP 主要跟翻譯連結 |
| 4 | **Multi-Dimensional Quality Assessment via Content-Format Decomposition** | 最直白 | 沒有連結到任何 established 文獻框架 |

**我的建議：用第 1 個。** 原因：
1. "Schema-Grounded" 強調你的 JSON schema 是**有明確定義的結構**，不是隨意的
2. "Decomposed Evaluation" 直接對接 FActScore/RAGAS/CheckEval 這個 2023-2025 頂會熱門方向
3. "Formal Document Generation" 明確應用領域
4. 不會被 AutoEncoder/Concept Bottleneck 的術語包袱拖累

### 4.3 故事線轉向

| | 舊故事 | **新故事** |
|---|---|---|
| 核心問題 | 「能不能把公文拆成 Content + Rules？」 | **「怎麼系統性地評估 LLM 生成公文的品質？」** |
| 為什麼重要 | 解耦本身有理論價值 | **公文是高風險文件，品質評估需要可解釋、多維度、可追溯** |
| 方法 | Symbolic AutoEncoder | **Schema-Grounded Decomposed Evaluation** |
| 中間表示 | 「潛在空間」 | **「評估用的結構化概念層」** |
| Encode 的角色 | 壓縮信息 | **提取可檢查的品質維度** |
| Decode 的角色 | 重建原文 | **驗證概念層的完備性和充分性** |
| 六維分數的角色 | 衡量重建品質 | **多維度品質診斷報告** |
| 交叉重建的角色 | 證明解耦成功 | **測試 content/format 維度的獨立性** |
| AE vs Direct 的角色 | 證明結構化瓶頸有價值 | **比較「有可檢查中間層」vs「無中間層」的評估能力** |

---

## 五、重新定位後的論文結構

### 標題建議

> **Schema-Grounded Decomposed Evaluation for LLM-Based Formal Document Generation**

或中文：

> **以結構化解構實現公文生成的多維度可解釋評估**

### 5.1 Introduction

**開場問題（不是「能不能拆開」，而是「怎麼評」）：**

LLM 越來越常被用來生成正式文件（公文、法律文書、合規報告）。但怎麼知道生成的品質好不好？

現有的評估方法有三個不夠：

1. **BLEU/ROUGE 不夠**：它們基於 n-gram 重疊，無法區分「格式對但內容錯」和「內容對但格式亂」。
2. **單分數 LLM Judge 不夠**：G-Eval (Liu et al. 2023) 用 GPT-4 打一個分數，但你不知道分數低是因為什麼。一份格式完美但捏造事實的公文，和一份事實正確但格式全錯的公文，可能拿到一樣的 3 分。
3. **人工評估不夠快**：正式文件的人工評估需要領域專家，成本高、速度慢。

**我們的方法**：把「評估」問題拆解為「先用結構化 schema 解構文件，再在每個結構維度上分別評估」。

### 5.2 Related Work

分三個區塊（比舊版更聚焦）：

**A. Decompose-then-Verify Evaluation**
- FActScore (Min et al. 2023) — 原子事實分解 + 逐一驗證
- SAFE (Wei et al. 2024) — LLM agent 分解 + 搜尋驗證
- RAGAS (Es et al. 2024) — RAG 四維度評估框架
- FineSurE (Song et al. 2024) — keyfact 級精細評估
- CheckEval (Kim et al. 2025) — 二元 checklist 分解，inter-rater agreement 提升 0.45
- DnA-Eval (Li et al. 2024) — 自動提出評估維度 → 逐維打分 → 聚合

**B. Multi-Dimensional NLG Evaluation**
- UniEval (Zhong et al. 2022) — Boolean QA 多維評估
- G-Eval (Liu et al. 2023) — CoT + 機率加權
- FLASK (Ye et al. 2023) — 12 種 fine-grained skill 評估
- Prometheus (Kim et al. 2024) — 基於自定義 rubric 的開源 evaluator
- LLM-Rubric (Hashemi et al. 2024) — 多維度校準評估，用 MCQ 替代直接打分
- TIGERScore (Jiang et al. 2024) — 結構化錯誤分析（定位 + 解釋 + 扣分）

**C. Round-Trip & Reconstruction-Based Evaluation**
- BARTScore (Yuan et al. 2021) — 用重建機率做評分
- CycleGT (Guo et al. 2020) — 文本↔圖的雙向一致性
- QuestEval (Scialom et al. 2021) — 雙向 QA 評估
- PARENT (Dhingra et al. 2019) — 以結構化資料為錨點的 table-to-text 評估

**D. Formal Document Evaluation（新增）**
- JuDGE (2025) — 中國法律判決書生成的四維評估
- CaseGen (Li et al. 2025) — 多階段法律文書生成評估
- Instruction Tuning for Official Document (2025, JCIP) — 中文公文生成的人工四維評估
- RegNLP/RIRAG (2024) — 合規文件的義務級評估

### 5.3 Method

**不要叫它 AutoEncoder。叫它 Decomposed Evaluation Pipeline。**

```
                Schema-Grounded Decomposed Evaluation Pipeline
                ═══════════════════════════════════════════════

  ┌─────────┐     ┌──────────────────────┐     ┌─────────┐     ┌─────────┐
  │ Document │──▶  │ Structured Extractor │──▶  │ Content │     │  Rules  │
  │  (input) │     │  (Schema-guided LLM) │     │  JSON   │     │  JSON   │
  └─────────┘     └──────────────────────┘     └────┬────┘     └────┬────┘
                                                     │               │
                                               ┌─────▼───────────────▼─────┐
                                               │    Reconstructor (LLM)    │
                                               └───────────┬───────────────┘
                                                           │
                                                    ┌──────▼──────┐
                                                    │ Reconstructed│
                                                    │  Document    │
                                                    └──────┬──────┘
                                                           │
         ┌─────────────────────────────────────────────────┤
         │                                                 │
  ┌──────▼──────┐                                   ┌──────▼──────┐
  │  原始文件    │◄──────── 6-Dimension Compare ────▶│  重建文件    │
  └─────────────┘                                   └─────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  Quality Diagnostic Report                                   │
  │  ┌─────────────────┬──────┬────────────────────────────┐    │
  │  │ Dimension       │Score │ Method                      │    │
  │  ├─────────────────┼──────┼────────────────────────────┤    │
  │  │ rule_adherence  │ 0.89 │ Regex pattern matching      │    │
  │  │ structural_match│ 0.83 │ Field-by-field comparison   │    │
  │  │ semantic_sim    │ 0.92 │ Embedding cosine similarity │    │
  │  │ content_accuracy│ 0.89 │ Embedding cosine similarity │    │
  │  │ content_pres    │ 0.80 │ LLM Judge (1-5)             │    │
  │  │ format_comply   │ 0.88 │ LLM Judge (1-5)             │    │
  │  └─────────────────┴──────┴────────────────────────────┘    │
  └─────────────────────────────────────────────────────────────┘
```

**核心思路的學術定位**：

這是一個 **Schema-Grounded Decompose-then-Verify** 評估管線。跟 FActScore 拆成原子事實不同，我們拆成**二維結構化 schema**（語義 × 格式），這讓每個品質維度可以用最適合的方法（Regex / Embedding / LLM）獨立評估。

**跟 Concept Bottleneck 的關係**：

Koh et al. (2020) 的 Concept Bottleneck Model 強迫所有信息通過人類可讀的概念層。我們把這個思路**用在評估上**：強迫所有品質資訊通過一個結構化的概念層（Content JSON + Rules JSON），這讓品質評估變得**可分解、可檢查、可干預**。

| CBM 概念 | 我們的評估框架 |
|---------|-------------|
| Concept Layer（概念層） | Content JSON + Rules JSON |
| Concept Prediction（概念預測） | Schema-guided Extraction（Encoder） |
| Task Prediction（任務預測） | 品質分數（六維度） |
| Human Intervention（人類介入） | 修改 JSON → 重新生成 → 觀察分數變化 |
| Concept Independence（概念獨立性） | Content 和 Rules 分別對應不同品質維度 |

### 5.4 Evaluation Dimensions（六維度的學術定位）

重新解讀每個維度的定位：

| 維度 | 方法 | 測量什麼 | 對應的文獻範式 |
|------|------|---------|-------------|
| **rule_adherence** | Regex | 重建文件是否符合格式規範（日期、字號、段落） | CheckList (Ribeiro et al. 2020) — 行為測試 |
| **structural_match** | Field comparison | Encoder 能否正確提取格式參數 | Schema validation — 結構正確性 |
| **semantic_similarity** | Embedding cosine | 重建文件與原文的整體語意距離 | BARTScore (Yuan et al. 2021) — 重建一致性 |
| **content_accuracy** | Embedding cosine | Encoder 提取的語意核是否準確 | FActScore (Min et al. 2023) — 事實精確度的 proxy |
| **content_preservation** | LLM Judge | 重建文件是否保留了所有重要資訊 | G-Eval (Liu et al. 2023) — LLM-as-Judge |
| **format_compliance** | LLM Judge | 重建文件是否像一份正式公文 | Prometheus (Kim et al. 2024) — rubric-based 評估 |

**三種方法的交叉驗證是一個貢獻**：
- Regex（硬）：不可能被 LLM 偏差影響
- Embedding（統計）：連續值，粒度高
- LLM Judge（主觀）：最接近人類判斷

如果三種方法的結論一致 → 強證據。如果不一致 → 指出哪個維度有問題。

### 5.5 Experiments（重新設計）

重點從「證明解耦成功」轉到「驗證評估框架的有效性」：

#### Exp 1: 框架能區分好壞嗎？（Discriminative Power）

**目的**：驗證六維分數能否區分不同品質層級的公文。

**做法**：
- 生成三種品質的公文：(a) 完整 AE 路徑（高品質），(b) 只給 topic 直接生成（中品質），(c) 隨機打亂 Rules（低品質）
- 看六維分數能否正確排序 a > b > c
- **新增**：用人工評估驗證框架排序是否跟人類一致

**這比 AE vs Direct 的意義更清楚**：不是在比「哪條路更好」，而是在測「尺能不能量」。

#### Exp 2: 維度是否獨立？（Dimension Independence）

**目的**：驗證六個維度確實在測量不同的東西，不是在重複測同一件事。

**做法**：
- 計算六維分數之間的 Pearson/Spearman 相關矩陣
- 用**受控退化實驗**：故意弄壞一個維度（比如打亂 Rules），看是否只有格式相關的維度下降
- 理想結果：打亂 Rules → rule_adherence、format_compliance 下降，但 content_accuracy 不變

**這比消融實驗更有說服力**：因為你是在測「指標的行為」，不是在用恆等式指標證明結論。

#### Exp 3: 跟人工評估的一致性（Human Correlation）

**目的**：六維自動評分跟人類專家的判斷有多一致？

**做法**：
- 請 3+ 位有公文撰寫經驗的人，獨立對 50+ 份公文打六維分數
- 計算 inter-rater agreement（Krippendorff's α）
- 計算自動評分 vs 人工評分的 Spearman correlation
- **對標**：G-Eval (Liu et al. 2023) 報告的 Spearman ≈ 0.514，Prometheus (Kim et al. 2024) 報告的 Pearson ≈ 0.897

**這是最關鍵的實驗。** 如果你的框架跟人類的相關性 > G-Eval，那就是一篇可發表的論文。

#### Exp 4: Schema 設計的影響（Schema Ablation）

**目的**：JSON schema 的設計如何影響評估品質？

**做法**：
- 比較不同粒度的 schema：
  - 粗糙版：Content 只有 {topic, summary}，Rules 只有 {doc_type, tone}
  - 現有版：Content 6 欄位，Rules 9 欄位
  - 精細版：Content 10+ 欄位，Rules 15+ 欄位
- 看哪個粒度的評估最接近人類判斷
- 用 BIC 類比找最佳 schema 複雜度

**這回答了之前的「兩個分量夠不夠」問題**，但重新框架為「評估 schema 的最佳粒度」。

#### Exp 5: 跨模型一致性（Cross-Model Robustness）

**目的**：換不同 LLM 做 Encoder/Judge，評估結果還穩定嗎？

**做法**：
- Encoder 用 GPT-4o-mini vs Claude Sonnet vs Llama 3
- Judge 用 GPT-4o-mini vs Claude Opus vs GPT-4o
- 看六維分數的 inter-model agreement
- **修正了 Review W3 的問題**：不再是自己評自己

#### Exp 6: 交叉重建作為診斷工具（Cross-Recon as Diagnostic）

**目的**：交叉重建不是為了「證明解耦」，而是作為**品質診斷手段**。

**做法**：
- 用 C_i × R_j 的完整矩陣（修正只用 1 個 Content source 的 bug）
- 如果換 Rules 後 content_accuracy 大幅下降 → 表示 Content 提取對格式有依賴
- 如果換 Content 後 format_compliance 大幅下降 → 表示格式生成對語意有依賴
- **這提供了可操作的診斷信息**：告訴使用者哪些品質維度互相糾纏

---

## 六、現有的東西哪些可以保留？

| 現有元素 | 保留？ | 新的角色 |
|---------|--------|---------|
| 四階段 Pipeline (Gen→Enc→Dec→Eval) | ✓ 全部保留 | 重新描述為 Decomposed Evaluation Pipeline |
| Content + Rules 雙 JSON | ✓ 保留 | 「評估用的結構化概念層」，不是「潛在空間」 |
| 六維評估系統 | ✓ 核心保留 | **這就是論文的主要貢獻** |
| 三種方法混合 (Regex + Embedding + LLM) | ✓ 保留，這是亮點 | 強調為「multi-method triangulation」 |
| 逆向資料生成 | ✓ 保留 | 重新描述為「controlled document generation for evaluation validation」 |
| 交叉重建 | ✓ 保留思路 | 從「解耦證據」變成「品質維度獨立性診斷」；必須修正 bug |
| AE vs Direct | ✓ 保留思路 | 從「哪個更好」變成「有中間層 vs 無中間層的評估能力比較」；必須修正公平性 |
| Self-refinement (Paper 3) | **暫擱** | 除非改成不看 ground truth 的版本 |
| 「Symbolic AutoEncoder」命名 | **✗ 放棄** | 改用 Decomposed Evaluation Framework |

---

## 七、需要新增的實驗（優先級排序）

| 優先級 | 實驗 | 目的 | 工作量 | 影響力 |
|--------|------|------|--------|--------|
| **P0** | 人工評估 50+ 份 | 驗證框架有效性 | 中（需找公務人員） | ★★★ **決定性** |
| **P0** | 跨模型 Judge | 消除自評偏差 | 低（換 API key） | ★★★ |
| **P0** | 修正交叉重建 bug | 用完整 N×N 矩陣 | 低（改迴圈） | ★★ |
| **P0** | 六維度相關矩陣 | 驗證維度獨立性 | 低（算 correlation） | ★★ |
| **P1** | 樣本量擴充到 100+ | 統計顯著性 | 中（API 費用） | ★★ |
| **P1** | 受控退化實驗 | 驗證指標敏感度 | 低 | ★★ |
| **P1** | Schema 粒度消融 | 找最佳評估粒度 | 中 | ★★ |
| **P1** | 修正 AE vs Direct 公平性 | 給 Direct 同等信息 | 低（改 prompt） | ★ |
| **P2** | 語義連貫的資料配對 | 修正荒謬文件問題 | 中 | ★ |
| **P2** | 真實公文測試 | 驗證在真實世界的效果 | 高（需合作） | ★★★ |

**為什麼 P0 裡人工評估排第一？**

因為一個 Evaluation Framework 的論文，最終的說服力來自「跟人類的一致性」。FActScore 報告了人工驗證 < 2% 錯誤率，RAGAS 報告了跟人工的相關性，CheckEval 報告了 inter-rater agreement 提升 0.45。**沒有人工數據的 eval 框架論文，在頂會過不了。**

---

## 八、新論文的完整故事

### 標題
> Schema-Grounded Decomposed Evaluation for LLM-Based Formal Document Generation

### Abstract（草稿）

> Evaluating LLM-generated formal documents (e.g., government correspondence) requires assessing both content fidelity and format compliance — dimensions that existing metrics conflate into a single score. We propose a **schema-grounded decomposed evaluation framework** that forces all quality information through a structured concept layer (Content JSON + Rules JSON), enabling independent assessment on six orthogonal dimensions using a multi-method approach (regex pattern matching, embedding similarity, and LLM-as-judge). On a corpus of N Taiwan government documents, our framework achieves Spearman ρ = X.XX with expert human judgments, outperforming single-score baselines (G-Eval: ρ = 0.XX, UniEval: ρ = 0.XX). Controlled degradation experiments confirm that each dimension is independently sensitive to targeted quality perturbations. We release the evaluation framework, schema definitions, and annotated dataset to support future research on formal document quality assessment.

### 核心貢獻（重新定義）

1. **第一個針對正式公文的多維度解構評估框架**——把公文品質拆成 content × format 的二維結構
2. **三種方法交叉驗證**（Regex + Embedding + LLM Judge）——比單一方法更可靠
3. **Schema-grounded evaluation**——用 JSON schema 作為評估的錨點，使評估可解釋、可干預
4. **維度獨立性驗證**——用受控退化實驗和交叉重建證明六個維度確實在測不同的東西
5. **跟人類判斷的校準**——提供 inter-rater agreement 和 correlation 數據

### 目標會議

| 會議 | 為什麼適合 |
|------|-----------|
| **EMNLP** | Decomposed eval 是 EMNLP 的熱門方向（FActScore、CheckEval 都在 EMNLP） |
| **ACL** | 多維評估（UniEval、LLM-Rubric、FineSurE 都在 ACL） |
| **NAACL** | ARES 在 NAACL，formal/legal NLP 是 NAACL 的關注領域 |
| **COLING** | DnA-Eval 在 COLING，中文 NLP 是 COLING 的傳統強項 |

---

## 九、跟 THELMA 的關係

你的 repo 裡還有 THELMA（Task-Based Holistic Evaluation of Large Language Model Applications），這是一個 RAG QA 的 reference-free 評估框架。兩者的關係：

| | THELMA | GongWen Eval |
|---|---|---|
| 評估對象 | RAG QA 系統的回答 | 公文生成系統的輸出 |
| 解構方式 | 拆成 sub-questions + claims | 拆成 Content JSON + Rules JSON |
| 維度 | 6 維（SP, SQC, RP, RQC, SD, GR） | 6 維（RA, SM, SS, CA, CP, FC） |
| 共同點 | 都是 decompose-then-verify | 都是 decompose-then-verify |
| 差別 | 評估「回答是否忠實於來源」 | 評估「生成是否同時忠實於語意和格式」 |

**可以寫成一個系列**：THELMA 是 RAG 場景的 decomposed eval，GongWen Eval 是 formal document generation 場景的 decomposed eval。兩者共享「解構後驗證」的方法論核心。

---

## 十、參考文獻精選（最核心的 25 篇）

### Decompose-then-Verify Evaluation
1. Min et al. (2023) "FActScore: Fine-grained Atomic Evaluation of Factual Precision" **EMNLP**
2. Wei et al. (2024) "Long-form Factuality in LLMs (SAFE)" **NeurIPS**
3. Es et al. (2024) "RAGAS: Automated Evaluation of Retrieval Augmented Generation" **EACL**
4. Song et al. (2024) "FineSurE: Fine-grained Summarization Evaluation using LLMs" **ACL**
5. Kim et al. (2025) "CheckEval: Reliable LLM-as-a-Judge Using Checklists" **EMNLP**
6. Li et al. (2024) "DnA-Eval: Decompose and Aggregate" **COLING**
7. Scialom et al. (2021) "QuestEval: Summarization Asks for Fact-based Evaluation" **EMNLP**
8. Laban et al. (2022) "SummaC: NLI-based Inconsistency Detection" **TACL**

### Multi-Dimensional Evaluation
9. Zhong et al. (2022) "UniEval: Unified Multi-Dimensional Evaluator" **EMNLP**
10. Liu et al. (2023) "G-Eval: NLG Evaluation using GPT-4" **EMNLP**
11. Ye et al. (2023) "FLASK: Fine-grained Language Model Evaluation" **ICLR 2024**
12. Kim et al. (2024) "Prometheus: Fine-grained Evaluation Capability" **ICLR**
13. Hashemi et al. (2024) "LLM-Rubric: Multidimensional, Calibrated Approach" **ACL**
14. Jiang et al. (2024) "TIGERScore: Explainable Metric for All Text Generation" **TMLR**

### Round-Trip / Reconstruction-Based Evaluation
15. Yuan et al. (2021) "BARTScore: Evaluating Generated Text as Text Generation" **NeurIPS**
16. Guo et al. (2020) "CycleGT: Unsupervised Graph-to-Text via Cycle Training" **WebNLG+**
17. Dhingra et al. (2019) "PARENT: Table-to-Text Evaluation" **ACL**

### LLM-as-Judge
18. Zheng et al. (2023) "Judging LLM-as-a-Judge with MT-Bench" **NeurIPS**
19. Verga et al. (2024) "Replacing Judges with Juries: PoLL" arXiv
20. Chan et al. (2024) "ChatEval: Multi-Agent Debate" **ICLR**

### Concept Bottleneck Foundation
21. Koh et al. (2020) "Concept Bottleneck Models" **ICML**
22. Yamaguchi et al. (2024) "Concept Bottleneck Large Language Models" **ICLR 2025**

### Formal Document Evaluation
23. JuDGE (2025) "Benchmarking Judgment Document Generation" **SIGIR**
24. CaseGen (Li et al. 2025) "Multi-Stage Legal Case Documents Generation" arXiv
25. JCIP (2025) "Instruction Tuning of LLMs for Official Document Generation" **中文信息學報**

### Diagnostic Testing
26. Ribeiro et al. (2020) "CheckList: Behavioral Testing of NLP Models" **ACL**
27. Sai et al. (2021) "Perturbation CheckLists for NLG Evaluation Metrics" **EMNLP**

---

## 十一、一句話總結

**你做的「拆開→重建→比較」不只是一個 AutoEncoder 的概念展示——它是一個可以獨立成篇的 evaluation methodology。重點不是「拆得開」，而是「拆開之後可以量化地評估每個維度的品質」。**

把火力集中在「eval framework」上：
- 不用解釋為什麼叫 AutoEncoder（因為不叫了）
- 不用證明解耦的理論正確性（因為重點不在解耦）
- 只需要證明：**這個框架能可靠地、可解釋地評估公文品質，而且跟人類專家的判斷一致**

---

*分析完成 — 2026-02-11*
*基於兩個獨立文獻調研代理的 60+ 篇論文整合*
