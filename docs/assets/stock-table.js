/** @typedef {string} InvestorKey */
/** @typedef {"code" | "name" | "amount_millions" | "ratio_percent" | "net_cash_ratio" | "per" | "equity_ratio" | "fcf_yield_avg" | "croic"} SortColumn */
/** @typedef {"asc" | "desc"} SortDirection */
/**
 * @typedef {Object} InvestorStock
 * @property {string} code
 * @property {string} name
 * @property {number | null} amount_millions
 * @property {number} ratio_percent
 * @property {number | null} [net_cash_ratio]
 * @property {number | null} [per]
 * @property {number | null} [equity_ratio]
 * @property {number | null} [fcf_yield_avg]
 * @property {number | null} [croic]
 */
/**
 * @typedef {Object} StockMetrics
 * @property {number | null} net_cash_ratio
 * @property {number | null} per
 * @property {number | null} equity_ratio
 * @property {number | null} fcf_yield_avg
 * @property {number | null} croic
 * @property {number | null} market_cap
 */
/**
 * @typedef {Object} InvestorDataset
 * @property {string} name
 * @property {InvestorStock[]} stocks
 */
/** @typedef {Object.<string, InvestorDataset>} InvestorsDocument */

const DEFAULT_TITLE = "保有銘柄ビューア - 四季報オンラインリンク一覧";
const DEFAULT_INVESTOR_KEY = "watch";
const DEFAULT_SORT_COLUMN = "code";
const DEFAULT_SORT_DIRECTION = "asc";
const INVESTOR_DATA_URL = "assets/data/investors.json?v=20260501-yoshida";
const METRICS_DATA_URL = "assets/data/metrics.json";
const IS_GITHUB_PAGES = location.hostname === "expgolemclone.github.io";
const ASC_ARROW = "▲";
const DESC_ARROW = "▼";
const INACTIVE_ARROW = "▽";
const SORTABLE_COLUMNS = ["code", "name", "amount_millions", "ratio_percent", "net_cash_ratio", "per", "equity_ratio", "fcf_yield_avg", "croic"];
const TOGGLEABLE_COLUMNS = ["net_cash_ratio", "per", "equity_ratio", "fcf_yield_avg", "croic"];

/** @type {Object.<string, {good?: function(number): boolean, bad?: function(number): boolean}>} */
const METRIC_THRESHOLDS = {
  net_cash_ratio: { good: function(v) { return v > 1; } },
  per: { good: function(v) { return v > 0 && v <= 7; }, bad: function(v) { return v > 7; } },
  equity_ratio: { good: function(v) { return v >= 50; } },
  fcf_yield_avg: { good: function(v) { return v >= 10; } },
  croic: { good: function(v) { return v >= 15; } },
};
const HIDDEN_COLUMNS_KEY = "hiddenColumns";

/** @type {{
 *   investors: InvestorsDocument | null,
 *   currentInvestorKey: InvestorKey,
 *   sortColumn: SortColumn,
 *   sortDirection: SortDirection,
 *   hiddenColumns: Set<string>,
 *   isLoading: boolean,
 *   errorMessage: string,
 *   metricsCache: Object.<string, StockMetrics>,
 *   metricsLoading: boolean
 * }}
 */
const state = {
  investors: null,
  currentInvestorKey: DEFAULT_INVESTOR_KEY,
  sortColumn: DEFAULT_SORT_COLUMN,
  sortDirection: DEFAULT_SORT_DIRECTION,
  hiddenColumns: loadHiddenColumns(),
  isLoading: true,
  errorMessage: "",
  metricsCache: {},
  metricsLoading: false,
};

const elements = {
  tabBar: /** @type {HTMLElement} */ (document.getElementById("investorTabs")),
  statusMessage: /** @type {HTMLElement} */ (document.getElementById("statusMessage")),
  tbody: /** @type {HTMLElement} */ (document.getElementById("tbody")),
  sortButtons: /** @type {HTMLButtonElement[]} */ (Array.from(document.querySelectorAll("[data-sort-column]"))),
  toggleChips: /** @type {HTMLButtonElement[]} */ (Array.from(document.querySelectorAll("[data-toggle-column]"))),
};

// Open desktop-targeted links through the local helper server when available.
document.addEventListener("click", function(/** @type {MouseEvent} */ event) {
  const link = /** @type {HTMLAnchorElement | null} */ (event.target instanceof Element ? event.target.closest("a[data-browser]") : null);
  if (!link) {
    return;
  }

  const browserKey = link.getAttribute("data-browser") || "";
  const url = link.href;

  event.preventDefault();
  fetch("/open?browser=" + encodeURIComponent(browserKey) + "&url=" + encodeURIComponent(url))
    .then(function(/** @type {Response} */ response) {
      if (!response.ok) {
        window.open(url, "_blank", "noopener");
      }
    })
    .catch(function() {
      window.open(url, "_blank", "noopener");
    });
});

