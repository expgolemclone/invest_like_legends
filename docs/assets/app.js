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
const StockTable = getStockTable();
/* ------------------------------------------------------------------ */
/*  Column definitions                                                 */
/* ------------------------------------------------------------------ */
const COLUMNS = [
    {
        key: "code",
        header: "code",
        type: "code",
        title: "銘柄コード（証券コード）",
        render: (row) => String(row.code ?? ""),
        stockLink: "monex",
    },
    {
        key: "name",
        header: "name",
        type: "name",
        title: "会社名",
        render: (row) => String(row.name ?? ""),
        stockLink: "yazi",
    },
    {
        key: "price",
        header: "price",
        type: "num",
        title: "株価（終値）",
        toggleable: true,
        render: (row) => {
            const v = row.price;
            return v !== null && v !== undefined
                ? v.toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 })
                : "-";
        },
        sortValue: (row) => row.price ?? null,
    },
    {
        key: "net_cash_ratio",
        header: "ncr",
        type: "num",
        title: "(流動資産 - 棚卸資産 + 有価証券 * 0.7) / 時価総額",
        toggleable: true,
        render: (row) => {
            const v = row.net_cash_ratio;
            return v !== null && v !== undefined ? v.toFixed(2) : "-";
        },
        sortValue: (row) => row.net_cash_ratio ?? null,
    },
    {
        key: "per",
        header: "per",
        type: "num",
        title: "株価 / 来期予想EPS",
        toggleable: true,
        render: (row) => {
            const v = row.per;
            return v !== null && v !== undefined ? v.toFixed(1) : "-";
        },
        sortValue: (row) => row.per ?? null,
    },
    {
        key: "equity_ratio",
        header: "equity",
        type: "num",
        title: "自己資本 / 総資産 * 100",
        toggleable: true,
        render: (row) => {
            const v = row.equity_ratio;
            return v !== null && v !== undefined ? v.toFixed(1) + "%" : "-";
        },
        sortValue: (row) => row.equity_ratio ?? null,
    },
    {
        key: "fcf_yield_avg",
        header: "fcf_y",
        type: "num",
        title: "10期の平均FCF / 時価総額",
        toggleable: true,
        render: (row) => {
            const v = row.fcf_yield_avg;
            if (v === null || v === undefined) {
                return "-";
            }
            return (v * 100).toFixed(2) + "%";
        },
        sortValue: (row) => {
            const v = row.fcf_yield_avg;
            return v != null ? v * 100 : null;
        },
    },
    {
        key: "croic",
        header: "croic",
        type: "num",
        title: "FCF / (自己資本 + 有利子負債)",
        toggleable: true,
        render: (row) => {
            const v = row.croic;
            if (v === null || v === undefined) {
                return "-";
            }
            return (v * 100).toFixed(2) + "%";
        },
        sortValue: (row) => {
            const v = row.croic;
            return v != null ? v * 100 : null;
        },
    },
    {
        key: "amount_millions",
        header: "amount",
        type: "num",
        title: "投資家の保有金額",
        isPosition: true,
        render: (row) => {
            const v = row.amount_millions;
            if (v === null || v === undefined) {
                return "-";
            }
            return (v / 100).toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "億";
        },
        sortValue: (row) => row.amount_millions ?? null,
    },
    {
        key: "ratio_percent",
        header: "ratio",
        type: "num",
        title: "投資家の保有株数 / 発行済株式総数 * 100",
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
const METRIC_THRESHOLDS = {
    net_cash_ratio: { good: (v) => v > 1 },
    per: { good: (v) => v > 0 && v <= 7, bad: (v) => v > 7 },
    equity_ratio: { good: (v) => v >= 50 },
    fcf_yield_avg: { good: (v) => v >= 10 },
    croic: { good: (v) => v >= 15 },
};
const IS_GITHUB_PAGES = location.hostname === "expgolemclone.github.io";
/* ------------------------------------------------------------------ */
/*  Bootstrap                                                          */
/* ------------------------------------------------------------------ */
function bootstrap() {
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
}
else {
    bootstrap();
}
export {};
