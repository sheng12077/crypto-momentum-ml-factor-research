# 專案現況與 Coder Agent 評估交接

更新日期：2026-11-22。用途：讓其他 agent 評估工作複雜度、模型需求與分工。
本文件描述既有工作；不授權接手 agent 自行啟動完整回測、調參或改寫歷史。

## 1. 目前在做什麼

這是 Binance USDⓈ-M 永續合約的中低頻橫截面多空因子研究。
目標是建立可驗證、可重現的交易模擬，再依結果決定是否值得進入 paper trading。
目前範圍到歷史模擬；尚未建立或核准實盤／paper trading 系統。

原型曾限於固定 37 個識別碼，目前正在完成新版動態資產池研究。
原始清單有 924 個識別碼，但不能直接稱為 924 個可交易加密資產：包含不同
上市／下架時期、身分重用及非加密貨幣商品。每個決策日依當時資料與資格選池，
保留資產可用的歷史區間，不要求它在整個研究期間始終存在。

目前策略：

- 三類訊號：20／60／120 日動量、7 日 funding、7 日主動買賣失衡。
- Size 暫未納入；新聞／NLP 未納入。
- LightGBM regression 預測 7 日價格報酬，僅使用截止時已成熟的訓練標籤。
- 各年度使用擴展訓練窗，交易年度內固定模型；TreeSHAP 用於解釋模型。
- 每兩週排序，目標 5 多／5 空、單幣各為 NAV 的 10%，總多／空各 50%。
- 至少 20 個候選；目前沒有 buffer、動態權重或額外趨勢倉位控制。
- NautilusTrader 執行／帳務；永續 taker 5 bps、無 BNB 折扣的研究成本假設，
  另做 5／10／20 bps 滑點；逐筆計入 funding。這不是已驗證的歷史帳戶費率。
- 每窗 30 次金融執行：模型／純動量／等權因子分數各 3 種滑點、20 個
  固定種子隨機選幣對照、1 次主模型重播。BTC／ETH 現貨持有作額外基準。
- 另做獨立成交／手續費／funding／NAV 核對，不能只看 engine success。

## 2. 已完成與當前阻塞

| Window | 狀態 | 模型 5 bps 結果 |
| --- | --- | --- |
| 2021 訓練／2022 交易 | 30 案例完成並通過核對 | 報酬約 +21.76% |
| 2021–2022 訓練／2023 交易 | 30 案例完成，重播一致、獨立核對通過 | +51.56%、Sharpe 1.42、MDD −21.07% |
| 2021–2023 訓練／2024 交易 | 設定與修正已完成，等待使用者重新執行 | 尚無本版有效績效 |

2023 模型在 20 bps 滑點下仍約 +41.42%，但排除最佳月後只剩 +5.77%。
2023 主模型實際交易過 129 個不同合約；preflight 建立 211 個商品，後者包含
訓練與驗證需要的商品，不是每期候選數，也不是同時持倉數。
新版各年度結果不能直接當成無年度資金重置的連續帳戶績效。
原研究區分：2023／2024 驗證，2025–2026 最終 OOS；此工作不更動切分。

最新 2024 停止於 `data/processed/dynamic_2024/e58811244cbeac121539/`：

- prepare 載入 312 個商品、30166 筆候選列（含訓練期），不能當成每期池大小。
- preflight 有 12 筆問題，實際涉及 6 個合約：UNFI、BOND、KLAY、GAL、BLZ、DAR。
- 回補的 6 根 K 線成交量全為零；原因是配置漏了這些合約的下架／換幣公告。
- 已在 `config/dynamic_2024.json` 補公告；6 份公告及公告後正成交量的一分鐘
  退出價格均已透過現有來源程式驗證。沿用公告後 5 分鐘處理規則，沒有調參。
- 修正 commit：`b5ead6f`，已合併 main。實驗 022 登記 commit：`6a16769`。
- 修改配置會建立新 run identity，需重新 prepare／fit／preflight；不能沿用
  停止版本的模型。舊目錄保留；尚未替使用者執行新版完整流程。
- 最近 13 項針對性測試與相關 lint 通過；不代表全套測試或所有資料已無問題。

## 3. 資料夾概觀

以下以專案根目錄為基準；省略快取與非關鍵檔案。

