/**
 * invest_like_legends – app.ts
 *
 * Tab-mode configuration for StockTable.
 * Displays investor holdings with position data and financial metrics.
 */
function getStockTable() {
    const runtime = globalThis.StockTable;
    if (!runtime) {
        throw new Error("Shared StockTable runtime is not loaded.");
    }
    return runtime;
}
function getStockColumns() {
    const cols = globalThis.StockColumns;
    if (!cols) {
        throw new Error("Shared StockColumns module is not loaded.");
    }
    return cols;
}
const StockTable = getStockTable();
const C = getStockColumns();
/* ------------------------------------------------------------------ */
/*  Metrics accessor (flat access)                                     */
/* ------------------------------------------------------------------ */
function flatAccessor(key) {
    return (row) => row[key] ?? null;
}
function renderPreferredShares(row) {
    if (row.has_preferred_shares === true) {
        return "yes";
    }
    if (row.has_preferred_shares === false) {
        return "no";
    }
    return "-";
}
function preferredSharesSortValue(row) {
    if (row.has_preferred_shares === true) {
        return 1;
    }
    if (row.has_preferred_shares === false) {
        return 0;
    }
    return null;
}
/* ------------------------------------------------------------------ */
/*  Column definitions                                                 */
/* ------------------------------------------------------------------ */
const COLUMNS = [
    C.codeCol,
    C.nameCol,
    C.priceCol,
    C.buildMetricCol(C.NCR_SPEC, flatAccessor("net_cash_ratio")),
    C.buildMetricCol(C.PER_A_SPEC, flatAccessor("per_actual")),
    C.buildMetricCol(C.PER_C_SPEC, flatAccessor("per")),
    C.buildMetricCol(C.PER_N_SPEC, flatAccessor("per_next")),
    C.peg5yCol,
    C.peg5y2fCol,
    {
        key: "has_preferred_shares",
        header: "pref",
        type: "text",
        title: "優先株",
        toggleable: true,
        render: renderPreferredShares,
        sortValue: preferredSharesSortValue,
    },
    C.buildMetricCol(C.EQUITY_SPEC, flatAccessor("equity_ratio")),
    C.fcfYCol,
    C.croicCol,
    {
        key: "amount_millions",
        header: "amount",
        type: "num",
        title: "investor holding amount",
        isPosition: true,
        render: (row) => {
            const v = row.amount_millions;
            if (v === null || v === undefined) {
                return "-";
            }
            return (v / 100).toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "儆";
        },
        sortValue: (row) => row.amount_millions ?? null,
    },
    {
        key: "ratio_percent",
        header: "ratio",
        type: "num",
        title: "investor shares / total shares * 100",
        isPosition: true,
        render: (row) => {
            const v = row.ratio_percent;
            if (v === null || v === undefined) {
                return "-";
            }
            return v + "%";
        },
        sortValue: (row) => row.ratio_percent ?? null,
    },
];
const METRIC_THRESHOLDS = C.COMMON_THRESHOLDS;
const IS_GITHUB_PAGES = location.hostname === "expgolemclone.github.io";
/* ------------------------------------------------------------------ */
/*  Bootstrap                                                          */
/* ------------------------------------------------------------------ */
function bootstrap() {
    StockTable.init({
        defaultTitle: "investor holdings viewer",
        dataUrl: IS_GITHUB_PAGES ? "assets/data/investors.json" : "/api/portfolio",
        columns: COLUMNS,
        metricThresholds: METRIC_THRESHOLDS,
        defaultSortKey: "net_cash_ratio",
        defaultSortDirection: "desc",
        tabMode: true,
        defaultTabKey: "watch",
        githubPages: IS_GITHUB_PAGES,
    });
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
}
else {
    bootstrap();
}
export {};
