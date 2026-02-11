# GongWen-AE 重新定位分析：它到底是什麼、該叫什麼、怎麼救

> **用途**：基於 70+ 篇文獻的調研，回答三個核心問題：
> 1. 這套系統到底該叫什麼？（不是 AutoEncoder）
> 2. 兩個分量夠不夠？像 PCA 一樣，有沒有「最佳分量數」？
> 3. prompt 定義的分解能不能寫成數學公式？
>
> **寫法**：白話、先講道理再給名詞。

---

## 一、它到底是什麼？三秒鐘版

**你做的事情**：用 LLM prompt 把一份公文拆成兩個人類可讀的 JSON（語義 + 格式），再從這兩個 JSON 還原公文。

**這件事在學術界已經有名字了**。不叫 AutoEncoder，叫：

### **Concept Bottleneck**（概念瓶頸）

---

## 二、為什麼叫 Concept Bottleneck？

### 2.1 什麼是 Concept Bottleneck Model（CBM）？

Koh et al. (2020, ICML) 提出：在模型的預測過程中，**強迫所有信息都經過一層人類可理解的「概念層」**，然後再做最終預測。

```
傳統模型：  輸入 ──[黑箱]──▶ 輸出

CBM：       輸入 ──▶ [概念層：鳥嘴形狀=彎, 翅膀顏色=黑] ──▶ 輸出
                         ↑
                    人類可讀、可編輯
```

### 2.2 你的系統跟 CBM 的對應關係

| CBM 的概念 | 你的系統 |
|-----------|---------|
| 輸入 | 原始公文 |
| 概念層 | Content JSON + Rules JSON |
| 概念 | JSON 的每個欄位（topic, intent, doc_type, tone...） |
| 最終輸出 | 重建的公文 |
| 人類介入 | 修改 JSON 欄位 → 重新生成 |
| 概念瓶頸 | 所有信息必須通過兩個 JSON，沒有旁路 |

**白話翻譯**：你做的就是一個「概念瓶頸生成模型」——所有公文資訊都被迫通過一組人類可讀的概念（JSON 欄位），再從這些概念重建公文。

### 2.3 為什麼 CBM 比 AutoEncoder 準確？

| 比較項 | AutoEncoder | Concept Bottleneck |
|--------|-------------|-------------------|
| 需要訓練嗎？ | 需要梯度下降 | 不一定，可以用 prompt |
| 潛在表示 | 連續向量（不可讀） | 人類可讀的概念 |
| 需要損失函數嗎？ | 必須有 reconstruction loss | 不必須（但可以定義） |
| 你的系統是哪個？ | ✗ | **✓** |

**關鍵文獻**：
- Koh et al. (2020) "Concept Bottleneck Models" — ICML，原始論文
- Yamaguchi et al. (2024) "Concept Bottleneck Large Language Models" — ICLR 2025，**第一個把 CBM 整合進 LLM 的框架**，同時支援分類和生成
- Liu et al. (2024) "Concept Bottleneck Generative Models" — ICLR 2024，**把 CBM 擴展到生成式模型**（GAN/VAE/Diffusion），用正交性損失確保概念獨立
- Yamaguchi & Nishida (2025) "Explanation Bottleneck Models" — AAAI 2025，用**自由格式自然語言**作為瓶頸（不是固定概念槽位）

### 2.4 建議的新名稱

按學術適切度排序：

| 排名 | 名稱 | 優點 | 缺點 |
|------|------|------|------|
| 1 | **Symbolic Concept Bottleneck for Document Generation** | 精確對接 CBM 文獻；「Symbolic」強調 JSON 可讀性 | 名字稍長 |
| 2 | **Schema-Guided Document Decomposition** | 直白描述做的事；連接 Schema-Guided NLG 文獻 | 少了「瓶頸」這個理論核心 |
| 3 | **Prompt-Defined Factor Decomposition** | 強調 prompt 是分解的定義者；連接因子分析文獻 | 比較抽象 |
| 4 | **Interpretable Content-Format Bottleneck** | 簡短明確 | 沒有 established 文獻可連結 |

**我的建議：用第 1 個。** 原因：
1. CBM 是一個有 ICML/ICLR/NeurIPS 多篇頂會論文的成熟框架
2. 2024-2025 年 CBM 正在從 vision 擴展到 NLP（CB-LLMs, TBM, SCBM），你剛好搭上這班車
3. 「Symbolic」明確區分你跟傳統 CBM 的不同（你的概念是 JSON 而非 embedding）
4. 「for Document Generation」明確了應用領域

