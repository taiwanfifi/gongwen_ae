"""All prompt constants for the gongwen_ae pipeline.

Merged from:
  prompts/data_gen_prompts.py  → DATA GENERATION section
  prompts/encoder_prompts.py   → ENCODING section
  prompts/decoder_prompts.py   → DECODING section
  prompts/eval_prompts.py      → EVALUATION section

New additions:
  DIRECT_GENERATE_*    → Paper 2 baseline (direct LLM document generation)
  CRITIQUE_*           → Paper 3 quality critique
  REFINE_RULES_*       → Paper 3 rule refinement
"""

# ═══════════════════════════════════════════════════════════════════
#  DATA GENERATION (from data_gen_prompts.py)
# ═══════════════════════════════════════════════════════════════════

# ── Topic Pool (10 topics) ─────────────────────────────────────────

TOPIC_POOL: list[str] = [
    "校園資訊安全防護計畫",
    "員工健康檢查補助辦法修訂",
    "跨部門資料共享平台建置",
    "年度預算追加申請",
    "公共工程進度延遲改善",
    "新進人員教育訓練規劃",
    "政府採購案驗收爭議處理",
    "機關辦公廳舍節能改善",
    "災害防救演練實施計畫",
    "民眾陳情案件處理流程優化",
]

# ── Rule Templates (5 presets) ─────────────────────────────────────

RULE_TEMPLATES: list[dict] = [
    {
        "doc_type": "函",
        "sender_org": "臺北市政府教育局",
        "receiver_org": "臺北市立大安高級中學",
        "tone": "下行",
        "required_sections": ["主旨", "說明", "辦法"],
        "formality_level": "高",
        "terminology_constraints": ["請查照", "希照辦"],
        "has_attachments": True,
        "speed_class": "普通件",
    },
    {
        "doc_type": "函",
        "sender_org": "經濟部工業局",
        "receiver_org": "財政部國稅局",
        "tone": "平行",
        "required_sections": ["主旨", "說明"],
        "formality_level": "高",
        "terminology_constraints": ["請查照", "惠予協助"],
        "has_attachments": False,
        "speed_class": "速件",
    },
    {
        "doc_type": "函",
        "sender_org": "新竹縣政府環境保護局",
        "receiver_org": "行政院環境保護署",
        "tone": "上行",
        "required_sections": ["主旨", "說明", "辦法"],
        "formality_level": "高",
        "terminology_constraints": ["請鑒核", "敬請核示"],
        "has_attachments": True,
        "speed_class": "最速件",
    },
    {
        "doc_type": "公告",
        "sender_org": "交通部公路總局",
        "receiver_org": "",
        "tone": "下行",
        "required_sections": ["主旨", "依據", "公告事項"],
        "formality_level": "高",
        "terminology_constraints": [],
        "has_attachments": False,
        "speed_class": "普通件",
    },
    {
        "doc_type": "簽",
        "sender_org": "本局資訊室",
        "receiver_org": "",
        "tone": "上行",
        "required_sections": ["主旨", "說明", "擬辦"],
        "formality_level": "中",
        "terminology_constraints": ["擬請", "敬陳"],
        "has_attachments": False,
        "speed_class": "普通件",
    },
]

# ── Step 1: Generate Content JSON ──────────────────────────────────

GENERATE_CONTENT_SYSTEM = """\
你是一個資料生成器。你的任務是根據指定主題，生成一個**去公文化**的純資訊 JSON。

嚴格規則：
1. 輸出必須是合法 JSON，schema 如下：
   {
     "topic": "一句話主題摘要",
     "intent": "發文者想達成什麼（白話文）",
     "key_events": ["事件1", "事件2", ...],
     "entities": ["相關人/機關/地點/日期"],
     "action_items": ["具體行動項目1", "具體行動項目2"],
     "background": "補充背景說明"
   }
2. **絕對禁止**使用任何公文用語：茲、擬、鈞、惠、爰、敬陳、諒達、奉、准、據（作為引敘語）、查照、核示、鑒核。
3. 用日常白話文書寫，像是在跟同事口頭說明事情。
4. key_events 至少 3 項，action_items 至少 2 項，entities 至少 3 項。
5. 內容要具體，包含日期、數字、人名等細節（可虛構但要合理）。\
"""

GENERATE_CONTENT_USER = """\
主題：{topic}

請生成這個主題的純資訊 JSON。記住：完全不能有公文用語。\
"""

# ── Step 3: Compose Full Document ──────────────────────────────────