/** @returns {Set<string>} */
function loadHiddenColumns() {
  try {
    var stored = localStorage.getItem(HIDDEN_COLUMNS_KEY);
    if (stored) {
      var parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) {
        return new Set(parsed.filter(function(c) { return TOGGLEABLE_COLUMNS.includes(c); }));
      }
    }
  } catch (_e) {
    // ignore
  }
  return new Set();
}

/** @param {Set<string>} columns */
function saveHiddenColumns(columns) {
  try {
    localStorage.setItem(HIDDEN_COLUMNS_KEY, JSON.stringify(Array.from(columns)));
  } catch (_e) {
    // ignore
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initialize);
} else {
  initialize();
}

function initialize() {
  bindEvents();
  render();
  void loadInvestors();
}

function bindEvents() {
  elements.tabBar.addEventListener("click", function(event) {
    const tab = /** @type {HTMLElement | null} */ (event.target instanceof Element ? event.target.closest("[data-investor-key]") : null);
    if (!tab) {
      return;
    }

    const investorKey = tab.getAttribute("data-investor-key");
    if (!investorKey || !hasInvestorKey(investorKey)) {
      return;
    }

    switchInvestor(investorKey);
  });

  elements.sortButtons.forEach(function(button) {
    button.addEventListener("click", function() {
      const sortColumn = button.getAttribute("data-sort-column");
      if (!isSortColumn(sortColumn)) {
        return;
      }

      if (state.sortColumn === sortColumn) {
        state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
      } else {
        state.sortColumn = sortColumn;
        state.sortDirection = sortColumn === DEFAULT_SORT_COLUMN ? DEFAULT_SORT_DIRECTION : "asc";
      }

      render();
    });
  });

  elements.toggleChips.forEach(function(chip) {
    chip.addEventListener("click", function() {
      var column = chip.getAttribute("data-toggle-column");
      if (!column || !TOGGLEABLE_COLUMNS.includes(column)) {
        return;
      }
      if (state.hiddenColumns.has(column)) {
        state.hiddenColumns.delete(column);
      } else {
        state.hiddenColumns.add(column);
      }
      saveHiddenColumns(state.hiddenColumns);
      render();
    });
  });
}

/** @param {string[]} codes */
async function loadMetrics(codes) {
  if (state.metricsLoading) {
    return;
  }

  // GitHub Pages では静的 JSON を使用
  if (IS_GITHUB_PAGES) {
    // まだキャッシュがない場合のみ全データを読み込み
    if (Object.keys(state.metricsCache).length === 0) {
      state.metricsLoading = true;
      try {
        const response = await fetch(METRICS_DATA_URL + "?v=" + Date.now());
        if (!response.ok) {
          console.error("Failed to load metrics:", response.statusText);
          return;
        }
        const metrics = /** @type {Object.<string, StockMetrics>} */ (await response.json());
        Object.assign(state.metricsCache, metrics);
      } catch (error) {
        console.error("Error loading metrics:", error);
      } finally {
        state.metricsLoading = false;
      }
    }
    return;
  }

  // ローカル環境では API を使用
  const uncachedCodes = codes.filter(function(code) {
    return !(code in state.metricsCache);
  });

  if (uncachedCodes.length === 0) {
    return;
  }

  state.metricsLoading = true;

  try {
    const response = await fetch("/api/metrics?codes=" + uncachedCodes.join(","));
    if (!response.ok) {
      console.error("Failed to load metrics:", response.statusText);
      return;
    }

    const metrics = /** @type {Object.<string, StockMetrics>} */ (await response.json());
    Object.assign(state.metricsCache, metrics);
  } catch (error) {
    console.error("Error loading metrics:", error);
  } finally {
    state.metricsLoading = false;
  }
}

async function loadInvestors() {
  try {
    const response = await fetch(INVESTOR_DATA_URL, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load investor data");
    }

    const rawInvestors = /** @type {unknown} */ (await response.json());
    state.investors = normalizeInvestors(rawInvestors);
    state.currentInvestorKey = resolveDefaultInvestorKey(state.investors);
    state.isLoading = false;
    state.errorMessage = "";
    render();
  } catch (error) {
    console.error(error);
    state.isLoading = false;
    state.errorMessage = "投資家データを読み込めませんでした。";
    render();
  }
}

/** @param {unknown} rawInvestors
 *  @returns {InvestorsDocument}
 */
