# アーキテクチャ

## 概要

投資家ごとの保有銘柄一覧を表示する Web アプリケーション。GitHub Pages で静的にホスティングし、`docs/assets/data/investors.json` は毎日 GitHub Actions で再生成する。投資家別の銘柄一覧は静的JSONを手入力せず、`../japan_company_handbook/data/stock_performance.db` の `major_shareholders` から導出する。

## ディレクトリ構成

```
invest_like_legends/
├── .github/workflows/     # GitHub Actions ワークフロー
├── config/                # names-only の設定と watch 銘柄コード
│   ├── investors.json     # タブキー -> 投資家名
│   └── watch_codes.txt    # watch タブ用の銘柄コード
├── docs/                  # 静的サイト（GitHub Pages）
│   ├── index.html         # stock_web_ui テンプレートから生成した HTML
│   └── assets/
│       ├── data/
│       │   └── investors.json   # 生成済みの表示用データ
│       └── app.js         # invest_like_legends 用テーブル設定
├── scripts/
│   └── enrich_investors.py
├── tests/
├── investor_data.py       # 共有データビルダー
├── serve.py               # ローカルサーバー
└── src_ts/                # TypeScript ソース
```

## コンポーネント

### 設定ファイル (`config/`)

- `investors.json`: 生成元の唯一のJSON設定。保持するのは投資家名だけで、保有銘柄一覧は持たない
- `watch_codes.txt`: `watch` タブ専用の静的銘柄コード一覧。`watch` は大株主DBから導出できないため別管理

### データビルダー (`investor_data.py`)

- `build_investors_document()` がローカルAPIと静的JSON生成の共通入口
- 入力ソース
  - `config/investors.json`
  - `config/watch_codes.txt`
  - `japan_company_handbook/data/stock_performance.db` の `major_shareholders`
  - `stock_db` の `stocks.db` から引く会社名
  - `formula_screening.web.compute_all_stock_metrics()` が返す指標
- 投資家名の照合手順
  - NFKC 正規化
  - 空白・記号・法人格表現の除去
  - 完全一致
  - 包含一致
  - それでも0件なら、先頭2文字が CJK の投資家名に限って先頭2文字一致
- 同一銘柄で複数の株主別名が一致した場合は、`shares` と `ratio_pct` を銘柄単位で合算する
- `amount_millions` は四季報の `shares` を万株単位として `round(shares * price / 100)` で百万円換算する
- 会社名が取れない場合は `（銘柄コード XXXX）` を使う
- 一致する大株主が0件でも、設定上の投資家タブは残し `stocks: []` を返す

### フロントエンド (`docs/`)

- `index.html`: `stock_web_ui` 共通テンプレートから生成したHTML
- `assets/app.js`: 共有 `StockTable` runtime を起動するだけの設定ファイル
- `assets/data/investors.json`: 表示用の完全データ
  - トップレベル順から投資家タブを生成する
  - 各銘柄は `code`, `name`, `amount_millions`, `ratio_percent`, 指標列を含む
  - `watch` は `amount_millions: null`, `ratio_percent: 0`
  - 人手で編集しない。常に `scripts/enrich_investors.py` で再生成する

#### テーブルカラム

各ヘッダーには `title` 属性が設定され、ホバー時に日本語ツールチップを表示する。

| カラム | 説明 | ソートキー | トグル可 | 閾値 |
|--------|------|------------|----------|------|
| code | 銘柄コード（クリックでMonex財務ページ） | `code` | - |
| name | 会社名（ローカルでは yazi で四季報PDFを開く） | `name` | - |
| price | 株価（終値。クリックで四季報オンラインを開く） | `price` | o |
| ncr | `(流動資産 - 棚卸資産 + 有価証券 * 0.7) / 時価総額` | `net_cash_ratio` | o | > 1: good |
| per | `株価 / 来期予想EPS` | `per` | o | 0<per<=7: good, >7: bad |
| equity | `自己資本 / 総資産 * 100` | `equity_ratio` | o | >= 50: good |
| fcf_y | `10期の平均FCF / 時価総額` | `fcf_yield_avg` | o | >= 10%: good |
| croic | `FCF / (自己資本 + 有利子負債)` | `croic` | o | >= 15%: good |
| amount | 投資家の保有金額（百万円を億円表示） | `amount_millions` | - |
| ratio | 投資家の保有割合（%） | `ratio_percent` | - |

### ローカルサーバー (`serve.py`)

- `/api/portfolio` は `build_investors_document()` を毎回呼び、最新DBから投資家データを組み立てて返す
- 生成済み `docs/assets/data/investors.json` はローカルAPIの入力には使わない
- `stock_web_ui.page.IndexPage` でローカル用 `index.html` を描画し、HTTPサーバー本体は `stock_web_ui` に委譲する

### 生成スクリプト (`scripts/enrich_investors.py`)

- `build_investors_document()` を使って `docs/assets/data/investors.json` を完全再生成する
- 既存JSONへのマージは行わない

### GitHub Actions (`.github/workflows/update_investors.yml`)

- 毎日日本時間 0:00 に `scripts/enrich_investors.py` を実行する
- 依存repoとして `stock_db`, `formula_screening`, `stock_web_ui`, `japan_company_handbook` を checkout する
- `stock_db` の `stocks.db` は `stocks-db` artifact から取得する
- `japan_company_handbook` は `data/stock_performance.db` だけ sparse checkout する
- `uv` の相対パス依存を満たすため、workflow 内で sibling symlink を作る
- 生成後は `docs/assets/data/investors.json` だけをコミットして push する

## データフロー

### ローカル開発環境

```
ブラウザ
  ↓
stock_web_ui.handler
  ↓
serve.py (/api/portfolio)
  ↓
investor_data.build_investors_document()
  ↓
config/investors.json + watch_codes.txt
  ↓
major_shareholders + stocks.db + formula_screening metrics
  ↓
JSON / yazi / 外部ブラウザ
```

### GitHub Pages

```
GitHub Actions (毎日0:00)
  ↓
scripts/enrich_investors.py
  ↓
investor_data.build_investors_document()
  ↓
docs/assets/data/investors.json
  ↓
git commit & push
  ↓
GitHub Pages デプロイ
  ↓
ブラウザ → invest_like_legends/index.html
  ↓
stock_web_ui/assets/stock-table.js + style.css
  ↓
invest_like_legends/assets/data/investors.json
```

## 依存プロジェクト

- `formula_screening`: 指標計算ロジック。`compute_all_stock_metrics()` を公開APIとして利用する
- `stock_db`: 会社名DB (`stocks.db`) と接続APIを提供する
- `stock_web_ui`: Web UI フレームワーク。GitHub Pages 上の共有 runtime / style 配信元でもある
- `japan_company_handbook`: 四季報の大株主データ (`stock_performance.db`) とPDF群を保持する
