/**
 * invest_like_legends – app.js
 *
 * Tab-mode configuration for StockTable.
 * Displays investor holdings with position data and financial metrics.
 */
"use strict";

var COLUMNS = [
    {
        key: "code",
        header: "code",
        type: "code",
        title: "\u9298\u67C4\u30B3\u30FC\u30C9\uFF08\u8A3C\u5238\u30B3\u30FC\u30C9\uFF09",
        render: function (row) { return row.code; },
        sortValue: function (row) { return row.code; },
    },
    {
        key: "name",
        header: "name",
        type: "name",
        title: "\u4F1A\u793E\u540D",
        render: function (row) { return row.name || ""; },
    },
    {
        key: "price",
        header: "price",
        type: "num",
        title: "\u682A\u4FA1\uFF08\u7D42\u5024\uFF09",
        toggleable: true,
        render: function (row) {
            var v = row.price;
            return v !== null && v !== undefined ? v.toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : "-";
        },
        sortValue: function (row) { return row.price != null ? row.price : null; },
    },
    {
        key: "net_cash_ratio",
        header: "ncr",
        type: "num",
        title: "(\u6D41\u52D5\u8CC7\u7523 - \u68DA\u5378\u8CC7\u7523 + \u6709\u4FA1\u8A3C\u5238 * 0.7) / \u6642\u4FA1\u7DCF\u984D",
        toggleable: true,
        render: function (row) {
            var v = row.net_cash_ratio;
            return v !== null && v !== undefined ? v.toFixed(2) : "-";
        },
        sortValue: function (row) { return row.net_cash_ratio != null ? row.net_cash_ratio : null; },
    },
    {
        key: "per",
        header: "per",
        type: "num",
        title: "\u682A\u4FA1 / \u6765\u671F\u4E88\u60F3EPS",
        toggleable: true,
        render: function (row) {
            var v = row.per;
            return v !== null && v !== undefined ? v.toFixed(1) : "-";
        },
        sortValue: function (row) { return row.per != null ? row.per : null; },
    },
    {
        key: "equity_ratio",
        header: "equity",
        type: "num",
        title: "\u81EA\u5DF1\u8CC7\u672C / \u7DCF\u8CC7\u7523 * 100",
        toggleable: true,
        render: function (row) {
            var v = row.equity_ratio;
            return v !== null && v !== undefined ? v.toFixed(1) + "%" : "-";
        },
        sortValue: function (row) { return row.equity_ratio != null ? row.equity_ratio : null; },
    },
    {
        key: "fcf_yield_avg",
        header: "fcf_y",
        type: "num",
        title: "10\u671F\u306E\u5E73\u5747FCF / \u6642\u4FA1\u7DCF\u984D",
        toggleable: true,
        render: function (row) {
            var v = row.fcf_yield_avg;
            if (v === null || v === undefined) { return "-"; }
            return (v * 100).toFixed(2) + "%";
        },
        sortValue: function (row) { return row.fcf_yield_avg != null ? row.fcf_yield_avg * 100 : null; },
    },
    {
        key: "croic",
        header: "croic",
        type: "num",
        title: "FCF / (\u81EA\u5DF1\u8CC7\u672C + \u6709\u5229\u5B50\u8CA0\u50B5)",
        toggleable: true,
        render: function (row) {
            var v = row.croic;
            if (v === null || v === undefined) { return "-"; }
            return (v * 100).toFixed(2) + "%";
        },
        sortValue: function (row) { return row.croic != null ? row.croic * 100 : null; },
    },
    {
        key: "amount_millions",
        header: "amount",
        type: "num",
        title: "\u6295\u8CC7\u5BB6\u306E\u4FDD\u6709\u91D1\u984D",
        isPosition: true,
        render: function (row) {
            var v = row.amount_millions;
            if (v === null || v === undefined) { return "-"; }
            return (v / 100).toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "\u5104";
        },
        sortValue: function (row) { return row.amount_millions != null ? row.amount_millions : null; },
    },
    {
        key: "ratio_percent",
        header: "ratio",
        type: "num",
        title: "\u6295\u8CC7\u5BB6\u306E\u4FDD\u6709\u682A\u6570 / \u767A\u884C\u6E08\u682A\u5F0F\u7DCF\u6570 * 100",
        isPosition: true,
        render: function (row) {
            var v = row.ratio_percent;
            if (v === null || v === undefined) { return "-"; }
            return v + "%";
        },
        sortValue: function (row) { return row.ratio_percent != null ? row.ratio_percent : null; },
    },
];

var METRIC_THRESHOLDS = {
    net_cash_ratio: { good: function (v) { return v > 1; } },
    per: { good: function (v) { return v > 0 && v <= 7; }, bad: function (v) { return v > 7; } },
    equity_ratio: { good: function (v) { return v >= 50; } },
    fcf_yield_avg: { good: function (v) { return v >= 10; } },
    croic: { good: function (v) { return v >= 15; } },
};

var IS_GITHUB_PAGES = location.hostname === "expgolemclone.github.io";

/* ------------------------------------------------------------------ */
/*  Bootstrap                                                         */
/* ------------------------------------------------------------------ */

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
} else {
    bootstrap();
}

function bootstrap() {
    StockTable.init({
        defaultTitle: "\u4FDD\u6709\u9298\u67C4\u30D3\u30E5\u30FC\u30A2 - \u56DB\u5B63\u5831\u30AA\u30F3\u30E9\u30A4\u30F3\u30EA\u30F3\u30AF\u4E00\u89A7",
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
