# GongWen-AE: 台灣公文符號化自編碼器

**Symbolic AutoEncoder for Taiwan Government Documents**

> 以 LLM 實現公文的**語義-格式解耦（Content-Rules Disentanglement）**，支援交叉重建、循環一致性驗證、自我修正等研究實驗。

---

## 目錄

- [研究動機](#研究動機)
- [理論框架](#理論框架)
- [系統架構](#系統架構)
- [三篇論文實驗設計](#三篇論文實驗設計)
- [實驗結果分析](#實驗結果分析)
- [安裝與使用](#安裝與使用)
- [專案結構](#專案結構)
- [引用](#引用)

---

## 研究動機

### 問題背景

台灣政府公文是一種高度結構化的文體，同時包含兩個正交維度：

1. **語義內容（Semantic Content）**：公文要傳達的實際資訊——誰、做了什麼、何時、為什麼
2. **格式規則（Formatting Rules）**：公文的文類、語氣、段落結構、術語用詞

傳統的文本生成方法（如直接 prompting LLM）將這兩者混為一談，導致：

- **內容幻覺**：LLM 會自由發揮，加入原始意圖沒有的資訊
- **格式不一致**：同一主題在不同生成中可能產生截然不同的格式
- **難以控制**：無法獨立調整內容或格式

### 核心洞察

我們觀察到公文的**內容與格式是可分離的**——同一份「核准補助」的語義內容，可以用「函」（平行公文）、「簽」（內部簽呈）、「公告」（對外公告）等不同格式表達。這啟發我們設計一個**符號化自編碼器（Symbolic AutoEncoder）**：

- **Encoder**：將公文全文分解為「純語義 Content JSON」+「格式參數 Rules JSON」
- **Decoder**：從 Content + Rules 重建完整公文

這種架構的關鍵優勢：

1. **可解釋的潛在空間**：不同於 VAE 的連續向量，我們的潛在表示是人類可讀的 JSON
2. **可控生成**：可以固定 Content 調換 Rules（或反之）來生成風格遷移後的公文
3. **可評估**：潛在表示有明確的 ground truth（來自逆向生成流程），支援定量評估

### 研究問題

本研究圍繞三個核心問題展開：

| 論文 | 研究問題 |
|------|---------|
| **Paper 1** | LLM 能否真正將公文的 Content 與 Rules 解耦？是否存在 information leakage？ |
| **Paper 2** | AE 架構相比直接生成（Direct Generation）有何優勢？潛在表示的循環一致性如何？ |
| **Paper 3** | Agent 能否透過「評分→批評→修正」的迴圈自動提升重建品質？修正邊界在哪裡？ |

---

## 理論框架

### 符號化自編碼器（Symbolic AutoEncoder）

傳統自編碼器將輸入壓縮為**連續向量**，本系統則壓縮為**結構化 JSON**：

```
                    ┌─────────────────┐
                    │   Latent Space  │
                    │  (Symbolic JSON) │
                    │                 │
   ┌─────────┐      │  ┌───────────┐  │      ┌─────────┐
   │ 公文全文 │─────▶│  │  Content  │  │─────▶│ 重建公文 │
   │ full_text│ Enc  │  │ (語義核)  │  │ Dec  │reconstructed│
   └─────────┘      │  └───────────┘  │      └─────────┘
                    │  ┌───────────┐  │
                    │  │   Rules   │  │
                    │  │ (格式殼)  │  │
                    │  └───────────┘  │
                    └─────────────────┘
```

### 雙潛在空間設計

**Content（語義核）**——去公文化的純資訊：

```json
{
  "topic": "校園資訊安全防護計畫",
  "intent": "希望校方配合執行資安措施",
  "key_events": ["112年9月發生資安事件", "已完成系統升級"],
  "entities": ["教育局", "大安高中", "張主任", "112年10月15日"],
  "action_items": ["定期檢查網路設備", "發送資安手冊"],
  "background": "配合行政院資安政策推動"
}
```

- **關鍵約束**：**禁止任何公文用語**（茲、擬、鈞、惠、請查照、請核示等）
- **設計理念**：將公文「翻譯」回日常白話文，像在跟同事口頭說明事情

**Rules（格式殼）**——完全參數化的格式設定：

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

### 為什麼這種分離有意義？

**正交性假設**：Content 和 Rules 描述的是公文的兩個獨立維度：

- 固定 Content，改變 Rules → 同一事件用不同格式表達（風格遷移）
- 固定 Rules，改變 Content → 同一格式承載不同事件（模板填充）

**可測試的預測**：

1. 交叉重建（Content_A + Rules_B）應該生成「A 的內容 + B 的格式」的公文
2. 消融 Content（Rules-only）應該導致語義崩壞但格式完整
3. 消融 Rules（Content-only）應該導致格式崩壞但語義完整

---

## 系統架構

### Pipeline 總覽

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Generate │ ──▶ │  Encode  │ ──▶ │  Decode  │ ──▶ │ Evaluate │
│ 合成公文  │     │ 提取潛在表示│     │ 重建公文  │     │ 6 指標評分 │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
      │                │                │                │
   full_text      (Content,        reconstructed     eval_report
   + gt_labels     Rules)            _text            .csv
```

### 逆向資料生成（Reverse Data Generation）

傳統做法是「先有公文，再提取 Content/Rules」，但這無法獲得 ground truth。

我們採用**逆向生成**：

1. **先生成 Content JSON**：給定主題，LLM 生成去公文化的純資訊
2. **選擇 Rules 模板**：從預定義的 5 種格式模板中選擇
3. **組合成公文**：LLM 根據 Content + Rules 撰寫正式公文

這樣每份公文都有**完美的 ground truth**（gt_content, gt_rules），支援精確評估。

### 六維評估指標

| 指標 | 類型 | 權重 | 說明 |
|------|------|------|------|
| `rule_adherence` | Hard | 15% | 9 項 regex 格式檢查的通過率 |
| `structural_match` | Hard | 10% | gt_rules vs predicted_rules 的欄位匹配率 |
| `semantic_similarity` | Soft | 20% | 原始 vs 重建公文的 embedding cosine similarity |
| `content_accuracy` | Soft | 25% | gt_content vs predicted_content 的 embedding similarity |
| `content_preservation` | LLM Judge | 15% | LLM 評審內容完整性（1-5 分） |
| `format_compliance` | LLM Judge | 15% | LLM 評審格式合規性（1-5 分） |

**設計原則**：Hard metric（確定性）+ Soft metric（embedding）+ LLM judge（主觀評審）三層混合，兼顧精確性與語義理解。

---

## 三篇論文實驗設計

### Paper 1: Symbolic Disentanglement（符號化解耦）

**研究問題**：LLM 能否將公文的 Content 與 Rules 完全分離？

#### 實驗 A — 交叉重建（Cross-Reconstruction）

```
Document A: Content_A + Rules_A  ─┐
                                  │
Document B: Content_B + Rules_B  ─┼─▶  Cross: Content_A + Rules_B
                                  │
預期：生成公文內容為 A、格式為 B     ◀─┘
```

- 取 N 篇公文，各自 Encode 得到 (Content_i, Rules_i)
- 交叉配對：Content_A + Rules_B → Decode
- **預期**：content_accuracy 維持高分（來自 A），structural_match 匹配 B

#### 實驗 B — 消融實驗（Ablation Study）

| 條件 | Content | Rules | 預期 |
|------|---------|-------|------|
| Content-only | ✓ | 歸零為預設值 | 語義完整，格式崩壞 |
| Rules-only | 歸零為空值 | ✓ | 格式完整，語義為空洞套話 |

### Paper 2: Closed-loop Evaluation（閉環評估）

**研究問題**：AE 架構相比直接生成有何優勢？

#### 實驗 A — 循環一致性（Cycle Consistency）

```
原始公文 ─▶ Encode ─▶ (Content₁, Rules₁)
                           │
                           ▼
                       Decode
                           │
                           ▼
                    重建公文 ─▶ Re-Encode ─▶ (Content₂, Rules₂)

比較：similarity(Content₁, Content₂), similarity(Rules₁, Rules₂)
理想：≈ 1.0（資訊無損循環）
```

#### 實驗 B — AE vs Direct 基線對比

| 路徑 | 流程 | 特點 |
|------|------|------|
| **AE path** | topic → Generate Content → Generate Rules → Compose → Encode → Decode | 有結構化 bottleneck |
| **Direct path** | topic + rules → 直接生成公文（無 AE） | LLM 自由發揮 |

**預期**：AE path 在 content_preservation 上優於 Direct（因為有明確的 ground truth 約束）

### Paper 3: Self-Refining Agent（自我修正代理）

**研究問題**：Agent 能否透過迴圈自動提升重建品質？

```
┌──────────────────────────────────────────┐
│                                          │
│  Decode ──▶ Evaluate ──▶ score < 0.92?   │
│                              │           │
│                    ┌────Yes──┘           │
│                    ▼                     │
│              Critique（分析問題）          │
│                    │                     │
│                    ▼                     │
│           Refine Rules（調整規則）         │
│                    │                     │
│                    └───────────▶ 回到 Decode
│                                          │
└──────────────────────────────────────────┘
```

**Score-Gated Refinement**：只有當新分數 > 舊分數時才接受修正，避免高分文件退化。

---

## 實驗結果分析

### Paper 1 結果：解耦的三項證據

#### 核心指標對照表

| 條件 | content_accuracy | structural_match | content_pres | weighted_total |
|------|-----------------|-----------------|-------------|----------------|
| **Baseline**（正常重建） | 0.9004 | 0.8889 | 0.6000 | **0.8566** |
| **Cross-Recon** | 0.8935 | 0.8667 | 0.3200 | **0.7724** |
| **Content-only** | 0.9004 | 0.6111 | 0.6000 | **0.7876** |
| **Rules-only** | 0.4098 | 0.8889 | 0.2000 | **0.5934** |

#### 關鍵發現

1. **Content 攜帶語義，Rules 攜帶格式**：
   - content_accuracy 在 Baseline/Cross/Content-only 保持 0.90，但 **Rules-only 暴跌至 0.41**
   - structural_match 在 Baseline/Cross/Rules-only 保持 0.87-0.89，但 **Content-only 跌至 0.61**
   - **結論**：兩空間各自獨立攜帶不同維度的資訊

2. **交叉重建成功**：Cross-Recon 的 content_accuracy（0.8935）與 Baseline（0.9004）幾乎相同，證明用 B 的格式替換 A 的規則後，A 的語義核未受影響

3. **消融確認雙空間缺一不可**：
   - Rules-only weighted_total 僅 0.5934（比 baseline 低 26%）
   - Content-only weighted_total 為 0.7876（比 baseline 低 8%）
   - **Content 的貢獻 > Rules**（符合預期：語義是核心）

### Paper 2 結果：結構化中間表示的價值

#### 循環一致性

| 指標 | 平均值 | 解讀 |
|------|--------|------|
| content_similarity | **0.9772** | Encode-Decode 後語義高度保留 |
| rules_similarity | **0.9579** | 格式參數在循環中穩定 |

#### AE vs Direct 對比

| 指標 | AE | Direct | Δ |
|------|-----|--------|---|
| content_preservation | **0.7333** | 0.3333 | **+120%** |
| content_accuracy | **0.8934** | 0.7976 | +12% |
| weighted_total | **0.8298** | 0.7971 | +4% |

**核心發現**：AE 的結構化 bottleneck 迫使 Encoder 提取明確的 key_events、entities，讓 Decoder 有具體事實可依循；Direct 模式僅靠 topic 就自由發揮，容易產生幻覺。

### Paper 3 結果：自我修正的機制與邊界

#### 修正軌跡

**低分文件**（起點 0.796）：
```
iter 0: 0.7963 ─▶ iter 1: 0.8007 (+0.4%) ─▶ iter 2: 0.8342 (+3.4%) ─▶ iter 3: 0.8576 (+2.3%)
總提升：+7.7%（持續改善）
```

**高分文件**（起點 0.864）：
```
iter 0: 0.8640 ─▶ iter 1: 0.8032 (-6.1%) ─▶ iter 2: 0.8034 (+0.0%) ─▶ iter 3: 0.8507 (+4.7%)
V 型曲線：過度修正導致退化，後續回復
```

#### 關鍵發現

1. **低分文件**：修正迴圈有效，3 輪可提升 5-8%
2. **高分文件**：存在過度修正風險，需要 **score-gated refinement**
3. **Critique 品質**：能精確指出問題（日期錯誤、字號不一致），但有時會建議結構性大改導致退化

---

## 安裝與使用

### 環境需求

- Python 3.10+
- OpenAI API Key（使用 GPT-4o-mini）

### 安裝

```bash
git clone git@github.com:taiwanfifi/gongwen_ae.git
cd gongwen_ae
pip install -r requirements.txt
```

### 設定 API Key

```bash
export OPENAI_API_KEY="your-api-key"
```

### 執行實驗

```bash
# POC 快速測試（5 篇文件）
python main.py --mode poc --count 5

# Paper 1：解耦實驗（交叉重建 + 消融）
python main.py --mode paper1 --count 20

# Paper 2：閉環評估（循環一致性 + AE vs Direct）
python main.py --mode paper2 --count 20

# Paper 3：自我修正迴圈
python main.py --mode paper3 --count 10
```

### 輸出目錄

```
data/results/
├── poc/                          # POC 結果
│   └── eval_report.csv
├── paper1/                       # Paper 1 結果
│   ├── eval_report.csv           # Baseline
│   ├── cross/eval_report.csv     # 交叉重建
│   ├── ablation_content_only/    # Content-only 消融
│   └── ablation_rules_only/      # Rules-only 消融
├── paper2/                       # Paper 2 結果
│   ├── ae/eval_report.csv        # AE 路徑
│   ├── direct/eval_report.csv    # Direct 路徑
│   └── cycle_consistency.json    # 循環一致性
└── paper3/                       # Paper 3 結果
    └── refinement_log.json       # 修正迴圈日誌
```

---

## 專案結構

```
gongwen_ae/
├── main.py              # 主程式入口，定義所有實驗模式
├── pipeline.py          # DataGenerator, Encoder, Decoder, Evaluator 類別
├── models.py            # Pydantic 資料模型（GongWenContent, GongWenRules 等）
├── prompts.py           # 所有 LLM prompt 常量
├── client.py            # OpenAI API 封裝
├── config.py            # 設定參數（模型、權重、閾值）
├── requirements.txt     # Python 依賴
├── research.md          # 詳細實驗筆記
├── data/
│   ├── generated/       # 合成公文（JSON）
│   ├── encoded/         # Encoder 輸出
│   ├── decoded/         # Decoder 輸出
│   ├── results/         # 評估報告
│   └── rules/           # 公文格式規則參考
└── README.md
```

### 核心類別

| 類別 | 檔案 | 功能 |
|------|------|------|
| `DataGenerator` | pipeline.py | 逆向生成公文 + ground truth |
| `Encoder` | pipeline.py | 公文 → (Content, Rules) |
| `Decoder` | pipeline.py | (Content, Rules) → 公文 |
| `Evaluator` | pipeline.py | 6 維評估指標計算 |
| `DirectGenerator` | pipeline.py | 直接生成公文（Paper 2 baseline）|
| `LLMClient` | client.py | OpenAI API 封裝 + embedding |

---

## 設定參數

編輯 `config.py`：

```python
# 模型設定
LLM_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

# 實驗參數
POC_COUNT = 20              # 預設樣本數
CROSS_RECON_PAIRS = 10      # Paper 1 交叉重建對數
CYCLE_CONSISTENCY_N = 10    # Paper 2 循環一致性樣本數
REFINEMENT_MAX_ITER = 3     # Paper 3 最大迭代次數
REFINEMENT_THRESHOLD = 0.92 # Paper 3 品質閾值

# 評估權重
EVAL_WEIGHTS = {
    "rule_adherence": 0.15,
    "structural_match": 0.10,
    "semantic_similarity": 0.20,
    "content_accuracy": 0.25,
    "content_preservation": 0.15,
    "format_compliance": 0.15,
}
```

---

## 引用

如果您使用本專案，請引用：

```bibtex
@software{gongwen_ae,
  title = {GongWen-AE: Symbolic AutoEncoder for Taiwan Government Documents},
  author = {Taiwan FiFi},
  year = {2024},
  url = {https://github.com/taiwanfifi/gongwen_ae}
}
```

---

## License

MIT License
