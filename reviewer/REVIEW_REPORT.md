# GongWen-AE 學術同儕審查報告
# Academic Peer Review Report: GongWen-AE

**審查者 (Reviewer):** Claude Opus 4.6 — Automated Peer Reviewer
**審查日期 (Date):** 2026-02-11
**審查對象 (Subject):** GongWen-AE: Symbolic AutoEncoder for Taiwan Government Documents
**投稿目標 (Target Venues):** ACL / EMNLP / COLING (Long Paper)

---

## 總評分 (Overall Score): 38 / 100

**判定 (Verdict):** 目前不具備在頂級期刊/會議發表的水準 (Not ready for top-venue publication)

**一句話評價：** 本專案提出了一個有創意的概念框架（以 LLM 實現符號化自編碼器），但存在多個根本性的方法論缺陷、嚴重的實驗設計問題、以及與現有文獻的脫節，需要大幅度的修改才有可能達到發表水準。

---

## 目錄

1. [優點與創新 (Strengths)](#1-優點與創新-strengths)
2. [根本性方法論問題 (Fundamental Methodological Issues)](#2-根本性方法論問題-fundamental-methodological-issues)
3. [實驗設計缺陷 (Experimental Design Flaws)](#3-實驗設計缺陷-experimental-design-flaws)
4. [數據驗證結果 (Data Verification)](#4-數據驗證結果-data-verification)
5. [與現有文獻的比較 (Literature Comparison)](#5-與現有文獻的比較-literature-comparison)
6. [評估指標的根本問題 (Evaluation Metric Issues)](#6-評估指標的根本問題-evaluation-metric-issues)
7. [各論文逐篇評審 (Per-Paper Reviews)](#7-各論文逐篇評審-per-paper-reviews)
8. [分項評分 (Breakdown Scores)](#8-分項評分-breakdown-scores)
9. [潛在研究方向 (Potential Research Directions)](#9-潛在研究方向-potential-research-directions)
10. [修改建議 (Revision Recommendations)](#10-修改建議-revision-recommendations)

---

## 1. 優點與創新 (Strengths)

### S1. 概念框架有吸引力
將公文處理建模為一個「符號化自編碼器」是一個有趣且直觀的概念隱喻。將高度結構化文體分解為「語意核 (Content)」和「格式殼 (Rules)」的雙空間設計有一定的理論優雅性。

### S2. 完整的實驗管線
專案包含完整的四階段管線（Generate → Encode → Decode → Evaluate），代碼結構清晰，可復現性較好。三篇論文分別回答不同研究問題，有合理的實驗設計邏輯。

### S3. 逆向資料生成策略
先生成 Content + Rules 再組合成公文的「逆向生成」策略，解決了 ground truth 獲取的問題。這是一個合理的工程決策。

### S4. 迭代改進的態度
從 v1 到 v3 的版本迭代中，作者識別並修正了多個問題（Paper 2 不公平比較、Paper 3 閾值太低、cosine similarity 浮點溢出），展現了良好的自我批判精神。

### S5. Score-Gated Refinement
Paper 3 的 score-gating 機制（只在新分數 > 舊分數時才接受修正）是一個合理的設計，解決了過度修正的問題。

---

## 2. 根本性方法論問題 (Fundamental Methodological Issues)

### W1. ★★★ 「自編碼器」類比在學術上不成立

**問題描述：** 本系統自稱為「Symbolic AutoEncoder」，但在技術上這不是任何正式意義上的自編碼器：

- **無可學習參數 (No Learnable Parameters)**：真正的自編碼器（VAE、β-VAE、離散自編碼器）通過梯度下降優化一個重建損失函數。本系統完全依賴 LLM 的 prompt engineering，沒有任何可訓練的參數。
- **無損失函數 (No Loss Function)**：沒有明確定義的重建損失可以被最小化。
- **無瓶頸約束 (No True Bottleneck Constraint)**：在真正的 AE 中，瓶頸是通過限制潛在維度來實現的。這裡的「瓶頸」只是一個 JSON schema，LLM 可以在其中自由填寫任意內容。
- **本質是 Prompt-based Extraction + Generation**：Encoder 是一個結構化信息提取 prompt，Decoder 是一個模板化文件生成 prompt。這本身有價值，但不應被稱為「自編碼器」。

**影響：** 這構成了核心概念的誤導。在 NeurIPS/ICML/ACL 等會議上，審查者會質疑這種術語的使用，認為是 buzzword borrowing。

**參考文獻對比：**
- Bowman et al. (2016) "Generating Sentences from a Continuous Space" — 真正的文本 VAE，有可學習的 encoder/decoder 參數和 KL divergence 損失。
- Ge et al. (2023) "In-Context Autoencoder for Context Compression in a Large Language Model" (ICLR 2024) — 雖然名稱含 autoencoder，但確實有用 LoRA 訓練 encoder 參數，並有 autoencoding 和 language modeling 兩個訓練目標。
- 本專案的「autoencoder」只是 prompt 的組合，沒有任何訓練過程。

### W2. ★★★ 合成數據的根本局限

**問題描述：** 所有 20 篇公文都是 LLM 合成的，沒有使用任何真實公文。更嚴重的是，主題與規則的隨機配對產生了語義上荒謬的文件：

- **文件 972ad03a**：主題是「校園資訊安全防護計畫」，但發文者是「經濟部工業局」，受文者是「財政部國稅局」。為什麼工業局要向國稅局發送校園資安計畫？
- **文件 654b7559**：主題是「政府採購案驗收爭議處理」，但發文者是「臺北市政府教育局」，受文者是「臺北市立大安高級中學」。為什麼教育局要向一所高中發送採購爭議處理函？
- **文件 9dc436b9**：主題是「災害防救演練」，發文者是「交通部公路總局」，但內容提到「全校師生」—— 公路總局沒有「全校」。

**根因：** 系統從 10 個主題和 5 個規則模板中隨機配對，導致語義不連貫。

**影響：**
1. 這種不真實的數據無法驗證系統在真實場景中的表現。
2. 「解耦」的結論只在人工構造的、語義不連貫的文件上成立。
3. 真實公文中，Content 和 Rules 之間存在強相關性（例如「公告」幾乎只用於下行），這種相關性在隨機配對中被消除了，使得「解耦」變得更容易。

### W3. ★★★ 循環自我評估的根本偏差

**問題描述：** 系統使用 GPT-4o-mini 完成以下所有任務：
1. **生成**公文內容 (Content)
2. **撰寫**公文全文 (Compose)
3. **提取** Content 和 Rules (Encode)
4. **重建**公文 (Decode)
5. **評估**重建品質 (LLM Judge)

用同一個模型（或同一模型家族）來生成、處理並評估自己的輸出，構成了一個嚴重的循環偏差：

- **LLM judge 偏好自己的輸出模式**：已有研究表明，LLM-as-Judge 對同一模型家族生成的文本有系統性偏好（Zheng et al. 2023 "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"; Panickssery et al. 2024 "LLM Evaluators Recognize and Favor Their Own Generations"）。
- **高循環一致性可能是 trivial 的**：Encode-Decode-Re-Encode 的高一致性（0.965/0.983）可能只是反映 GPT-4o-mini 的 deterministic pattern，而非真正的「資訊無損」。
- **content_accuracy 的 embedding 相似度可能是 inflated**：gt_content 和 predicted_content 都是同一 LLM 生成的 JSON 格式文本，它們在 embedding 空間中天然接近。

**參考文獻：**
- Zheng et al. (2023) "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" — 首次系統性研究 LLM-as-Judge 的偏差。
- Panickssery et al. (2024) "LLM Evaluators Recognize and Favor Their Own Generations" — 直接證明 LLM judge 偏好自己的輸出。
- Huang et al. (2024) "Large Language Models Cannot Self-Correct Reasoning Yet" — 質疑 LLM 自我修正能力的重要反證。

### W4. ★★ Paper 2 的比較根本不公平

**問題描述：** AE path vs Direct path 的比較存在根本性的信息不對稱：

| 路徑 | 輸入給 Decoder/Generator 的信息 |
|------|-------------------------------|
| AE path | 完整的 Content JSON（topic, intent, key_events, entities, action_items, background）+ Rules JSON |
| Direct path | 僅主題字串 (topic) + Rules JSON |

AE path 的 Decoder 收到了詳細的事件列表、實體清單、行動項目等結構化資訊，而 Direct path 只收到一個粗略的主題描述。這不是在比較「有結構化瓶頸 vs 沒有」—— 這是在比較「更多輸入信息 vs 更少輸入信息」。

**更準確的說法：** AE 的優勢並非來自「結構化瓶頸」本身，而是來自 Encoder 提取了更豐富的中間表示。如果給 Direct Generator 同等量的信息（例如完整的 Content JSON），差距很可能會大幅縮小。

### W5. ★★ Paper 3 的「自我修正」使用了 ground truth

Paper 3 的 Critique 步驟將重建公文與**原始公文**進行比較來分析問題。但在實際應用場景中，你不會有原始公文可以對照。因此：

- 這不是真正的「self-correction」，而是「correction with ground truth oracle」。
- 真正的 self-correction（如 Madaan et al. 2023 "Self-Refine"）不依賴 ground truth。
- Kamoi et al. (2024) "When Can LLMs Actually Correct Their Own Mistakes?" 的調查指出，許多 self-correction 論文因為使用了外部 oracle 信息而高估了修正效果。

---

## 3. 實驗設計缺陷 (Experimental Design Flaws)

### E1. ★★★ 交叉重建實驗只用了一份文件的 Content

**實際數據驗證：** 所有 10 個交叉重建樣本的 doc_id 為：
```
cross_972ad03a_526e6a63
cross_972ad03a_8c1783c5
cross_972ad03a_53ee356b
cross_972ad03a_654b7559
cross_972ad03a_d04b5ef8
cross_972ad03a_0f7de825
cross_972ad03a_74e8ba80
cross_972ad03a_9dcf53b3
cross_972ad03a_9bac5322
cross_972ad03a_c5d83814
```

**所有 10 個交叉對都使用文件 972ad03a 的 Content**。結果就是：
- content_accuracy 在所有 10 個樣本中幾乎完全相同（0.9469 ± 0.00003），因為它們共享同一個 predicted_content。
- 這意味著交叉重建實驗實際上只測試了 **1 份文件的語義保留**能力搭配 10 種不同的格式模板。
- 聲稱「Cross-Recon 的 content_accuracy (0.9469) 甚至高於 Baseline (0.8912)」在統計上毫無意義——它只是那 1 份特定文件 (972ad03a) 的分數。

**預期修正：** 應該測試 C_i × R_j 的完整矩陣，或至少隨機抽樣多個不同的 Content source。

### E2. ★★ LLM Judge 分數的極低粒度

**實際數據驗證：**

| 指標 | 所有可能的取值 |
|------|--------------|
| content_preservation | {0.2, 0.4, 0.6, 0.8}（永遠不出現 1.0）|
| format_compliance | {0.6, 0.8, 1.0}（永遠不出現 0.2 或 0.4）|

content_preservation 在 AE 路徑中只取 {0.6, 0.8}，在 Direct 路徑中只取 {0.2, 0.4}。這意味著：
- LLM judge 本質上是一個**二元分類器**（高/低），不是一個細粒度的評分者。
- 報告的「paired t-test, p < 0.001」雖然數學上正確（t=7.356），但實際上是在比較兩個幾乎二元的分佈，統計意義被嚴重高估。
- 更適合的統計檢定是 Wilcoxon signed-rank test 或 McNemar's test。

### E3. ★★ 樣本量仍然不足

N=20 對於大多數頂級會議來說仍然偏小：
- ACL/EMNLP 的文本生成論文通常使用 100+ 甚至 1000+ 個樣本。
- 5 個 rules 模板 × 10 個主題 = 最多 50 種組合，但只測了 20。
- Paper 3 只有 N=3，統計推斷幾乎不可能。
- 交叉重建只有 N=10 且全部來自同一個 Content source。

### E4. ★★ 完全沒有人工評估

- 沒有人工評審驗證 LLM judge 的可靠性。
- 沒有 inter-rater agreement 測量。
- 沒有公文領域專家的參與。
- 頂級會議論文通常要求至少部分人工評估來驗證自動指標的有效性。

### E5. ★ 消融實驗的 content_accuracy 和 structural_match 是恆等式

**數據驗證：**
- Content-only ablation 的 content_accuracy **與 Baseline 完全相同**（20/20 匹配，差異 < 0.001）。這是因為 content_accuracy 只比較 gt_content vs predicted_content，而 Content-only ablation 沒有改變 predicted_content。
- Rules-only ablation 的 structural_match **與 Baseline 完全相同**（20/20 匹配）。同理。

這意味著所報告的消融結果中，最關鍵的兩個指標（content_accuracy 和 structural_match）是**恆等式而非實驗發現**。真正的消融效果只體現在其他指標上（semantic_similarity、content_preservation、format_compliance），而這些指標的粒度很低。

---

## 4. 數據驗證結果 (Data Verification)

### 4.1 報告數字的準確性

所有報告的平均值經過逐一核算，**數字本身是準確的**（誤差 < 0.0001）。paired t-test 的 t 統計量和 p-value 也與報告一致：

| 統計量 | 報告值 | 核算值 | 一致 |
|--------|--------|--------|------|
| weighted_total t-stat | 7.356 | 7.356 | ✓ |
| weighted_total p-value | 0.000001 | 0.00000057 | ✓ |
| content_pres t-stat | 11.461 | 11.461 | ✓ |
| cycle content_sim mean | 0.9651 | 0.9651 | ✓ |
| cycle rules_sim mean | 0.9833 | 0.9833 | ✓ |

### 4.2 可疑模式

| 問題 | 嚴重程度 | 說明 |
|------|---------|------|
| 交叉重建只用一個 Content source | ★★★ | 所有 10 個 cross pairs 的 content_accuracy 完全相同 |
| content_preservation 只有 2-3 個離散值 | ★★ | LLM judge 實際上是粗粒度分類器 |
| Content-only 的 content_accuracy = Baseline | ★ | 恆等式，非實驗發現 |
| Rules-only 的 structural_match = Baseline | ★ | 恆等式，非實驗發現 |
| 語意不連貫的文件 | ★★★ | 主題-規則隨機配對產生荒謬文件 |
| format_compliance 普遍偏高（0.78-0.96） | ★ | 即使 rules-only ablation 也有 0.78 |

---

## 5. 與現有文獻的比較 (Literature Comparison)

### 5.1 文本解耦表示學習 (Disentangled Text Representation)

本專案聲稱「不同於 VAE 的連續向量，我們的潛在表示是人類可讀的 JSON」。然而，相關領域已有大量成熟研究：

| 論文 | 方法 | 與本專案的關係 |
|------|------|--------------|
| Higgins et al. (2017) "β-VAE: Learning Basic Visual Concepts with a Constrained Variational Framework" ICLR | β-VAE 框架 | 提出了量化解耦的 metric (DCI, FactorVAE metric)。本專案沒有使用任何標準化的解耦量化指標。|
| John et al. (2019) "Disentangled Representation Learning for Non-Parallel Text Style Transfer" ACL | 文本 content/style 分離 | **直接相關的前置研究**——已經實現了文本的 content-style 解耦，但使用真正的 VAE 訓練。|
| Bao et al. (2019) "Generating Sentences from Disentangled Syntactic and Semantic Spaces" ACL | 語法/語意空間分離 | 同樣實現了雙空間分離，有可學習的模型。|
| Cheng et al. (2020) "Improving Disentangled Text Representation Learning with Information-Theoretic Guidance" ACL | 信息論指導的解耦 | 提出了更嚴格的解耦度量標準（mutual information）。|
| Hu et al. (2022) "Text Style Transfer: A Survey" Computational Linguistics | 風格遷移綜述 | 全面回顧了 content-style 分離的方法論。|

**關鍵差距：** 本專案沒有與任何現有的 disentanglement 方法進行定量比較，也沒有使用標準化的解耦指標（如 DCI score、mutual information ratio）。

### 5.2 LLM-as-Judge 的偏差與局限

| 論文 | 發現 | 對本專案的影響 |
|------|------|-------------|
| Zheng et al. (2023) "Judging LLM-as-a-Judge" NeurIPS | LLM judge 存在 position bias、verbosity bias、self-enhancement bias | 本專案的 format_compliance 和 content_preservation 可能受這些偏差影響。|
| Panickssery et al. (2024) "LLM Evaluators Recognize and Favor Their Own Generations" | LLM 偏好自己模型家族的輸出 | GPT-4o-mini 評估 GPT-4o-mini 的輸出可能系統性高估。|
| Liu et al. (2023) "G-Eval: NLG Evaluation using GPT-4" EMNLP | 即使 GPT-4 做 judge 也需要人工校準 | 本專案缺少人工校準步驟。|
| Wang et al. (2023) "ChatGPT as NLG Evaluator: a Preliminary Study" | GPT 評分的粒度有限 | 與本專案中 content_preservation 只有 2-3 個離散值的現象一致。|

### 5.3 自我修正的局限

| 論文 | 發現 | 對 Paper 3 的影響 |
|------|------|-----------------|
| Madaan et al. (2023) "Self-Refine: Iterative Refinement with Self-Feedback" NeurIPS | 在不使用 ground truth 的情況下，self-refine 效果有限 | Paper 3 使用了 ground truth（原始公文），不是真正的 self-refine。|
| Huang et al. (2024) "Large Language Models Cannot Self-Correct Reasoning Yet" ICLR | LLM 無法通過 self-correction 改善推理 | 對 Paper 3 的 self-correction 假說提出根本質疑。|
| Kamoi et al. (2024) "When Can LLMs Actually Correct Their Own Mistakes?" TACL | 許多 self-correction 論文高估了效果，因為使用了 oracle 信息 | Paper 3 的 Critique 步驟直接使用了原始公文作為 oracle。|
| Stechly et al. (2024) "Self-Verification Improves Few-Shot Clinical Information Extraction" | 在特定領域（臨床），有條件的自我驗證可以改善 | Paper 3 的場景可能更類似這種有限的改善。|

### 5.4 結構化信息提取

| 論文 | 方法 | 與本專案的關係 |
|------|------|--------------|
| Wei et al. (2023) "Zero-Shot Information Extraction via Chatting with ChatGPT" | 用 LLM 做零樣本信息提取 | 本專案的 Encoder 本質上就是這種方法。|
| Xu et al. (2024) "Large Language Models for Generative Information Extraction: A Survey" | LLM 做結構化抽取的全面調查 | 本專案的 Encoder 屬於此類方法，但論文中沒有引用。|
| Dunn et al. (2022) "Structured Information Extraction from Complex Scientific Text with Fine-tuned LLMs" | 從科學文本提取結構化信息 | Nature Comms 發表，使用了真實數據和人工驗證，方法論更嚴謹。|

### 5.5 政府/法律文件處理

| 論文 | 內容 | 與本專案的關係 |
|------|------|--------------|
| 台灣司法院判決書 NLP 研究 | 使用真實法律文件做 NLP | 本專案應使用真實公文而非合成數據。|
| Chalkidis et al. (2020) "LEGAL-BERT" ACL | 法律領域的預訓練模型 | 領域特化的重要性。|
| Zhong et al. (2020) "JEC-QA: A Legal-Domain Question Answering Dataset" AAAI | 中文法律 QA | 中文法律/政府文件 NLP 的先例。|
| 各種 Chinese NLP 研究 | 中文分詞、命名實體識別 | 中文公文有其特殊的語言處理挑戰。|

### 5.6 可控文本生成 & 模板生成

| 論文 | 方法 | 與本專案的關係 |
|------|------|--------------|
| Shen et al. (2017) "Style Transfer from Non-Parallel Text by Cross-Alignment" NeurIPS | 非平行文本風格遷移 | 與 Paper 1 的交叉重建概念相似。|
| Hu et al. (2017) "Toward Controlled Generation of Text" ICML | VAE + attribute discriminator | 控制文本生成的經典方法。|
| Li et al. (2018) "Delete, Retrieve, Generate" NAACL | 操作式風格遷移 | 更簡單的 content-style 操作方法。|
| Keskar et al. (2019) "CTRL: A Conditional Transformer Language Model" | 控制碼引導生成 | 用控制碼控制文本屬性。|
| Yang et al. (2023) "Doc2Bot: Accessing Heterogeneous Documents via Conversational Bots" EMNLP Findings | 從文件生成對話 | 文件到結構化表示的轉換。|

---

## 6. 評估指標的根本問題 (Evaluation Metric Issues)

### 6.1 Embedding Similarity 作為主要指標的問題

content_accuracy（權重 25%，最高）和 semantic_similarity（權重 20%）都基於 embedding cosine similarity。問題在於：

1. **Embedding 空間的高基準**：text-embedding-3-small 對語義相似的中文文本天然產生高 cosine similarity（通常 > 0.7），即使文本有重大差異。
2. **JSON 格式的影響**：將 Content JSON 序列化為字串再做 embedding 比較，但 JSON 的 key 名稱（topic, intent, key_events 等）在所有樣本中都相同，這會人為提高 similarity。
3. **缺少 baseline 對比**：不知道隨機配對的文件之間的 embedding similarity 是多少。如果隨機基準已經是 0.6，那麼 0.89 的 content_accuracy 的實際信號可能沒有看起來那麼強。

### 6.2 六維指標的獨立性問題

六個指標之間可能高度相關：
- rule_adherence 和 format_compliance 都衡量格式正確性
- semantic_similarity 和 content_preservation 都衡量內容保留
- content_accuracy 衡量的是 Encoder 提取品質，而非重建品質

加權求和可能放大了某些維度的影響。缺少指標間的相關性分析。

### 6.3 structural_match 只比較 6 個離散欄位

structural_match 只檢查 6 個欄位（doc_type, tone, required_sections, formality_level, has_attachments, speed_class）是否完全匹配。這意味著分數只能取 {0, 1/6, 2/6, 3/6, 4/6, 5/6, 1}。實際出現的值為 {0.5, 0.667, 0.833, 1.0}，粒度非常粗。

---

## 7. 各論文逐篇評審 (Per-Paper Reviews)

### Paper 1: Symbolic Disentanglement (符號化解耦)

**目標：** ACL / EMNLP / COLING
**子評分：** 30/100

**主要問題：**
1. 「解耦」的證據來自消融實驗，但消融中的 content_accuracy 和 structural_match 是恆等式而非實驗發現（見 E5）。
2. 交叉重建只用了 1 份文件的 Content（見 E1），結論不可泛化。
3. 沒有與任何現有的 disentanglement 方法比較。
4. 「Symbolic AutoEncoder」的術語使用不當（見 W1）。
5. 消融實驗的 default Rules（函/平行/高/無附件）仍然提供了大量格式信息，不是真正的「歸零」。

**需要改進：**
- 使用標準解耦指標（DCI score, mutual information）
- 在真實公文上測試
- 增加交叉重建的多樣性
- 與 β-VAE/FactorVAE 等方法比較

### Paper 2: Structured Bottleneck (結構化瓶頸)

**目標：** ACL / EMNLP / NAACL
**子評分：** 40/100

**主要問題：**
1. AE vs Direct 的比較存在根本性的信息不對稱（見 W4）。
2. 統計顯著性主要由粗粒度的 content_preservation 驅動（見 E2）。
3. 循環一致性可能只是反映 LLM 的 deterministic pattern（見 W3）。
4. 缺少人工評估驗證（見 E4）。

**亮點：**
- 如果修正比較的公平性（例如給 Direct path 同等量的信息），可能仍然有有趣的發現。
- Cycle consistency 的概念是好的，但需要更嚴格的控制。

### Paper 3: Self-Refining Agent (自我修正)

**目標：** ACL / EMNLP
**子評分：** 35/100

**主要問題：**
1. 使用了 ground truth 進行 Critique，不是真正的 self-correction（見 W5）。
2. 只有 N=3 個文件，統計推斷不可能。
3. 3 個文件中 2 個沒有改善（best_score = initial_score）。
4. 與 Madaan et al. (2023) Self-Refine 的直接比較缺失。
5. 只修改 Rules 不修改 Content 的修正策略過於受限。

---

## 8. 分項評分 (Breakdown Scores)

| 維度 | 分數 (0-100) | 說明 |
|------|------------|------|
| **新穎性 (Novelty)** | 35 | 概念有創意但類比不準確；content-style 分離已被大量研究 |
| **方法論嚴謹性 (Rigor)** | 20 | 多個根本性方法論問題（循環評估、不公平比較、術語誤用）|
| **實驗設計 (Experimental Design)** | 25 | 交叉重建設計嚴重缺陷、樣本量不足、缺少人工評估 |
| **數據品質 (Data Quality)** | 30 | 合成數據語義不連貫、無真實公文驗證 |
| **技術貢獻 (Technical Contribution)** | 40 | 管線完整、代碼結構清晰、可復現 |
| **文獻回顧 (Literature Review)** | 25 | 大量相關工作未引用，缺少與現有方法的比較 |
| **寫作品質 (Writing)** | 50 | 中文文檔清晰、結構化，但尚未有正式英文論文稿 |
| **實際影響 (Impact)** | 45 | 台灣公文處理是一個有實際價值的應用場景 |
| **統計分析 (Statistical Analysis)** | 40 | 數字準確但粒度分析不足，統計檢定的前提條件未驗證 |
| **可復現性 (Reproducibility)** | 60 | 代碼完整、數據有保存，但依賴商業 API（GPT-4o-mini）|
| **加權總分** | **38** | |

---

## 9. 潛在研究方向 (Potential Research Directions)

基於本專案的核心概念，以下是我觀察到的有潛力的研究方向：

### RD1. ★★★ 真實公文的大規模解耦研究
- 與台灣政府機關合作，取得真實公文（可脫敏處理）
- 在真實數據上驗證 Content-Rules 分離的可行性
- 分析真實公文中 Content 和 Rules 的相關性分佈
- 建立台灣公文的第一個公開 NLP 基準數據集

### RD2. ★★★ 將 SFT_data.json 整合為訓練/評估資源
- 專案中有 16.5MB 的 SFT 數據，包含鴻海 FoxBrain 的公文生成樣本，含有 thinking/reasoning chain
- 這些數據可以用來訓練一個真正的（可學習的）公文自編碼器
- 或用作評估基準，取代合成數據

### RD3. ★★ 使用可學習的 Adapter 實現真正的自編碼器
- 使用 LoRA 或 Adapter 訓練一個真正的 Encoder（可參考 ICAE, Ge et al. 2023）
- 定義明確的重建損失函數並用梯度下降優化
- 這樣才能在學術上正當地稱為「AutoEncoder」

### RD4. ★★ 多語言/多文體的解耦研究
- 將框架擴展到其他高度結構化的文體（法律文件、醫療報告、學術論文）
- 跨語言比較（台灣公文 vs 日本公文 vs 韓國公文）
- 研究不同文體中 content-style 耦合程度的差異

### RD5. ★★ 人類對公文「解耦品質」的認知研究
- 設計人類評估實驗：給公務員看 Content JSON 和 Rules JSON，請他們評估是否完整捕捉了原文
- 研究人類與 LLM judge 之間的一致性
- 建立公文品質評估的 gold standard

### RD6. ★ 公文風格遷移的應用研究
- 將解耦框架應用於實際的公文風格遷移場景
- 例如：將「簽」轉換為「函」，或將「下行」語氣轉為「上行」語氣
- 評估遷移後公文的可用性和專業性

### RD7. ★ 探索 Information Leakage 的量化方法
- 開發量化 Content → Rules 和 Rules → Content 信息洩漏的指標
- 使用 mutual information、probing classifier 等技術
- 為「解耦度」提供更嚴格的理論基礎

---

## 10. 修改建議 (Revision Recommendations)

### 短期修改（可在 1-2 個月內完成）

1. **修改術語**：放棄「Symbolic AutoEncoder」的命名，改用更準確的名稱如 "LLM-based Content-Format Decomposition" 或 "Symbolic Disentanglement Pipeline"
2. **修正交叉重建實驗**：使用完整的 N×N 矩陣或至少隨機抽樣多個不同的 Content source
3. **增加人工評估**：至少 50 個樣本的人工評審，計算 inter-rater agreement
4. **修正 Paper 2 比較**：給 Direct path 同等量的輸入信息（完整的 Content 描述，而非僅 topic）
5. **增加隨機基準**：報告隨機配對文件之間的 embedding similarity 作為 baseline
6. **修正語義不連貫的數據**：確保主題與發文機關/受文機關的搭配在語義上合理

### 中期修改（需要 3-6 個月）

7. **使用真實公文**：至少部分實驗應在真實公文上進行
8. **增加樣本量**：至少 100 個文件
9. **增加比較方法**：與至少一種基準方法（如 β-VAE、GPT-4 直接提取等）比較
10. **使用標準化解耦指標**：DCI score、mutual information ratio 等
11. **分離評估模型**：使用不同的 LLM（如 Claude）作為 judge，避免自我偏好

### 長期方向（6+ 個月）

12. **訓練真正的自編碼器**：使用 SFT 數據訓練可學習的 Encoder/Decoder
13. **建立公開數據集**：與政府機關合作建立台灣公文 NLP 基準
14. **跨文體驗證**：在法律文件、醫療報告等其他結構化文體上驗證框架

---

## 附錄 A：引用的比較論文清單

1. Bowman et al. (2016) "Generating Sentences from a Continuous Space" CoNLL
2. Higgins et al. (2017) "β-VAE: Learning Basic Visual Concepts with a Constrained Variational Framework" ICLR
3. Kim & Mnih (2018) "Disentangling by Factorising" ICML
4. Chen et al. (2018) "Isolating Sources of Disentanglement in Variational Autoencoders" NeurIPS
5. Hu et al. (2017) "Toward Controlled Generation of Text" ICML
6. Shen et al. (2017) "Style Transfer from Non-Parallel Text by Cross-Alignment" NeurIPS
7. Li et al. (2018) "Delete, Retrieve, Generate: A Simple Approach to Sentiment and Style Transfer" NAACL
8. John et al. (2019) "Disentangled Representation Learning for Non-Parallel Text Style Transfer" ACL
9. Bao et al. (2019) "Generating Sentences from Disentangled Syntactic and Semantic Spaces" ACL
10. Cheng et al. (2020) "Improving Disentangled Text Representation Learning with Information-Theoretic Guidance" ACL
11. Keskar et al. (2019) "CTRL: A Conditional Transformer Language Model" arXiv
12. Hu et al. (2022) "Text Style Transfer: A Survey" Computational Linguistics
13. Zheng et al. (2023) "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" NeurIPS
14. Liu et al. (2023) "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment" EMNLP
15. Wang et al. (2023) "Is ChatGPT a Good NLG Evaluator?" NewSumm Workshop
16. Panickssery et al. (2024) "LLM Evaluators Recognize and Favor Their Own Generations" arXiv
17. Madaan et al. (2023) "Self-Refine: Iterative Refinement with Self-Feedback" NeurIPS
18. Huang et al. (2024) "Large Language Models Cannot Self-Correct Reasoning Yet" ICLR
19. Kamoi et al. (2024) "When Can LLMs Actually Correct Their Own Mistakes?" TACL
20. Ge et al. (2023) "In-Context Autoencoder for Context Compression in a Large Language Model" ICLR 2024
21. Wei et al. (2023) "Zero-Shot Information Extraction via Chatting with ChatGPT" arXiv
22. Xu et al. (2024) "Large Language Models for Generative Information Extraction: A Survey" Frontiers of CS
23. Dunn et al. (2024) "Structured Information Extraction from Scientific Text with Fine-tuned LLMs" Nature Comms
24. Chalkidis et al. (2020) "LEGAL-BERT: The Muppets Straight out of Law School" EMNLP Findings
25. Zhong et al. (2020) "JEC-QA: A Legal-Domain Question Answering Dataset" AAAI
26. Yang et al. (2023) "Doc2Bot: Accessing Heterogeneous Documents via Conversational Bots" EMNLP Findings
27. Locatello et al. (2019) "Challenging Common Assumptions in the Unsupervised Learning of Disentangled Representations" ICML (Best Paper)
28. Kingma & Welling (2014) "Auto-Encoding Variational Bayes" ICLR
29. Razavi et al. (2019) "Generating Diverse High-Fidelity Images with VQ-VAE-2" NeurIPS
30. van den Oord et al. (2017) "Neural Discrete Representation Learning" (VQ-VAE) NeurIPS
31. Zhao et al. (2018) "Adversarially Regularized Autoencoders" ICML
32. Li et al. (2020) "Optimus: Organizing Sentences via Pre-trained Modeling of a Latent Space" EMNLP
33. Dathathri et al. (2020) "Plug and Play Language Models" ICLR
34. Yang & Klein (2021) "FUDGE: Controlled Text Generation With Future Discriminators" NAACL
35. Liu et al. (2021) "DExperts: Decoding-Time Controlled Text Generation" ACL
36. Bai et al. (2022) "Constitutional AI: Harmlessness from AI Feedback" arXiv
37. Shinn et al. (2023) "Reflexion: Language Agents with Verbal Reinforcement Learning" NeurIPS
38. Chen et al. (2024) "Teaching Large Language Models to Self-Debug" ICLR
39. Olausson et al. (2024) "Is Self-Repair a Silver Bullet for Code Generation?" ICLR
40. Stechly et al. (2024) "Self-Verification Improves Few-Shot Clinical Information Extraction" arXiv
41. Peng et al. (2023) "Check Your Facts and Try Again: Improving LLMs with External Knowledge and Automated Feedback" arXiv
42. Welleck et al. (2023) "Generating Sequences by Learning to Self-Correct" ICLR

---

## 附錄 B：審查者聲明

本審查報告由 Claude Opus 4.6 自動生成，基於對專案代碼、數據、論文大綱的全面閱讀，以及對 40+ 篇相關文獻的比較分析。所有數值驗證均通過程式化計算確認。

本報告的目的是提供建設性的學術反饋，幫助作者識別需要改進的領域。嚴格的批評是學術進步的基礎——被指出的問題不代表概念本身沒有價值，而是指出了從概念到可發表論文之間需要填補的差距。

---

*報告結束 — 2026-02-11*