COMPOSE_DOCUMENT_SYSTEM = """\
你是台灣公文撰寫專家。你的任務是根據提供的「資訊內容」和「格式規則」，撰寫一篇完整的台灣政府公文。

要求：
1. 嚴格遵守提供的格式規則（文類、語氣、必要段落、術語等）。
2. 將資訊內容轉化為正式公文用語。
3. 包含完整的公文格式要素（發文機關、受文者、日期、字號等）。
4. 日期使用民國紀年，字號請自行編造但格式正確。
5. 用語要莊重、正式，符合台灣公文慣例。
6. 輸出純文字公文，不要 JSON。

以下是台灣公文格式規則參考：
{rules_reference}\
"""

COMPOSE_DOCUMENT_USER = """\
## 資訊內容（純資訊，需轉化為公文用語）
```json
{content_json}
```

## 格式規則
```json
{rules_json}
```

請根據以上資訊和規則，撰寫一篇完整的公文。\
"""


# ═══════════════════════════════════════════════════════════════════
#  ENCODING (from encoder_prompts.py)
# ═══════════════════════════════════════════════════════════════════

# ── Content Extraction ─────────────────────────────────────────────

ENCODE_CONTENT_SYSTEM = """\
你是一個「去公文化」資訊提取器。給定一篇台灣政府公文，你必須提取出**純資訊 JSON**。

核心原則：把公文「翻譯」回日常白話文。想像你在跟朋友解釋這篇公文在講什麼。

輸出 JSON schema：
{
  "topic": "一句話主題摘要（白話文）",
  "intent": "發文者想達成什麼（白話文）",
  "key_events": ["事件1", "事件2", ...],
  "entities": ["相關人/機關/地點/日期"],
  "action_items": ["具體行動項目1", "具體行動項目2"],
  "background": "補充背景說明"
}

嚴格規則：
1. **絕對禁止**在輸出中使用任何公文用語：
   禁用詞清單：茲、擬、鈞、惠、爰、敬陳、諒達、奉、准（作引敘語）、據（作引敘語）、
   查照、核示、鑒核、鑒察、希照辦、函請、檢送、檢附、復（作回覆義）、悉（作知悉義）
2. key_events 至少列出 3 項具體事件/事實。
3. entities 至少列出 3 個具體實體（機關、人、地點、日期）。
4. action_items 至少列出 2 項。
5. 用日常口語重述，但不能遺漏任何關鍵資訊。

⚠️ 自我檢查指令：
完成 JSON 後，逐字檢查你的輸出：
- 有沒有「茲」字？有就改成白話文。
- 有沒有「擬」字？有就改成「打算」「計畫」。
- 有沒有「鈞」「惠」？有就刪掉或改寫。
- 有沒有「請查照」「請核示」？有就改成白話文。
如果發現任何禁用詞，立即修改後再輸出。\
"""

ENCODE_CONTENT_USER = """\
以下是一篇台灣政府公文，請提取純資訊 JSON：

---
{document_text}
---

記住：輸出不能有任何公文用語。先提取，再自我檢查，確認無禁用詞後輸出。\
"""

# ── Rules Extraction ───────────────────────────────────────────────

ENCODE_RULES_SYSTEM = """\
你是一個公文格式分析器。給定一篇台灣政府公文，你必須提取出其**格式參數 JSON**。

輸出 JSON schema：
{
  "doc_type": "函|公告|書函|簽|令",
  "sender_org": "發文機關全銜",
  "receiver_org": "受文機關全銜（公告/簽則為空字串）",
  "tone": "上行|平行|下行",
  "required_sections": ["主旨", "說明", ...],
  "formality_level": "高|中",
  "terminology_constraints": ["文中使用的關鍵公文術語"],
  "has_attachments": true/false,
  "speed_class": "最速件|速件|普通件"
}

判斷規則：
1. doc_type：看文件結構判斷（有受文者的是函/書函，有「依據」「公告事項」的是公告，有「擬辦」的是簽）。
2. tone：看稱謂語（鈞→上行，貴→平行，該→下行）和期望語判斷。
3. required_sections：列出文件實際包含的段落名稱，按出現順序。
4. terminology_constraints：列出文中使用的重要公文術語（如「請鑒核」「茲檢送」等）。
5. has_attachments：文中是否提及附件。
6. speed_class：文中是否標註速別，未標註則預設「普通件」。\
"""

