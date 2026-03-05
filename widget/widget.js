/**
 * daily-article 埋め込み用 JS スニペット
 *
 * 使い方:
 *   <div id="daily-article-widget"></div>
 *   <script src="https://{username}.github.io/library-daily-article/widget/widget.js"></script>
 *
 * オプション（script タグの前に定義）:
 *   window.TDA_VPN_URL = 'https://your-institution.ac.jp/vpn';
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

  var DATA_URL    = baseUrl + '../data/today.json';
  var STYLE_URL   = baseUrl + 'style.css';
  var VPN_URL     = (window.TDA_VPN_URL || '');
  var ARCHIVE_URL = baseUrl + 'archive.html';

  var container = document.getElementById('daily-article-widget');
  if (!container) {
    console.warn('[daily-article] #daily-article-widget が見つかりません。');
    return;
  }

  // Google Fonts を注入（重複注入を防ぐ）
  if (!document.getElementById('tda-fonts')) {
    var fonts = document.createElement('link');
    fonts.id   = 'tda-fonts';
    fonts.rel  = 'stylesheet';
    fonts.href = 'https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700&family=DM+Serif+Display&family=Noto+Sans+JP:wght@400;500;700&display=swap';
    document.head.appendChild(fonts);
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

  // 新旧両フォーマットに対応
  function normalize(data) {
    var parts = (data.date || '').split('-');
    var month = parseInt(parts.length >= 3 ? parts[1] : parts[0]) || '';
    var day   = parseInt(parts.length >= 3 ? parts[2] : parts[1]) || '';

    var eventYear = '', eventText = '';
    if (data.event) {
      eventYear = data.event.year || '';
      eventText = data.event.text || '';
    } else if (data.today_topic) {
      var m = (data.today_topic.text || '').match(/^(\d{4})年\s*[-－]\s*(.+)$/);
      if (m) { eventYear = m[1]; eventText = m[2]; }
      else     eventText = data.today_topic.text || '';
    }

    var p  = data.paper    || {};
    var db = data.database || {};

    var author = '';
    if (p.author) {
      author = p.author;
    } else if (Array.isArray(p.authors) && p.authors.length > 0) {
      author = p.authors[0] + (p.authors.length > 1 ? ' ほか' : '');
    }

    return { month: month, day: day, eventYear: eventYear, eventText: eventText,
             author: author, p: p, db: db };
  }

  // ── レンダリング ──────────────────────────────────────
  function render(data) {
    var n = normalize(data);
    var p  = n.p;
    var db = n.db;
    var qrSrc = VPN_URL
      ? 'https://api.qrserver.com/v1/create-qr-code/?size=56x56&data=' + encodeURIComponent(VPN_URL)
      : '';

    var vpnBlock = VPN_URL ? [
      '<div class="vpn-notice">大学ネットワークまたはVPN接続が必要</div>',
      '<div class="vpn-access">',
        '<div class="vpn-qr"><img src="' + qrSrc + '" alt="VPN設定ページQRコード" width="56" height="56"></div>',
        '<div class="vpn-link-area">',
          '<div class="vpn-link-label">VPN接続方法</div>',
          '<a class="vpn-link" href="' + escapeHtml(VPN_URL) + '" target="_blank" rel="noopener">大学VPN設定ページへ</a>',
        '</div>',
      '</div>',
    ].join('') : '';

    container.innerHTML = [
      '<div class="widget">',
        '<div class="header">',
          '<div class="header-label">Today in History</div>',
          '<div class="header-date">今日は何の日？<br>',
            '<span>— ' + n.month + '月' + n.day + '日</span>',
          '</div>',
        '</div>',
        '<div class="event-section">',
          '<div class="event-label">Today\'s Event</div>',
          '<div class="event-text">',
            n.eventYear ? '<span class="event-year">' + escapeHtml(String(n.eventYear)) + '年</span> — ' : '',
            escapeHtml(n.eventText),
          '</div>',
        '</div>',
        p.connection ? '<div class="connection-section"><div class="connection-text">' + p.connection + '</div></div>' : '',
        '<div class="paper-card">',
          '<div class="paper-title">' + escapeHtml(p.title || '') + '</div>',
          p.abstract_ja ? [
            '<div class="abstract-box">',
              '<div class="abstract-text">' + escapeHtml(p.abstract_ja) + '</div>',
              '<div class="abstract-note">機械翻訳による要約です。原文と異なる場合があります。</div>',
            '</div>',
          ].join('') : '',
          '<div class="paper-meta">',
            n.author   ? '<span>著者｜'  + escapeHtml(n.author)         + '</span>' : '',
            p.journal  ? '<span>掲載誌｜' + escapeHtml(p.journal)        + '</span>' : '',
            p.year     ? '<span>出版年｜' + escapeHtml(String(p.year))   + '</span>' : '',
          '</div>',
          p.doi_url ? '<a class="btn-primary" href="' + escapeHtml(p.doi_url) + '" target="_blank" rel="noopener">この論文を読む →</a>' : '',
        '</div>',
        '<a class="past-link" href="' + ARCHIVE_URL + '">過去の記事を見る ›</a>',
        '<div class="db-card">',
          '<div class="db-label">この論文が読めるデータベース</div>',
          '<div class="db-name">' + escapeHtml(db.name || '') + '</div>',
          '<div class="db-desc">' + escapeHtml(db.description || '') + '</div>',
          vpnBlock,
          db.url ? '<a class="btn-secondary" href="' + escapeHtml(db.url) + '" target="_blank" rel="noopener">データベースへアクセス →</a>' : '',
        '</div>',
      '</div>',
    ].join('');
  }

  function renderError() {
    container.innerHTML =
      '<div class="widget"><p class="tda-error">コンテンツを読み込めませんでした。しばらく後にお試しください。</p></div>';
  }

  // ── データ取得 ────────────────────────────────────────
  container.innerHTML = '<div class="widget"><div class="tda-loading">読み込み中…</div></div>';

  var xhr = new XMLHttpRequest();
  xhr.open('GET', DATA_URL, true);
  xhr.onreadystatechange = function () {
    if (xhr.readyState !== 4) return;
    if (xhr.status === 200) {
      try {
        render(JSON.parse(xhr.responseText));
      } catch (e) {
        console.error('[daily-article]', e);
        renderError();
      }
    } else {
      console.error('[daily-article] fetch failed:', xhr.status);
      renderError();
    }
  };
  xhr.send();
})();
