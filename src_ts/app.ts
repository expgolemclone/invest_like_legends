/**
 * invest_like_legends – app.ts
 *
 * Tab-mode configuration for StockTable.
 * Displays investor holdings with position data and financial metrics.
 */

import { StockTable } from "./stock-table.js";
import type { ColumnDef, MetricThreshold } from "./stock-table.js";

function buildMonexUrl(code: string): string {
  return "https://monex.ifis.co.jp/index.php?sa=report_zaimu&bcode=" + encodeURIComponent(code);
}

function buildShikihoUrl(code: string): string {
  return "https://shikiho.toyokeizai.net/stocks/" + encodeURIComponent(code) + "/shikiho";
}

function buildYaziUrl(code: string): string {
  return "/open-yazi/" + encodeURIComponent(code);
}

/* ------------------------------------------------------------------ */
/*  Column definitions                                                 */
/* ------------------------------------------------------------------ */

const COLUMNS: ColumnDef[] = [
  {
    key: "code",
    header: "code",
    type: "code",
    title: "銘柄コード（証券コード）",
    render: (row): string => String(row.code ?? ""),
    linkHref: (row): string => buildMonexUrl(String(row.code ?? "")),
    linkMode: "browser",
    browserKey: "monex",
  },
  {
    key: "name",
    header: "name",
    type: "name",
    title: "会社名",
    render: (row): string => String(row.name ?? ""),
    linkHref: (row, context): string => {
      const code: string = String(row.code ?? "");
      return context.githubPages ? buildShikihoUrl(code) : buildYaziUrl(code);
    },
    linkMode: (_row, context): "direct" | "yazi" => context.githubPages ? "direct" : "yazi",
  },
  {
    key: "price",
    header: "price",
    type: "num",
    title: "株価（終値）",
    toggleable: true,
    render: (row): string => {
      const v = row.price as number | null | undefined;
      return v !== null && v !== undefined
        ? v.toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 })
        : "-";
    },
    sortValue: (row): number | null => (row.price as number) ?? null,
  },
  {
    key: "net_cash_ratio",
    header: "ncr",
    type: "num",
    title: "(流動資産 - 棚卸資産 + 有価証券 * 0.7) / 時価総額",
    toggleable: true,
    render: (row): string => {
      const v = row.net_cash_ratio as number | null | undefined;
      return v !== null && v !== undefined ? v.toFixed(2) : "-";
    },
    sortValue: (row): number | null => (row.net_cash_ratio as number) ?? null,
  },
  {
    key: "per",
    header: "per",
    type: "num",
    title: "株価 / 来期予想EPS",
    toggleable: true,
    render: (row): string => {
      const v = row.per as number | null | undefined;
      return v !== null && v !== undefined ? v.toFixed(1) : "-";
    },
    sortValue: (row): number | null => (row.per as number) ?? null,
  },
  {
    key: "equity_ratio",
    header: "equity",
    type: "num",
    title: "自己資本 / 総資産 * 100",
    toggleable: true,
    render: (row): string => {
      const v = row.equity_ratio as number | null | undefined;
      return v !== null && v !== undefined ? v.toFixed(1) + "%" : "-";
    },
    sortValue: (row): number | null => (row.equity_ratio as number) ?? null,
  },
  {
    key: "fcf_yield_avg",
    header: "fcf_y",
    type: "num",
    title: "10期の平均FCF / 時価総額",
    toggleable: true,
    render: (row): string => {
      const v = row.fcf_yield_avg as number | null | undefined;
      if (v === null || v === undefined) { return "-"; }
      return (v * 100).toFixed(2) + "%";
    },
    sortValue: (row): number | null => {
      const v = row.fcf_yield_avg as number | null | undefined;
      return v != null ? v * 100 : null;
    },
  },
  {
    key: "croic",
    header: "croic",
    type: "num",
    title: "FCF / (自己資本 + 有利子負債)",
    toggleable: true,
    render: (row): string => {
      const v = row.croic as number | null | undefined;
      if (v === null || v === undefined) { return "-"; }
      return (v * 100).toFixed(2) + "%";
    },
    sortValue: (row): number | null => {
      const v = row.croic as number | null | undefined;
      return v != null ? v * 100 : null;
    },
  },
  {
    key: "amount_millions",
    header: "amount",
    type: "num",
    title: "投資家の保有金額",
    isPosition: true,
    render: (row): string => {
      const v = row.amount_millions as number | null | undefined;
      if (v === null || v === undefined) { return "-"; }
      return (v / 100).toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "億";
    },
    sortValue: (row): number | null => (row.amount_millions as number) ?? null,
  },
  {
    key: "ratio_percent",
    header: "ratio",
    type: "num",
    title: "投資家の保有株数 / 発行済株式総数 * 100",
    isPosition: true,
    render: (row): string => {
      const v = row.ratio_percent as number | null | undefined;
      if (v === null || v === undefined) { return "-"; }
      return v + "%";
    },
    sortValue: (row): number | null => (row.ratio_percent as number) ?? null,
  },
];

const METRIC_THRESHOLDS: Record<string, MetricThreshold> = {
  net_cash_ratio: { good: (v): boolean => v > 1 },
  per: { good: (v): boolean => v > 0 && v <= 7, bad: (v): boolean => v > 7 },
  equity_ratio: { good: (v): boolean => v >= 50 },
  fcf_yield_avg: { good: (v): boolean => v >= 10 },
  croic: { good: (v): boolean => v >= 15 },
};

const IS_GITHUB_PAGES: boolean = location.hostname === "expgolemclone.github.io";

/* ------------------------------------------------------------------ */
/*  Bootstrap                                                          */
/* ------------------------------------------------------------------ */

function bootstrap(): void {
  StockTable.init({
    defaultTitle: "保有銘柄ビューア - 四季報オンラインリンク一覧",
    dataUrl: IS_GITHUB_PAGES ? "assets/data/investors.json" : "/api/portfolio",
    columns: COLUMNS,
    metricThresholds: METRIC_THRESHOLDS,
    defaultSortKey: "code",
    defaultSortDirection: "asc",
    tabMode: true,
    defaultTabKey: "watch",
    githubPages: IS_GITHUB_PAGES,
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrap);
} else {
  bootstrap();
}