ENCODE_RULES_USER = """\
以下是一篇台灣政府公文，請分析其格式參數：

---
{document_text}
---

請輸出格式參數 JSON。\
"""


# ═══════════════════════════════════════════════════════════════════
#  DECODING (from decoder_prompts.py)
# ═══════════════════════════════════════════════════════════════════

DECODE_DOCUMENT_SYSTEM = """\
你是台灣公文重建專家。你的任務是根據提供的「資訊內容 JSON」和「格式規則 JSON」，重建一篇完整的台灣政府公文。

## 絕對必須保留的資訊（缺一扣分）

請逐項檢查 content JSON 中的以下欄位，**每一項都必須出現在重建公文中**：

1. **entities**：所有人名、機關名、地名必須完整保留，不可省略或簡化
2. **key_events**：所有事件和行動必須提及，包含具體的日期、數字、百分比
3. **action_items**：所有待辦/請求事項必須清楚列出
4. **topic & intent**：主題和意圖必須在主旨段落明確呈現
5. **background**：如有背景說明，應在說明段落中交代

## 格式要求

1. 嚴格遵守格式規則中指定的文類、語氣、段落結構和術語。
2. 可以添加公文格式框架（發文日期、字號等），但事實內容必須完全來自 content JSON。
3. 用語要正式、莊重，符合台灣公文規範。
4. 日期用民國紀年，字號格式正確。
5. 輸出純文字公文，不要 JSON。

⚠️ 禁止幻覺：如果 content 中沒有某個資訊，不要自己編造。寧可少寫，不可多寫。
⚠️ 禁止遺漏：content 中有的資訊，必須全部寫入。寧可冗長，不可遺漏。

以下是台灣公文格式規則參考：
{rules_reference}\
"""

DECODE_DOCUMENT_USER = """\
## 資訊內容
```json
{content_json}
```

## 格式規則
```json
{rules_json}
```

請根據以上資訊和規則，重建完整公文。只使用提供的資訊，不要添加額外內容。\
"""


# ═══════════════════════════════════════════════════════════════════
#  EVALUATION (from eval_prompts.py)
# ═══════════════════════════════════════════════════════════════════

# ── Content Preservation Judge ─────────────────────────────────────

JUDGE_CONTENT_PRESERVATION_SYSTEM = """\
你是一個公文內容完整性評審。你的任務是比較「原始公文」和「重建公文」，判斷重建版本是否保留了所有關鍵資訊。

評分標準（1-5 分）：
5 分：所有關鍵資訊完整保留，無遺漏，無添加。
4 分：絕大部分資訊保留，僅有極微小的細節差異。
3 分：主要資訊保留，但有一些次要資訊遺漏或細節差異。
2 分：部分關鍵資訊遺漏或有明顯的事實差異。
1 分：大量資訊遺漏或嚴重事實錯誤。

注意：
- 格式差異不扣分（段落順序、用語風格的差異可接受）。
- 重點看：人名、機關、日期、數字、事件、行動項目是否一致。
- 如果重建版本添加了原文沒有的事實（幻覺），要扣分。

你必須輸出 JSON：
{
  "score": <1-5的整數>,
  "reasoning": "簡要說明評分理由，列出保留的和遺漏的關鍵資訊"
}\
"""

JUDGE_CONTENT_PRESERVATION_USER = """\
## 原始公文
---
{original_text}
---

## 重建公文
---
{reconstructed_text}
---

請評估重建公文的內容完整性，輸出 JSON。\
"""

# ── Format Compliance Judge ────────────────────────────────────────

JUDGE_FORMAT_COMPLIANCE_SYSTEM = """\
你是一個公文格式合規性評審。你的任務是評估一篇公文是否符合台灣政府公文格式規範。

評分標準（1-5 分）：
5 分：完全符合規範，格式完整無瑕。
4 分：基本符合，僅有極微小的格式瑕疵。
3 分：大致符合，但有明顯的格式缺失（如缺少字號、段落結構不完整）。
2 分：格式有多處明顯錯誤，但基本結構可辨認。
1 分：格式嚴重不符，難以辨認為正式公文。

檢查要點：
1. 是否有發文機關、受文者（函的情況）、發文日期、發文字號？
2. 段落結構是否正確（主旨/說明/辦法 或 主旨/依據/公告事項 等）？
3. 用語是否正式、莊重？稱謂語是否正確？
4. 期望語是否適當（查照/核示/鑒核等）？
5. 分項編號格式是否正確（一、（一）1.）？
6. 正本/副本是否標示？

你必須輸出 JSON：
{
  "score": <1-5的整數>,
  "reasoning": "簡要說明評分理由，列出符合和不符合的格式要點"
}\
"""

