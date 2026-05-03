# アーキテクチャ

## 概要

投資家の保有銘柄一覧を表示するWebアプリケーション。GitHub Pages で静的にホスティングされ、指標データは GitHub Actions で毎日更新されます。

## ディレクトリ構成

```
invest_like_legends/
├── .github/workflows/     # GitHub Actions ワークフロー
├── config/                # 設定ファイル
├── docs/                  # 静的サイト（GitHub Pages）
│   ├── index.html         # stock_web_ui テンプレートから生成した HTML
│   └── assets/
│       ├── data/          # 生成データ（investors.json, metrics.json）
│       └── app.js         # invest_like_legends 用テーブル設定
├── scripts/               # ユーティリティスクリプト
├── src_ts/                # TypeScript ソース
├── tests/                 # テスト
└── serve.py               # ローカルサーバー起動スクリプト
```

## コンポーネント

### フロントエンド (`docs/`)

- **index.html**: `python -m stock_web_ui.render_index --shared-asset-base-url https://expgolemclone.github.io/stock_web_ui/assets ...` で共通テンプレートから生成した HTML
- **共有 runtime / style**: `stock_web_ui` の GitHub Pages 配下 `assets/stock-table.js` / `assets/style.css`
  - 投資家タブ切り替え
  - `investors.json` のトップレベル順から投資家タブを動的生成
  - ソート機能
  - 指標カラムの表示/非表示トグル（localStorage で永続化）
  - 指標データ表示（GitHub Pages では静的JSON、ローカルでは API 使用）
  - 指標の色分け（閾値による good/bad 表示）
- **assets/app.js**: `@stock-web-ui/runtime` の型を参照しつつ、ブラウザでは先に読み込まれた共有 `StockTable` API を使って起動する
- **assets/data/investors.json**: 投資家保有銘柄データ
  - 対応キー: `watch`, `naito`, `hikari`, `kiyohara`, `katayama`, `imura`, `gomi`, `one_warikabunihon`, `yoshida`
  - `watch` は監視銘柄（保有していない銘柄の一覧）。`amount_millions: null`, `ratio_percent: 0`
  - 銘柄の追加・削除で dataset 件数が変わる場合は `tests/test_investor_data.py` の `EXPECTED_STOCK_COUNTS` も更新する
- **assets/data/metrics.json**: 指標データ（GitHub Actions で生成）

#### テーブルカラム

各ヘッダーには `title` 属性が設定されており、ホバー時にネイティブのツールチップで日本語の解説が表示される。

| カラム | 説明 | ソートキー | トグル可 | 閾値 |
|--------|------|------------|----------|------|
| code | 銘柄コード（クリックでMonex財務ページを開く） | `code` | - |
| name | 会社名（クリックでyaziで四季報PDFを開く。GitHub Pagesでは四季報オンラインにフォールバック） | `name` | - |
| price | 株価（終値、小数点第一位まで表示） | `price` | o |
| ncr | ネットキャッシュレシオ — 現金同等物から有利子負債を引いた額を時価総額で割った値。高いほど財務が安全 | `net_cash_ratio` | o | > 1: good |
| per | 株価収益率 — 株価を1株当たり利益で割った値。低いほど割安（目安: 15倍以下） | `per` | o | 0<per<=7: good, >7: bad |
| equity | 自己資本比率 — 自己資本 / 総資産 * 100 | `equity_ratio` | o | >= 50: good |
| fcf_y | フリーキャッシュフローイールド — FCFを時価総額で割った値。高いほどキャッシュ創出力が優れている | `fcf_yield_avg` | o | >= 10%: good |
| croic | CROIC — FCF / (自己資本 + 有利子負債) | `croic` | o | >= 15%: good |
| amount | 投資家の保有額（億円、小数点第一位まで表示） | `amount_millions` | - |
| ratio | 投資家の保有割合（%） | `ratio_percent` | - |

### サーバー起動スクリプト (`serve.py`)

- `investors.json` を読み込み、`formula_screening.web.compute_all_stock_metrics()` 公開APIで DB からリアルタイムに指標を計算して `/api/portfolio` を組み立てる
- `formula_screening` の内部モジュール（db.repository, indicators, metrics）は直接importせず、公開API経由で利用する
- API リクエストごとに最新データを返すため、DB 更新後にサーバー再起動なしで指標が反映される
- `stock_web_ui.page.IndexPage` を使ってローカル用 `index.html` を共通テンプレートから描画する。共有 runtime / style はローカル相対の `/assets/*` を指し、実体は `docs/assets/` 不在時に `stock_web_ui.ASSETS_DIR` からフォールバック配信される
- HTTP サーバー本体、ポート解放、起動ブラウザ、`/open`、`/open-yazi/{code}` は `stock_web_ui.serve` / `stock_web_ui.handler` に委譲する

### スクリプト (`scripts/`)

- **generate_metrics.py**: 全銘柄の指標を `formula_screening.web.compute_all_stock_metrics()` 公開APIで計算して JSON に保存

### GitHub Actions (`.github/workflows/`)

- **update_metrics.yml**: 毎日日本時間 0:00 に指標データを更新

## データフロー

### ローカル開発環境

```
ブラウザ → HTTP リクエスト → stock_web_ui.handler
                                    ↓
                              serve.py (/api/portfolio)
                                    ↓
                     investors.json + formula_screening (DB)
                                    ↓
                            JSON / yazi / 外部ブラウザ
```

### GitHub Pages

```
GitHub Actions (毎日0:00)
        ↓
scripts/generate_metrics.py
        ↓
docs/assets/data/metrics.json
        ↓
git commit & push
        ↓
GitHub Pages デプロイ
        ↓
ブラウザ → 静的 JSON 読み込み
```

## 依存プロジェクト

- **formula_screening**: 指標計算ロジック。`formula_screening.web.compute_all_stock_metrics()` 公開API経由で利用（内部モジュールの直接importはしない）
- **stock_web_ui**: Web UI フレームワーク（ハンドラ、ページ、サーバー機能をAPIとして利用）
- **japan_company_handbook**: 四季報PDFデータ（`data/{YYYY_Q}/{code}.pdf`）
