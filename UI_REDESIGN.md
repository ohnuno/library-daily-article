# widget/index.html UIリニューアル実装指示書

## 概要

`widget/index.html` のUIを全面リニューアルする。
デザインの方針・配色・HTML構造・CSSをすべてこのドキュメントに記載する。
**既存のHTMLを本ドキュメントの仕様で置き換えること。**

---

## フォント

Google Fonts から以下を読み込む。

```html
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700&family=DM+Serif+Display&family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
```

| 用途 | フォント |
|------|----------|
| 基本テキスト | Noto Sans JP |
| ヘッダー日付・論文タイトル | DM Serif Display |
| 日本語見出し補助 | Noto Serif JP |

---

## カラーパレット（牡丹色）

```css
/* メインカラー */
--color-dark:   #7a1f4a;   /* 濃牡丹：ヘッダー深色・強調テキスト */
--color-main:   #b5406e;   /* 牡丹：ボタン・ボーダー・アクセント */
--color-light:  #d4688f;   /* 薄牡丹：ヘッダーグラデーション末端 */

/* 背景系 */
--color-bg1:    #fdf5f8;   /* 極薄牡丹：セクション背景 */
--color-bg2:    #f7e8ef;   /* 淡牡丹：グラデーション終端 */
--color-border: #e8c4d4;   /* ボーダー */
--color-divider:#f0e8ed;   /* セクション区切り線 */

/* テキスト系 */
--color-text:   #2c3e50;   /* 本文 */
--color-sub:    #546e8a;   /* サブテキスト */
--color-meta:   #8a9bb0;   /* メタ情報・ラベル */
--color-note:   #a0afc0;   /* 注記 */
--color-warn:   #c0392b;   /* VPN警告 */
```

---

## HTML構造

`today.json` から取得したデータをJavaScriptで各要素に流し込む。
以下がウィジェット全体の構造。

```html
<div class="widget">

  <!-- 1. ヘッダー -->
  <div class="header">
    <div class="header-label">Today in History</div>
    <div class="header-date">
      今日は何の日？<br>
      <span>— {月}月{日}日</span>
    </div>
  </div>

  <!-- 2. 出来事セクション -->
  <div class="event-section">
    <div class="event-label">Today's Event</div>
    <div class="event-text">
      <span class="event-year">{year}年</span> — {event_text}
    </div>
  </div>

  <!-- 3. 出来事→論文の接続説明 -->
  <div class="connection-section">
    <div class="connection-text">
      {connection_text}
      <!-- 例: この出来事を深掘りするなら、<strong>{keyword}</strong>を扱う以下の論文が参考になります。 -->
    </div>
  </div>

  <!-- 4. 論文カード -->
  <div class="paper-card">
    <div class="paper-title">{paper_title}</div>

    <!-- 抄録訳（機械翻訳）-->
    <div class="abstract-box">
      <div class="abstract-text">{abstract_ja}</div>
      <div class="abstract-note">機械翻訳による要約です。原文と異なる場合があります。</div>
    </div>

    <!-- メタ情報 -->
    <div class="paper-meta">
      <span>著者｜{author}</span>
      <span>掲載誌｜{journal}</span>
      <span>出版年｜{year}</span>
    </div>

    <a class="btn-primary" href="{doi_url}" target="_blank" rel="noopener">この論文を読む →</a>
  </div>

  <!-- 過去記事リンク -->
  <a class="past-link" href="archive.html">過去の記事を見る ›</a>

  <!-- 5. DBカード -->
  <div class="db-card">
    <div class="db-label">この論文が読めるデータベース</div>
    <div class="db-name">{db_name}</div>
    <div class="db-desc">{db_description}</div>

    <div class="vpn-notice">大学ネットワークまたはVPN接続が必要</div>

    <!-- VPNアクセスエリア（QRコード＋リンク） -->
    <div class="vpn-access">
      <div class="vpn-qr">
        <!--
          QRコードはqrserver.com APIで動的生成。
          VPN説明ページのURLを data= に設定すること。
          例: https://api.qrserver.com/v1/create-qr-code/?size=56x56&data={VPN_PAGE_URL}
        -->
        <img
          src="https://api.qrserver.com/v1/create-qr-code/?size=56x56&data={VPN_PAGE_URL}"
          alt="VPN設定ページQRコード"
          width="56"
          height="56"
        >
      </div>
      <div class="vpn-link-area">
        <div class="vpn-link-label">VPN接続方法</div>
        <a class="vpn-link" href="{VPN_PAGE_URL}" target="_blank" rel="noopener">
          大学VPN設定ページへ
        </a>
      </div>
    </div>

    <a class="btn-secondary" href="{db_url}" target="_blank" rel="noopener">データベースへアクセス →</a>
  </div>

</div>
```

### プレースホルダーと `today.json` のキー対応

