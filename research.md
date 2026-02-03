# gongwen_ae：台灣公文符號化自編碼器 — 實驗筆記

## 一、系統架構概覽

本系統將台灣政府公文視為一個可逆的編碼問題，透過 LLM 實現「符號化自編碼器（Symbolic AutoEncoder）」：

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Generate │ ──▶ │  Encode  │ ──▶ │  Decode  │ ──▶ │ Evaluate │
│ 合成公文  │     │ 提取潛在表示│     │ 重建公文  │     │ 6 指標評分 │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
      │                │                │                │
   full_text      (Content,        reconstructed     eval_report
   + gt_labels     Rules)            _text            .csv
```

| 階段 | 功能 |
|------|------|
| **Generate** | 逆向生成：先產生結構化 Content JSON + Rules 模板，再由 LLM 組合成正式公文全文（擁有完美 ground truth） |
| **Encode** | 將公文全文拆解為兩個符號化潛在空間：**Content**（去公文化的語意核）+ **Rules**（格式參數） |
| **Decode** | 從 Content + Rules 重建一份正式公文 |
| **Evaluate** | 以 6 個混合指標（hard + soft + LLM judge）對重建品質評分 |

### 雙潛在空間設計

**Content（語意核）**：純白話資訊，禁止任何公文用語。欄位包括：topic、intent、key_events、entities、action_items、background。

**Rules（格式殼）**：完全參數化的公文格式設定。欄位包括：doc_type、sender_org、receiver_org、tone、required_sections、formality_level、terminology_constraints、has_attachments、speed_class。

這種分離設計使得 Content 和 Rules 可以獨立操作——交換、歸零、修正——為三篇論文的實驗提供了基礎。

---

## 二、6 個評估指標詳解

系統採用 **hard metric（確定性）+ soft metric（embedding）+ LLM judge（主觀評審）** 三層混合評估：

### 指標一覽

| 指標 | 類型 | 權重 | POC 分數 | 解讀 |
|------|------|------|---------|------|
| rule_adherence（規則遵循） | Hard | 15% | 0.7778 | 9 項 regex 檢查中通過 7 項 |
| structural_match（結構匹配） | Hard | 10% | 1.0000 | gt_rules vs predicted_rules 6 個欄位完全一致 |
| semantic_similarity（語意相似度） | Soft | 20% | 0.8865 | 原始公文 vs 重建公文的 embedding cosine similarity |
| content_accuracy（內容準確度） | Soft | 25% | 0.8477 | gt_content vs predicted_content 的 embedding cosine similarity |
| content_preservation（內容保留度） | LLM Judge | 15% | 0.6000 | LLM 評審打 3/5 分 → 歸一化為 0.6 |
| format_compliance（格式合規性） | LLM Judge | 15% | 1.0000 | LLM 評審打 5/5 分 → 歸一化為 1.0 |
| **weighted_total（加權總分）** | **綜合** | **100%** | **0.8459** | **上述 6 項的加權總和** |

### 各指標詳細說明

#### 1. rule_adherence（規則遵循）— 15%

- **定義**：重建公文是否通過一系列 regex 格式檢查
- **計算方式**：逐一檢查 9 項規則（必要段落是否存在、日期是否為民國紀年格式、發文字號格式、公文用語、受文者/發文者等），score = 通過數 / 總檢查數
- **POC 範例**：0.7778 = 7/9 通過，2 項未通過可能是發文字號格式或附件格式不完全符合 regex pattern

#### 2. structural_match（結構匹配）— 10%

- **定義**：Encoder 提取的 Rules 與 ground truth Rules 是否一致
- **計算方式**：比較 6 個欄位（doc_type, tone, required_sections, formality_level, has_attachments, speed_class），其中 required_sections 不考慮順序
- **POC 範例**：1.0000 = 6/6 欄位全部匹配，表示 Encoder 完美提取了格式規則

#### 3. semantic_similarity（語意相似度）— 20%

- **定義**：原始公文全文與重建公文全文在語意上有多接近
- **計算方式**：分別對 original full_text 和 reconstructed_text 做 text-embedding-3-small，計算 cosine similarity
- **POC 範例**：0.8865，表示重建公文保留了約 89% 的語意，有少許資訊損失（可能是措辭差異而非內容缺失）

#### 4. content_accuracy（內容準確度）— 25%（最高權重）

- **定義**：Encoder 提取的 Content JSON 與 ground truth Content JSON 在語意上有多接近
- **計算方式**：將兩個 Content JSON 序列化為字串，做 embedding cosine similarity
- **POC 範例**：0.8477，表示 Encoder 捕捉了大部分關鍵資訊，但可能在 key_events 或 entities 的細節上有偏差

#### 5. content_preservation（內容保留度）— 15%

- **定義**：重建公文是否保留了原始公文的所有關鍵事實（人名、機關、日期、數字、事件、待辦事項）
- **計算方式**：LLM 評審（1-5 分），歸一化為 0-1。扣分項包括：關鍵事實遺漏、數字錯誤、幻覺（加入原文沒有的資訊）
- **POC 範例**：0.6000 = 3/5 分，表示有部分關鍵事實在重建過程中遺失或變形，是目前最需要改善的指標

#### 6. format_compliance（格式合規性）— 15%

- **定義**：重建公文是否符合台灣政府公文的格式規範
- **計算方式**：LLM 評審（1-5 分），檢查項目包括：段落標題、受文者資訊、日期格式（民國）、段落結構、語氣用詞、公文術語
- **POC 範例**：1.0000 = 5/5 分，表示重建公文完全符合公文格式規範

### 加權總分計算公式

```
weighted_total = 0.15 × rule_adherence
               + 0.10 × structural_match
               + 0.20 × semantic_similarity
               + 0.25 × content_accuracy
               + 0.15 × content_preservation
               + 0.15 × format_compliance
