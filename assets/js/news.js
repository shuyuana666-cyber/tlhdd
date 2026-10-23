(function () {
  "use strict";
  if (!document.querySelector("[data-home-news], [data-news-list], [data-news-detail]")) return;

  const defaults = window.TlhNewsArticles || [];
  let articles = [];
  let language = "zh";
  let category = new URLSearchParams(location.search).get("category") || "all";
  let media = [];
  let contentLoaded = false;
  let loadFailed = false;
  const text = {
    all: { zh: "全部资讯", en: "All articles", ru: "Все статьи" },
    company: { zh: "公司资讯", en: "Company", ru: "О компании" },
    industry: { zh: "行业动态", en: "Industry", ru: "Отрасль" },
    service: { zh: "业务资讯", en: "Services", ru: "Услуги" },
    more: { zh: "更多内容", en: "All articles", ru: "Все статьи" },
    read: { zh: "阅读全文", en: "Read article", ru: "Читать статью" },
    source: { zh: "来源：通利华汽车集团", en: "Source: Tonglihua Automotive Group", ru: "Источник: Tonglihua Automotive Group" },
    updated: { zh: "发布时间：", en: "Published:", ru: "Опубликовано:" },
    previous: { zh: "上一篇", en: "Previous article", ru: "Предыдущая статья" },
    next: { zh: "下一篇", en: "Next article", ru: "Следующая статья" },
    related: { zh: "其他内容", en: "More to read", ru: "Другие статьи" },
    back: { zh: "返回新闻中心", en: "Back to news", ru: "Вернуться к новостям" },
    business: { zh: "了解相关业务", en: "Explore this service", ru: "Узнать об услуге" },
    empty: { zh: "暂无相关资讯", en: "No articles in this category", ru: "В этой категории пока нет статей" },
    missing: { zh: "未找到这篇资讯", en: "Article not found", ru: "Статья не найдена" },
    loading: { zh: "正在加载文章…", en: "Loading article…", ru: "Загрузка статьи…" },
    loadError: { zh: "新闻加载失败，请刷新重试", en: "Could not load news. Please refresh to retry.", ru: "Не удалось загрузить новости. Обновите страницу." },
    missingBody: { zh: "文章可能已下线，请返回新闻中心查看其他内容。", en: "This article may no longer be available. Browse other articles in the news center.", ru: "Статья может быть недоступна. Посмотрите другие материалы в разделе новостей." }
  };
  const local = value => typeof value === "string" ? value : (value?.[language] || value?.zh || "");
  const copy = key => local(text[key]);
  const escape = value => String(value || "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
  const href = article => `news-detail.html?id=${encodeURIComponent(article.id)}`;
  const arrow = '<i data-lucide="arrow-right" aria-hidden="true"></i>';
  const safeImage = url => {
    try { const parsed = new URL(url, location.origin); return parsed.protocol === "https:" || (parsed.origin === location.origin && /^\/(assets|uploads)\//.test(parsed.pathname)) ? parsed.href : ""; } catch { return ""; }
  };


  function imageFor(article) {
    if (article.image) return safeImage(article.image);
    const item = media.find(item => item.page_key === "home" && item.media_key === article.mediaKey);
    if (item) return [false, 0, "0"].includes(item.is_active) ? "" : safeImage(item.optimized_url || item.image_url);
    return "/assets/default-media/024c0f7a350b47b2626664145306d3e1-optimized.webp";
  }

  function dateHtml(article, label = true) {
    if (!article.published || !/^\d{4}-\d{2}-\d{2}/.test(article.published)) return "";
    const date = new Date(article.published.replace(" ", "T") + "Z");
    if (Number.isNaN(date.getTime())) return "";
    const stamp = new Date(date.getTime() + 8 * 3600000).toISOString().slice(0, 16).replace("T", " ");
    return `<time datetime="${date.toISOString()}">${label ? escape(copy("updated")) + "　" : ""}${stamp}</time>`;
  }

  function emptyState() {
    return `<p class="news-empty" role="status">${escape(copy(loadFailed ? "loadError" : contentLoaded ? "empty" : "loading"))}</p>`;
  }

  function metadata(article) {
    return `<span>${escape(copy(article.category))}</span>${dateHtml(article)}`;
  }

  function renderHome() {
    const grid = document.querySelector("[data-home-news]");
    if (!grid) return;
    const [feature, ...rest] = articles.slice(0, 3);
    if (!feature) {
      grid.innerHTML = emptyState();
      return;
    }
    const image = imageFor(feature);
    grid.innerHTML = `<a class="home-news-feature" href="${href(feature)}">
      <div class="home-news-image${image ? "" : " is-image-missing"}">${image ? `<img src="${escape(image)}" alt="" loading="lazy" decoding="async">` : '<i data-lucide="file-text" aria-hidden="true"></i>'}</div>
      <div class="home-news-feature-copy"><div class="news-meta">${metadata(feature)}</div><h3>${escape(local(feature.title))}</h3><p>${escape(local(feature.summary))}</p><span class="news-read">${escape(copy("read"))}${arrow}</span></div>
    </a><div class="home-news-summaries">${rest.map(article => `<a class="home-news-summary" href="${href(article)}"><div class="news-meta">${metadata(article)}</div><h3>${escape(local(article.title))}</h3><p>${escape(local(article.summary))}</p><span class="news-read">${escape(copy("read"))}${arrow}</span></a>`).join("")}</div>`;
    const more = document.querySelector("[data-news-more]");
    if (more) more.innerHTML = `${escape(copy("more"))}${arrow}`;
  }

  function renderList() {
    const list = document.querySelector("[data-news-list]");
    if (!list) return;
    document.title = `${local({ zh: "新闻中心", en: "News Center", ru: "Новости" })} | 通利华汽车集团`;
    const filtered = articles.filter(article => category === "all" || article.category === category);
    list.innerHTML = filtered.map(article => `<a class="news-list-row" href="${href(article)}"><div><div class="news-meta">${metadata(article)}</div><h2>${escape(local(article.title))}</h2><p>${escape(local(article.summary))}</p></div><span class="news-list-arrow">${arrow}</span></a>`).join("") || emptyState();
    document.querySelectorAll("[data-news-category]").forEach(button => {
      button.textContent = copy(button.dataset.newsCategory);
      button.setAttribute("aria-pressed", String(button.dataset.newsCategory === category));
    });
  }

  function paragraphs(value) {
    return local(value).split(/\n+/).filter(line => line.trim()).map(line => `<p>${escape(line)}</p>`).join("");
  }

  function renderDetail() {
    const detail = document.querySelector("[data-news-detail]");
    if (!detail) return;
    const id = new URLSearchParams(location.search).get("id");
    const index = articles.findIndex(article => article.id === id);
    const article = articles[index];
    if (!article) {
      if (!contentLoaded) {
        detail.innerHTML = `<p class="news-empty" role="status">${escape(copy("loading"))}</p>`;
        return;
      }
      if (loadFailed) { detail.innerHTML = emptyState(); return; }
      detail.innerHTML = `<div class="news-empty"><h1>${escape(copy("missing"))}</h1><p>${escape(copy("missingBody"))}</p><a href="news.html">${escape(copy("back"))}${arrow}</a></div>`;
      document.title = `${copy("missing")} | 通利华汽车集团`;
      return;
    }
    const title = local(article.title);
    document.title = `${title} | 通利华汽车集团`;
    document.querySelectorAll("[data-news-current]").forEach(node => { node.textContent = copy(article.category); });
    document.querySelectorAll("[data-news-crumb-title]").forEach(node => { node.textContent = title; node.title = title; });
    document.querySelectorAll("[data-detail-category]").forEach(node => {
      if (node.dataset.detailCategory === article.category) node.setAttribute("aria-current", "true");
      else node.removeAttribute("aria-current");
    });
    const adjacent = (item, key) => item ? `<a href="${href(item)}" title="${escape(local(item.title))}"><span>${escape(copy(key))}：</span><span>${escape(local(item.title))}</span></a>` : `<span class="news-no-adjacent">${escape(copy(key))}：${local({zh:"无",en:"None",ru:"Нет"})}</span>`;
    const body = article.content ? local(article.content) : `<p>${escape(local(article.summary))}</p>${(article.sections || []).map(section => `${local(section.title) ? `<h2>${escape(local(section.title))}</h2>` : ""}${paragraphs(section.body)}`).join("")}`;
    detail.innerHTML = `<article class="news-article">
      <header class="news-article-header"><h1>${escape(title)}</h1><div class="news-article-meta"><div class="news-publication">${dateHtml(article) || `<span>${escape(copy("updated"))}　—</span>`}<span>${local({zh:"来源：",en:"Source:",ru:"Источник:"})}　${escape(article.source || "通利华汽车集团")}</span></div>${shareControls(title)}</div></header>
      <div class="news-article-body">${body}</div>
      <nav class="news-article-pagination" aria-label="${escape(copy("related"))}">${adjacent(articles[index - 1], "previous")}${adjacent(articles[index + 1], "next")}</nav>
    </article><section class="news-related"><h2>${escape(copy("related"))}</h2><div>${articles.filter(item => item.id !== id).slice(0, 4).map(item => `<a href="${href(item)}"><h3>${escape(local(item.title))}</h3>${dateHtml(item, false)}<p>${escape(local(item.summary))}</p></a>`).join("") || `<p class="news-empty">${escape(copy("empty"))}</p>`}</div></section>`;
  }

  function shareControls(title) {
    const url = encodeURIComponent(location.href), caption = encodeURIComponent(title);
    const icons = {
      weibo: '<path d="M13 7c5-4 10 1 6 5 4 1 3 7-3 9-6 2-13 0-13-4 0-3 5-8 8-8 2 0 1 2 2-2Z"/><ellipse cx="11" cy="16" rx="4" ry="3" fill="currentColor" stroke="none"/><path d="M17 3c4 0 6 3 5 6M18 6c1 0 2 1 2 2"/>',
      wechat: '<path d="M14 13c0 4-4 6-8 4l-3 1 1-3C0 11 3 5 8 5c4 0 7 3 6 8Z"/><path d="M14 10c7-1 10 7 4 10l-3-1-2 1v-2c-5-2-3-8 1-8Z"/><path d="M6 9h.1M10 9h.1M14 14h.1M18 14h.1"/>',
      qq: '<path d="M8 9c-2-8 10-8 8 0l3 7-3-1 1 5-4-1h-2l-4 1 1-5-3 1 3-7Z"/><path d="M8 11h8"/>',
      qzone: '<path d="m12 2 3 7 7 1-5 5 1 7-6-4-6 4 1-7-5-5 7-1 3-7Z"/><path d="m8 10 7 1-6 5h7"/>',
      link: '<path d="m10 14 4-4M9 16l-2 2a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0M15 8l2-2a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0"/>'
    };
    const icon = key => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[key]}</svg>`;
    return `<div class="news-share" aria-label="${local({zh:"分享文章",en:"Share article",ru:"Поделиться"})}">
      <a class="share-weibo" href="https://service.weibo.com/share/share.php?url=${url}&title=${caption}" target="_blank" rel="noopener noreferrer" aria-label="微博分享" title="微博分享">${icon("weibo")}</a>
      <button class="share-wechat" type="button" data-news-copy="wechat" aria-label="复制链接到微信分享" title="复制链接到微信分享">${icon("wechat")}</button>
      <a href="https://connect.qq.com/widget/shareqq/index.html?url=${url}&title=${caption}" target="_blank" rel="noopener noreferrer" aria-label="QQ分享" title="QQ分享">${icon("qq")}</a>
      <a href="https://sns.qzone.qq.com/cgi-bin/qzshare/cgi_qzshare_onekey?url=${url}&title=${caption}" target="_blank" rel="noopener noreferrer" aria-label="QQ空间分享" title="QQ空间分享">${icon("qzone")}</a>
      <button type="button" data-news-copy="link" aria-label="复制文章链接" title="复制文章链接">${icon("link")}</button>
    </div>`;
  }

  async function copyArticle(channel) {
    let success = false;
    try { await navigator.clipboard.writeText(location.href); success = true; } catch {
      const field = document.createElement("textarea"); field.value = location.href; field.className = "news-copy-field";
      document.body.append(field); field.select(); success = document.execCommand("copy"); field.remove();
    }
    let toast = document.querySelector(".news-share-feedback");
    if (!toast) { toast = document.createElement("div"); toast.className = "news-share-feedback"; toast.setAttribute("role", "status"); document.body.append(toast); }
    toast.textContent = success ? (channel === "wechat" ? local({zh:"链接已复制，请在微信中粘贴分享",en:"Link copied. Paste it in WeChat to share.",ru:"Ссылка скопирована для WeChat."}) : local({zh:"文章链接已复制",en:"Article link copied",ru:"Ссылка скопирована"})) : local({zh:"复制失败，请复制浏览器地址栏中的链接",en:"Please copy the URL from your address bar.",ru:"Скопируйте ссылку из адресной строки."});
    toast.hidden = false;
    clearTimeout(copyArticle.timer); copyArticle.timer = setTimeout(() => { toast.hidden = true; }, 3000);
  }

  function render() {
    renderHome();
    renderList();
    renderDetail();
    if (window.lucide) window.lucide.createIcons();
  }

  window.TlhNews = {
    setLanguage(lang) { language = ["zh", "en", "ru"].includes(lang) ? lang : "zh"; render(); },
    finishLoading() { contentLoaded = true; loadFailed = true; renderHome(); renderList(); renderDetail(); if (window.lucide) window.lucide.createIcons(); },
    updateData(data) {
      contentLoaded = true;
      media = data.page_media || [];
      const banner = imageFor(defaults[0]);
      if (banner) document.querySelector('.news-masthead')?.style.setProperty('--news-banner-image', `url("${banner}")`);
      loadFailed = false;
      articles = (data.news || []).map(item => ({
        id: item.slug || String(item.id), category: item.category,
        title: { zh: item.title_zh, en: item.title_en, ru: item.title_ru },
        summary: Object.fromEntries(["zh", "en", "ru"].map(lang => {
          const node = document.createElement("template"); node.innerHTML = item[`content_${lang}`] || "";
          return [lang, item[`summary_${lang}`] || (node.content.textContent || "").slice(0, 180)];
        })),
        content: { zh: item.content_zh, en: item.content_en, ru: item.content_ru },
        image: item.image_url, mediaKey: "news-feature", published: item.published_at, source: item.source
      }));
      render();
    }
  };

  document.addEventListener("click", event => {
    const share = event.target.closest("[data-news-copy]");
    if (share) copyArticle(share.dataset.newsCopy);
    const button = event.target.closest("[data-news-category]");
    if (button) { category = button.dataset.newsCategory; renderList(); if (window.lucide) window.lucide.createIcons(); }
  });
  document.addEventListener("error", event => {
    if (event.target.matches?.(".home-news-image img")) {
      const frame = event.target.parentElement;
      frame.classList.add("is-image-missing");
      frame.innerHTML = '<i data-lucide="file-text" aria-hidden="true"></i>';
      if (window.lucide) window.lucide.createIcons();
    }
  }, true);
  render();
})();
