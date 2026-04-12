/** @typedef {"naito" | "hikari" | "kiyohara" | "katayama" | "imura" | "gomi"} InvestorKey */
/** @typedef {"code" | "name" | "amount_millions" | "ratio_percent"} SortColumn */
/** @typedef {"asc" | "desc"} SortDirection */
/**
 * @typedef {Object} InvestorStock
 * @property {string} code
 * @property {string} name
 * @property {number | null} amount_millions
 * @property {number} ratio_percent
 */
/**
 * @typedef {Object} InvestorDataset
 * @property {string} name
 * @property {string} subtitle
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
 */

const DEFAULT_TITLE = "保有銘柄ビューア - 四季報オンラインリンク一覧";
const DEFAULT_INVESTOR_KEY = "naito";
const DEFAULT_SORT_COLUMN = "amount_millions";
const DEFAULT_SORT_DIRECTION = "desc";
const INVESTOR_DATA_URL = "assets/data/investors.json?v=07593bcc1ea5";
const ASC_ARROW = "▲";
const DESC_ARROW = "▼";
const INACTIVE_ARROW = "▽";
const SORTABLE_COLUMNS = ["code", "name", "amount_millions", "ratio_percent"];
const AMOUNT_SUFFIX = "百万円";

/** @type {{
 *   investors: InvestorsDocument | null,
 *   currentInvestorKey: InvestorKey,
 *   searchQuery: string,
 *   sortColumn: SortColumn,
 *   sortDirection: SortDirection,
 *   isLoading: boolean,
 *   errorMessage: string
 * }}
 */
const state = {
  investors: null,
  currentInvestorKey: DEFAULT_INVESTOR_KEY,
  searchQuery: "",
  sortColumn: DEFAULT_SORT_COLUMN,
  sortDirection: DEFAULT_SORT_DIRECTION,
  isLoading: true,
  errorMessage: "",
};