function normalizeInvestors(rawInvestors) {
  if (!rawInvestors || typeof rawInvestors !== "object" || Array.isArray(rawInvestors)) {
    throw new Error("Investor data must be an object");
  }

  const investors = /** @type {Object.<string, unknown>} */ (rawInvestors);
  const normalized = /** @type {InvestorsDocument} */ ({});

  Object.entries(investors).forEach(function(entry) {
    const investorKey = entry[0];
    const rawDataset = entry[1];

    if (investorKey === "") {
      throw new Error("Investor key must not be empty");
    }

    normalized[investorKey] = normalizeInvestorDataset(rawDataset);
  });

  if (Object.keys(normalized).length === 0) {
    throw new Error("Investor datasets are missing or invalid");
  }

  return normalized;
}

/** @param {unknown} candidate
 *  @returns {InvestorDataset}
 */
function normalizeInvestorDataset(candidate) {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
    throw new Error("Investor dataset must be an object");
  }

  const dataset = /** @type {{name?: unknown, stocks?: unknown}} */ (candidate);
  if (typeof dataset.name !== "string" || dataset.name === "") {
    throw new Error("Investor name must be a non-empty string");
  }
  if (!Array.isArray(dataset.stocks)) {
    throw new Error("Investor stocks must be an array");
  }

  return {
    name: dataset.name,
    stocks: dataset.stocks.map(normalizeInvestorStock),
  };
}

/** @param {unknown} candidate
 *  @returns {InvestorStock}
 */
function normalizeInvestorStock(candidate) {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
    throw new Error("Investor stock must be an object");
  }

  const stock = /** @type {{code?: unknown, name?: unknown, amount_millions?: unknown, ratio_percent?: unknown}} */ (candidate);
  if (typeof stock.code !== "string" || stock.code === "") {
    throw new Error("Investor stock code must be a non-empty string");
  }
  if (typeof stock.name !== "string" || stock.name === "") {
    throw new Error("Investor stock name must be a non-empty string");
  }
  if (stock.amount_millions !== null && !isInteger(stock.amount_millions)) {
    throw new Error("Investor stock amount must be an integer or null");
  }
  if (!isNumber(stock.ratio_percent)) {
    throw new Error("Investor stock ratio must be numeric");
  }

  return {
    code: stock.code,
    name: stock.name,
    amount_millions: stock.amount_millions === null ? null : stock.amount_millions,
    ratio_percent: Number(stock.ratio_percent),
  };
}

/** @param {InvestorsDocument} investors
 *  @returns {InvestorKey}
 */
function resolveDefaultInvestorKey(investors) {
  if (Object.prototype.hasOwnProperty.call(investors, DEFAULT_INVESTOR_KEY)) {
    return DEFAULT_INVESTOR_KEY;
  }

  const investorKeys = Object.keys(investors);
  if (investorKeys.length === 0) {
    throw new Error("Investor datasets are missing or invalid");
  }

  return investorKeys[0];
}

/** @param {InvestorKey} investorKey */
function switchInvestor(investorKey) {
  if (!hasInvestorKey(investorKey)) {
    return;
  }

  state.currentInvestorKey = investorKey;
  state.sortColumn = DEFAULT_SORT_COLUMN;
  state.sortDirection = DEFAULT_SORT_DIRECTION;
  render();
}

function render() {
  renderTabs();
  renderSortButtons();
  renderToggleChips();

  if (state.isLoading) {
    document.title = DEFAULT_TITLE;
    elements.statusMessage.textContent = "投資家データを読み込み中です。";
    renderMessageRow("投資家データを読み込み中です。");
    return;
  }

  if (state.errorMessage !== "") {
    document.title = DEFAULT_TITLE;
    elements.statusMessage.textContent = state.errorMessage;
    renderMessageRow(state.errorMessage);
    return;
  }

  const investor = getCurrentInvestor();
  if (!investor) {
    document.title = DEFAULT_TITLE;
    elements.statusMessage.textContent = "投資家データが見つかりません。";
    renderMessageRow("投資家データが見つかりません。");
    return;
  }

  document.title = investor.name + " 保有銘柄 - 四季報オンラインリンク一覧";

  const visibleStocks = getVisibleStocks(investor.stocks);
  elements.statusMessage.textContent = visibleStocks.length.toLocaleString("ja-JP") + " 件";

  if (visibleStocks.length === 0) {
    renderMessageRow("該当する銘柄はありません。");
    return;
  }

  renderStocks(visibleStocks);

  // Load metrics for visible stocks
  const codes = visibleStocks.map(function(stock) { return stock.code; });
  void loadMetrics(codes).then(function() {
    renderStocks(getVisibleStocks(investor.stocks));
  });
}