| プレースホルダー | `today.json` のキー | 備考 |
|-----------------|-------------------|------|
| `{月}` `{日}` | `date` | "MM-DD" 形式から分割して表示 |
| `{year}` | `event.year` | 出来事の年 |
| `{event_text}` | `event.text` | 出来事の説明文 |
| `{connection_text}` | `paper.connection` | AIが生成した接続説明文。`<strong>`タグを含む場合あり |
| `{paper_title}` | `paper.title` | 英語タイトルをそのまま表示 |
| `{abstract_ja}` | `paper.abstract_ja` | Geminiが生成した日本語抄録訳 |
| `{author}` | `paper.author` | 著者名。複数いる場合は筆頭著者 + "ほか" |
| `{journal}` | `paper.journal` | 掲載誌名 |
| `{year}` | `paper.year` | 出版年 |
| `{doi_url}` | `paper.doi_url` | DOIリンク（https://doi.org/...） |
| `{db_name}` | `database.name` | データベース名 |
| `{db_description}` | `database.description` | データベース説明文 |
| `{db_url}` | `database.url` | データベースURLまたはリゾルバURL |
| `{VPN_PAGE_URL}` | 固定値 | `js/config.js` 等に定数として定義し、QRとリンク両方に使う |

---

## CSS

既存のCSSをすべて以下で置き換える。

```css
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  font-family: 'Noto Sans JP', sans-serif;
  padding: 24px 16px;
}

.widget {
  width: 100%;
  max-width: 420px;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 8px 40px rgba(0,0,0,0.15);
  background: #fff;
}

/* ── ヘッダー ── */
.header {
  background: linear-gradient(135deg, #7a1f4a 0%, #b5406e 60%, #d4688f 100%);
  padding: 20px 20px 16px;
  position: relative;
  overflow: hidden;
}
.header::before {
  content: '';
  position: absolute;
  top: -40px; right: -40px;
  width: 160px; height: 160px;
  border-radius: 50%;
  background: rgba(255,255,255,0.07);
}
.header::after {
  content: '';
  position: absolute;
  bottom: -20px; left: 30px;
  width: 80px; height: 80px;
  border-radius: 50%;
  background: rgba(255,255,255,0.05);
}
.header-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: rgba(255,255,255,0.65);
  text-transform: uppercase;
  margin-bottom: 6px;
}
.header-date {
  font-family: 'DM Serif Display', serif;
  font-size: 28px;
  color: #fff;
  line-height: 1.1;
}
.header-date span {
  font-family: 'Noto Serif JP', serif;
  font-size: 22px;
}

/* ── 出来事セクション ── */
.event-section {
  background: linear-gradient(90deg, #fdf5f8 0%, #f7e8ef 100%);
  padding: 14px 20px;
  border-left: 3px solid #b5406e;
}
.event-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #b5406e;
  text-transform: uppercase;
  margin-bottom: 5px;
}
.event-text {
  font-size: 13px;
  color: #2c3e50;
  line-height: 1.6;
}
.event-year {
  font-weight: 700;
  color: #7a1f4a;
}

/* ── 接続説明 ── */
.connection-section {
  padding: 14px 20px 10px;
  border-bottom: 1px solid #f0e8ed;
}
.connection-text {
  font-size: 12.5px;
  color: #546e8a;
  line-height: 1.7;
  padding: 10px 14px;
  background: #fdf5f8;
  border-radius: 3px;
  border-left: 3px solid #b5406e;
}
.connection-text strong {
  color: #7a1f4a;
}

/* ── 論文カード ── */
.paper-card {
  padding: 18px 20px 14px;
  border-bottom: 1px solid #f0e8ed;
}
.paper-title {
  font-family: 'DM Serif Display', serif;
  font-size: 15px;
  color: #1a2a4a;
  line-height: 1.55;
  margin-bottom: 10px;
  font-weight: 400;
}

/* 抄録ボックス */
.abstract-box {
  background: #fdf5f8;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 14px;
}
.abstract-text {
  font-size: 12.5px;
  color: #3a4e66;
  line-height: 1.75;
  margin-bottom: 6px;
}
.abstract-note {
  font-size: 10.5px;
  color: #a0afc0;
}

/* メタ情報（著者・掲載誌・出版年） */
.paper-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11.5px;
  color: #8a9bb0;
  margin-bottom: 14px;
}
.paper-meta span {
  display: flex;
  align-items: center;
}

/* 主ボタン */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #7a1f4a, #b5406e);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  padding: 10px 20px;
  border-radius: 25px;
  text-decoration: none;
  letter-spacing: 0.03em;
  box-shadow: 0 4px 14px rgba(181,64,110,0.35);
  transition: transform 0.15s, box-shadow 0.15s;
}
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(181,64,110,0.45);
}

/* 過去記事リンク */
.past-link {
  display: block;
  text-align: right;
  font-size: 11.5px;
  color: #8a9bb0;
  padding: 8px 20px 0;
  text-decoration: none;
  transition: color 0.15s;
}
.past-link:hover { color: #b5406e; }

/* ── DBカード ── */
.db-card {
  margin: 12px 16px 16px;
  background: linear-gradient(135deg, #fdf5f8 0%, #f7e8ef 100%);
  border: 1px solid #e8c4d4;
  border-radius: 14px;
  padding: 16px;
}
.db-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #8a9bb0;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.db-name {
  font-size: 16px;
  font-weight: 700;
  color: #7a1f4a;
  margin-bottom: 6px;
}
.db-desc {
  font-size: 12px;
  color: #546e8a;
  line-height: 1.65;
  margin-bottom: 12px;
}
.vpn-notice {
  font-size: 11.5px;
  color: #c0392b;
  font-weight: 500;
  margin-bottom: 10px;
}

/* VPNアクセスエリア（QR＋リンク） */
.vpn-access {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border: 1px solid #e8c4d4;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.vpn-qr {
  flex-shrink: 0;
  width: 56px;
  height: 56px;
  border-radius: 6px;
  overflow: hidden;
}
.vpn-qr img {
  width: 56px;
  height: 56px;
  display: block;
}
.vpn-link-area { flex: 1; }
.vpn-link-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #8a9bb0;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.vpn-link {
  font-size: 12px;
  color: #b5406e;
  font-weight: 600;
  text-decoration: none;
  word-break: break-all;
}
.vpn-link:hover { text-decoration: underline; }

/* 副ボタン */
.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  color: #7a1f4a;
  font-size: 12.5px;
  font-weight: 700;
  padding: 9px 18px;
  border-radius: 25px;
  text-decoration: none;
  border: 1.5px solid #b5406e;
  letter-spacing: 0.03em;
  transition: background 0.15s, color 0.15s;
}
.btn-secondary:hover {
  background: #b5406e;
  color: #fff;
}
```