---

## 三、PCA 的直覺是對的——但更像 CFA

### 3.1 你的直覺整理

你提到 PCA 的正交分量概念，然後問：
1. 兩個分量（Content, Rules）夠不夠？
2. 有沒有「最佳分量數」？

這個直覺非常好。讓我幫你精確化。

### 3.2 PCA vs CFA：你做的是 CFA

| | PCA / EFA（探索性因子分析） | **CFA（驗證性因子分析）** |
|---|---|---|
| 邏輯 | 從資料中**發現**因子結構 | 先**假設**因子結構，再用資料驗證 |
| 因子數量 | 由資料決定（scree plot、eigenvalue > 1） | 由理論決定 |
| 因子含義 | 事後解讀 | **事前定義** |
| 你的系統 | ✗ | **✓**（你事前定義了 Content 和 Rules 兩個因子） |

**白話翻譯**：PCA 是「我不知道資料有幾個維度，讓演算法幫我找」。CFA 是「我假設有兩個維度（語義和格式），讓實驗幫我驗證」。**你做的是 CFA。**

### 3.3 為什麼 CFA 在這裡是對的？

Locatello et al. (2019, ICML **Best Paper**) 證明了一個關鍵的不可能定理：

> **在沒有歸納偏置（inductive bias）的情況下，無監督學習解耦表示是根本不可能的。**

翻成白話：如果你不告訴模型「應該拆成什麼」，它找出來的分量是隨機的——沒有理由認為 PCA 找到的第一個分量就是「語義」，第二個就是「格式」。

**你的 prompt 就是歸納偏置。** 你用 prompt 明確告訴 LLM「按語義提取」和「按格式提取」，這就是 CFA 的先驗假設。Locatello 的定理說，這種先驗是**必要的**——沒有它，解耦不可能。

**這反而是你的論文的一個優勢**，如果你正確定位的話：你不是在「學習」解耦（那需要克服 Locatello 的不可能定理），你是在**驗證一個先驗假設的解耦結構**。

### 3.4 兩個分量夠不夠？

這是一個可以實驗回答的問題。幾個思路：

#### 方案 A：增加分量，測量重建品質

```
2 分量（現在）：Content + Rules
3 分量：      Content + Structure + Style
4 分量：      Content + Structure + Style + Metadata
5 分量：      Content + Structure + Style + Metadata + Pragmatics

                      ┌─ Content（語義：事件、人物、行動）
                      ├─ Structure（結構：段落、順序、章節）
Document ──Encode──▶  ├─ Style（風格：語氣、正式度、用語）
                      ├─ Metadata（後設：日期、字號、速別）
                      └─ Pragmatics（語用：發收文關係、上下行）
```

如果 3 分量的重建品質顯著優於 2 分量，表示你目前的拆法太粗——Rules 裡面其實包含了可以進一步拆開的獨立維度。

#### 方案 B：用資訊論判斷最佳 k

借鏡 Preacher et al. (2013) 的因子分析框架，用 AIC/BIC 決定最佳分量數：

```
對每個 k = 1, 2, 3, 4, 5：
  1. 設計 k 個 prompt，分別提取 k 個 JSON
  2. 從 k 個 JSON 重建公文
  3. 計算重建品質 Q(k)
  4. 計算 BIC(k) = -2 × log(Q(k)) + k × log(N)
                    ↑ 重建品質        ↑ 複雜度懲罰

選擇 BIC 最小的 k
```

#### 方案 C：測量分量之間的互資訊

如果 Content 和 Rules 之間的互資訊 I(C; R) 很高，說明它們不夠正交——裡面有重疊的資訊，應該進一步拆分。

```
理想情況：I(Content; Rules) ≈ 0      → 兩個分量夠了
實際情況：I(Content; Rules) >> 0      → 可能需要更多分量
```

Cheng et al. (2020, ACL) 提供了計算文本表示之間互資訊上界的方法。

### 3.5 這裡面有一篇獨立的論文

**「公文有幾個正交維度？」** 這本身就是一個有價值的研究問題。你可以：
1. 從 k=1 到 k=6 做完整實驗
2. 用 BIC 和互資訊找出最佳 k
3. 用交叉重建驗證每個維度的獨立性
4. 比較「先驗指定 k」（CFA）和「從資料學 k」（EFA/PCA 類比）的差異

這比現在的 Paper 1-3 都更新穎、更有理論深度。

---

## 四、Prompt 能寫成數學公式嗎？