function renderTabs() {
  const investorEntries = getInvestorEntries();
  if (investorEntries.length === 0) {
    elements.tabBar.innerHTML = "";
    return;
  }

  elements.tabBar.innerHTML = investorEntries.map(function(entry) {
    const investorKey = entry[0];
    const investor = entry[1];
    const isActive = investorKey === state.currentInvestorKey;

    return (
      '<button class="tab' + (isActive ? " active" : "") + '" type="button" data-investor-key="' +
      escapeHtml(investorKey) +
      '" aria-selected="' +
      String(isActive) +
      '">' +
      escapeHtml(investor.name) +
      "</button>"
    );
  }).join("");
}

function renderSortButtons() {
  elements.sortButtons.forEach(function(button) {
    const sortColumn = button.getAttribute("data-sort-column");
    if (!isSortColumn(sortColumn)) {
      return;
    }

    const arrow = button.querySelector(".arrow");
    const isActive = state.sortColumn === sortColumn;
    const arrowText = isActive ? (state.sortDirection === "asc" ? ASC_ARROW : DESC_ARROW) : INACTIVE_ARROW;
    const th = button.closest("th");

    if (arrow) {
      arrow.textContent = arrowText;
    }
    button.classList.toggle("active", isActive);
    if (th) {
      th.setAttribute("aria-sort", isActive ? (state.sortDirection === "asc" ? "ascending" : "descending") : "none");
      th.classList.toggle("hidden-col", state.hiddenColumns.has(sortColumn));
    }
  });
}

function renderToggleChips() {
  elements.toggleChips.forEach(function(chip) {
    var column = chip.getAttribute("data-toggle-column");
    chip.classList.toggle("active", !state.hiddenColumns.has(column || ""));
  });
}

/** @returns {InvestorDataset | null} */
function getCurrentInvestor() {
  if (!state.investors || !hasInvestorKey(state.currentInvestorKey)) {
    return null;
  }

  return state.investors[state.currentInvestorKey];
}

/** @returns {Array<[InvestorKey, InvestorDataset]>} */
function getInvestorEntries() {
  return state.investors ? /** @type {Array<[InvestorKey, InvestorDataset]>} */ (Object.entries(state.investors)) : [];
}

/** @param {InvestorKey} investorKey
 *  @returns {boolean}
 */
function hasInvestorKey(investorKey) {
  return state.investors !== null && Object.prototype.hasOwnProperty.call(state.investors, investorKey);
}

/** @param {InvestorStock[]} stocks */
function getVisibleStocks(stocks) {
  return stocks.slice().sort(compareStocks);
}

/** @param {InvestorStock} leftStock
 *  @param {InvestorStock} rightStock
 */
function compareStocks(leftStock, rightStock) {
  const directionMultiplier = state.sortDirection === "asc" ? 1 : -1;

  if (state.sortColumn === "amount_millions") {
    if (leftStock.amount_millions === null && rightStock.amount_millions === null) {
      return leftStock.code.localeCompare(rightStock.code, "ja", { numeric: true });
    }
    if (leftStock.amount_millions === null) {
      return 1;
    }
    if (rightStock.amount_millions === null) {
      return -1;
    }
    return (leftStock.amount_millions - rightStock.amount_millions) * directionMultiplier;
  }

  if (state.sortColumn === "ratio_percent") {
    return (leftStock.ratio_percent - rightStock.ratio_percent) * directionMultiplier;
  }

  if (state.sortColumn === "code") {
    return leftStock.code.localeCompare(rightStock.code, "ja", { numeric: true }) * directionMultiplier;
  }

  // Handle metric columns (net_cash_ratio, per, equity_ratio, fcf_yield_avg, croic)
  const metricColumns = ["net_cash_ratio", "per", "equity_ratio", "fcf_yield_avg", "croic"];
  if (metricColumns.includes(state.sortColumn)) {
    const leftMetrics = state.metricsCache[leftStock.code];
    const rightMetrics = state.metricsCache[rightStock.code];
    const leftValue = leftMetrics ? leftMetrics[state.sortColumn] : null;
    const rightValue = rightMetrics ? rightMetrics[state.sortColumn] : null;

    if (leftValue === null && rightValue === null) {
      return leftStock.code.localeCompare(rightStock.code, "ja", { numeric: true });
    }
    if (leftValue === null) {
      return 1;
    }
    if (rightValue === null) {
      return -1;
    }
    return (leftValue - rightValue) * directionMultiplier;
  }

  return leftStock.name.localeCompare(rightStock.name, "ja") * directionMultiplier;
}

