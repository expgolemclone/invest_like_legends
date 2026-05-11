/**
 * invest_like_legends – app.ts
 *
 * Tab-mode configuration for StockTable.
 * Displays investor holdings with position data and financial metrics.
 */

import type { ColumnDef, MetricThreshold, StockTableConfig } from "@stock-web-ui/runtime";
import type { MetricColSpec } from "@stock-web-ui/columns";

type StockTableApi = {
  init: (config: StockTableConfig) => void;
};

type StockColumnsApi = {
  buildMetricCol: (spec: MetricColSpec, accessor: (row: Record<string, unknown>) => number | null) => ColumnDef;
  codeCol: ColumnDef;
  nameCol: ColumnDef;
  priceCol: ColumnDef;
  peg5yCol: ColumnDef;
  peg5y2fCol: ColumnDef;
  fcfYCol: ColumnDef;
  croicCol: ColumnDef;
  NCR_SPEC: MetricColSpec;
  PER_A_SPEC: MetricColSpec;
  PER_C_SPEC: MetricColSpec;
  PER_N_SPEC: MetricColSpec;
  EQUITY_SPEC: MetricColSpec;
  COMMON_THRESHOLDS: Record<string, MetricThreshold>;
};

function getStockTable(): StockTableApi {
  const runtime: StockTableApi | undefined = (
    globalThis as typeof globalThis & { StockTable?: StockTableApi }
  ).StockTable;
  if (!runtime) {
    throw new Error("Shared StockTable runtime is not loaded.");
  }
  return runtime;
}

function getStockColumns(): StockColumnsApi {
  const cols: StockColumnsApi | undefined = (
    globalThis as typeof globalThis & { StockColumns?: StockColumnsApi }
  ).StockColumns;
  if (!cols) {
    throw new Error("Shared StockColumns module is not loaded.");
  }
  return cols;
}

const StockTable: StockTableApi = getStockTable();
const C: StockColumnsApi = getStockColumns();

/* ------------------------------------------------------------------ */
/*  Metrics accessor (flat access)                                     */
/* ------------------------------------------------------------------ */

function flatAccessor(key: string): (row: Record<string, unknown>) => number | null {
  return (row: Record<string, unknown>): number | null => (row[key] as number) ?? null;
}

/* ------------------------------------------------------------------ */
/*  Column definitions                                                 */
/* ------------------------------------------------------------------ */

const COLUMNS: ColumnDef[] = [
  C.codeCol,
  C.nameCol,
  C.priceCol,
  C.buildMetricCol(C.NCR_SPEC, flatAccessor("net_cash_ratio")),
  C.buildMetricCol(C.PER_A_SPEC, flatAccessor("per_actual")),
  C.buildMetricCol(C.PER_C_SPEC, flatAccessor("per")),
  C.buildMetricCol(C.PER_N_SPEC, flatAccessor("per_next")),
  C.peg5yCol,
  C.peg5y2fCol,
  C.buildMetricCol(C.EQUITY_SPEC, flatAccessor("equity_ratio")),
  C.fcfYCol,
  C.croicCol,
  {
    key: "amount_millions",
    header: "amount",
    type: "num",
    title: "investor holding amount",
    isPosition: true,
    render: (row): string => {
      const v = row.amount_millions as number | null | undefined;
      if (v === null || v === undefined) { return "-"; }
      return (v / 100).toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "儆";
    },
    sortValue: (row): number | null => (row.amount_millions as number) ?? null,
  },
  {
    key: "ratio_percent",
    header: "ratio",
    type: "num",
    title: "investor shares / total shares * 100",
    isPosition: true,
    render: (row): string => {
      const v = row.ratio_percent as number | null | undefined;
      if (v === null || v === undefined) { return "-"; }
      return v + "%";
    },
    sortValue: (row): number | null => (row.ratio_percent as number) ?? null,
  },
];

const METRIC_THRESHOLDS: Record<string, MetricThreshold> = C.COMMON_THRESHOLDS;

const IS_GITHUB_PAGES: boolean = location.hostname === "expgolemclone.github.io";

/* ------------------------------------------------------------------ */
/*  Bootstrap                                                          */
/* ------------------------------------------------------------------ */

function bootstrap(): void {
  StockTable.init({
    defaultTitle: "investor holdings viewer",
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