**可以。** 而且有多個框架可以用。

### 4.1 框架一：Prompt 是「函數選擇器」

Petrov et al. (2024, ICML) 證明了：

> **用 prompt prefix 控制的預訓練 Transformer 是通用函數近似器（universal function approximator）。**

翻成白話：LLM 本身是一個巨大的函數空間。每個 prompt 從這個空間中「選出」一個特定的函數。

數學寫法：

```
設 f_θ 為固定參數的 LLM
設 p 為 prompt（一段文字）

則 f_θ(p, ·) 定義了一個函數 g_p: D → Z
其中 D 是文件空間，Z 是輸出空間

你的系統定義了三個函數：
  g_content(d) = f_θ(p_content, d)     → Content JSON
  g_rules(d)   = f_θ(p_rules, d)       → Rules JSON
  g_decode(c,r) = f_θ(p_decode, c, r)  → 重建公文

重建品質：Q(d) = sim(d, g_decode(g_content(d), g_rules(d)))
```

### 4.2 框架二：Prompt 是「投影算子」

Park et al. (2024, ICML) 的 Linear Representation Hypothesis：

> LLM 表示空間中，高層概念對應到**線性子空間**。

如果「語義內容」和「文件格式」各佔一個子空間，那 prompt 的作用就是**投影**：

```
文件 d ∈ D（高維空間）

Π_C: D → C   （Content 投影：保留語義子空間的分量）
Π_R: D → R   （Rules 投影：保留格式子空間的分量）

正交性條件：Π_C · Π_R = 0
            （投影到語義子空間的分量和投影到格式子空間的分量正交）

完備性條件：d ≈ Decode(Π_C(d), Π_R(d))
            （兩個投影合在一起足以重建原文）
```

**這就是你的 PCA 直覺的精確數學版本。**

### 4.3 框架三：Information Bottleneck

Tishby et al. (1999) 的資訊瓶頸理論：

```
最佳表示 T 最小化：I(X; T) - β × I(T; Y)
  其中 X = 原始文件
       T = 壓縮表示（Content JSON + Rules JSON）
       Y = 重建目標
       I = 互資訊
       β = 壓縮-保留的權衡參數

白話：壓縮表示應該盡量小（I(X;T) 小），
     但保留足夠資訊來重建（I(T;Y) 大）。
```

你的系統裡：
- Content JSON 保留了語義相關的資訊
- Rules JSON 保留了格式相關的資訊
- 兩者**互補**：I(Content; Rules) 應該趨近 0（不重疊）
- 兩者**充分**：I(Content + Rules; Document) 應該趨近 H(Document)（足以重建）

### 4.4 框架四：ICA（獨立成分分析）

Honkela et al. (2010) 和 Yamagiwa et al. (2023, EMNLP) 證明：

> 對文本做 ICA（而非 PCA），得到的獨立成分更可解讀、更跨語言通用。

PCA 找的是**不相關**（uncorrelated）的分量，ICA 找的是**統計獨立**（independent）的分量。獨立 > 不相關。

```
PCA：  Cov(Content, Rules) = 0        （二階統計量：不相關）
ICA：  P(Content, Rules) = P(Content) × P(Rules)  （完全獨立）
```

你聲稱 Content 和 Rules 是「正交的」——如果要嚴格，應該追求 ICA 意義上的獨立，不只是 PCA 意義上的不相關。

### 4.5 能不能化為公式？可以，但需要近似

**難點**：f_θ（LLM）是一個超大型非線性函數，不可能精確寫出 Π_C 和 Π_R 的解析形式。

**解法**：用可操作的代理指標（proxy metrics）：

| 數學概念 | 可操作的代理 |
|---------|------------|
| 正交性 I(C; R) ≈ 0 | 用 embedding 計算 C 和 R 的 cosine similarity；或用 probing classifier 測試「能不能從 C 預測 R」 |
| 完備性 I(C+R; D) ≈ H(D) | 重建品質（semantic similarity + LLM judge） |
| 最佳 k | BIC(k) = -2 log Q(k) + k log N |
| 介入獨立性 | Geiger et al. (2021) 的 interchange intervention：換掉 C 不影響 R 的重建效果 |

**這些都是可以立刻實作的實驗。**

---

## 五、怎麼救這篇論文？重新定位路線圖

### 5.1 一句話重新定位

```
舊定位：「我們提出了一個 Symbolic AutoEncoder」
新定位：「我們提出了一個 Symbolic Concept Bottleneck 框架，
        把公文生成強制經過人類可讀的概念層，
        並用 CFA 的方法論驗證概念維度的正交性」
```

