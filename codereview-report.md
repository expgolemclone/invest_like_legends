# コードレビュー監査メモ

作成日: 2026-05-18

## 指摘

### High: `STOCKS_DB_PATH` を指定しても指標だけ別 DB を読む

- `ARCHITECTURE.md` は `STOCKS_DB_PATH` で DB を差し替えられると説明しているが、`investor_data.resolve_stocks_db_path()` だけがこの環境変数を見ており、指標計算は `formula_screening.web.compute_all_stock_metrics()` 内で `stock_db.paths.STOCKS_DB_PATH` を直接使っている。
- 再現:

```text
$ STOCKS_DB_PATH=/tmp/alt-stocks.db uv run python ...
resolve_stocks_db_path()                  -> /tmp/alt-stocks.db
formula_screening 側の STOCKS_DB_PATH    -> /home/exp/projects/stock_db/var/db/stocks.db
```

- そのため、会社名と Stooq 更新は差し替え先 DB、PER や価格などの指標は既定 DB から取得される。ローカル確認や一時 DB を使った再生成で、同じ JSON 内に別 DB 由来の値が混在する。
- 該当箇所:
  - `ARCHITECTURE.md:46-50`
  - `investor_data.py:345-355`
  - `formula_screening/src/formula_screening/web.py:23-44`
- 推奨修正:
  - 指標 API に DB パスを渡せる公開インターフェースを用意し、この repo では `resolve_stocks_db_path()` の結果を一貫して渡す。
  - 代替として `STOCKS_DB_PATH` を廃止し、`stock_db` が既に使う `STOCK_DB_VAR_DIR` に一本化するなら、ドキュメントと呼び出し側を同時に揃える。
  - 環境変数差し替え時に会社名・指標・更新対象 DB が同じパスになる統合テストを追加する。

### Medium: ローカル API が毎リクエスト全量再計算する

- `serve.main()` は起動時に `stock_names`、`metrics_map`、`shareholder_rows` を読み込んで公開 JSON を作っているが、API ルートはその値を再利用せず、毎回 `build_investors_document()` / `build_shareholder_candidates_document()` を引数なしで呼び直している。
- 現在のデータ量では、同一プロセス内の単発実行でも `portfolio` 生成に約 `9.03s`、`candidates` 生成に約 `3.57s` かかった。ブラウザ更新や view 切替のたびに同じ DB 読み込みと指標計算が再実行される。
- 該当箇所:
  - `serve.py:35-50`
  - `serve.py:77-100`
- 影響:
  - ローカル UI の初回表示後も API 応答が秒単位で遅くなる。
  - 起動時に既に払った計算コストをリクエストごとに再度払っており、負荷の増え方がデータ量に比例する。
- 推奨修正:
  - 起動時に作った依存データを route handler に閉じ込めて再利用する。
  - 「最新 DB を毎回読む」必要があるなら、手動リロード用の明示的な更新経路を分け、通常表示はキャッシュ済み payload を返す。
  - API ルートのテストに、起動時にロードした依存を再利用することを検証するケースを追加する。

### Medium: candidate 詳細表示が 5.3 MB の全候補 JSON を毎回読む

- candidate 詳細は 1 件だけ表示すればよいが、`bootstrapCandidateDetailView()` は `shareholder_candidates.json` 全体を `fetch()` してから `id` で 1 件を探している。
- 現在の生成物は `1000` 候補・`9176` 保有行で `5.3 MB`。一覧から詳細へ通常リンク遷移するとページ全体が再読込されるため、詳細 1 件を見るたびにこの payload を再取得・再 parse する。
- 該当箇所:
  - `src_ts/app.ts:435-467`
  - `docs/assets/data/shareholder_candidates.json`
- 影響:
  - GitHub Pages 上の詳細画面が回線速度に強く依存し、候補数を増やすほど悪化する。
  - 将来 `limit` をさらに増やすと、詳細画面の表示コストまで一緒に膨らむ。
- 推奨修正:
  - 候補一覧と詳細 payload を分割する。例: 一覧 JSON には summary のみ置き、詳細は candidate ごとの JSON か `id -> detail` の別ファイルにする。
  - 既存 URL 形状を維持するなら、ビルド時に detail 用索引を生成する。
  - フロントエンドに candidate 一覧 / 詳細のデータロードを検証するテストを追加する。

## 確認した範囲

- この repo:
  - `investor_data.py`
  - `serve.py`
  - `scripts/enrich_investors.py`
  - `src_ts/app.ts`
  - `docs/index.html`
  - `.github/workflows/update_investors.yml`
  - `tests/`
  - `config/`
  - 生成済み JSON
- 接続点:
  - `formula_screening.web.compute_all_stock_metrics()`
  - `stock_db` の DB パス解決、Stooq 更新 API、株式名 API
  - `stock_web_ui` の `StockTable` 公開インターフェース
  - `japan_company_handbook` の `major_shareholders` スキーマ

## 実行した確認

- `uv run pytest`
  - `11 passed`
- `npm run typecheck`
  - 成功
- `STOCKS_DB_PATH` 差し替え時の実パス確認
- `major_shareholders` の行数と NULL 有無の確認
  - `38303` 行、`shares` / `ratio_pct` の NULL は現時点で `0`
- 生成済み JSON の大きさ確認
  - `investors.json`: `256K`
  - `shareholder_candidates.json`: `5.3M`

## 残リスク

- ブラウザ操作の自動テストがないため、`portfolio` / `candidates` / `candidate` の画面遷移、shared runtime との実ブラウザ互換性は目視確認に依存している。
- `shareholder` 名寄せは仕様として prefix fallback を持つため、将来 DB 側に同姓の別人が増えた場合の誤結合リスクは残る。現行生成物では重大な誤結合を確認していないが、継続的な検出テストはない。
- この repo 直下には `RULES.md` が存在しなかったため、レビュー時は `AGENTS.md` と隣接 repo の `RULES.md` を参照した。
