/**
 * tufs-daily-article 埋め込み用 JS スニペット
 *
 * 使い方:
 *   <div id="tufs-daily-article"></div>
 *   <script src="https://{username}.github.io/tufs-daily-article/widget/widget.js"></script>
 */
(function () {
  // script タグの src から自分のベース URL を導出
  var scripts = document.getElementsByTagName('script');
  var baseUrl = '';
  for (var i = 0; i < scripts.length; i++) {
    var src = scripts[i].src || '';
    if (src.indexOf('widget.js') !== -1) {
      baseUrl = src.replace(/widget\.js(\?.*)?$/, '');
      break;
    }
  }

  var DATA_URL  = baseUrl + '../data/today.json';
  var STYLE_URL = baseUrl + 'style.css';

  var container = document.getElementById('tufs-daily-article');
  if (!container) {
    console.warn('[tufs-daily-article] #tufs-daily-article が見つかりません。');
    return;
  }

  // CSS をページに注入（重複注入を防ぐ）
  if (!document.getElementById('tda-style')) {
    var link = document.createElement('link');
    link.id   = 'tda-style';
    link.rel  = 'stylesheet';
    link.href = STYLE_URL;
    document.head.appendChild(link);
  }

  // ── ヘルパー ──────────────────────────────────────────
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatAuthors(authors) {
    if (!authors || authors.length === 0) return '';
    var displayed = authors.slice(0, 3).map(escapeHtml);
    return displayed.join(' / ') + (authors.length > 3 ? ' ほか' : '');
  }

  // ── レンダリング ──────────────────────────────────────
  function render(data) {
    var p     = data.paper;
    var db    = data.database;
    var topic = data.today_topic;

    var parts = (data.date || '').split('-');
    var dateLabel = parts[1] && parts[2]
      ? parseInt(parts[1]) + '月' + parseInt(parts[2]) + '日'
      : '';

    var lockIcon = db.ip_restricted ? '🔒 ' : '';

    container.innerHTML = [
      '<div class="tda-widget" role="region" aria-label="今日の論文ウィジェット">',
        '<div class="tda-header">📅 今日は何の日？ ― ' + escapeHtml(dateLabel) + '</div>',
        '<div class="tda-topic">' + escapeHtml(topic.text || '') + '</div>',
        '<div class="tda-paper">',
          '<div class="tda-paper-title">📄 ' + escapeHtml(p.title) + '</div>',
          '<div class="tda-paper-meta">',
            formatAuthors(p.authors),
            p.journal ? ' ／ ' + escapeHtml(p.journal) : '',
            p.year    ? ' ／ ' + escapeHtml(String(p.year)) : '',
          '</div>',
          p.abstract_ja
            ? '<div class="tda-abstract">' + escapeHtml(p.abstract_ja) + '</div>'
            : '',
          p.doi_url
            ? '<a class="tda-btn tda-btn-primary" href="' + escapeHtml(p.doi_url) +
              '" target="_blank" rel="noopener noreferrer">この論文を読む →</a>'
            : '',
        '</div>',
        '<div class="tda-db">',
          '<div class="tda-db-label">この論文が読めるデータベース</div>',
          '<div class="tda-db-name">' + escapeHtml(db.name) + '</div>',
          '<div class="tda-db-desc">' + escapeHtml(db.description) + '</div>',
          db.access_note
            ? '<div class="tda-access-note">' + lockIcon + escapeHtml(db.access_note) + '</div>'
            : '',
          db.url
            ? '<a class="tda-btn tda-btn-secondary" href="' + escapeHtml(db.url) +
              '" target="_blank" rel="noopener noreferrer">データベースへアクセス →</a>'
            : '',
        '</div>',
      '</div>'
    ].join('');
  }

  function renderError() {
    container.innerHTML =
      '<div class="tda-widget"><div class="tda-error">' +
      'コンテンツを読み込めませんでした。しばらく後にお試しください。' +
      '</div></div>';
  }

  // ── データ取得 ────────────────────────────────────────
  container.innerHTML =
    '<div class="tda-widget"><div class="tda-loading">読み込み中…</div></div>';

  var xhr = new XMLHttpRequest();
  xhr.open('GET', DATA_URL, true);
  xhr.onreadystatechange = function () {
    if (xhr.readyState !== 4) return;
    if (xhr.status === 200) {
      try {
        render(JSON.parse(xhr.responseText));
      } catch (e) {
        console.error('[tufs-daily-article]', e);
        renderError();
      }
    } else {
      console.error('[tufs-daily-article] fetch failed:', xhr.status);
      renderError();
    }
  };
  xhr.send();
})();