### 5.2 重新定位後的論文結構

#### 一篇整合論文（取代 Paper 1 + Paper 2）

**標題建議**：

> "Symbolic Concept Bottleneck for Controllable Government Document Generation"

或中文：

> 「以符號概念瓶頸實現可控公文生成：內容與格式的可驗證解耦」

**故事線**：

1. **Introduction**：公文是 content+format 高度耦合的文體。直接讓 LLM 寫會產生幻覺。我們假設把資訊強制經過人類可讀的「概念層」可以改善品質。

2. **Related Work**：
   - Concept Bottleneck Models（Koh 2020 → CB-LLMs 2025）
   - Content-Style Disentanglement（Shen 2017, Cheng 2020）
   - Information Bottleneck（Tishby 1999）
   - Locatello 2019：無監督解耦不可能 → 需要先驗

3. **Method**：
   - 框架：Prompt-Defined Concept Bottleneck
   - 數學定義：投影算子 Π_C, Π_R；重建函數 Decode
   - 概念空間設計：Content（6 欄位）, Rules（9 欄位）
   - 正交性的操作定義：互資訊、介入實驗、交叉重建
   - **最佳概念數 k 的探索**：k=1,2,3,4,5 的實驗

4. **Experiments**：
   - Exp 1：重建品質（baseline）
   - Exp 2：正交性驗證（交叉重建，但要修正——用多個 Content source）
   - Exp 3：消融（但要修正——用正確的 dependent metrics）
   - Exp 4：最佳 k 探索（BIC + 互資訊）
   - Exp 5：AE vs Direct（但要修正——給 Direct 同等資訊量）
   - **新增：人工評估**（至少 50 份）
   - **新增：不同 LLM 做 judge**（避免自我偏好）

5. **Analysis**：
   - 互資訊測量：Content 和 Rules 有多獨立？
   - 殘差分析：什麼資訊被兩個 JSON 都遺漏了？
   - 失敗案例：什麼時候解耦會崩壞？

6. **Conclusion**：Prompt-defined concept bottleneck 是可行的，最佳概念數為 k=?，為高風險文件生成提供了可控方案。

### 5.3 哪些東西可以直接保留？

| 現有元素 | 保留？ | 修改建議 |
|---------|--------|---------|
| 四階段 Pipeline | ✓ 保留 | 重新描述為 Concept Bottleneck 管線 |
| Content / Rules 雙 JSON 設計 | ✓ 保留 | 重新稱為「概念層」，加入最佳 k 的討論 |
| 逆向資料生成 | ✓ 保留 | 但必須修正語義不連貫的配對 |
| 六維評估 | 部分保留 | 加入互資訊指標、去掉恆等式指標 |
| 交叉重建 | ✓ 保留思路 | 必須修正為多 Content source |
| 消融實驗 | ✓ 保留思路 | 必須使用非恆等式的指標 |
| AE vs Direct | ✓ 保留思路 | 必須修正為公平比較 |
| Self-refinement | ✗ 暫時擱置 | 除非能在不看 ground truth 的情況下做 |

### 5.4 需要新增的實驗

| 優先級 | 實驗 | 目的 | 難度 |
|--------|------|------|------|
| **P0** | 最佳概念數 k 探索 | 回答「兩個分量夠不夠」 | 中 |
| **P0** | 互資訊測量 I(C; R) | 量化正交性 | 低 |
| **P0** | 多 Content source 交叉重建 | 修正現有 bug | 低 |
| **P0** | 公平的 AE vs Direct | 給 Direct 同等信息 | 低 |
| **P1** | 人工評估（50+ 份） | 驗證 LLM judge | 中 |
| **P1** | 不同 LLM 做 judge | 排除自我偏好 | 低 |
| **P1** | 介入實驗（Interchange intervention） | 最嚴格的正交性測試 | 中 |
| **P2** | 真實公文測試 | 驗證在真實世界的效果 | 高 |
| **P2** | 殘差分析 | 什麼資訊被遺漏了 | 中 |

---

## 六、你提到的 PCA 直覺的完整數學對照

把所有東西拉到一起，這是你的 PCA 直覺跟系統的完整對應：