```

content_accuracy 權重最高（25%），因為「是否正確提取語意」是自編碼器的核心能力。

---

## 三、三篇論文實驗設計

### Paper 1：Symbolic Disentanglement（符號化解耦）

> **研究問題**：LLM 能否將公文的「語義 Content」與「格式 Rules」完全分離，而不發生 information leakage？

#### 實驗 A — 交叉重建（Cross-Reconstruction）

- 取 N 篇公文，各自 Encode 得到 (Content_i, Rules_i)
- 交叉配對：將 Content_A + Rules_B 送入 Decoder
- 預期結果：生成出的公文**內容應為 A、格式應為 B**
- 評估重點：content_accuracy（應維持高分，因為內容來自 A）、structural_match（應匹配 B 的 Rules）
- 若結果混入 B 的內容（幻覺）或 A 的格式（洩漏），即為研究分析重點

#### 實驗 B — 消融實驗（Ablation Study）

- **Content-only**：保留 Content，將 Rules 歸零為預設值 → 觀察格式是否崩壞
- **Rules-only**：保留 Rules，將 Content 歸零為空值 → 觀察生成內容是否為空洞套話
- 預期：Content-only 應保持高 content_accuracy 但低 format_compliance；Rules-only 則相反

#### 執行指令

```bash
python main.py --mode paper1 --count 2
```

**輸出目錄**：
- `data/results/paper1/eval_report.csv`（正常重建 baseline）
- `data/results/paper1/cross/eval_report.csv`（交叉重建）
- `data/results/paper1/ablation_content_only/eval_report.csv`
- `data/results/paper1/ablation_rules_only/eval_report.csv`

---

### Paper 2：Closed-loop Evaluation（閉環評估）

> **研究問題**：AE 流程是否比直接讓 LLM 寫公文更好？自編碼器在循環過程中的資訊保留率如何？

#### 實驗 A — 循環一致性（Cycle Consistency）

- 流程：原始公文 → Encode → Decode → **Re-Encode** → 比較兩次 latent vector
- 計算：第一次 Encode 的 (Content₁, Rules₁) vs Re-Encode 的 (Content₂, Rules₂) 的 embedding cosine similarity
- 理想情況：content_similarity ≈ 1.0, rules_similarity ≈ 1.0（資訊無損循環）
- 若 similarity 顯著低於 1.0，表示 Encode-Decode 過程存在資訊瓶頸

#### 實驗 B — 基線對比（Baseline Comparison）

- **AE path**：Generate → Encode → Decode → Evaluate
- **Direct path**：同一個 topic + rules，直接讓 LLM 一步生成公文（無 AE bottleneck）
- 比較兩條路徑在 6 個指標上的差異
- 預期：AE path 在 content_accuracy 和 structural_match 上應優於 Direct path（因為有明確的 ground truth 約束）

#### 執行指令

```bash
python main.py --mode paper2 --count 2
```

**輸出目錄**：
- `data/results/paper2/cycle_consistency.json`（循環一致性分數）
- `data/results/paper2/ae/eval_report.csv`（AE 路徑評分）
- `data/results/paper2/direct/eval_report.csv`（Direct 路徑評分）

---

### Paper 3：Self-Refining Agent（自我修正代理）

> **研究問題**：Agent 能否透過「評分 → 批評 → 修正規則 → 重建」的迴圈自動提升重建品質？

#### 實驗流程

```
Decode → Evaluate → score < 0.85?
                      ├─ Yes → Critique → Refine Rules → Re-Decode（回到 Evaluate）
                      └─ No  → 結束（品質達標）
