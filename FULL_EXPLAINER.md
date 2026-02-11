# GongWen-AE 全原理白話解讀

> **風格**：管顧式——先講道理，再給名詞；每個公式都附帶數字跑一遍。
> **對象**：具 CS / EE / AI / ML 背景的理工讀者。

---

## 目錄

1. [一句話理解整個專案](#一句話理解整個專案)
2. [在解決什麼問題？](#在解決什麼問題)
3. [為什麼這個問題重要？](#為什麼這個問題重要)
4. [核心原理：符號化自編碼器](#核心原理符號化自編碼器)
5. [四階段 Pipeline 逐步拆解](#四階段-pipeline-逐步拆解)
6. [雙潛在空間設計原理](#雙潛在空間設計原理)
7. [六維評估系統原理](#六維評估系統原理)
8. [三篇論文的實驗邏輯](#三篇論文的實驗邏輯)
9. [實驗結果解讀](#實驗結果解讀)
10. [整體架構決策的工程直覺](#整體架構決策的工程直覺)

---

## 一句話理解整個專案

把一份正式公文**拆成「說了什麼」和「怎麼說的」兩個 JSON**，再用這兩個 JSON 還原公文。如果還原出來的東西跟原文差不多，就證明拆法是對的。

---

## 在解決什麼問題？

### 背景：公文是一種「內容+格式」高度耦合的文體

台灣政府公文有兩個面向同時存在：

| 面向 | 舉例 | 性質 |
|------|------|------|
| **語義內容** | 「教育局要求大安高中做資安檢查」 | 跟著事件走，每份都不同 |
| **格式規則** | 「用函、下行語氣、必須有主旨/說明/辦法」 | 跟著文類走，同類公文格式一樣 |

問題是：當你讓 LLM 直接寫公文時，這兩個面向混在一起，你沒辦法單獨控制任何一個。

### 具體表現

想像你跟 LLM 說：「幫我寫一份關於資安防護的公文」

LLM 可能的問題：
- **幻覺**：你只提了 A 事件，它自己編了 B、C 事件
- **格式不穩定**：同一主題，跑兩次生出兩種格式
- **無法遷移**：你想把同一份內容改成「簽」的格式，得重新 prompt 一遍，結果內容也跟著變了

**根本原因**：LLM 把「內容」和「格式」當成一團東西處理，沒有分開。

---

## 為什麼這個問題重要？

### 1. 可控性（Controllability）

工程價值：如果你能把內容和格式拆開，就能做到——

- **風格遷移**：同一份「核准補助」的內容，一鍵切換成「函」「簽」「公告」
- **模板填充**：固定格式，只換內容，批量生成同類公文
- **精準修改**：只改格式（比如把「平行」改成「下行」），內容不動

### 2. 可解釋性（Interpretability）

傳統 AutoEncoder（如 VAE）壓縮出來的是一個 128 維向量，人看不懂。

本系統壓縮出來的是兩個 **JSON**，人直接就能讀：

```
❌ VAE latent: [0.23, -1.47, 0.82, ..., -0.15]  ← 看不懂
✅ Symbolic latent: {"topic": "資安防護計畫", "intent": "要求配合執行"}  ← 看得懂
```

### 3. 可評估性（Evaluability）

因為潛在表示是人類可讀的 JSON，你可以直接跟 ground truth 比——欄位對不對、事實全不全。神經網路的 latent vector 做不到這一點。

---

## 核心原理：符號化自編碼器

### 先講 AutoEncoder 的本質

AutoEncoder 的核心思想：

```
輸入 → 壓縮（Encoder）→ 壓縮表示（Latent）→ 還原（Decoder）→ 輸出

如果 輸出 ≈ 輸入，表示壓縮表示「抓住了」輸入的本質
```

**用日常比喻**：你讀了一篇 2000 字的文章，用 50 字跟朋友轉述，朋友聽完能重寫出一篇大意相同的文章。那你的 50 字就是好的「壓縮表示」。

### 本系統的 AutoEncoder

本系統做的不是向量壓縮，而是**結構化拆解**：

```
                    ┌─────────────────┐
                    │   Latent Space   │
                    │  (兩個 JSON)      │
                    │                  │
   ┌─────────┐     │  ┌───────────┐   │     ┌─────────┐
   │ 公文全文  │─Enc─│  │  Content  │   │─Dec─│ 重建公文  │
   │ (2000字) │     │  │ (語義核)   │   │     │ (2000字) │
   └─────────┘     │  └───────────┘   │     └─────────┘
                    │  ┌───────────┐   │
                    │  │   Rules    │   │
                    │  │ (格式殼)   │   │
                    │  └───────────┘   │
                    └─────────────────┘
```

**關鍵創新**：壓縮表示不是一個不可解釋的向量，而是兩個人類可讀可編輯的 JSON。

### 為什麼叫「符號化」？

| 方法 | 潛在表示 | 可讀性 | 可編輯性 |
|------|---------|--------|---------|
| VAE（傳統 AutoEncoder） | 128-d float vector | 不可讀 | 不可編輯 |
| **本系統（Symbolic AE）** | **兩個 JSON** | **可讀** | **可編輯** |

「符號化」= 潛在空間是人類符號（文字、JSON 欄位），不是連續數值。

---

## 四階段 Pipeline 逐步拆解

```
Generate ──▶ Encode ──▶ Decode ──▶ Evaluate
(合成公文)    (拆解)     (重組)     (打分)
```

### 第一階段：Generate（逆向資料生成）

**問題**：要評估 Encoder 的拆解是否正確，你需要知道「正確答案」（ground truth）。但真實公文沒有標註好的 Content 和 Rules。

**解法——逆向思維**：

不是「先有公文 → 再提取 Content/Rules」（沒有 ground truth）

而是「先造 Content + 選 Rules → 組合成公文」（Content 和 Rules 本身就是 ground truth）

```
正向（不可行）：公文 → (Content?, Rules?)  ← 你不知道正確答案是什麼
逆向（本系統）：Content + Rules → 公文      ← Content 和 Rules 就是正確答案
```

#### 逆向生成的三步流程

```
Step 1: LLM 根據主題生成 Content JSON（白話文，禁止公文用語）
         ↓
Step 2: 從 5 個預設模板中隨機選一個 Rules JSON
         ↓
Step 3: LLM 根據 Content + Rules 撰寫正式公文
         ↓
輸出：(公文全文, gt_content, gt_rules)  ← 三件套，gt = ground truth
```

**工程直覺**：這就像出考試題。你先寫好「標準答案」(Content + Rules)，再根據答案出一道題（公文）。然後讓 Encoder 去「解題」，看它解出來的答案跟你的標準答案差多少。

#### 具體範例

Step 1 — LLM 生成 Content（白話文，禁用「茲」「擬」「鈞」等公文用語）：

```json
{
  "topic": "校園資訊安全防護計畫",
  "intent": "希望校方配合執行資安措施",
  "key_events": ["112年9月發生資安事件", "已完成系統升級", "預計11月做教育訓練"],
  "entities": ["教育局", "大安高中", "張主任", "112年10月15日"],
  "action_items": ["定期檢查網路設備", "發送資安手冊"],
  "background": "配合行政院資安政策推動"
}
```

Step 2 — 隨機選 Rules 模板：

```json
{
  "doc_type": "函",
  "sender_org": "臺北市政府教育局",
  "receiver_org": "臺北市立大安高級中學",
  "tone": "下行",
  "required_sections": ["主旨", "說明", "辦法"],
  "formality_level": "高",
  "terminology_constraints": ["請查照", "希照辦"],
  "has_attachments": true,
  "speed_class": "普通件"
}
```

Step 3 — LLM 組合成正式公文（約 2000 字，含發文日期、字號、正本副本等完整格式）。

### 第二階段：Encode（雙軌提取）

Encoder 做的事：**拿到公文全文，拆出 Content JSON 和 Rules JSON**。

關鍵設計：Content 和 Rules 的提取是**兩個獨立的 LLM 呼叫**，平行執行（`asyncio.gather`），互不干擾。

```python
# 平行提取——兩個獨立 LLM 呼叫
content_task = llm.chat_json(system=ENCODE_CONTENT_SYSTEM, user=公文全文)
rules_task   = llm.chat_json(system=ENCODE_RULES_SYSTEM,   user=公文全文)
content_dict, rules_dict = await asyncio.gather(content_task, rules_task)
```

**為什麼要平行？**
1. **速度**：兩個提取互相不依賴，平行走省一半時間
2. **解耦保證**：Content 提取的 prompt 完全不知道 Rules 提取的存在，反之亦然。這從架構層面保證了「不會互相洩漏資訊」

#### Content Encoder 的核心約束

Content 提取的 prompt 有一條**硬規則**：

> **絕對禁止**使用任何公文用語：茲、擬、鈞、惠、爰、敬陳、諒達、奉、准、據（作為引敘語）、查照、核示、鑒核

**為什麼？** 如果 Content JSON 裡面出現了「茲因」「擬請鑒核」，那就表示 Content 裡混入了格式資訊（公文用語是格式的一部分）。禁用這些詞是為了**強制語義與格式分離**。

這就像化學實驗中的「純化」步驟——你把內容中的「格式雜質」全部洗掉，剩下的才是純語義。

#### Rules Encoder 的提取邏輯

Rules 提取是**結構化欄位填寫**，LLM 根據公文的格式線索判斷：

| 欄位 | 判斷線索 |
|------|---------|
| doc_type | 有受文者 → 函/書函；有「公告事項」→ 公告；有「擬辦」→ 簽 |
| tone | 稱謂語判斷：「鈞」→ 上行；「貴」→ 平行；「該」→ 下行 |
| required_sections | 列出實際存在的段落標題 |
| terminology_constraints | 列出文中使用的關鍵公文術語 |

### 第三階段：Decode（重建公文）

Decoder 做的事：**拿到 Content JSON + Rules JSON，重組一份正式公文**。

```
Content JSON（白話文）  ─┐
                         ├─▶ LLM ─▶ 重建公文（正式公文格式）
Rules JSON（格式參數）  ─┘
```

**Decoder prompt 的兩大約束**：

1. **禁止幻覺**：Content 中沒有的資訊，不能自己編造。寧可少寫，不可多寫。
2. **禁止遺漏**：Content 中有的資訊，必須全部寫入。寧可冗長，不可遺漏。

**工程直覺**：Decoder 就像一個「翻譯官」——把白話文（Content）翻譯成公文語言，同時遵守格式規範（Rules）。它不能自由發揮，只能用 Content 提供的素材。

### 第四階段：Evaluate（六維評估）

用 6 個指標打分，判斷重建品質。詳見下一節。

---

## 雙潛在空間設計原理

### 正交性假設

本系統的核心假設：**Content 和 Rules 是正交的（orthogonal）**。

「正交」在這裡的含義：

```
改變 Content，不影響 Rules → 同一格式可以承載不同事件
改變 Rules，不影響 Content → 同一事件可以用不同格式表達
```

這就像 x 軸和 y 軸——你沿 x 軸走不會改變 y 座標。

### 可測試的預測

正交性假設產生三個可測試的預測：

| 操作 | 預測 | 對應實驗 |
|------|------|---------|
| Content_A + Rules_B → Decode | 生成的公文內容為 A，格式為 B | Paper 1：交叉重建 |
| Content + 空 Rules → Decode | 語義完整，格式崩壞 | Paper 1：Content-only 消融 |
| 空 Content + Rules → Decode | 格式完整，語義空洞 | Paper 1：Rules-only 消融 |

如果三個預測都成立，就證明 Content 和 Rules 確實是正交的。

### Content JSON 的六個欄位

| 欄位 | 型別 | 含義 | 範例 |
|------|------|------|------|
| `topic` | string | 一句話主題 | "校園資訊安全防護計畫" |
| `intent` | string | 發文者想達成什麼 | "希望校方配合執行資安措施" |
| `key_events` | list[str] | 關鍵事件（至少 3 項） | ["112年9月發生資安事件", ...] |
| `entities` | list[str] | 涉及的人/機關/地/時（至少 3 個） | ["教育局", "大安高中", "張主任"] |
| `action_items` | list[str] | 待辦事項（至少 2 項） | ["定期檢查網路設備", ...] |
| `background` | string | 補充背景 | "配合行政院資安政策推動" |

**設計原則**：這六個欄位覆蓋了新聞寫作的 5W1H（Who、What、When、Where、Why、How），確保語義資訊的完整性。

### Rules JSON 的九個欄位

| 欄位 | 型別 | 含義 | 可選值 |
|------|------|------|--------|
| `doc_type` | enum | 文類 | 函 / 公告 / 書函 / 簽 / 令 |
| `sender_org` | string | 發文機關 | "臺北市政府教育局" |
| `receiver_org` | string | 受文機關 | "臺北市立大安高中"（公告/簽為空） |
| `tone` | enum | 語氣方向 | 上行 / 平行 / 下行 |
| `required_sections` | list[str] | 必要段落 | ["主旨", "說明", "辦法"] |
| `formality_level` | enum | 正式程度 | 高 / 中 |
| `terminology_constraints` | list[str] | 必須出現的公文術語 | ["請查照", "希照辦"] |
| `has_attachments` | bool | 是否有附件 | true / false |
| `speed_class` | enum | 速別 | 最速件 / 速件 / 普通件 |

**設計原則**：每個欄位都是可枚舉或結構化的。這讓 Rules 成為一個**完全參數化**的格式設定，可以像調 config 一樣調整格式。

---

## 六維評估系統原理

### 為什麼需要六個指標？

單一指標不夠——BLEU 只看詞彙重疊、BERTScore 只看語義相似度——都無法同時檢測「格式對不對」和「事實全不全」。

本系統的六個指標分三層，各有不同的「感知粒度」：

```
         ┌───────────────┐
Layer 3  │  LLM Judge    │  ← 最聰明但最慢，理解語義
         │  (主觀評審)    │
         ├───────────────┤
Layer 2  │  Embedding    │  ← 中等，捕捉語義相似度
         │  (Soft Metric) │
         ├───────────────┤
Layer 1  │  Regex / 比對  │  ← 最快但最笨，只看格式
         │  (Hard Metric) │
         └───────────────┘
```

### 六個指標逐一拆解

#### 指標 1：rule_adherence（規則遵循）— Hard — 權重 15%

**做什麼**：用 regex 檢查重建公文是否包含必要的格式元素。

**怎麼算**：9 項檢查，score = 通過數 / 總數

```
檢查項目：
 ✓ 「主旨」段落是否存在？
 ✓ 「說明」段落是否存在？
 ✓ 「辦法」段落是否存在？
 ✓ 日期是否為民國紀年？（regex: 中華民國\s*\d{2,3}\s*年\s*\d{1,2}\s*月...）
 ✓ 發文字號格式？（regex: 第\s*[\d\w]+(號|号)）
 ✓ 術語「請查照」是否出現？
 ✓ 術語「希照辦」是否出現？
 ✓ 發文機關名稱是否出現？
 ...

數值範例：通過 7 項 / 總共 9 項 = 0.7778
```

**工程直覺**：這是最「笨」的檢查——只看格式要素有沒有出現，不管語義。就像作業交上來先看有沒有寫名字和日期。

#### 指標 2：structural_match（結構匹配）— Hard — 權重 10%

**做什麼**：比較 Encoder 提取的 Rules JSON 和 ground truth Rules JSON，逐欄位對比。

**怎麼算**：比較 6 個欄位，score = 匹配數 / 6

```
欄位比較：
 doc_type:          gt=函,     pred=函     → ✓ match
 tone:              gt=下行,   pred=下行    → ✓ match
 required_sections: gt={主旨,說明,辦法}, pred={主旨,說明,辦法} → ✓ match（忽略順序）
 formality_level:   gt=高,     pred=高     → ✓ match
 has_attachments:   gt=true,   pred=true   → ✓ match
 speed_class:       gt=普通件, pred=普通件  → ✓ match

數值範例：6/6 = 1.0000
```

**工程直覺**：這測的是 Encoder 的「格式提取能力」。如果 Encoder 連文類都判斷錯，那後面的重建肯定格式不對。

#### 指標 3：semantic_similarity（語義相似度）— Soft — 權重 20%

**做什麼**：原始公文 vs 重建公文的語義相似度。

**怎麼算**：

```
1. 對 original_text 做 embedding → 向量 A（1536 維）
2. 對 reconstructed_text 做 embedding → 向量 B（1536 維）
3. cosine_similarity(A, B)

cosine_sim = (A · B) / (||A|| × ||B||)

數值範例：
  假設 A · B = 120.5, ||A|| = 11.2, ||B|| = 11.5
  cosine_sim = 120.5 / (11.2 × 11.5) = 120.5 / 128.8 = 0.9356
```

**工程直覺**：這看的是「整體感覺像不像」。即使措辭不同，只要語義接近，cosine similarity 就高。

**用的 Embedding 模型**：`text-embedding-3-small`（OpenAI，1536 維）

#### 指標 4：content_accuracy（內容準確度）— Soft — 權重 25%（最高）

**做什麼**：Encoder 提取的 Content JSON vs ground truth Content JSON 的語義相似度。

**怎麼算**：

```
1. 把 gt_content JSON 序列化為字串 → embedding → 向量 C_gt
2. 把 predicted_content JSON 序列化為字串 → embedding → 向量 C_pred
3. cosine_similarity(C_gt, C_pred)

數值範例：
  gt_content: {"topic":"資安防護","intent":"要求配合","key_events":["9月事件","系統升級"]}
  pred_content: {"topic":"資安防護計畫","intent":"配合資安措施","key_events":["9月資安事件","完成升級"]}

  cosine_sim(embed(gt), embed(pred)) = 0.8912
  → 大部分事實對了，細節措辭有差
```

**為什麼權重最高？** Content 提取的準確度是整個系統的核心能力——如果語義核提取不準，後面怎麼 Decode 都沒用。

#### 指標 5：content_preservation（內容保留度）— LLM Judge — 權重 15%

**做什麼**：讓另一個 LLM 當「評審」，比較原始公文和重建公文，判斷關鍵事實是否都保留了。

**怎麼算**：

```
LLM 評審打分（1-5 分），再除以 5 歸一化到 [0, 1]：

5 分 = 所有關鍵資訊完整保留     → 1.0
4 分 = 極微小細節差異            → 0.8
3 分 = 主要資訊保留，次要遺漏    → 0.6
2 分 = 部分關鍵資訊遺漏          → 0.4
1 分 = 大量資訊遺漏              → 0.2

數值範例：LLM 打 3 分 → 3/5 = 0.6000
```

**評審重點**：人名、機關、日期、數字、事件、待辦事項——這些「硬事實」有沒有一致。格式差異不扣分。

**為什麼用 LLM 當評審？** Regex 看不懂語義，Embedding 太粗糙（「遺漏一個日期」不會顯著改變 cosine similarity），只有 LLM 能理解「少了一個關鍵日期」是嚴重問題。

#### 指標 6：format_compliance（格式合規性）— LLM Judge — 權重 15%

**做什麼**：讓 LLM 評審檢查重建公文是否符合公文格式規範。

**評審檢查項目**：
- 有沒有發文機關、受文者、日期、字號？
- 段落結構對不對（主旨/說明/辦法）？
- 用語正不正式？稱謂語對不對？
- 期望語（查照/核示/鑒核）用得對不對？

```
數值範例：LLM 打 5 分 → 5/5 = 1.0000（完全合規）
```

### 加權總分計算

```
weighted_total = 0.15 × rule_adherence
               + 0.10 × structural_match
               + 0.20 × semantic_similarity
               + 0.25 × content_accuracy        ← 最重要
               + 0.15 × content_preservation
               + 0.15 × format_compliance

用 POC 結果跑一遍：
= 0.15 × 0.7778
+ 0.10 × 1.0000
+ 0.20 × 0.8865
+ 0.25 × 0.8477
+ 0.15 × 0.6000
+ 0.15 × 1.0000

= 0.1167 + 0.1000 + 0.1773 + 0.2119 + 0.0900 + 0.1500
= 0.8459
```

**0.8459 代表什麼？** 大約 84.6% 的資訊和格式被成功保留。主要扣分點在 content_preservation（0.60），意味 Encoder→Decoder 過程中有部分事實細節丟失。

---

## 三篇論文的實驗邏輯

### Paper 1：Content 和 Rules 真的是分開的嗎？（Symbolic Disentanglement）

**核心問題**：你說你把內容和格式拆開了，證據呢？

**驗證策略**：如果兩個空間真的是正交的，那：

#### 實驗 A — 交叉重建（Cross-Reconstruction）

```
公文 A → Encode → (Content_A, Rules_A)
公文 B → Encode → (Content_B, Rules_B)

交叉：Content_A + Rules_B → Decode → 新公文

預期：新公文的「內容」像 A，「格式」像 B
```

**數值範例**：

```
content_accuracy（比較新公文 vs A 的內容）= 0.8935 ← 接近 Baseline 的 0.9004
structural_match（比較新公文 vs B 的格式）= 0.8667 ← 接近 Baseline 的 0.8889

→ 結論：Content 和 Rules 可以獨立替換，交叉重建成功
```

#### 實驗 B — 消融實驗（Ablation Study）

把其中一個空間「關掉」，看另一個還能不能獨立工作：

```
Content-only（Rules 歸零為預設值）：
  content_accuracy = 0.9004  ← 不受影響！語義還在
  structural_match = 0.6111  ← 暴跌！格式崩壞

Rules-only（Content 歸零為空值）：
  content_accuracy = 0.4098  ← 暴跌！沒有語義了
  structural_match = 0.8889  ← 不受影響！格式還在
```

**工程直覺**：就像拔掉 x 軸只剩 y 軸——y 資訊完好，x 資訊消失。反之亦然。這就是「正交」的證據。

### Paper 2：有結構化中間表示到底有沒有用？（Closed-loop Evaluation）

**核心問題**：你多做了 Encode + Decode 兩步，值不值得？直接讓 LLM 一步生出公文不就好了？

#### 實驗 A — 循環一致性（Cycle Consistency）

測試 AutoEncoder 的「資訊損失」有多少：

```
原始公文 → Encode → (C₁, R₁) → Decode → 重建公文 → Re-Encode → (C₂, R₂)

比較：similarity(C₁, C₂) 和 similarity(R₁, R₂)
理想值：都是 1.0（完美循環，零損失）
```

**數值結果**：

```
content_similarity = 0.9772  ← 接近 1.0
rules_similarity   = 0.9579  ← 接近 1.0

→ 資訊損失極小（< 5%），AutoEncoder 是「近乎無損」的
```

**用日常比喻**：你讀了一篇文章，用 50 字摘要轉述給朋友，朋友重寫文章，你再讀一遍做 50 字摘要。如果兩次摘要幾乎一樣，表示你的「摘要能力」很穩定，沒有在循環中丟東西。

#### 實驗 B — AE vs Direct 基線對比

```
AE 路徑：  topic → 生成 Content → 生成 Rules → 組合公文 → Encode → Decode
Direct 路徑：topic + Rules → 直接讓 LLM 生成公文（一步到位）
```

**公平比較設計**：Direct 生成的公文也經過 Encoder 提取 Content，再跟 ground truth 比，確保兩條路徑用同一把尺評量。

**數值結果**：

```
                    AE        Direct      差距
content_preservation: 0.7333    0.3333    +120% ← AE 是 Direct 的 2.2 倍！
content_accuracy:     0.8934    0.7976    +12%
weighted_total:       0.8298    0.7971    +4%

統計檢定（Paired t-test, N=20）：
  weighted_total: p = 0.000001 ***
  content_preservation: p < 0.000001 ***
```

**為什麼 AE 更好？**

```
Direct 路徑：LLM 只看到「主題：校園資安」→ 自由發揮，編造細節
AE 路徑：LLM 看到完整的 Content JSON（具體日期、人名、事件）→ 被迫依循事實

→ 結構化中間表示 = 事實錨點（Fact Anchor），減少幻覺
```

**工程直覺**：Direct 像是叫實習生「寫一篇關於資安的公文」——他會編故事。AE 像是先給他一份事實清單，再讓他寫——他被限制在事實範圍內。

### Paper 3：Agent 能自己修正錯誤嗎？（Self-Refining Agent）

**核心問題**：如果初次重建的分數不夠高，能不能讓 LLM 自己分析問題、修正規則、重新生成？

#### 修正迴圈的流程

```
                    ┌────────────────────────┐
                    │                        │
Decode ──▶ Evaluate ──▶ score < 0.92?       │
                          │                  │
                   Yes ───┤                  │
                          ▼                  │
                    Critique（分析問題）       │
                          │                  │
                          ▼                  │
                    Refine Rules（調整規則）   │
                          │                  │
                          └──────────▶ 回到 Decode
                                             │
                    最多 3 輪 ───────────────┘
```

#### Score-Gated Refinement（分數門控）

**問題**：修正不一定會讓分數變好——有時候「改太多」反而退化。

**解法**：只有當新分數 > 舊最佳分數時，才接受修正結果。

```
iter 0: score = 0.8226  ✓ accepted（初始值）
iter 1: score = 0.8455  ✓ accepted（比 0.8226 高）
iter 2: score = 0.7857  ✗ rejected（比最佳 0.8455 低，丟棄）
iter 3: score = 0.8016  ✗ rejected（仍低於 0.8455，丟棄）

最終 best_score = 0.8455（保證不退化）
```

**工程直覺**：就像版本控制的 cherry-pick——只合入改善的 commit，退化的 commit 直接丟棄。

#### Critique 和 Refine 的機制

**Critique**（品質分析）：LLM 比較原始公文和重建公文，輸出結構化問題報告：

```json
{
  "content_issues": ["遺漏了「112年10月15日」這個日期", "張主任的名字沒有出現"],
  "format_issues": ["缺少「辦法」段落"],
  "rule_violations": ["terminology_constraints 要求「請查照」但文中沒有"],
  "root_causes": ["Rules 中的 required_sections 可能不完整"],
  "suggestions": ["在 required_sections 中加入「辦法」", "在 terminology_constraints 中加入「請查照」"]
}
```

**Refine Rules**（規則調整）：另一個 LLM 根據 Critique 報告，調整 Rules JSON 的具體欄位。調整原則是**保守修正**——每次只改有明確證據支持的欄位。

---

## 實驗結果解讀

### Paper 1：三項證據證明解耦成功

| 條件 | content_accuracy | structural_match | weighted_total |
|------|:---:|:---:|:---:|
| Baseline（正常重建） | 0.90 | 0.89 | **0.86** |
| Cross-Recon（交叉重建） | 0.89 | 0.87 | **0.77** |
| Content-only（只有內容） | 0.90 | **0.61** ↓ | **0.79** |
| Rules-only（只有格式） | **0.41** ↓ | 0.89 | **0.59** |

**讀法**：
- 箭頭 ↓ 表示暴跌，正好出現在「被關掉」的那個維度
- Content-only 時，格式崩壞（structural_match 0.61），但語義完好（content_accuracy 0.90）
- Rules-only 時，語義崩壞（content_accuracy 0.41），但格式完好（structural_match 0.89）

**結論**：Content 和 Rules 各自獨立攜帶不同維度的資訊，互不替代。✅ 解耦成功。

### Paper 2：AE 顯著優於 Direct

| 指標 | AE | Direct | 提升 |
|------|:---:|:---:|:---:|
| content_preservation | **0.73** | 0.33 | +120% |
| content_accuracy | **0.89** | 0.80 | +12% |
| weighted_total | **0.83** | 0.80 | +4% |

統計檢定 p < 0.001，結果高度顯著。

**核心論點**：多花兩步（Encode + Decode）的計算成本，換來了**大幅提升的事實忠實度**。在政府公文這種「不能有錯」的場景，這個 trade-off 是值得的。

### Paper 3：Score-Gating 消除退化

| 文件 | 初始分 | 最終最佳分 | 改善 | 是否退化 |
|------|:---:|:---:|:---:|:---:|
| 低分文件 | 0.823 | 0.846 | +2.3% | 否 |
| 高分文件 | 0.907 | 0.907 | ±0% | **成功避免退化** |

**結論**：Score-gated refinement 提供了**單調改善保證**——最終分數 ≥ 初始分數，永遠不會更差。

---

## 整體架構決策的工程直覺

### Q1：為什麼用 JSON 而不是自然語言做 latent space？

| 方案 | 優點 | 缺點 |
|------|------|------|
| 自然語言摘要 | 彈性高 | 無法精確比較、無法逐欄位控制 |
| **JSON** | **可精確比對、可逐欄位操控、可序列化** | 欄位設計需要領域知識 |
| 向量（VAE） | 數學上最優雅 | 不可解釋、不可編輯 |

JSON 是在「結構化程度」和「彈性」之間最好的平衡點。

### Q2：為什麼評估需要三層（Regex + Embedding + LLM Judge）？

```
層次      能力                    成本     適合場景
Regex     精確格式檢查            幾乎零   「有沒有日期？」
Embedding 語義相似度              低      「整體意思像不像？」
LLM Judge 深度語義理解            高      「少了一個關鍵日期算不算嚴重？」
```

三者互補：Regex 快但笨，LLM 聰明但慢且貴。混合使用兼顧效率與品質。

### Q3：為什麼逆向生成而不是用真實公文？

| 方案 | Ground Truth | 現實可行性 |
|------|:---:|:---:|
| 真實公文 + 人工標註 | 需大量人力標註 | 成本極高 |
| 真實公文 + 無標註 | 無 ground truth | 無法定量評估 |
| **逆向生成** | **自動獲得完美 ground truth** | **零人工成本** |

代價：合成公文可能不如真實公文自然。但對於驗證「解耦是否成功」這個研究問題，合成數據已經足夠。

### Q4：為什麼 content_accuracy 的權重最高（25%）？

因為這是 AutoEncoder 的核心能力指標。如果 Encoder 提取的語義核就不準確，後面無論怎麼 Decode 都不可能正確。就像考試——如果你審題就審錯了，答案寫得再好也沒用。

### Q5：整體系統的 LLM 呼叫數量

```
一份公文的完整流程：
  Generate:  2 calls（生成 Content + 組合公文）
  Encode:    2 calls（提取 Content + 提取 Rules，平行）
  Decode:    1 call （重建公文）
  Evaluate:  2 calls（LLM Judge × 2）+ 2 embed calls
  ─────────────────────────────────
  Total:     7 LLM calls + 2 embed calls per document

Paper 3 每輪修正多加：
  Critique:  1 call
  Refine:    1 call
  Re-Decode: 1 call
  Re-Eval:   2 calls + 2 embeds
  ─────────────────────────────────
  Extra:     5 calls + 2 embeds per iteration
```

N=20 份公文的 poc 模式大約需要 140 次 LLM 呼叫 + 40 次 embedding 呼叫。

### Q6：技術棧選擇

| 元件 | 選擇 | 原因 |
|------|------|------|
| LLM | GPT-4o-mini | 性價比最高，JSON mode 穩定 |
| Embedding | text-embedding-3-small | 1536 維，夠用且便宜 |
| 資料模型 | Pydantic | 自動 JSON 序列化/反序列化，型別驗證 |
| 非同步 | asyncio | Encoder 雙軌平行提取，embedding 批次平行 |
| API 封裝 | AsyncOpenAI + retry | 自動重試，指數退避 |

---

## 總結：一張圖看懂全部

```
┌─────────────────────── GongWen-AE 全系統 ───────────────────────┐
│                                                                  │
│  INPUT              LATENT SPACE              OUTPUT             │
│                                                                  │
│  ┌────────┐     ┌──────────────────┐     ┌──────────────┐       │
│  │ 公文全文 │─Enc─│ Content (語義核)  │─Dec─│ 重建公文      │       │
│  │ 2000 字 │     │ {"topic":...}    │     │ 2000 字      │       │
│  └────────┘     │ {"intent":...}   │     └──────┬───────┘       │
│       │         │ 禁止公文用語!     │            │               │
│       │         ├──────────────────┤            │               │
│  gt_content     │ Rules (格式殼)    │         ┌──▼──┐            │
│  gt_rules       │ {"doc_type":"函"} │         │Eval │            │
│  (逆向生成      │ {"tone":"下行"}   │         │ 6個  │            │
│   的正確答案)   │ 完全參數化        │         │指標  │            │
│                 └──────────────────┘         └──┬──┘            │
│                                                  │               │
│  Paper 1: 交叉 Content_A + Rules_B → 證明正交性   │               │
│  Paper 2: AE vs Direct → 證明結構化中間表示的價值   │               │
│  Paper 3: Critique → Refine → 自動修正迴圈        │               │
│                                                  ▼               │
│                                          eval_report.csv         │
└──────────────────────────────────────────────────────────────────┘
```

> **一句話結論**：GongWen-AE 證明了 LLM 可以充當「符號化自編碼器」——把公文拆成兩個人類可讀的 JSON 再還原，而且還原品質可量化、可控制、可自動修正。