```
PCA / 因子分析世界             你的系統
─────────────────────        ─────────────────────
資料矩陣 X                    公文集合 {d₁, d₂, ..., dₙ}
主成分 / 因子                  概念維度（Content, Rules, ...）
因子載荷矩陣                   Prompt 定義的提取邏輯
因子分數                       提取出來的 JSON 值
重建 X̂ = F × L^T + E         重建 d̂ = Decode(C, R) + 殘差
殘差 E                        重建公文與原文的差異
正交約束 F^T F = I            I(C; R) ≈ 0
最佳 k（scree plot/BIC）      最佳概念數（BIC 類比實驗）
EFA（無先驗）                  PCA 類比——從資料學分量
CFA（有先驗）                  **你的方法**——先驗指定分量
```

### Locatello (2019) 的關鍵結論的角色

```
Locatello: 沒有歸納偏置 → 無監督解耦不可能
                ↓
你的系統: prompt 就是歸納偏置
                ↓
結論: 你的 CFA 方法論不只是「可行的替代方案」，
     而是「理論上必須的方法」——因為 EFA/PCA 方法
     在沒有監督/先驗的情況下根本不保證能找到正確的分量。
```

**這是一個很強的論點。** 你可以說：「我們不是因為懶才用 prompt 定義分量，而是因為 Locatello et al. 證明了你必須這麼做。」

---

## 七、一個有可能的新論文故事

如果你願意做上面 P0 級的實驗（大約 2-3 週工作量），可以寫出這樣一篇論文：

---

**標題**：How Many Concepts Does a Government Document Have? Exploring Prompt-Defined Concept Bottlenecks for Controllable Document Generation

**一句話**：我們把公文生成建模為 Concept Bottleneck 問題，實驗發現 k=? 個 prompt 定義的概念維度就足以高品質重建，並且提出了一套量化正交性的方法論。

**新穎貢獻**：
1. 第一次把 Concept Bottleneck 框架應用到**公文生成**（政府文件領域）
2. 提出 **prompt-defined CFA** 作為結構化文件分解的理論框架
3. 實驗回答「公文有幾個正交維度」的問題
4. 用互資訊和介入實驗**量化**概念正交性（而非只用消融定性展示）
5. 連接 Locatello 的不可能定理，論證 prompt-defined 分解是理論上必要的

**目標會議**：ACL / EMNLP / NAACL

---

## 八、參考文獻精選（最核心的 20 篇）

### Concept Bottleneck 核心
1. Koh et al. (2020) "Concept Bottleneck Models" ICML
2. Yamaguchi et al. (2024) "Concept Bottleneck Large Language Models" ICLR 2025
3. Liu et al. (2024) "Concept Bottleneck Generative Models" ICLR 2024
4. Yamaguchi & Nishida (2025) "Explanation Bottleneck Models" AAAI 2025
5. Ludan et al. (2023) "Text Bottleneck Models" arXiv
6. Shang et al. (2024) "Incremental Residual Concept Bottleneck Models" CVPR 2024

### 解耦理論
7. Locatello et al. (2019) "Challenging Common Assumptions..." ICML (Best Paper)
8. Cheng et al. (2020) "Improving Disentangled Text Representation Learning with Information-Theoretic Guidance" ACL
9. Shen et al. (2017) "Style Transfer from Non-Parallel Text by Cross-Alignment" NeurIPS
10. Park et al. (2024) "The Linear Representation Hypothesis and the Geometry of LLMs" ICML

### 數學形式化
11. Petrov et al. (2024) "Prompting a Pretrained Transformer Can Be a Universal Approximator" ICML
12. Tishby et al. (1999) "The Information Bottleneck Method" Allerton Conference
13. Geiger et al. (2021) "Causal Abstractions of Neural Networks" NeurIPS

### 文本分解
14. Honkela et al. (2010) "WordICA" Natural Language Engineering
15. Yamagiwa et al. (2023) "Discovering Universal Geometry in Embeddings with ICA" EMNLP
16. "Can LLMs (or Humans) Disentangle Text?" (2024) NLP+CSS @ NAACL

### NLG Pipeline
17. Reiter & Dale (2000) "Building Natural Language Generation Systems" Cambridge UP
18. Puduppully et al. (2019) "Data-to-Text Generation with Content Selection and Planning" AAAI
19. Musumeci et al. (2024) "LLM-Based Multi-Agent Generation of Semi-structured Documents from Semantic Templates" HCII/Springer

### 因子數量選擇
20. Preacher et al. (2013) "Choosing the Optimal Number of Factors in Exploratory Factor Analysis" Multivariate Behavioral Research

---

*分析完成 — 2026-02-11*
*基於三個獨立文獻調研代理的 70+ 篇論文整合*
