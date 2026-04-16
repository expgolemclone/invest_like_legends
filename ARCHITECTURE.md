# アーキテクチャ

## 概要

投資家の保有銘柄一覧を表示するWebアプリケーション。GitHub Pages で静的にホスティングされ、指標データは GitHub Actions で毎日更新されます。

## ディレクトリ構成

```
invest_like_legends/
├── .github/workflows/     # GitHub Actions ワークフロー
├── config/                # 設定ファイル
├── docs/                  # 静的サイト（GitHub Pages）
│   └── assets/
│       ├── data/          # 生成データ（investors.json, metrics.json）
│       ├── style.css      # スタイルシート
│       └── stock-table.js # メインJavaScript
├── scripts/               # ユーティリティスクリプト
├── server/                # ローカル開発サーバー
├── tests/                 # テスト
└── serve.py              # サーバー起動スクリプト
```

## コンポーネント

### フロントエンド (`docs/`)

- **index.html**: メインHTMLページ
- **assets/stock-table.js**: メインJavaScript
  - 投資家タブ切り替え
  - 検索・ソート機能
  - 指標データ表示（GitHub Pages では静的JSON、ローカルでは API 使用）
- **assets/data/investors.json**: 投資家保有銘柄データ
- **assets/data/metrics.json**: 指標データ（GitHub Actions で生成）

#### テーブルカラム

各ヘッダーには `title` 属性が設定されており、ホバー時にネイティブのツールチップで日本語の解説が表示される。

| カラム | 説明 | ソートキー |
|--------|------|------------|
| code | 銘柄コード（証券コード） | `code` |
| name | 会社名 | `name` |
| amount | 投資家の保有額（億円、小数点第一位まで表示） | `amount_millions` |
| ratio | 投資家の保有割合（%） | `ratio_percent` |
| ncr | ネットキャッシュレシオ — 現金同等物から有利子負債を引いた額を時価総額で割った値。高いほど財務が安全 | `net_cash_ratio` |
| per | 株価収益率 — 株価を1株当たり利益で割った値。低いほど割安（目安: 15倍以下） | `per` |
| equity | 自己資本比率 — 自己資本 / 総資産 * 100 | `equity_ratio` |
| fcf_y | フリーキャッシュフローイールド — FCFを時価総額で割った値。高いほどキャッシュ創出力が優れている | `fcf_yield_avg` |
| croic | CROIC — FCF / (自己資本 + 有利子負債) | `croic` |
| url | リンク（ソート機能なし） | - |

### バックエンド (`server/`)

- **handler.py**: HTTP リクエストハンドラー
  - `/`: 静的ファイル配信
  - `/api/metrics`: 指標データ API（ローカル開発用）
  - `/open`: ブラウザで URL を開く
- **browser.py**: ブラウザ起動ユーティリティ
- **config.py**: 設定管理

### スクリプト (`scripts/`)

- **generate_metrics.py**: 全銘柄の指標を計算して JSON に保存

### GitHub Actions (`.github/workflows/`)

- **update_metrics.yml**: 毎日日本時間 0:00 に指標データを更新

## データフロー

### ローカル開発環境

```
ブラウザ → HTTP リクエスト → server/handler.py
                                    ↓
                            formula_screening DB
                                    ↓
                            JSON レスポンス
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

- **formula_screening**: 指標計算ロジック
- **stock_db**: 財務データベース