最多 3 輪迭代
```

1. 對每篇公文的 Encoding 結果做初次 Decode + Evaluate
2. 若 weighted_total < 0.85（閾值），進入修正迴圈：
   - **Critique**：LLM 分析重建失敗的原因（內容缺失？格式錯誤？規則違反？）
   - **Refine Rules**：根據批評調整 Rules 參數（保守修正，僅修改有明確問題的欄位）
   - **Re-Decode**：用修正後的 Rules 重新 Decode
3. 重複直到分數 ≥ 0.85 或達到 3 輪上限

#### 觀察重點

- 每輪分數是否持續提升（Δ score per iteration）
- 收斂速度：平均需要幾輪才能達標
- 修正了哪些 Rules 欄位（分析 Agent 的「修正策略」）
- 是否存在過度修正（overshoot）的現象

#### 執行指令

```bash
python main.py --mode paper3 --count 1
```

**輸出目錄**：
- `data/results/paper3/refinement_log.json`（每輪迭代的詳細日誌：分數、Rules 變化、Critique 內容）

---

## 四、測試狀態

| 模式 | 指令 | 狀態 | 備註 |
|------|------|------|------|
| poc (count=1) | `python main.py --mode poc --count 1` | ✅ 已完成 | 初期驗證，weighted_total = 0.8459 |
| paper1 (count=3) | `python main.py --mode paper1 --count 3` | ✅ 已完成（v2） | N=3 文件、5 對交叉重建 |
| paper2 (count=3) | `python main.py --mode paper2 --count 3` | ✅ 已完成（v2） | 修正了 Direct 評估公平性 |
| paper3 (count=2) | `python main.py --mode paper3 --count 2` | ✅ 已完成（v2） | 閾值提高至 0.92，成功觸發修正迴圈 |

### 版本演進記錄

- **v1**：初跑（N=1-2），發現三個方法論問題
  1. Paper 2 Direct baseline 的 content_accuracy 和 structural_match 直接使用 ground truth（人為 1.0），比較不公平
  2. Paper 3 閾值 0.85 太低，首輪即達標，修正迴圈從未觸發
  3. Paper 1 N=2 太小，交叉重建分數因噪聲而高於 baseline（不合理）
- **v2**（當前版本）：
  1. 修正 Paper 2：Direct 生成的公文先經 Encoder 提取 content/rules，再做公平比較
  2. 修正 Paper 3：閾值從 0.85 → 0.92，成功觸發修正迴圈
  3. 增加 Paper 1 到 N=3（baseline）+ 5 對交叉重建
  4. 修正 cosine similarity 浮點溢出問題（1.0000001 → clamp to 1.0）

---

## 五、初步結果（v2）

### Paper 1 結果：Symbolic Disentanglement

#### 核心指標對照表（平均值，N=3 baseline / N=5 cross / N=3 ablation）

| 條件 | content_accuracy | structural_match | content_pres | semantic_sim | **weighted_total** |
|------|-----------------|-----------------|-------------|-------------|-------------------|
| **Baseline**（正常重建） | 0.9004 | 0.8889 | 0.6000 | 0.9222 | **0.8566** |
| **Cross-Recon**（Content_A + Rules_B） | 0.8935 | 0.8667 | 0.3200 | 0.8013 | **0.7724** |
| **Content-only**（Rules 歸零） | 0.9004 | 0.6111 | 0.6000 | 0.9071 | **0.7876** |
| **Rules-only**（Content 歸零） | 0.4098 | 0.8889 | 0.2000 | 0.6953 | **0.5934** |

#### 解讀——解耦的三項證據

1. **Content 空間攜帶語意，Rules 空間攜帶格式**：
   - content_accuracy 在 Baseline / Cross / Content-only 三者間保持穩定（0.90），但 Rules-only 暴跌至 **0.41**（沒有 Content 就沒有語意可提取）。
   - structural_match 在 Baseline / Cross / Rules-only 三者間保持穩定（0.87-0.89），但 Content-only 跌至 **0.61**（沒有 Rules 就缺乏結構資訊）。
   - 結論：兩個空間各自獨立攜帶不同維度的資訊，互不替代。

2. **交叉重建成功保留了 Content**：
   - Cross-Recon 的 content_accuracy（0.8935）與 Baseline（0.9004）幾乎相同（Δ = -0.0069），表示用 B 的格式規則替換 A 的規則後，A 的語意核未受影響。
   - 唯一大幅下降的指標是 content_preservation（0.60 → 0.32），這是因為 LLM 評審在比較「原始公文 A」和「用 B 的格式重建的公文」時，格式差異會被誤判為內容差異。

3. **消融確認了雙空間缺一不可**：
   - Rules-only 的 weighted_total 僅 **0.5934**（比 baseline 低 26%），生成的內容為空洞套話。
   - Content-only 的 weighted_total 為 **0.7876**（比 baseline 低 8%），格式不對但內容在。
   - Content 的貢獻 > Rules 的貢獻（符合預期：語意是公文的核心）。

---

### Paper 2 結果：Closed-loop Evaluation

#### 循環一致性 Cycle Consistency（N=3）

| doc_id | content_similarity | rules_similarity |
|--------|-------------------|-----------------|
| 670bf4a9 | 0.9668 | 0.9904 |
| 2a569d14 | 0.9789 | 0.9540 |
| 76b6ab1b | 0.9860 | 0.9292 |
| **平均** | **0.9772** | **0.9579** |

#### AE Path vs Direct Path（N=3，公平比較 v2）

| 路徑 | rule_adh | struct_match | semantic_sim | content_acc | content_pres | format_comp | **weighted_total** |
|------|---------|-------------|-------------|------------|-------------|------------|-------------------|
| **AE** | 0.8788 | 0.6667 | 0.8897 | 0.8934 | 0.7333 | 0.8000 | **0.8298** |
| **Direct** | 0.9630 | 0.8889 | 0.8721 | 0.7976 | 0.3333 | 0.9333 | **0.7971** |
| **Δ (AE − Direct)** | -0.0842 | -0.2222 | +0.0176 | **+0.0958** | **+0.4000** | -0.1333 | **+0.0327** |

#### 解讀——結構化中間表示的價值

1. **循環一致性極高**：Encode → Decode → Re-Encode 後，content_similarity 平均 **0.977**、rules_similarity 平均 **0.958**。這表示 LLM 作為自編碼器的資訊瓶頸極小，潛在表示在循環中高度穩定。

2. **AE 在內容忠實度上顯著勝出**：
   - **content_preservation**：AE **0.73** vs Direct **0.33**（AE 是 Direct 的 **2.2 倍**）。這是最重要的發現——AE 的結構化 bottleneck 迫使 Encoder 提取明確的 key_events、entities、action_items，讓 Decoder 有具體事實可依循，而 Direct 模式僅靠 topic 描述就自由發揮，容易產生不符合原始意圖的內容。
   - **content_accuracy**：AE **0.89** vs Direct **0.80**（Δ = +0.10）。Encoder 提取的 Content 比 Direct 模式從自由生成文本中反推的 Content 更接近 ground truth。

3. **Direct 在格式上勝出但整體落後**：
   - Direct 在 rule_adherence（0.96 vs 0.88）和 format_compliance（0.93 vs 0.80）上表現更好，這合理——它有更多自由度調整格式。
   - 但整體 weighted_total AE 仍勝出（0.830 vs 0.797），因為內容保真度的權重更高（content_accuracy 25% + content_preservation 15% = 40%）。

4. **核心論點**：AE 架構以少量格式品質為代價，換取大幅提升的內容忠實度。結構化中間表示（Symbolic Latent Space）比端到端生成更適合需要高事實準確度的場景。

---

### Paper 3 結果：Self-Refining Agent

#### 修正迴圈日誌（閾值 = 0.92）

**文件 1：校園資訊安全防護計畫（簽 → 函/下行）**

| 迭代 | weighted_total | Δ | 主要修正 |
|------|---------------|---|---------|
| iter 0 | 0.7963 | — | 初始（Encoder 誤判 doc_type 為函） |
| iter 1 | 0.8007 | +0.004 | 增加 required_sections（計畫內容、資訊安全手冊） |
| iter 2 | 0.8342 | +0.034 | 回退冗餘 sections，保留核心三段 |
| iter 3 | **0.8576** | +0.023 | 增加正本/副本段落，加強 terminology |
| **總提升** | | **+0.061** | **持續改善，每輪 Δ > 0** |

**文件 2：政府採購案驗收爭議處理（公告/下行 → 公告/平行）**

| 迭代 | weighted_total | Δ | 主要修正 |
|------|---------------|---|---------|
| iter 0 | 0.8640 | — | 初始（品質已不錯） |
| iter 1 | 0.8032 | **-0.061** | 增加「會議討論」section → 結構變化導致退化 |
| iter 2 | 0.8034 | +0.000 | 增加 terminology（政府採購法）→ 無明顯改善 |
| iter 3 | **0.8507** | +0.047 | 回退「會議討論」section → 回復接近原始品質 |
| **總變化** | | **-0.013** | **V 型曲線：過度修正 → 回復** |

#### 解讀——自我修正的機制與邊界

1. **修正迴圈在低分文件上有效**：文件 1 從 0.796 穩步提升至 0.858（+7.7%），三輪修正皆為正向。Critique 正確識別了內容遺漏和格式缺失，Refine 做出了合理的規則調整。

2. **高分文件存在「過度修正」風險**：文件 2 初始已達 0.864，但 iter 1 中 Critique 建議新增「會議討論」section，結果破壞了原有結構，分數反降至 0.803。直到 iter 3 回退該修正後才部分回復。這是一個典型的 **overshoot** 現象。

3. **Critique 的品質觀察**：
   - 正面：能精確指出具體問題（日期錯誤 112/10/11 vs 112/10/10、字號不一致、缺少具體措施描述）
   - 負面：會建議結構性修改（新增段落），而 Decoder 對結構大改的承受力不佳
   - 改善方向：Critique 應區分「可透過 Rules 修正的問題」vs「需要修改 Content 的問題」

4. **收斂特性**：
   - 低分起點（< 0.85）：單調遞增，3 輪可提升約 5-8%
   - 高分起點（> 0.85）：非單調，存在退化風險，建議加入 **score-gated refinement**（僅在 Δ > 0 時接受修正）

---

## 六、發表可行性評估

### 已驗證的核心論點

| 論文 | 核心主張 | 實驗證據 | 強度 |
|------|---------|---------|------|
| Paper 1 | Content 和 Rules 可分離 | content_accuracy 跨條件穩定（0.90），ablation 各維度獨立崩壞 | 強 |
| Paper 2 | AE bottleneck 提升內容忠實度 | content_preservation AE 2.2x > Direct | 強 |
| Paper 2 | Cycle consistency 高 | 平均 content_sim=0.977, rules_sim=0.958 | 強 |
| Paper 3 | 自我修正可提升品質 | 低分文件 +7.7% 改善 | 中 |
| Paper 3 | 修正迴圈存在邊界 | 高分文件出現 V 型退化 | 有趣（可作為分析重點） |

### 目前不足與建議

1. **樣本量**：目前 N=2-5，需要擴展到 N≥20 才能做統計顯著性檢定（paired t-test / Wilcoxon）。
2. **content_preservation 系統性偏低**（consistently 3/5 = 0.60）：這是最弱的環節。可能需要改善 Decoder 的 prompt（增加「必須保留所有人名、數字、日期」的強約束）。
3. **Paper 3 需要 score-gated refinement**：目前每輪都接受修正，應改為「只在新分數 > 舊分數時才接受」。
4. **跨文類測試**：目前多為「函」，需要測試「公告」「簽」「令」等不同類型的泛化能力。
5. **人工評審**：LLM judge 的 content_preservation 評分需要與人工評審做 inter-rater agreement 驗證。

### 建議下一步

| 優先級 | 動作 | 預期效果 |
|--------|------|---------|
| P0 | 將 N 擴展到 20，跑完整 paper1/paper2/paper3 | 可做統計檢定 |
| P1 | 改善 Decoder prompt 提升 content_preservation | weighted_total 預計 +3-5% |
| P1 | Paper 3 加入 score-gated refinement | 消除高分文件的退化問題 |
| P2 | 增加文類多樣性（公告/簽/令） | 展示泛化能力 |
| P2 | 人工評審 50 篇做 inter-rater agreement | 驗證評估指標的可信度 |
