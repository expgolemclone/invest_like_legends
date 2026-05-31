# アーキテクチャ

## 概要

portfolio と candidates を表示する Web アプリケーション。GitHub Pages で静的にホスティングし、`docs/assets/data/investors.json`、`docs/assets/data/shareholder_candidates.json`、`docs/assets/stock-price-meta.json` は `scripts/enrich_investors.py` で再生成する。portfolio と candidates の表示データは静的JSONを手入力せず、`../japan_company_handbook/data/stock_performance.db` の `major_shareholders` から導出する。

コードレビュー監査メモは `codereview-report.md` に記録する。

## ディレクトリ構成

```
invest_like_legends/
├── config/                # names-only の設定と watch 銘柄コード
│   ├── investors.json     # タブキー -> 投資家名
│   └── watch_codes.txt    # watch タブ用の銘柄コード
├── docs/                  # 静的サイト（GitHub Pages）
│   ├── index.html         # stock_web_ui テンプレートから生成した HTML
│   └── assets/
│       ├── data/
│       │   ├── investors.json                 # 生成済みの投資家別表示データ
│       │   └── shareholder_candidates.json    # 生成済みの株主候補データ
│       ├── stock-price-meta.json              # 株価基準日 metadata
│       └── app.js         # invest_like_legends 用テーブル設定
├── scripts/
│   └── enrich_investors.py
├── tests/
├── investor_data.py       # 共有データビルダー
├── serve.py               # ローカルサーバー
└── src_ts/                # TypeScript ソース
```

## 開発と運用

### 前提

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Node.js / npm
- このリポジトリと同じ親ディレクトリに、以下の関連リポジトリがあること

```text
../formula_screening
../stock_db
../stock_web_ui
../japan_company_handbook
```

四季報大株主 DB の場所を標準構成から変える場合は、環境変数で指定する。`stock_db` の DB パスはこの repo では扱わず、`stock_db.api` が内部で解決する。

```powershell
$env:HANDBOOK_DB_PATH="C:\path\to\stock_performance.db"
```

### セットアップと確認

```powershell
uv sync
npm install
uv run pytest
```

TypeScript は `tsconfig.json` と `package.json` / `package-lock.json` の TypeScript 依存でコンパイルする。`src_ts/app.ts` を変更した場合は `npx tsc` を実行し、生成済み JavaScript の `docs/assets/app.js` も更新する。

### ローカル確認と公開データ更新

```powershell
uv run python serve.py
uv run python scripts/enrich_investors.py
```

`serve.py` はローカル確認用で、`/api/portfolio` と `/api/shareholder-candidates` が手元の四季報 DB、設定、`stock_db` / `formula_screening` の公開 API から毎回データを組み立てる。`/api/stock-price-meta` は `stock_db.api.get_stock_price_metadata()` を返し、共通UIのステータス欄に株価基準日を表示する。`scripts/enrich_investors.py` は公開ページが読む `docs/assets/data/investors.json`、`docs/assets/data/shareholder_candidates.json`、`docs/assets/stock-price-meta.json` を完全再生成する。

### 投資家と監視銘柄の追加

投資家タブを追加する場合は `config/investors.json` にキーと表示名を追加する。通常は表示名から大株主 DB を自動照合する。名義を厳密に指定したい場合は `{ "name": "...", "aliases": [...] }` 形式を使い、明示した名義の正規化完全一致だけを拾う。

監視銘柄を追加する場合は `config/watch_codes.txt` に銘柄コードを 1 行ずつ追加する。設定変更後は、ローカル確認には `uv run python serve.py`、公開用 JSON の更新には `uv run python scripts/enrich_investors.py` を使う。

## コンポーネント

### 設定ファイル (`config/`)

- `investors.json`: 生成元の唯一のJSON設定。値は表示名文字列、または `name` と `aliases` を持つオブジェクト。保有銘柄一覧は持たない
- `watch_codes.txt`: `watch` タブ専用の静的銘柄コード一覧。`watch` は大株主DBから導出できないため別管理し、今村証券（7175）などの手動監視銘柄をここに追加する

### データビルダー (`investor_data.py`)

- `build_investors_document()` が投資家別表示データの共通入口
- `build_shareholder_candidates_document()` が株主候補データの共通入口
- 入力ソース
- `config/investors.json`
- `config/watch_codes.txt`
- `japan_company_handbook/data/stock_performance.db` の `major_shareholders`
- `stock_db.api.get_stock_names()` から引く会社名
- `formula_screening.web.run_screening_strategy_payload(..., return_all=True)` が返す Rust-backed 公開 payload
  - 指標計算に使う財務データは `formula_screening` が `stock_db` 公開 API 経由で取得する。EDINET XBRL を正、四季報予想を補助ソースとする責務は `stock_db` 側に閉じる
  - `per_actual` は実績純利益、`per` は四季報今期予想純利益、`per_next` は四季報来期予想純利益 (`source=shikiho`) から計算された値を使う
