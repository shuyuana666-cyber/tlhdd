(() => {
  "use strict";

  const body = document.body;
  if (!body?.classList.contains("about-redesign")) return;

  const forceMotion = body.classList.contains("about-redesign");
  const reduceMotion = { matches: window.matchMedia("(prefers-reduced-motion: reduce)").matches && !forceMotion };
  document.querySelectorAll(".about-brand-grid > span").forEach((item, index) => {
    item.setAttribute("data-about-reveal", "");
    item.style.setProperty("--delay", `${(index % 8) * 55}ms`);
  });
  body.classList.add("about-motion-ready", "about-motion-forced");

  const revealItems = [...document.querySelectorAll("[data-about-reveal]")];
  if (reduceMotion.matches || !("IntersectionObserver" in window)) {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  } else {
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -9%", threshold: 0.12 });
    revealItems.forEach((item) => revealObserver.observe(item));
  }

  const revealScenes = [];
  const introScene = document.querySelector(".about-intro-top");
  const introScenePhoto = document.querySelector(".about-intro-photo");
  if (introScene && introScenePhoto) revealScenes.push({ root: introScene, items: [introScenePhoto] });
  document.querySelectorAll(".about-unit").forEach((unit) => {
    revealScenes.push({ root: unit, items: [...unit.querySelectorAll(".about-unit-photo, .about-unit-copy")] });
  });
  const teamScene = document.querySelector(".about-team");
  const teamWindow = document.querySelector(".about-team-window");
  if (teamScene && teamWindow) revealScenes.push({ root: teamScene, items: [teamWindow] });

  if (reduceMotion.matches || !("IntersectionObserver" in window)) {
    revealScenes.forEach((scene) => scene.items.forEach((item) => item.classList.add("is-visible")));
  } else {
    const sceneMap = new Map(revealScenes.map((scene) => [scene.root, scene.items]));
    const sceneObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        (sceneMap.get(entry.target) || []).forEach((item) => item.classList.add("is-visible"));
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -7%", threshold: 0.16 });
    revealScenes.forEach((scene) => sceneObserver.observe(scene.root));
  }

  const formatNumber = (value) => new Intl.NumberFormat(document.documentElement.lang || "zh-CN").format(value);
  const counters = [...document.querySelectorAll("[data-about-count]")];
  const runCounter = (node) => {
    if (node.dataset.counted === "true") return;
    node.dataset.counted = "true";
    const target = Number(node.dataset.aboutCount || node.textContent.replace(/\D/g, ""));
    if (!Number.isFinite(target)) return;
    if (reduceMotion.matches) {
      node.textContent = formatNumber(target);
      return;
    }
    const startValue = target > 1000 ? Math.max(0, target - 260) : 0;
    const started = performance.now();
    const duration = 1450;
    const tick = (now) => {
      const progress = Math.min(1, (now - started) / duration);
      const eased = 1 - Math.pow(1 - progress, 4);
      node.textContent = formatNumber(Math.round(startValue + (target - startValue) * eased));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  if ("IntersectionObserver" in window) {
    const countObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        runCounter(entry.target);
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.45 });
    counters.forEach((counter) => countObserver.observe(counter));
  } else {
    counters.forEach(runCounter);
  }

  const parallaxSections = [
    document.querySelector(".about-hero"),
    document.querySelector(".about-standard"),
    document.querySelector(".about-brands")
  ].filter(Boolean);
  const introPhoto = document.querySelector(".about-intro-photo");
  const units = [...document.querySelectorAll(".about-unit")];
  let ticking = false;
  const updateParallax = () => {
    ticking = false;
    if (reduceMotion.matches) return;
    const viewport = window.innerHeight;
    parallaxSections.forEach((section, index) => {
      const rect = section.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > viewport) return;
      const centerDelta = rect.top + rect.height / 2 - viewport / 2;
      const distance = Math.max(-68, Math.min(68, centerDelta * (index ? -0.075 : -0.052)));
      section.style.setProperty("--about-parallax", `${distance}px`);
    });
    const hero = parallaxSections[0];
    if (hero) {
      const heroProgress = Math.max(0, Math.min(1, window.scrollY / Math.max(1, hero.offsetHeight)));
      hero.style.setProperty("--about-scale", String(1.04 + heroProgress * 0.1));
      hero.style.setProperty("--hero-copy-shift", `${heroProgress * 72}px`);
      hero.style.setProperty("--hero-copy-opacity", String(1 - heroProgress * 0.72));
    }
    if (introPhoto) {
      const rect = introPhoto.getBoundingClientRect();
      const progress = Math.max(-1, Math.min(1, (rect.top + rect.height / 2 - viewport / 2) / viewport));
      introPhoto.style.setProperty("--photo-drift", `${progress * -42}px`);
    }
    units.forEach((unit) => {
      const rect = unit.getBoundingClientRect();
      if (rect.bottom < -150 || rect.top > viewport + 150) return;
      const progress = Math.max(-1, Math.min(1, (rect.top + rect.height / 2 - viewport / 2) / viewport));
      unit.style.setProperty("--unit-drift", `${progress * -34}px`);
      unit.style.setProperty("--unit-copy-drift", `${progress * 13}px`);
    });
  };
  const requestParallax = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(updateParallax);
  };
  window.addEventListener("scroll", requestParallax, { passive: true });
  window.addEventListener("resize", requestParallax, { passive: true });
  requestParallax();

  const team = document.querySelector("[data-about-team]");
  if (team) {
    const track = team.querySelector(".about-team-track");
    const slides = [...team.querySelectorAll(".about-team-track article")];
    const dots = team.querySelector("[data-about-team-dots]");
    const prev = team.querySelector("[data-about-team-prev]");
    const next = team.querySelector("[data-about-team-next]");
    let index = 0;
    let timer = 0;

    const visibleCount = () => {
      if (window.innerWidth <= 600) return 1;
      if (window.innerWidth <= 900) return 2;
      if (window.innerWidth <= 1180) return 4;
      return 5;
    };
    const maxIndex = () => Math.max(0, slides.length - visibleCount());
    const renderDots = () => {
      if (!dots) return;
      dots.replaceChildren();
      for (let i = 0; i <= maxIndex(); i += 1) {
        const button = document.createElement("button");
        button.type = "button";
        button.setAttribute("aria-label", `第 ${i + 1} 组`);
        button.addEventListener("click", () => {
          index = i;
          render();
          restart();
        });
        dots.appendChild(button);
      }
    };
    const render = () => {
      index = Math.max(0, Math.min(index, maxIndex()));
      track?.style.setProperty("--team-index", String(index));
      [...(dots?.children || [])].forEach((dot, dotIndex) => dot.classList.toggle("is-active", dotIndex === index));
    };
    const step = (direction) => {
      const max = maxIndex();
      index = max ? (index + direction + max + 1) % (max + 1) : 0;
      render();
    };
    const stop = () => window.clearInterval(timer);
    const start = () => {
      stop();
      if (!reduceMotion.matches && maxIndex() > 0) timer = window.setInterval(() => step(1), 3000);
    };
    const restart = () => {
      stop();
      start();
    };

    prev?.addEventListener("click", () => { step(-1); restart(); });
    next?.addEventListener("click", () => { step(1); restart(); });
    team.addEventListener("mouseenter", stop);
    team.addEventListener("mouseleave", start);
    team.addEventListener("focusin", stop);
    team.addEventListener("focusout", start);
    window.addEventListener("resize", () => { renderDots(); render(); start(); });
    document.addEventListener("visibilitychange", () => document.hidden ? stop() : start());
    renderDots();
    render();
    start();
  }

  const honors = document.querySelector("[data-about-honors]");
  if (honors) {
    const cards = [...honors.querySelectorAll(".about-certificate")];
    const dots = honors.querySelector("[data-about-honor-dots]");
    const prev = honors.querySelector("[data-about-honors] [data-about-honor-prev]") || honors.querySelector("[data-about-honor-prev]");
    const next = honors.querySelector("[data-about-honors] [data-about-honor-next]") || honors.querySelector("[data-about-honor-next]");
    let active = 1;
    let timer = 0;

    const positionClass = (offset) => {
      if (offset === 0) return "is-active";
      if (offset === -1) return "is-prev";
      if (offset === 1) return "is-next";
      return offset < 0 ? "is-far-prev" : "is-far-next";
    };
    const render = () => {
      cards.forEach((card, cardIndex) => {
        card.classList.remove("is-active", "is-prev", "is-next", "is-far-prev", "is-far-next");
        let offset = cardIndex - active;
        if (offset > cards.length / 2) offset -= cards.length;
        if (offset < -cards.length / 2) offset += cards.length;
        card.classList.add(positionClass(offset));
        card.setAttribute("aria-hidden", offset === 0 ? "false" : "true");
      });
      [...(dots?.children || [])].forEach((dot, dotIndex) => dot.classList.toggle("is-active", dotIndex === active));
    };
    const go = (nextIndex) => {
      active = (nextIndex + cards.length) % cards.length;
      render();
    };
    const stop = () => window.clearInterval(timer);
    const start = () => {
      stop();
      if (!reduceMotion.matches && cards.length > 1) timer = window.setInterval(() => go(active + 1), 3400);
    };
    const restart = () => { stop(); start(); };

    cards.forEach((card, cardIndex) => card.addEventListener("click", () => { go(cardIndex); restart(); }));
    if (dots) {
      cards.forEach((_, cardIndex) => {
        const button = document.createElement("button");
        button.type = "button";
        button.setAttribute("aria-label", `第 ${cardIndex + 1} 项荣誉`);
        button.addEventListener("click", () => { go(cardIndex); restart(); });
        dots.appendChild(button);
      });
    }
    prev?.addEventListener("click", () => { go(active - 1); restart(); });
    next?.addEventListener("click", () => { go(active + 1); restart(); });
    honors.addEventListener("mouseenter", stop);
    honors.addEventListener("mouseleave", start);
    render();
    start();
  }
})();