const elements = {
  pageTitle: /** @type {HTMLElement} */ (document.getElementById("pageTitle")),
  pageSubtitle: /** @type {HTMLElement} */ (document.getElementById("pageSubtitle")),
  statCount: /** @type {HTMLElement} */ (document.getElementById("statCount")),
  statMaxAmount: /** @type {HTMLElement} */ (document.getElementById("statMaxAmount")),
  search: /** @type {HTMLInputElement} */ (document.getElementById("search")),
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
  elements.search.addEventListener("input", function() {
    state.searchQuery = elements.search.value.trim().toLowerCase();
    render();
  });

  elements.tabs.forEach(function(tab) {
    tab.addEventListener("click", function() {
      const investorKey = tab.getAttribute("data-investor-key");
      if (investorKey === "naito" || investorKey === "hikari" || investorKey === "kiyohara" || investorKey === "katayama" || investorKey === "imura" || investorKey === "gomi") {
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
  if (!isInvestorDataset(investors.naito) || !isInvestorDataset(investors.hikari) || !isInvestorDataset(investors.kiyohara) || !isInvestorDataset(investors.katayama) || !isInvestorDataset(investors.imura) || !isInvestorDataset(investors.gomi)) {
    throw new Error("Investor datasets are missing or invalid");
  }

  return /** @type {InvestorsDocument} */ ({
    naito: investors.naito,
    hikari: investors.hikari,
    kiyohara: investors.kiyohara,
    katayama: investors.katayama,
    imura: investors.imura,
    gomi: investors.gomi,
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
    typeof dataset.subtitle === "string" &&
    Array.isArray(dataset.stocks)
  );
}

/** @param {InvestorKey} investorKey */
function switchInvestor(investorKey) {
  if (!state.investors || !state.investors[investorKey]) {
    return;
  }

  state.currentInvestorKey = investorKey;
  state.searchQuery = "";
  state.sortColumn = DEFAULT_SORT_COLUMN;
  state.sortDirection = DEFAULT_SORT_DIRECTION;
  elements.search.value = "";
  render();
}

function render() {
  renderTabs();
  renderSortButtons();

  if (state.isLoading) {
    document.title = DEFAULT_TITLE;
    elements.pageTitle.textContent = "保有銘柄一覧";
    elements.pageSubtitle.textContent = "投資家データを読み込み中です。";
    elements.search.disabled = true;
    elements.statusMessage.textContent = "投資家データを読み込み中です。";
    renderStats(null);
    renderMessageRow("投資家データを読み込み中です。");
    return;
  }

  if (state.errorMessage !== "") {
    document.title = DEFAULT_TITLE;
    elements.pageTitle.textContent = "保有銘柄一覧";
    elements.pageSubtitle.textContent = state.errorMessage;
    elements.search.disabled = true;
    elements.statusMessage.textContent = state.errorMessage;
    renderStats(null);
    renderMessageRow(state.errorMessage);
    return;
  }

  const investor = getCurrentInvestor();
  if (!investor) {
    document.title = DEFAULT_TITLE;
    elements.pageTitle.textContent = "保有銘柄一覧";
    elements.pageSubtitle.textContent = "投資家データが見つかりません。";
    elements.search.disabled = true;
    elements.statusMessage.textContent = "投資家データが見つかりません。";
    renderStats(null);
    renderMessageRow("投資家データが見つかりません。");
    return;
  }

  elements.search.disabled = false;
  document.title = investor.name + " 保有銘柄 - 四季報オンラインリンク一覧";
  elements.pageTitle.textContent = investor.name + " 保有銘柄一覧";
  elements.pageSubtitle.textContent = investor.subtitle;
  renderStats(investor.stocks);

  const visibleStocks = getVisibleStocks(investor.stocks);
  elements.statusMessage.textContent = visibleStocks.length.toLocaleString("ja-JP") +
    " / " +
    investor.stocks.length.toLocaleString("ja-JP") +
    " 件表示";

  if (visibleStocks.length === 0) {
    renderMessageRow("該当する銘柄はありません。");
    return;
  }

  renderStocks(visibleStocks);
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

/** @param {InvestorStock[] | null} stocks */
function renderStats(stocks) {
  if (!stocks) {
    elements.statCount.textContent = "-";
    elements.statMaxAmount.textContent = "-";
    return;
  }

  elements.statCount.textContent = stocks.length.toLocaleString("ja-JP");
  elements.statMaxAmount.textContent = formatMaxAmount(stocks);
}

/** @param {InvestorStock[]} stocks */
function formatMaxAmount(stocks) {
  const amounts = stocks
    .map(function(stock) { return stock.amount_millions; })
    .filter(function(amount) { return amount !== null; });
  if (amounts.length === 0) {
    return "-";
  }

  return Math.max.apply(null, amounts).toLocaleString("ja-JP") + AMOUNT_SUFFIX;
}

function getCurrentInvestor() {
  return state.investors ? state.investors[state.currentInvestorKey] : null;
}

/** @param {InvestorStock[]} stocks */
function getVisibleStocks(stocks) {
  const query = state.searchQuery;
  const filteredStocks = query === ""
    ? stocks.slice()
    : stocks.filter(function(stock) {
        return stock.code.toLowerCase().includes(query) || stock.name.toLowerCase().includes(query);
      });

  return filteredStocks.sort(compareStocks);
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

  return leftStock.name.localeCompare(rightStock.name, "ja") * directionMultiplier;
}

/** @param {InvestorStock[]} stocks */
function renderStocks(stocks) {
  elements.tbody.innerHTML = stocks.map(function(stock) {
    const shikihoUrl = "https://shikiho.toyokeizai.net/stocks/" + encodeURIComponent(stock.code) + "/shikiho";
    const monexUrl = "https://scouter.monex.co.jp/report/zaimu/" + encodeURIComponent(stock.code);
    const amountText = stock.amount_millions === null ? "-" : stock.amount_millions.toLocaleString("ja-JP");

    return (
      "<tr>" +
        '<td class="code">' + escapeHtml(stock.code) + "</td>" +
        '<td class="name">' + escapeHtml(stock.name) + "</td>" +
        '<td class="num">' + amountText + "</td>" +
        '<td class="num">' + escapeHtml(String(stock.ratio_percent)) + "</td>" +
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
    '<tr><td class="table-message" colspan="5">' + escapeHtml(message) + "</td></tr>";
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