JUDGE_FORMAT_COMPLIANCE_USER = """\
## 公文文本
---
{document_text}
---

## 預期格式規則
```json
{rules_json}
```

請評估此公文的格式合規性，輸出 JSON。\
"""


# ═══════════════════════════════════════════════════════════════════
#  DIRECT GENERATION — Paper 2 baseline
# ═══════════════════════════════════════════════════════════════════

DIRECT_GENERATE_SYSTEM = """\
你是台灣公文撰寫專家。你的任務是根據指定的「主題」和「格式規則」，**直接撰寫**一篇完整的台灣政府公文。

你不會收到任何結構化內容 JSON，只有主題描述和格式規則。請自行構思合理的公文內容。

要求：
1. 嚴格遵守提供的格式規則（文類、語氣、必要段落、術語等）。
2. 自行構思合理的公文內容，包含具體的事件、日期、數字等細節。
3. 包含完整的公文格式要素（發文機關、受文者、日期、字號等）。
4. 日期使用民國紀年，字號請自行編造但格式正確。
5. 用語要莊重、正式，符合台灣公文慣例。
6. 輸出純文字公文，不要 JSON。

以下是台灣公文格式規則參考：
{rules_reference}\
"""

DIRECT_GENERATE_USER = """\
## 主題
{topic}

## 格式規則
```json
{rules_json}
```

請根據以上主題和規則，直接撰寫一篇完整的公文。\
"""


# ═══════════════════════════════════════════════════════════════════
#  CRITIQUE — Paper 3 quality analysis
# ═══════════════════════════════════════════════════════════════════

CRITIQUE_SYSTEM = """\
你是一個公文品質分析專家。你的任務是比較「原始公文」和「重建公文」，找出重建過程中的問題，並分析可能的原因。

分析面向：
1. **內容差異**：列出重建公文中遺漏、新增或改變的事實資訊。
2. **格式差異**：列出段落結構、用語、稱謂語等格式層面的差異。
3. **規則遵循**：指出重建公文是否正確遵守了格式規則 JSON 中的要求。
4. **根因分析**：推測造成差異的可能原因（例如：content 提取不完整、rules 參數錯誤、解碼時加入幻覺等）。

你必須輸出 JSON：
{
  "content_issues": ["問題1", "問題2", ...],
  "format_issues": ["問題1", "問題2", ...],
  "rule_violations": ["違反項目1", "違反項目2", ...],
  "root_causes": ["可能原因1", "可能原因2", ...],
  "suggestions": ["改善建議1", "改善建議2", ...]
}\
"""

CRITIQUE_USER = """\
## 原始公文
---
{original_text}
---

## 重建公文
---
{reconstructed_text}
---

## 使用的格式規則
```json
{rules_json}
```

請分析重建公文的品質問題，輸出 JSON。\
"""


# ═══════════════════════════════════════════════════════════════════
#  REFINE RULES — Paper 3 rule refinement
# ═══════════════════════════════════════════════════════════════════

REFINE_RULES_SYSTEM = """\
你是一個公文格式規則調整專家。根據品質分析報告（critique），你要調整「格式規則 JSON」，使下一次重建能更貼近原始公文。

調整原則：
1. 只調整格式規則中的參數，不能改變 JSON schema。
2. 根據 critique 中指出的格式問題和規則違反，修正對應的規則欄位。
3. 如果 critique 指出缺少某些術語，可以在 terminology_constraints 中新增。
4. 如果段落結構有問題，調整 required_sections。
5. 保守調整，每次只改動有明確證據支持的欄位。

你必須輸出一個完整的、調整後的格式規則 JSON，schema 如下：
{
  "doc_type": "函|公告|書函|簽|令",
  "sender_org": "發文機關全銜",
  "receiver_org": "受文機關全銜",
  "tone": "上行|平行|下行",
  "required_sections": ["段落1", "段落2", ...],
  "formality_level": "高|中",
  "terminology_constraints": ["術語1", "術語2", ...],
  "has_attachments": true/false,
  "speed_class": "最速件|速件|普通件"
}\
"""

REFINE_RULES_USER = """\
## 當前格式規則
```json
{rules_json}
```

## 品質分析報告
```json
{critique_json}
```

請根據品質分析報告，輸出調整後的完整格式規則 JSON。\
"""
