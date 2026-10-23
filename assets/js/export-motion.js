(() => {
  "use strict";

  const body = document.body;
  if (!body?.classList.contains("export-redesign")) return;

  const forceMotion = true;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches && !forceMotion;
  const coarsePointer = window.matchMedia("(hover: none), (pointer: coarse)").matches;
  body.classList.add("export-motion-ready", "export-motion-forced");

  const staticNodes = [...document.querySelectorAll("[data-export-reveal]")];
  let revealObserver = null;
  let cardObserver = null;

  if (!reduceMotion && "IntersectionObserver" in window) {
    revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-export-visible");
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -8%", threshold: 0.12 });

    cardObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-export-visible");
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -6%", threshold: 0.08 });
  }

  staticNodes.forEach((node, index) => {
    node.style.setProperty("--export-delay", `${Math.min(index, 4) * 70}ms`);
    if (revealObserver) revealObserver.observe(node);
    else node.classList.add("is-export-visible");
  });

  const grids = [...document.querySelectorAll("[data-vehicle-grid='new'], [data-used-product-grid]")];
  const cardSelector = ".catalog-card, .used-product-card";
  const langCopy = {
    zh: "查看详情",
    en: "View Details",
    ru: "Подробнее"
  };

  const activeLanguage = () => {
    const value = document.documentElement.lang.toLowerCase();
    if (value.startsWith("en")) return "en";
    if (value.startsWith("ru")) return "ru";
    return "zh";
  };

  const updateCardLanguage = () => {
    const label = langCopy[activeLanguage()] || langCopy.zh;
    document.querySelectorAll(".export-card-link").forEach((link) => { link.textContent = label; });
  };

  const enhanceCard = (card, index) => {
    if (!(card instanceof HTMLElement) || card.dataset.exportEnhanced === "true") return;
    card.dataset.exportEnhanced = "true";
    card.setAttribute("data-export-card", "");
    card.style.setProperty("--export-delay", `${(index % 3) * 95}ms`);

    const imageLink = card.querySelector(".catalog-image, .used-product-image");
    const bodyNode = card.querySelector(".catalog-body, .used-product-body");
    if (imageLink && bodyNode && !bodyNode.querySelector(".export-card-link")) {
      const link = document.createElement("a");
      link.className = "export-card-link";
      link.href = imageLink.getAttribute("href") || "#";
      link.textContent = langCopy[activeLanguage()] || langCopy.zh;
      bodyNode.appendChild(link);
    }

    if (!coarsePointer) {
      card.addEventListener("pointermove", (event) => {
        const rect = card.getBoundingClientRect();
        const x = (event.clientX - rect.left) / Math.max(1, rect.width) - .5;
        card.style.setProperty("--export-shine-x", `${50 + x * 36}%`);
      });
    }

    if (cardObserver) cardObserver.observe(card);
    else card.classList.add("is-export-visible");
  };

  const cardsInGrid = (grid) => [...grid.querySelectorAll(cardSelector)];
  const enhanceGrid = (grid) => cardsInGrid(grid).forEach(enhanceCard);

  grids.forEach((grid) => {
    enhanceGrid(grid);
    const mutationObserver = new MutationObserver(() => {
      enhanceGrid(grid);
      if (grid.matches("[data-vehicle-grid='new']")) {
        window.setTimeout(() => {
          populateBrandFilter();
          applyQuickFilters();
        }, 0);
      }
    });
    mutationObserver.observe(grid, { childList: true });
  });

  const brandSelect = document.querySelector("[data-export-brand]");
  const modelSearch = document.querySelector("[data-export-search]");
  const resetButton = document.querySelector("[data-export-filter-reset]");

  function newCards() {
    return [...document.querySelectorAll("[data-vehicle-grid='new'] .catalog-card")];
  }

  function cardBrand(card) {
    return card.querySelector(".catalog-specs p:first-child strong")?.textContent.trim() || "";
  }

  function populateBrandFilter() {
    if (!brandSelect) return;
    const current = brandSelect.value;
    const brands = [...new Set(newCards().map(cardBrand).filter(Boolean))].sort((a, b) => a.localeCompare(b, "zh-Hans-CN"));
    const placeholder = ({ zh: "全部品牌", en: "All Brands", ru: "Все марки" })[activeLanguage()] || "全部品牌";
    brandSelect.replaceChildren(new Option(placeholder, ""), ...brands.map((brand) => new Option(brand, brand)));
    brandSelect.value = brands.includes(current) ? current : "";
  }

  function applyQuickFilters() {
    const brand = brandSelect?.value.trim() || "";
    const query = modelSearch?.value.trim().toLowerCase() || "";
    newCards().forEach((card) => {
      const matchesBrand = !brand || cardBrand(card) === brand;
      const matchesQuery = !query || card.textContent.toLowerCase().includes(query);
      card.hidden = !(matchesBrand && matchesQuery);
    });
  }

  brandSelect?.addEventListener("change", applyQuickFilters);
  modelSearch?.addEventListener("input", applyQuickFilters);
  resetButton?.addEventListener("click", () => {
    if (brandSelect) brandSelect.value = "";
    if (modelSearch) modelSearch.value = "";
    const allCategory = document.querySelector(".catalog-toolbar [data-new-category='']") || document.querySelector(".catalog-toolbar button");
    if (allCategory && !allCategory.classList.contains("is-active")) allCategory.click();
    applyQuickFilters();
  });

  populateBrandFilter();
  applyQuickFilters();

  const languageObserver = new MutationObserver(() => {
    updateCardLanguage();
    populateBrandFilter();
  });
  languageObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });

  const hero = document.querySelector(".export-hero");
  const productCards = () => [...document.querySelectorAll("[data-export-card].is-export-visible")];
  let scrollQueued = false;

  const updateScrollMotion = () => {
    scrollQueued = false;
    if (reduceMotion) return;
    const viewport = window.innerHeight;
    if (hero) {
      const progress = Math.max(0, Math.min(1, window.scrollY / Math.max(1, hero.offsetHeight)));
      hero.style.setProperty("--export-hero-y", `${window.scrollY * .13}px`);
      hero.style.setProperty("--export-hero-scale", String(1.08 + progress * .1));
      hero.style.setProperty("--export-copy-y", `${progress * 68}px`);
      hero.style.setProperty("--export-hero-opacity", String(1 - progress * .72));
    }
    productCards().forEach((card) => {
      const rect = card.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > viewport) return;
      const progress = Math.max(-1, Math.min(1, (rect.top + rect.height / 2 - viewport / 2) / viewport));
      card.style.setProperty("--export-card-y", `${progress * -13}px`);
      card.style.setProperty("--export-card-scale", String(1.035 + Math.abs(progress) * .02));
    });
  };

  const requestScrollMotion = () => {
    if (scrollQueued) return;
    scrollQueued = true;
    requestAnimationFrame(updateScrollMotion);
  };

  window.addEventListener("scroll", requestScrollMotion, { passive: true });
  window.addEventListener("resize", requestScrollMotion, { passive: true });
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-new-category], [data-new-page], [data-used-page], [data-used-filter-reset], [data-used-id-search]")) {
      window.setTimeout(() => grids.forEach(enhanceGrid), 50);
    }
  });

  updateCardLanguage();
  updateScrollMotion();
})();