/** @param {string} column
 *  @param {number | null} rawValue
 *  @returns {string} CSS class string or empty string
 */
function metricClass(column, rawValue) {
  if (rawValue === null) {
    return "";
  }
  var t = METRIC_THRESHOLDS[column];
  if (!t) {
    return "";
  }
  if (t.good && t.good(rawValue)) {
    return " metric-good";
  }
  if (t.bad && t.bad(rawValue)) {
    return " metric-bad";
  }
  return "";
}

/** @param {InvestorStock[]} stocks */
function renderStocks(stocks) {
  var h = state.hiddenColumns;
  var ncrCls = h.has("net_cash_ratio") ? " hidden-col" : "";
  var perCls = h.has("per") ? " hidden-col" : "";
  var eqCls = h.has("equity_ratio") ? " hidden-col" : "";
  var fcfCls = h.has("fcf_yield_avg") ? " hidden-col" : "";
  var croicCls = h.has("croic") ? " hidden-col" : "";

  elements.tbody.innerHTML = stocks.map(function(stock) {
    const shikihoUrl = "https://shikiho.toyokeizai.net/stocks/" + encodeURIComponent(stock.code) + "/shikiho";
    const monexUrl = "https://monex.ifis.co.jp/index.php?sa=report_zaimu&bcode=" + encodeURIComponent(stock.code);
    const amountText = stock.amount_millions === null ? "-" : (stock.amount_millions / 100).toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "億";

    const metrics = state.metricsCache[stock.code];
    const ncrRaw = metrics && metrics.net_cash_ratio !== null ? metrics.net_cash_ratio : null;
    const perRaw = metrics && metrics.per !== null ? metrics.per : null;
    const eqRaw = metrics && metrics.equity_ratio !== null ? metrics.equity_ratio : null;
    const fcfRaw = metrics && metrics.fcf_yield_avg !== null ? metrics.fcf_yield_avg * 100 : null;
    const croicRaw = metrics && metrics.croic !== null ? metrics.croic * 100 : null;
    const netCashRatio = ncrRaw !== null ? ncrRaw.toFixed(2) : "-";
    const per = perRaw !== null ? perRaw.toFixed(1) : "-";
    const equityRatio = eqRaw !== null ? eqRaw.toFixed(1) : "-";
    const fcfYield = fcfRaw !== null ? fcfRaw.toFixed(2) : "-";
    const croic = croicRaw !== null ? croicRaw.toFixed(2) : "-";

    return (
      "<tr>" +
        '<td class="code">' + escapeHtml(stock.code) + "</td>" +
        '<td class="name"><a href="' + (IS_GITHUB_PAGES ? shikihoUrl : "/pdf/" + encodeURIComponent(stock.code)) + '" target="_blank" rel="noopener">' + escapeHtml(stock.name) + "</a></td>" +
        '<td class="num">' + amountText + "</td>" +
        '<td class="num">' + escapeHtml(String(stock.ratio_percent)) + "%</td>" +
        '<td class="num' + ncrCls + metricClass("net_cash_ratio", ncrRaw) + '">' + netCashRatio + "</td>" +
        '<td class="num' + perCls + metricClass("per", perRaw) + '">' + per + "</td>" +
        '<td class="num' + eqCls + metricClass("equity_ratio", eqRaw) + '">' + equityRatio + "%</td>" +
        '<td class="num' + fcfCls + metricClass("fcf_yield_avg", fcfRaw) + '">' + fcfYield + "%</td>" +
        '<td class="num' + croicCls + metricClass("croic", croicRaw) + '">' + croic + "%</td>" +
        '<td><div class="links-cell">' +
          '<a class="link-btn shikiho" href="' + shikihoUrl + '" target="_blank" rel="noopener" data-browser="shikiho">四季報</a>' +
          '<a class="link-btn monex" href="' + monexUrl + '" target="_blank" rel="noopener" data-browser="monex">Monex</a>' +
        "</div></td>" +
      "</tr>"
    );
  }).join("");
}

/** @param {string} message */
function renderMessageRow(message) {
  var visibleColCount = 10 - state.hiddenColumns.size;
  elements.tbody.innerHTML =
    '<tr><td class="table-message" colspan="' + visibleColCount + '">' + escapeHtml(message) + "</td></tr>";
}

/** @param {string | null} candidate */
function isSortColumn(candidate) {
  return candidate !== null && SORTABLE_COLUMNS.includes(candidate);
}

/** @param {unknown} value */
function isInteger(value) {
  return typeof value === "number" && Number.isInteger(value);
}

/** @param {unknown} value */
function isNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

/** @param {string} value */
function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
