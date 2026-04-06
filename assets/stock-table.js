/** @type {Array<[string, string, number|null, number]>} */
const stocks = window.stockData;

/**
 * @param {string} browserKey
 * @param {string} url
 */
function openInBrowser(browserKey, url) {
  fetch('/open?browser=' + encodeURIComponent(browserKey) + '&url=' + encodeURIComponent(url))
    .catch(function() {});
}

/** @param {Array<[string, string, number|null, number]>} data */
function render(data) {
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = data.map(function(/** @type {[string, string, number|null, number]} */ s) {
    const shikihoUrl = 'https://shikiho.toyokeizai.net/stocks/' + s[0] + '/shikiho';
    const monexUrl = 'https://monex.ifis.co.jp/index.php?sa=find&ta=n&wd=' + s[0];
    const amt = s[2] !== null ? s[2].toLocaleString() : '-';
    return '<tr>' +
      '<td class="code">' + s[0] + '</td>' +
      '<td class="name">' + s[1] + '</td>' +
      '<td class="num">' + amt + '</td>' +
      '<td class="num">' + s[3] + '</td>' +
      '<td><div class="links-cell">' +
        '<a class="link-btn shikiho" href="#" onclick="event.preventDefault(); openInBrowser(\'shikiho\', \'' + shikihoUrl + '\')">四季報 →</a>' +
        '<a class="link-btn monex" href="#" onclick="event.preventDefault(); openInBrowser(\'monex\', \'' + monexUrl + '\')">Monex →</a>' +
      '</div></td>' +
    '</tr>';
  }).join('');
}

function filterTable() {
  const q = document.getElementById('search').value.toLowerCase();
  const filtered = stocks.filter(function(/** @type {[string, string, number|null, number]} */ s) {
    return s[0].toLowerCase().includes(q) || s[1].toLowerCase().includes(q);
  });
  render(filtered);
}

/** @type {number[]} */
const sortDir = [1, 1, 1, 1];

/** @param {number} col */
function sortTable(col) {
  sortDir[col] *= -1;
  stocks.sort(function(/** @type {[string, string, number|null, number]} */ a, /** @type {[string, string, number|null, number]} */ b) {
    let va = a[col];
    let vb = b[col];
    if (va === null) va = col === 2 ? -1 : '';
    if (vb === null) vb = col === 2 ? -1 : '';
    if (typeof va === 'number') return (va - vb) * sortDir[col];
    return String(va).localeCompare(String(vb), 'ja') * sortDir[col];
  });
  render(stocks);
}

render(stocks);