---

## 設定値（定数）

`widget/index.html` の `<script>` 内、または別ファイル `widget/config.js` に以下を定義すること。

```javascript
const CONFIG = {
  // VPN説明ページのURL（QRコードとテキストリンク両方に使用）
  VPN_PAGE_URL: 'https://xxxx.ac.jp/vpn',  // ← 実際のURLに変更すること

  // 過去記事アーカイブページ
  ARCHIVE_URL: 'archive.html',

  // today.json のパス（GitHub Pages配信の場合）
  DATA_URL: './data/today.json',
};
```

---

## `today.json` に追加が必要なフィールド

既存の `today.json` に以下のフィールドを追加すること。
`fetch_daily.py`（またはGemini生成スクリプト）側での出力対応が必要。

```json
{
  "date": "03-04",
  "event": {
    "year": "1665",
    "text": "イギリスがオランダに宣戦布告し、第二次英蘭戦争が勃発。"
  },
  "paper": {
    "title": "Abstracts of Books in the Field of...",
    "abstract_ja": "スカンジナビアのスラブ学者・バルト学者が近年刊行した...",
    "connection": "この出来事を深掘りするなら、<strong>スカンジナビアとバルト地域の歴史・文化</strong>を扱う以下の論文が参考になります。",
    "author": "Kjetil Rå Hauge",
    "journal": "Scando-Slavica",
    "year": "2010",
    "doi_url": "https://doi.org/xxxxxxxxxx"
  },
  "database": {
    "name": "Taylor & Francis SSH Library",
    "description": "社会科学・人文科学分野の1,400誌以上を収録するジャーナルパッケージ。1997年以降のバックファイルにアクセス可能。",
    "url": "https://xxxx"
  }
}
```

### `fetch_daily.py` への追記指示

Geminiへのプロンプトに以下の出力を追加すること。

| フィールド | Geminiへの指示 |
|-----------|--------------|
| `paper.abstract_ja` | 論文の抄録を150〜200字程度の日本語に翻訳・要約する |
| `paper.connection` | 今日の出来事と論文の関連を1文で説明する。`<strong>`タグで関連キーワードを1箇所囲む |

---

## 実装上の注意

- `connection_text` は `innerHTML` で挿入すること（`<strong>` タグを有効にするため）
- 著者が複数いる場合は筆頭著者のみ表示し、末尾に「ほか」を付ける
- `doi_url` が存在しない場合、「この論文を読む」ボタンは非表示にする
- QRコードの `data=` パラメータはURLエンコードすること
- ウィジェットは iframe / JS スニペット どちらの埋め込みにも対応できるよう、`body` の背景色は埋め込み時に `transparent` に切り替えられるようにしておく（クエリパラメータ `?embed=true` で制御する等）