- 投資家名の照合手順
  - `aliases` が指定された投資家は、各 alias と DB 上の株主名を同じルールで正規化し、完全一致する株主名だけを対象にする
  - `aliases` がない投資家は以下の既存ルールで表示名から照合する
    - NFKC 正規化
    - 空白・記号・法人格表現の除去
    - 完全一致
    - 包含一致
    - それでも0件なら、先頭2文字が CJK の投資家名に限って先頭2文字一致
- 同一銘柄で複数の株主別名が一致した場合は、`shares` と `ratio_pct` を銘柄単位で合算する
- `amount_millions` は四季報の `shares` を万株単位として `round(shares * price / 100)` で百万円換算する
- 会社名が取れない場合は `（銘柄コード XXXX）` を使う
- 一致する大株主が0件でも、設定上の投資家タブは残し `stocks: []` を返す
- 株主候補は正規化名ごとに集約し、2銘柄以上を持つ主体から総保有額降順で上位1000件を出す
- 株主候補の初期除外語は、自己株・持株会・信託名義・カストディ・証券口座系など運用主体の発掘に不向きな名義を対象にする

### フロントエンド (`docs/`)

- `index.html`: `stock_web_ui` 共通テンプレートから生成したHTML
- `assets/app.js`: 共有 `StockTable` runtime を使い、portfolio・candidates・candidate 詳細を切り替える設定ファイル。投資家タブと混同しないよう、上位の portfolio/candidates 切替は単一スイッチで表示する
- `assets/data/investors.json`: 表示用の完全データ
  - トップレベル順から投資家タブを生成する
  - 各投資家は `name`, `aliases`, `stocks` を持ち、`aliases` は銘柄抽出に使った DB 上の名寄せ済み株主名をすべて列挙する
  - 各銘柄は `code`, `name`, `price`, `price_date`, `net_cash_ratio`, `per_actual`, `per`, `per_next`, `fcf_yield_avg`, `total_payout_ratio`, `equity_ratio`, `peg_trailing_5`, `peg_trailing_5_status`, `peg_blended_5y_actual_2f`, `peg_blended_5y_actual_2f_status`, `dividend_yield`, `has_preferred_shares`, `croic`, `fcf_cagr`, `fcf_cagr_r2`, `fcf_sma_cagr`, `pbr`, `amount_millions`, `ratio_percent` を含む
  - `watch` は `amount_millions: null`, `ratio_percent: 0`
  - 人手で編集しない。常に `scripts/enrich_investors.py` で再生成する
- `assets/data/shareholder_candidates.json`: 株主候補の完全データ
  - 各候補は `id`, `name`, `aliases`, `holding_count`, `priced_holding_count`, `total_amount_millions`, `stocks` を持つ
  - `aliases` は同一候補に名寄せして `stocks` に含めた DB 上の株主名をすべて列挙する
  - `?view=candidates` は candidates、`?view=candidate&id=...` は candidate 詳細を表示する
  - 人手で編集しない。常に `scripts/enrich_investors.py` で再生成する
- `assets/stock-price-meta.json`: `stock_db.api.get_stock_price_metadata()` の `price_date` と `target_price_date` を持つ metadata。ローカルでは `/api/stock-price-meta` が同じ形を返す

#### テーブルカラム

各ヘッダーには `title` 属性が設定され、ホバー時にツールチップを表示する。
指標カラムは `../formula_screening/strategies/net_cash_fcf.toml` の列順に合わせる。投資家固有の `amount` / `ratio` は指標列の後ろに置く。

