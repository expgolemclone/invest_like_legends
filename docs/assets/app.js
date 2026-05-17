/**
 * invest_like_legends - app.ts
 *
 * Configures the shared StockTable runtime for:
 * - configured investor portfolios
 * - shareholder discovery candidates
 * - candidate portfolio details
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
const IS_GITHUB_PAGES = location.hostname === "expgolemclone.github.io";
/* ------------------------------------------------------------------ */
/*  Shared rendering helpers                                           */
/* ------------------------------------------------------------------ */
function flatAccessor(key) {
    return (row) => toNumber(row[key]);
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
function renderAmountMillions(value) {
    const amount = toNumber(value);
    if (amount === null) {
        return "-";
    }
    return (amount / 100).toLocaleString("ja-JP", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
    }) + "億";
}
function renderCount(value) {
    const count = toNumber(value);
    return count === null ? "-" : count.toLocaleString("ja-JP");
}
function toNumber(value) {
    return typeof value === "number" && Number.isFinite(value) ? value : null;
}
function escapeHtml(value) {
    return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}
/* ------------------------------------------------------------------ */
/*  Column definitions                                                 */
/* ------------------------------------------------------------------ */
const STOCK_COLUMNS = [
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
        render: (row) => renderAmountMillions(row.amount_millions),
        sortValue: (row) => toNumber(row.amount_millions),
    },
    {
        key: "ratio_percent",
        header: "ratio",
        type: "num",
        title: "investor shares / total shares * 100",
        isPosition: true,
        render: (row) => {
            const value = toNumber(row.ratio_percent);
            return value === null ? "-" : value + "%";
        },
        sortValue: (row) => toNumber(row.ratio_percent),
    },
];
const CANDIDATE_COLUMNS = [
    {
        key: "name",
        header: "shareholder",
        type: "name",
        title: "株主名",
        render: (row) => {
            const id = String(row.id ?? "");
            const name = String(row.name ?? "");
            if (!id || !name) {
                return "-";
            }
            return '<a href="' + escapeHtml(buildCandidateDetailUrl(id)) + '">' + escapeHtml(name) + "</a>";
        },
    },
    {
        key: "total_amount_millions",
        header: "amount",
        type: "num",
        title: "推定保有総額",
        isPosition: true,
        render: (row) => renderAmountMillions(row.total_amount_millions),
        sortValue: (row) => toNumber(row.total_amount_millions),
    },
    {
        key: "holding_count",
        header: "holdings",
        type: "num",
        title: "保有銘柄数",
        render: (row) => renderCount(row.holding_count),
        sortValue: (row) => toNumber(row.holding_count),
    },
    {
        key: "priced_holding_count",
        header: "priced",
        type: "num",
        title: "保有額を計算できた銘柄数",
        toggleable: true,
        render: (row) => renderCount(row.priced_holding_count),
        sortValue: (row) => toNumber(row.priced_holding_count),
    },
    {
        key: "aliases",
        header: "aliases",
        type: "text",
        title: "同一候補に集約した株主名",
        toggleable: true,
        render: (row) => {
            const aliases = row.aliases;
            if (!Array.isArray(aliases)) {
                return "-";
            }
            return escapeHtml(aliases
                .filter((alias) => typeof alias === "string")
                .join(" / "));
        },
    },
];
const METRIC_THRESHOLDS = C.COMMON_THRESHOLDS;
/* ------------------------------------------------------------------ */
/*  Navigation and view helpers                                        */
/* ------------------------------------------------------------------ */
function resolveView() {
    const view = new URLSearchParams(location.search).get("view");
    if (view === "candidates" || view === "candidate") {
        return view;
    }
    return "portfolio";
}
function buildPortfolioUrl() {
    return location.pathname;
}
function buildCandidatesUrl() {
    return buildViewUrl("candidates");
}
function buildCandidateDetailUrl(candidateId) {
    return buildViewUrl("candidate", candidateId);
}
function buildViewUrl(view, candidateId) {
    const params = new URLSearchParams();
    params.set("view", view);
    if (candidateId) {
        params.set("id", candidateId);
    }
    return location.pathname + "?" + params.toString();
}
function renderModeNavigation(activeView) {
    const tabBar = document.getElementById("tabBar");
    if (!tabBar?.parentElement) {
        return;
    }
    const nav = document.createElement("nav");
    nav.className = "tab-bar";
    nav.setAttribute("aria-label", "表示切替");
    const portfolioButton = createNavigationButton("保有銘柄", buildPortfolioUrl(), activeView === "portfolio");
    const candidateButton = createNavigationButton("候補発掘", buildCandidatesUrl(), activeView !== "portfolio");
    nav.append(portfolioButton, candidateButton);
    tabBar.parentElement.insertBefore(nav, tabBar);
}
function createNavigationButton(label, href, active) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tab" + (active ? " active" : "");
    button.textContent = label;
    button.setAttribute("aria-current", active ? "page" : "false");
    button.addEventListener("click", () => {
        location.href = href;
    });
    return button;
}
function getCandidatesDataUrl() {
    return IS_GITHUB_PAGES
        ? "assets/data/shareholder_candidates.json"
        : "/api/shareholder-candidates";
}
/* ------------------------------------------------------------------ */
/*  Bootstrap                                                          */
/* ------------------------------------------------------------------ */
function bootstrapPortfolioView() {
    StockTable.init({
        defaultTitle: "investor holdings viewer",
        dataUrl: IS_GITHUB_PAGES ? "assets/data/investors.json" : "/api/portfolio",
        columns: STOCK_COLUMNS,
        metricThresholds: METRIC_THRESHOLDS,
        defaultSortKey: "net_cash_ratio",
        defaultSortDirection: "desc",
        tabMode: true,
        defaultTabKey: "watch",
        githubPages: IS_GITHUB_PAGES,
    });
}
function bootstrapCandidateListView() {
    StockTable.init({
        defaultTitle: "shareholder candidates",
        dataUrl: getCandidatesDataUrl(),
        columns: CANDIDATE_COLUMNS,
        metricThresholds: {},
        defaultSortKey: "total_amount_millions",
        defaultSortDirection: "desc",
        githubPages: IS_GITHUB_PAGES,
    });
}
async function bootstrapCandidateDetailView() {
    const candidateId = new URLSearchParams(location.search).get("id");
    if (!candidateId) {
        location.replace(buildCandidatesUrl());
        return;
    }
    try {
        const response = await fetch(getCandidatesDataUrl(), { cache: "no-store" });
        if (!response.ok) {
            throw new Error("HTTP " + response.status);
        }
        const raw = await response.json();
        if (!Array.isArray(raw)) {
            throw new Error("Candidate data must be an array.");
        }
        const candidate = raw.find((entry) => isShareholderCandidate(entry) && entry.id === candidateId);
        if (!candidate) {
            throw new Error("Candidate not found.");
        }
        const payload = {
            [candidate.id]: {
                name: candidate.name,
                stocks: candidate.stocks,
            },
        };
        const detailUrl = URL.createObjectURL(new Blob([JSON.stringify(payload)], { type: "application/json" }));
        StockTable.init({
            defaultTitle: "shareholder candidate holdings viewer",
            dataUrl: detailUrl,
            columns: STOCK_COLUMNS,
            metricThresholds: METRIC_THRESHOLDS,
            defaultSortKey: "net_cash_ratio",
            defaultSortDirection: "desc",
            tabMode: true,
            defaultTabKey: candidate.id,
            githubPages: IS_GITHUB_PAGES,
        });
    }
    catch (error) {
        console.error(error);
        renderStandaloneError("候補データを読み込めませんでした。");
    }
}
function isShareholderCandidate(value) {
    if (!value || typeof value !== "object") {
        return false;
    }
    const candidate = value;
    return (typeof candidate.id === "string"
        && typeof candidate.name === "string"
        && Array.isArray(candidate.aliases)
        && typeof candidate.holding_count === "number"
        && typeof candidate.priced_holding_count === "number"
        && typeof candidate.total_amount_millions === "number"
        && Array.isArray(candidate.stocks));
}
function renderStandaloneError(message) {
    const status = document.getElementById("statusMessage");
    const tbody = document.getElementById("tbody");
    const tabBar = document.getElementById("tabBar");
    const toggleBar = document.getElementById("toggleBar");
    if (status) {
        status.textContent = message;
    }
    if (tabBar) {
        tabBar.innerHTML = "";
    }
    if (toggleBar) {
        toggleBar.innerHTML = "";
    }
    if (tbody) {
        tbody.innerHTML = '<tr><td class="table-message" colspan="1">' + escapeHtml(message) + "</td></tr>";
    }
}
async function bootstrap() {
    const view = resolveView();
    renderModeNavigation(view);
    if (view === "candidates") {
        bootstrapCandidateListView();
        return;
    }
    if (view === "candidate") {
        await bootstrapCandidateDetailView();
        return;
    }
    bootstrapPortfolioView();
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
        void bootstrap();
    });
}
else {
    void bootstrap();
}
export {};
