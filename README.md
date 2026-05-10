# invest_like_legends

投資家やファンドごとの保有銘柄を、大株主データと財務指標つきで見るための Web アプリです。

公開ページ: <https://expgolemclone.github.io/invest_like_legends/>

## できること

- `config/investors.json` に定義した投資家ごとの保有銘柄タブを表示する
- `config/watch_codes.txt` に並べた監視銘柄を `watch` タブに表示する
- 株価、ネットキャッシュ比率、今期予想 PER、来期予想 PER、自己資本比率、平均 FCF 利回り、CROIC を同じテーブルで確認する
- 投資家の保有金額と保有割合を銘柄ごとに表示する
- 銘柄コードから Monex、株価から四季報オンライン、会社名からローカルの四季報 PDF へ移動する

外部リンクを使う場合は、先にブラウザで以下へログインしてください。

- [東洋経済デジタルコンテンツ・ライブラリー](https://id.toyokeizai.net/dcl/)
- [Monex](https://mxp2.monex.co.jp/pc/ITS/login/LoginIDPassword.jsp)

## 仕組み

`docs/` は GitHub Pages で配信する静的サイトです。表示用データの `docs/assets/data/investors.json` は手で編集せず、`scripts/enrich_investors.py` で再生成します。

データ生成では以下を使います。

- `config/investors.json`: 投資家タブのキーと表示名
- `config/watch_codes.txt`: 監視銘柄タブの銘柄コード
- `../japan_company_handbook/data/stock_performance.db`: 大株主データ
- `stock_db`: 会社名 DB
- `formula_screening`: 財務指標の計算
- `stock_web_ui`: 共通テーブル UI とローカルサーバー

PER は `formula_screening` が `stock_db` の四季報予想 (`source=shikiho`) から計算した値を使い、今期予想 PER と来期予想 PER を分けて表示します。

より詳しい構成は [ARCHITECTURE.md](ARCHITECTURE.md) を参照してください。

## 前提

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

DB の場所を標準構成から変えたい場合は、環境変数で指定できます。

```powershell
$env:STOCKS_DB_PATH="C:\path\to\stocks.db"
$env:HANDBOOK_DB_PATH="C:\path\to\stock_performance.db"
```

## セットアップ

```powershell
uv sync
npm install
```

## ローカルで見る

```powershell
uv run python serve.py
```

ローカルサーバーでは `/api/portfolio` が毎回データを組み立てます。生成済みの `docs/assets/data/investors.json` ではなく、手元の DB と設定を直接見に行くため、設定や DB の確認に向いています。

## 静的データを更新する

```powershell
uv run python scripts/enrich_investors.py
```

このコマンドは `docs/assets/data/investors.json` を完全に再生成します。公開ページではこの JSON が読み込まれます。

## TypeScript を更新する

`src_ts/app.ts` を変更したら、生成済み JavaScript も更新します。

```powershell
npx tsc
```

出力先は `docs/assets/app.js` です。

## テスト

```powershell
uv run pytest
```

## 投資家や監視銘柄を追加する

投資家タブを追加する場合は `config/investors.json` にキーと表示名を追加します。保有銘柄は大株主 DB から自動で照合されるため、このファイルに銘柄一覧は書きません。

監視銘柄を追加する場合は `config/watch_codes.txt` に銘柄コードを 1 行ずつ追加します。

設定を変えた後は、ローカル確認なら `uv run python serve.py`、公開用 JSON を更新するなら `uv run python scripts/enrich_investors.py` を使います。

## 自動更新

GitHub Actions の `Update Investors Data` が毎日 0:00 JST に実行され、`docs/assets/data/investors.json` を再生成して push します。手動実行は GitHub Actions の `workflow_dispatch` から行えます。
