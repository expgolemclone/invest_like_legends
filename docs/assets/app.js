/**
 * invest_like_legends - app.ts
 *
 * Configures the shared StockTable runtime for:
 * - portfolio
 * - candidates
 * - candidate details
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
const VIEW_SWITCH_STYLE_ID = "invest-like-legends-view-switch-style";
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
const DIVIDEND_YIELD_SPEC = {
    key: "dividend_yield",
    header: "div%",
    decimals: 2,
};
const TOTAL_PAYOUT_RATIO_SPEC = {
    key: "total_payout_ratio",
    header: "payout%",
    decimals: 1,
    suffix: "%",
    title: "(|配当支払額| + |自己株式取得額|) / 時価総額 * 100",
};
const PBR_SPEC = {
    key: "pbr",
    header: "pbr",
    decimals: 2,
};
const FCF_CAGR_SPEC = {
    key: "fcf_cagr",
    header: "fcf_cagr%",
    decimals: 1,
    title: "指数回帰によるFCF年平均成長率（%）",
};
const FCF_CAGR_R2_SPEC = {
    key: "fcf_cagr_r2",
    header: "r2",
    decimals: 2,
    title: "FCF指数回帰トレンドの決定係数（1に近いほど安定成長）",
};
const FCF_SMA_CAGR_SPEC = {
    key: "fcf_sma_cagr",
    header: "sma_cagr%",
    decimals: 1,
    title: "3年移動平均ベースFCF年平均成長率（%）",
};
const STOCK_COLUMNS = [
    C.codeCol,
    C.nameCol,
    C.buildMetricCol(C.NCR_SPEC, flatAccessor("net_cash_ratio")),
    C.fcfYCol,
    C.buildMetricCol(TOTAL_PAYOUT_RATIO_SPEC, flatAccessor("total_payout_ratio")),
    C.peg5yCol,
    C.peg5y2fCol,
    C.buildMetricCol(DIVIDEND_YIELD_SPEC, flatAccessor("dividend_yield")),
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
    C.buildMetricCol(PBR_SPEC, flatAccessor("pbr")),
    C.croicCol,
    C.buildMetricCol(FCF_CAGR_SPEC, flatAccessor("fcf_cagr")),
    C.buildMetricCol(FCF_CAGR_R2_SPEC, flatAccessor("fcf_cagr_r2")),
    C.buildMetricCol(FCF_SMA_CAGR_SPEC, flatAccessor("fcf_sma_cagr")),
    C.priceCol,
    C.buildMetricCol(C.PER_A_SPEC, flatAccessor("per_actual")),
    C.buildMetricCol(C.PER_C_SPEC, flatAccessor("per")),
    C.buildMetricCol(C.PER_N_SPEC, flatAccessor("per_next")),
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
        title: "number of holdings",
        render: (row) => renderCount(row.holding_count),
        sortValue: (row) => toNumber(row.holding_count),
    },
    {
        key: "priced_holding_count",
        header: "priced",
        type: "num",
        title: "number of priced holdings",
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
const METRIC_THRESHOLDS = {
    ...C.COMMON_THRESHOLDS,
    dividend_yield: { good: (v) => v >= 4 },
    pbr: { good: (v) => v < 0.5 },
};
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
function renderViewSwitch(activeView) {
    const tabBar = document.getElementById("tabBar");
    if (!tabBar?.parentElement) {
        return;
    }
    injectViewSwitchStyles();
    const wrapper = document.createElement("div");
    wrapper.className = "view-switch";
    wrapper.setAttribute("aria-label", "表示切替");
    const label = document.createElement("label");
    label.className = "view-switch-control";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = activeView !== "portfolio";
    input.setAttribute("role", "switch");
    input.setAttribute("aria-label", "candidates");
    input.addEventListener("change", () => {
        location.href = input.checked ? buildCandidatesUrl() : buildPortfolioUrl();
    });
    const track = document.createElement("span");
    track.className = "view-switch-track";
    track.setAttribute("aria-hidden", "true");
    const knob = document.createElement("span");
    knob.className = "view-switch-knob";
    track.appendChild(knob);
    const portfolioLabel = document.createElement("span");
    portfolioLabel.className = "view-switch-label";
    portfolioLabel.textContent = "portfolio";
    const candidateLabel = document.createElement("span");
    candidateLabel.className = "view-switch-label";
    candidateLabel.textContent = "candidates";
    label.append(input, track);
    wrapper.append(portfolioLabel, label, candidateLabel);
    if (activeView === "candidate") {
        const backLink = document.createElement("a");
        backLink.className = "view-switch-back-link";
        backLink.href = buildCandidatesUrl();
        backLink.textContent = "candidates";
        wrapper.append(backLink);
    }
    tabBar.parentElement.insertBefore(wrapper, tabBar);
}
function injectViewSwitchStyles() {
    if (document.getElementById(VIEW_SWITCH_STYLE_ID)) {
        return;
    }
    const style = document.createElement("style");
    style.id = VIEW_SWITCH_STYLE_ID;
    style.textContent = `
.view-switch {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  color: var(--muted);
  font-size: 0.84rem;
  font-weight: 600;
}
.view-switch-control {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}
.view-switch-control input {
  position: absolute;
  opacity: 0;
  width: 1px;
  height: 1px;
}
.view-switch-track {
  width: 54px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  padding: 3px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: rgba(22, 33, 62, 0.72);
  transition: background-color 0.2s, border-color 0.2s;
}
.view-switch-knob {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: var(--muted);
  transition: transform 0.2s, background-color 0.2s;
}
.view-switch-control input:checked + .view-switch-track {
  border-color: rgba(91, 155, 255, 0.7);
  background: rgba(91, 155, 255, 0.24);
}
.view-switch-control input:checked + .view-switch-track .view-switch-knob {
  transform: translateX(26px);
  background: var(--accent);
}
.view-switch-control input:focus-visible + .view-switch-track {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}
.view-switch-back-link {
  color: var(--accent);
  text-decoration: none;
  padding-left: 6px;
}
.view-switch-back-link:hover {
  text-decoration: underline;
}
`;
    document.head.appendChild(style);
}
function getCandidatesDataUrl() {
    return IS_GITHUB_PAGES
        ? "assets/data/shareholder_candidates.json"
        : "/api/shareholder-candidates";
}
function getStockPriceMetadataUrl() {
    return IS_GITHUB_PAGES ? "assets/stock-price-meta.json" : "/api/stock-price-meta";
}
/* ------------------------------------------------------------------ */
/*  Bootstrap                                                          */
/* ------------------------------------------------------------------ */
function bootstrapPortfolioView() {
    StockTable.init({
        defaultTitle: "portfolio",
        dataUrl: IS_GITHUB_PAGES ? "assets/data/investors.json" : "/api/portfolio",
        metadataUrl: getStockPriceMetadataUrl(),
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
        defaultTitle: "candidates",
        dataUrl: getCandidatesDataUrl(),
        metadataUrl: getStockPriceMetadataUrl(),
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
            defaultTitle: "candidate",
            dataUrl: detailUrl,
            metadataUrl: getStockPriceMetadataUrl(),
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
    renderViewSwitch(view);
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