```text
momentum_strategy/
├── AGENTS.md                    # 工程、Git、實驗與執行分工規則
├── pyproject.toml               # Python 套件、依賴、CLI、測試設定
├── environment.yml
├── config/
│   ├── dynamic_first_window.json
│   ├── dynamic_2023.json
│   ├── dynamic_2024.json         # 本次要執行的配置
│   └── ...                      # 資料核實／原型配置
├── experiments/                 # 實驗登記；020／021／022 對應新版年度窗
├── src/
│   ├── crypto_factor_research/  # 新版動態資產池入口與工作流程
│   │   ├── cli.py               # window 與資料核實等 CLI
│   │   ├── first_window.py      # 共用年度流程，名稱仍沿用第一窗
│   │   ├── window_data.py       # 市場資料、公告、公開來源與事件適配
│   │   ├── window_audit.py      # 獨立帳務核對與歸因
│   │   ├── window_report.py     # 基準、表格、圖與 notebook
│   │   ├── capacity.py          # 按日期的候選池盤點
│   │   ├── universe.py          # 資產資格／輸入檢查
│   │   └── repair*.py, ...      # 來源補齊、核實及證據評估
│   └── momentum_data/          # 原型套件，部分元件由新版共用
│       ├── backtest/engine.py  # 新版仍使用的 Nautilus 帳務引擎
│       ├── reporting/analysis.py
│       └── ...                  # 另有原型資料／模型／連續重播流程
├── tests/                      # 預設測試位置；包含新版 window 與原型測試
├── data/                       # 本機資料／產物，禁止提交 Git
│   ├── raw/                    # 原始市場資料，部分路徑連到共享 lake
│   ├── canonical/              # 標準化小時／日資料與來源索引
│   ├── catalog/
│   ├── repairs/                # 補齊觀測、公開來源快取與證據
│   ├── interim/                # 歷史研究中間產物，仍有舊版本與基準來源
│   └── processed/
│       ├── dynamic_first_window/<run_id>/
│       ├── dynamic_2023/<run_id>/
│       └── dynamic_2024/<run_id>/
├── reports/                    # 執行日誌、資料核實表與摘要
├── notebooks/                  # 追蹤中的研究 notebook；新版亦在各 run 產生
├── scripts/                    # 少量舊套件 launcher；新版使用 package CLI
├── research/legacy/            # 舊腳本／研究／測試封存，不是新版主要入口
├── docs/                       # 狀態、runbook、資料證據與方法說明
└── tools/, requirements/       # 輔助工具與依賴相關檔案
```

典型 run：`manifest.json`、features／trade／mark／funding Parquet、`notices.json`、
`model/`（模型／預測／SHAP／交易計畫）、`preflight*.json`、`results/`（逐案帳簿）、
`report/`（績效／歸因／圖）、總結 JSON 與產生的 notebook。
來源、配置及重要程式有 hash 綁定；禁止手改產物繞過檢查。

**架構尚有技術債**：兩個套件並存、`first_window.py` 承擔多階段、舊 interim
版本多。README 與 `docs/PROJECT_STRUCTURE.md` 部分內容仍描述早期 37 資產
原型，不能當成新版狀態的唯一依據；優先讀本文件與 PROJECT_STATUS。
本次沒有擅自整理或刪除歷史檔案，也沒有重寫 README。

## 4. 執行環境與下一步

WSL Ubuntu-24.04；Linux 路徑：
`/home/sheng77/working_space/quant_research/strategies/momentum_strategy`

Windows 路徑：
`\\wsl.localhost\Ubuntu-24.04\home\sheng77\working_space\quant_research\strategies\momentum_strategy`

Conda 環境 `funding-strategy`，Python 3.13。最近已確認的版本：
NautilusTrader 1.231.0、LightGBM 4.7.0、pandas 3.1.1。

使用者執行完整任務：

```bash
cd /home/sheng77/working_space/quant_research/strategies/momentum_strategy
conda activate funding-strategy
python -m crypto_factor_research window --config config/dynamic_2024.json --stage all
# 完成後只分享精簡摘要：
python -m crypto_factor_research window --config config/dynamic_2024.json --stage summary
```

完整耗時尚未測量；log 在 `reports/acquisition/`，結果目錄由 CLI 印出。
成功要求：success=true、30 個案例、primary_replay_identical=true、獨立核對通過。
失敗時先讀輸出的 problem JSON，不能盲目重跑或放寬驗收。

小型驗證範例：

```bash
python -m pytest -q tests/test_window_2024.py tests/test_window_2023.py tests/test_spot_benchmark.py
python -m ruff check tests/test_window_2024.py
```

## 5. 希望其他 Agent 評估什麼

目前尚未接入 Qwen；14B／27B 的實作表現沒有在本 repo 實測過。
希望規劃／審查 agent 保留研究與驗收責任，讓較便宜的 coder 負責實作：

| 工作 | 建議分工 |
| --- | --- |
| 研究問題、凍結策略、實驗登記、驗收標準 | 使用者＋規劃 agent |
| 設定／報表／函式／測試／一般 bug 修正 | Coder，先以 14B 小任務試行 |
| 跨模組重構、困難除錯 | 依實測考慮 27B 或規劃 agent 介入 |
| 時間可知性、標籤、公告、成交、funding、hash／快取審查 | 審查 agent 必查 |
| 完整資料準備／下載／訓練／回測 | 使用者執行，除非另有明確授權 |

請評估：14B 能否在明確規格下完成小改動？返工是否抵銷省下的成本？
哪些工作值得升級？請以可重現的小型任務測量，不要單靠參數量判斷。
計量應包含任務書、coder 執行、審查、返工的總成本與時間。

Coder 每次交付：目標與不可更動項目、改動檔案／diff、測試指令與結果、
未解決問題。避免貼整個 repo、完整對話或巨量執行日誌。
未來可能研究持倉權重，但尚未授權或登記該實驗，不要混入本次 2024 修正。

## 6. 協作與 Git 邊界

- 先讀 AGENTS.md、PROJECT_STATUS 與相關 runbook；核對現有 branch／diff。
- 每段工作使用 feat/、fix/、exp/、research/、infra/、docs/ 或 chore/ 分支。
- 實驗預期與驗收先在 main 單獨 commit；完成工作 no-ff merge 並刪分支。
- Commit／merge 訊息英文；明確 stage；不使用 git commit -a。
- 不推送、不改寫歷史，除非使用者確認；資料與金鑰不進 Git。
- 目前有 17 個既有 research/legacy 文件／notebook／測試修改，請保留，
  不擅自納入自己的提交。具體清單以 git status --short 為準。
- 不把此次交接誤認為重構整個專案的授權，不自行新增因子或放寬資料檢查。