| カラム | 説明 | ソートキー | トグル可 | 閾値 |
|--------|------|------------|----------|------|
| code | 銘柄コード（クリックでMonex財務ページ） | `code` | - |
| name | 会社名（ローカルでは yazi で四季報PDFを開く） | `name` | - |
| ncr | `(流動資産 - 棚卸資産 + 有価証券 * 0.7 - 流動負債 - 固定負債) / 時価総額` | `net_cash_ratio` | o | > 1: good |
| fcf_10y% | `10期の平均FCF / 時価総額` | `fcf_yield_avg` | o | >= 10%: good |
| payout% | `(|配当支払額| + |自己株式取得額|) / 時価総額 * 100` | `total_payout_ratio` | o |
| peg_5y | `実績PER / 過去5年EPS CAGR[%]`。成長率が0以下なら `neg`、その他の欠損は `-` | `peg_trailing_5` | o |
| peg_5y2f | `来期予想PER / (過去5年実績+2期予想)EPS CAGR[%]`。成長率が0以下なら `neg`、その他の欠損は `-` | `peg_blended_5y_actual_2f` | o |
| div% | `1株配当 / 株価 * 100` | `dividend_yield` | o | >= 4: good |
| pref | 優先株有無 | `has_preferred_shares` | o |
| equity% | `自己資本 / 総資産 * 100` | `equity_ratio` | o | >= 50: good |
| pbr | `時価総額 / 純資産` | `pbr` | o | < 0.5: good |
| croic% | `FCF / (自己資本 + 有利子負債)` | `croic` | o | >= 15%: good |
| fcf_cagr% | 指数回帰によるFCF年平均成長率 | `fcf_cagr` | o |
| r2 | FCF指数回帰トレンドの決定係数 | `fcf_cagr_r2` | o |
| sma_cagr% | 3年移動平均ベースFCF年平均成長率 | `fcf_sma_cagr` | o |
| price | 株価（終値。クリックで四季報オンラインを開く） | `price` | o |
| per_a | `時価総額 / 実績純利益` | `per_actual` | o | 0<per_actual<=7: good, >7: bad |
| per_c | `時価総額 / 今期予想純利益` | `per` | o | 0<per<=7: good, >7: bad |
| per_n | `時価総額 / 来期予想純利益` | `per_next` | o | 0<per_next<=7: good, >7: bad |
| amount | 投資家の保有金額（百万円を億円表示） | `amount_millions` | - |
| ratio | 投資家の保有割合（%） | `ratio_percent` | - |

### ローカルサーバー (`serve.py`)

- 起動時に `stock_db.api.ensure_prices_fresh()` で株価鮮度を判定し、前営業日終値が揃っていない場合は `stock_db` 側の `refresh-prices --if-needed` 経由で Stooq 更新と Yahoo Finance JP 補完を実行する。個別銘柄の株価が取得できない場合も処理は継続し、古い株価は `price_date` と `target_price_date` により共通 UI 側で目立ちにくく表示する
- 起動時に `build_investors_document()` / `build_shareholder_candidates_document()` を呼び出し、公開用 JSON を自動生成する
- `/api/portfolio` は `build_investors_document()` を毎回呼び、最新DBから投資家データを組み立てて返す
- `/api/shareholder-candidates` は `build_shareholder_candidates_document()` を毎回呼び、最新DBから候補データを組み立てて返す
- `/api/stock-price-meta` は `stock_db.api.get_stock_price_metadata()` 経由で `{ "price_date": "YYYY-MM-DD", "target_price_date": "YYYY-MM-DD" }` を返す
- 生成済み JSON はローカルAPIの入力には使わない
- `stock_web_ui.page.IndexPage` でローカル用 `index.html` を描画し、HTTPサーバー本体は `stock_web_ui` に委譲する

### 生成スクリプト (`scripts/enrich_investors.py`)

- 投資家別表示データと株主候補データを同じ入力ソースから完全再生成する
- 株価基準日 metadata も同時に `docs/assets/stock-price-meta.json` へ書き出す
- 既存JSONへのマージは行わない
- 生成した公開JSONに差分がある場合は、対象JSONだけを `jj commit` し、`jj git push` する

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
major_shareholders + stock_db API + formula_screening metrics
  ↓
JSON / yazi / 外部ブラウザ
```

```
ブラウザ
  ↓
stock_web_ui.handler
  ↓
serve.py (/api/shareholder-candidates)
  ↓
investor_data.build_shareholder_candidates_document()
  ↓
major_shareholders + stock_db API + formula_screening metrics
  ↓
JSON / candidates / candidate detail
```

### GitHub Pages

```
uv run python scripts/enrich_investors.py
  ↓
investor_data.build_investors_document()
investor_data.build_shareholder_candidates_document()
  ↓
docs/assets/data/investors.json
docs/assets/data/shareholder_candidates.json
docs/assets/stock-price-meta.json
  ↓
jj commit & jj git push
  ↓
GitHub Pages デプロイ
  ↓
ブラウザ → invest_like_legends/index.html
  ↓
stock_web_ui/assets/stock-table.js + style.css
  ↓
invest_like_legends/assets/data/investors.json
invest_like_legends/assets/data/shareholder_candidates.json
invest_like_legends/assets/stock-price-meta.json
```

## 依存プロジェクト

- `formula_screening`: 指標計算ロジック。`run_screening_strategy_payload()` を公開APIとして利用する
- `stock_db`: 会社名、株価 metadata、価格更新、財務データを公開 API 経由で提供する
- `stock_web_ui`: Web UI フレームワーク。GitHub Pages 上の共有 runtime / style 配信元でもある
- `japan_company_handbook`: 四季報の大株主データ (`stock_performance.db`) とPDF群を保持する
