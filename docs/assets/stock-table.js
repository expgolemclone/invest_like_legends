/** @typedef {"naito" | "hikari" | "kiyohara" | "katayama" | "imura" | "gomi" | "one_warikabunihon"} InvestorKey */
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
/**
 * @typedef {Object} InvestorsDocument
 * @property {InvestorDataset} naito
 * @property {InvestorDataset} hikari
 * @property {InvestorDataset} kiyohara
 * @property {InvestorDataset} katayama
 * @property {InvestorDataset} imura
 * @property {InvestorDataset} gomi
 * @property {InvestorDataset} one_warikabunihon
 */

const DEFAULT_TITLE = "保有銘柄ビューア - 四季報オンラインリンク一覧";
const DEFAULT_INVESTOR_KEY = "naito";
const DEFAULT_SORT_COLUMN = "amount_millions";
const DEFAULT_SORT_DIRECTION = "desc";
const INVESTOR_DATA_URL = "assets/data/investors.json?v=a4123689e1bf";
const METRICS_DATA_URL = "assets/data/metrics.json";
const IS_GITHUB_PAGES = location.hostname === "expgolemclone.github.io";
const ASC_ARROW = "▲";
const DESC_ARROW = "▼";
const INACTIVE_ARROW = "▽";
const SORTABLE_COLUMNS = ["code", "name", "amount_millions", "ratio_percent", "net_cash_ratio", "per", "equity_ratio", "fcf_yield_avg", "croic"];
/** @type {{
 *   investors: InvestorsDocument | null,
 *   currentInvestorKey: InvestorKey,
 *   sortColumn: SortColumn,
 *   sortDirection: SortDirection,
 *   isLoading: boolean,
 *   errorMessage: string,
 *   metricsCache: Object<string, StockMetrics>,
 *   metricsLoading: boolean
 * }}
 */
const state = {
  investors: null,
  currentInvestorKey: DEFAULT_INVESTOR_KEY,
  sortColumn: DEFAULT_SORT_COLUMN,
  sortDirection: DEFAULT_SORT_DIRECTION,
  isLoading: true,
  errorMessage: "",
  metricsCache: {},
  metricsLoading: false,
};

const elements = {
  statusMessage: /** @type {HTMLElement} */ (document.getElementById("statusMessage")),
  tbody: /** @type {HTMLElement} */ (document.getElementById("tbody")),
  tabs: /** @type {HTMLButtonElement[]} */ (Array.from(document.querySelectorAll("[data-investor-key]"))),
  sortButtons: /** @type {HTMLButtonElement[]} */ (Array.from(document.querySelectorAll("[data-sort-column]"))),
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
  elements.tabs.forEach(function(tab) {
    tab.addEventListener("click", function() {
      const investorKey = tab.getAttribute("data-investor-key");
      if (investorKey === "naito" || investorKey === "hikari" || investorKey === "kiyohara" || investorKey === "katayama" || investorKey === "imura" || investorKey === "gomi" || investorKey === "one_warikabunihon") {
        switchInvestor(investorKey);
      }
    });
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
        const metrics = /** @type {Object<string, StockMetrics>} */ (await response.json());
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

    const metrics = /** @type {Object<string, StockMetrics>} */ (await response.json());
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
    state.isLoading = false;
    switchInvestor(DEFAULT_INVESTOR_KEY);
  } catch (error) {
    console.error(error);
    state.isLoading = false;
    state.errorMessage = "投資家データを読み込めませんでした。";
    render();
  }
}

/** @param {unknown} rawInvestors */
function normalizeInvestors(rawInvestors) {
  if (!rawInvestors || typeof rawInvestors !== "object") {
    throw new Error("Investor data must be an object");
  }

  const investors = /** @type {Partial<InvestorsDocument>} */ (rawInvestors);
  if (!isInvestorDataset(investors.naito) || !isInvestorDataset(investors.hikari) || !isInvestorDataset(investors.kiyohara) || !isInvestorDataset(investors.katayama) || !isInvestorDataset(investors.imura) || !isInvestorDataset(investors.gomi) || !isInvestorDataset(investors.one_warikabunihon)) {
    throw new Error("Investor datasets are missing or invalid");
  }

  return /** @type {InvestorsDocument} */ ({
    naito: investors.naito,
    hikari: investors.hikari,
    kiyohara: investors.kiyohara,
    katayama: investors.katayama,
    imura: investors.imura,
    gomi: investors.gomi,
    one_warikabunihon: investors.one_warikabunihon,
  });
}

/** @param {unknown} candidate */
function isInvestorDataset(candidate) {
  if (!candidate || typeof candidate !== "object") {
    return false;
  }

  const dataset = /** @type {Partial<InvestorDataset>} */ (candidate);
  return (
    typeof dataset.name === "string" &&
    Array.isArray(dataset.stocks)
  );
}

/** @param {InvestorKey} investorKey */
function switchInvestor(investorKey) {
  if (!state.investors || !state.investors[investorKey]) {
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
  elements.tabs.forEach(function(tab) {
    const isActive = tab.getAttribute("data-investor-key") === state.currentInvestorKey;
    tab.classList.toggle("active", isActive);
    tab.setAttribute("aria-selected", String(isActive));
  });
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
    }
  });
}

function getCurrentInvestor() {
  return state.investors ? state.investors[state.currentInvestorKey] : null;
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

/** @param {InvestorStock[]} stocks */
function renderStocks(stocks) {
  elements.tbody.innerHTML = stocks.map(function(stock) {
    const shikihoUrl = "https://shikiho.toyokeizai.net/stocks/" + encodeURIComponent(stock.code) + "/shikiho";
    const monexUrl = "https://monex.ifis.co.jp/index.php?sa=report_zaimu&bcode=" + encodeURIComponent(stock.code);
    const amountText = stock.amount_millions === null ? "-" : (stock.amount_millions / 100).toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "億";

    const metrics = state.metricsCache[stock.code];
    const netCashRatio = metrics && metrics.net_cash_ratio !== null ? metrics.net_cash_ratio.toFixed(2) : "-";
    const per = metrics && metrics.per !== null ? metrics.per.toFixed(1) : "-";
    const equityRatio = metrics && metrics.equity_ratio !== null ? metrics.equity_ratio.toFixed(1) : "-";
    const fcfYield = metrics && metrics.fcf_yield_avg !== null ? (metrics.fcf_yield_avg * 100).toFixed(2) : "-";
    const croic = metrics && metrics.croic !== null ? (metrics.croic * 100).toFixed(2) : "-";

    return (
      "<tr>" +
        '<td class="code">' + escapeHtml(stock.code) + "</td>" +
        '<td class="name"><a href="https://www.google.com/search?q=' + encodeURIComponent(stock.name) + '" target="_blank" rel="noopener">' + escapeHtml(stock.name) + "</a></td>" +
        '<td class="num">' + amountText + "</td>" +
        '<td class="num">' + escapeHtml(String(stock.ratio_percent)) + "%</td>" +
        '<td class="num">' + netCashRatio + "</td>" +
        '<td class="num">' + per + "</td>" +
        '<td class="num">' + equityRatio + "%</td>" +
        '<td class="num">' + fcfYield + "%</td>" +
        '<td class="num">' + croic + "%</td>" +
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
  elements.tbody.innerHTML =
    '<tr><td class="table-message" colspan="10">' + escapeHtml(message) + "</td></tr>";
}

/** @param {string | null} candidate */
function isSortColumn(candidate) {
  return candidate !== null && SORTABLE_COLUMNS.includes(candidate);
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
