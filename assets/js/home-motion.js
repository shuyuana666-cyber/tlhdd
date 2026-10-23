(function () {
  "use strict";

  var forceMotion = document.body && document.body.classList.contains("home-redesign");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches && !forceMotion;
  var coarsePointer = window.matchMedia("(hover: none), (pointer: coarse)").matches;
  var scrollScenes = [];
  var scrollQueued = false;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function sceneProgress(node) {
    var rect = node.getBoundingClientRect();
    return clamp((window.innerHeight - rect.top) / (window.innerHeight + rect.height), 0, 1);
  }

  function initReveal() {
    var nodes = Array.prototype.slice.call(document.querySelectorAll("[data-reveal]"));
    if (!nodes.length) return;
    if (reduceMotion || !("IntersectionObserver" in window)) {
      nodes.forEach(function (node) { node.classList.add("is-visible"); });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -7% 0px" });

    nodes.forEach(function (node, index) {
      var parent = node.parentElement;
      var siblings = parent ? Array.prototype.slice.call(parent.querySelectorAll(":scope > [data-reveal]")) : [];
      var order = siblings.indexOf(node);
      node.style.transitionDelay = Math.max(0, order) * 105 + "ms";
      node.dataset.revealOrder = String(index);
      observer.observe(node);
    });
  }

  function animateCounter(node) {
    var target = Number(node.dataset.counter || 0);
    if (!target || node.dataset.counted === "true") return;
    node.dataset.counted = "true";

    var suffix = node.querySelector("span, em");
    var startAt = performance.now();
    var duration = 1450;
    var startValue = target > 100 ? Math.round(target * 0.72) : 0;

    function tick(now) {
      var progress = Math.min(1, (now - startAt) / duration);
      var eased = 1 - Math.pow(1 - progress, 4);
      var value = Math.round(startValue + (target - startValue) * eased);
      if (suffix) {
        if (suffix.previousSibling) suffix.previousSibling.nodeValue = String(value);
        else node.insertBefore(document.createTextNode(String(value)), suffix);
      } else {
        node.textContent = String(value);
      }
      if (progress < 1) window.requestAnimationFrame(tick);
    }

    window.requestAnimationFrame(tick);
  }

  function initCounters() {
    var nodes = Array.prototype.slice.call(document.querySelectorAll("[data-counter]"));
    if (!nodes.length) return;
    if (reduceMotion || !("IntersectionObserver" in window)) {
      nodes.forEach(function (node) {
        var suffix = node.querySelector("span, em");
        if (suffix && suffix.previousSibling) suffix.previousSibling.nodeValue = node.dataset.counter;
        else if (!suffix) node.textContent = node.dataset.counter;
      });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.42 });

    nodes.forEach(function (node) { observer.observe(node); });
  }

  function initValueWall() {
    var wall = document.querySelector("[data-values-wall]");
    if (!wall) return;
    var panels = Array.prototype.slice.call(wall.querySelectorAll("[data-value-panel]"));
    if (!panels.length) return;

    function activate(panel) {
      panels.forEach(function (item) {
        var active = item === panel;
        item.classList.toggle("is-active", active);
        item.setAttribute("aria-pressed", String(active));
      });
    }

    function clear() {
      if (coarsePointer) return;
      activate(null);
    }

    panels.forEach(function (panel) {
      panel.addEventListener("click", function () { activate(panel); });
      panel.addEventListener("focus", function () { activate(panel); });
      if (!reduceMotion) panel.addEventListener("mouseenter", function () { activate(panel); });
    });
    wall.addEventListener("mouseleave", clear);
    if (coarsePointer) activate(panels[0]);
    else clear();
  }

  function initHeroMotion() {
    var carousel = document.querySelector("[data-hero-carousel]");
    if (!carousel) return;
    var previous = carousel.querySelector("[data-hero-prev]");
    var next = carousel.querySelector("[data-hero-next]");
    var current = carousel.querySelector("[data-hero-current]");
    var total = carousel.querySelector("[data-hero-total]");
    var progress = carousel.querySelector("[data-hero-progress]");
    var copy = carousel.querySelector(".home-hero-copy");
    var title = carousel.querySelector("[data-hero-title]");
    var lastIndex = -1;
    var dragStart = null;

    function getState() {
      var slides = Array.prototype.slice.call(carousel.querySelectorAll("[data-hero-slide]"));
      var dots = Array.prototype.slice.call(carousel.querySelectorAll("[data-hero-dots] button"));
      var index = slides.findIndex(function (slide) { return slide.classList.contains("is-active"); });
      return { slides: slides, dots: dots, index: Math.max(0, index) };
    }

    function restartProgress() {
      if (!progress || reduceMotion) return;
      progress.classList.remove("is-running");
      void progress.offsetWidth;
      progress.classList.add("is-running");
    }

    function animateCopy() {
      if (!copy || reduceMotion) return;
      copy.classList.remove("is-changing");
      void copy.offsetWidth;
      copy.classList.add("is-changing");
    }

    function sync() {
      var state = getState();
      if (total) total.textContent = String(state.slides.length).padStart(2, "0");
      if (current) current.textContent = String(state.index + 1).padStart(2, "0");
      if (state.index !== lastIndex) {
        lastIndex = state.index;
        restartProgress();
        animateCopy();
      }
    }

    function move(direction) {
      var state = getState();
      if (!state.dots.length) return;
      var target = (state.index + direction + state.dots.length) % state.dots.length;
      state.dots[target].click();
    }

    if (previous) previous.addEventListener("click", function () { move(-1); });
    if (next) next.addEventListener("click", function () { move(1); });

    carousel.addEventListener("mouseenter", function () {
      if (progress) progress.style.animationPlayState = "paused";
    });
    carousel.addEventListener("mouseleave", function () {
      if (progress) progress.style.animationPlayState = "running";
    });

    carousel.addEventListener("pointerdown", function (event) {
      if (event.pointerType === "mouse") return;
      dragStart = event.clientX;
    }, { passive: true });
    carousel.addEventListener("pointerup", function (event) {
      if (dragStart === null) return;
      var delta = event.clientX - dragStart;
      dragStart = null;
      if (Math.abs(delta) > 45) move(delta > 0 ? -1 : 1);
    }, { passive: true });

    if (!reduceMotion && !coarsePointer) {
      carousel.addEventListener("mousemove", function (event) {
        var rect = carousel.getBoundingClientRect();
        var x = ((event.clientX - rect.left) / rect.width - 0.5) * -18;
        var y = ((event.clientY - rect.top) / rect.height - 0.5) * -12;
        carousel.querySelectorAll("[data-hero-slide]").forEach(function (slide) {
          slide.style.setProperty("--hero-x", x.toFixed(1) + "px");
          slide.style.setProperty("--hero-y", y.toFixed(1) + "px");
        });
      });
      carousel.addEventListener("mouseleave", function () {
        carousel.querySelectorAll("[data-hero-slide]").forEach(function (slide) {
          slide.style.setProperty("--hero-x", "0px");
          slide.style.setProperty("--hero-y", "0px");
        });
      });
    }

    var observer = new MutationObserver(function (mutations) {
      var relevant = mutations.some(function (mutation) {
        return mutation.target.matches && (mutation.target.matches("[data-hero-slide]") || mutation.target.matches("[data-hero-dots]"));
      });
      if (relevant) window.requestAnimationFrame(sync);
    });
    observer.observe(carousel, { subtree: true, childList: true, attributes: true, attributeFilter: ["class"] });
    if (title) new MutationObserver(animateCopy).observe(title, { childList: true, subtree: true, characterData: true });
    window.setTimeout(sync, 80);
    window.setTimeout(sync, 900);
  }

  function initBusinessTilt() {
    if (reduceMotion || coarsePointer) return;
    document.querySelectorAll(".kh-business-card").forEach(function (card) {
      card.addEventListener("mousemove", function (event) {
        var rect = card.getBoundingClientRect();
        var px = clamp((event.clientX - rect.left) / rect.width, 0, 1);
        var py = clamp((event.clientY - rect.top) / rect.height, 0, 1);
        card.style.setProperty("--tilt-x", ((0.5 - py) * 5).toFixed(2) + "deg");
        card.style.setProperty("--tilt-y", ((px - 0.5) * 5).toFixed(2) + "deg");
        card.style.setProperty("--card-x", ((px - 0.5) * -10).toFixed(1) + "px");
        card.style.setProperty("--card-y", ((py - 0.5) * -8).toFixed(1) + "px");
        card.style.setProperty("--glow-x", (px * 100).toFixed(1) + "%");
        card.style.setProperty("--glow-y", (py * 100).toFixed(1) + "%");
      });
      card.addEventListener("mouseleave", function () {
        card.style.setProperty("--tilt-x", "0deg");
        card.style.setProperty("--tilt-y", "0deg");
        card.style.setProperty("--card-x", "0px");
        card.style.setProperty("--card-y", "0px");
      });
    });
  }

  function initScrollScenes() {
    var statement = document.querySelector("[data-parallax-section]");
    if (statement) {
      scrollScenes.push(function () {
        var rect = statement.getBoundingClientRect();
        var travel = Math.max(1, statement.offsetHeight - window.innerHeight);
        var progress = clamp(-rect.top / travel, 0, 1);
        statement.style.setProperty("--statement-progress", progress.toFixed(4));
        statement.style.setProperty("--statement-copy-opacity", clamp(0.32 + progress * 1.15, 0.32, 1).toFixed(3));
      });
    }

    var metrics = document.querySelector("[data-metric-scene]");
    if (metrics) {
      var layers = Array.prototype.slice.call(metrics.querySelectorAll("[data-metric-layer]"));
      scrollScenes.push(function () {
        var progress = sceneProgress(metrics);
        layers.forEach(function (layer) {
          var depth = Number(layer.dataset.metricLayer || 0);
          var shift = (progress - 0.5) * depth * 82;
          layer.style.setProperty("--metric-shift", shift.toFixed(1) + "px");
          if (layer.classList.contains("kh-photo-stat")) {
            layer.style.setProperty("--metric-scale", (0.96 + progress * 0.07).toFixed(4));
          }
        });
      });
    }

    var wall = document.querySelector("[data-photo-wall]");
    if (wall) {
      var rows = Array.prototype.slice.call(wall.querySelectorAll("[data-wall-row]"));
      scrollScenes.push(function () {
        var progress = sceneProgress(wall);
        wall.style.setProperty("--wall-progress", progress.toFixed(4));
        rows.forEach(function (row, index) {
          var direction = index % 2 === 0 ? 1 : -1;
          var distance = wall.offsetWidth * 0.18;
          var shift = direction * (0.5 - progress) * distance;
          row.style.setProperty("--wall-shift", shift.toFixed(1) + "px");
        });
      });
    }

    var pageProgress = document.querySelector("[data-page-progress]");
    if (pageProgress) {
      scrollScenes.push(function () {
        var max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
        pageProgress.style.setProperty("--page-progress", clamp(window.scrollY / max, 0, 1).toFixed(4));
      });
    }
  }

  function updateScrollScenes() {
    scrollScenes.forEach(function (update) { update(); });
    scrollQueued = false;
  }

  function requestScrollUpdate() {
    if (scrollQueued || reduceMotion) return;
    scrollQueued = true;
    window.requestAnimationFrame(updateScrollScenes);
  }

  function init() {
    document.body.classList.add("home-motion-ready", "home-motion-forced");
    initReveal();
    initCounters();
    initValueWall();
    initHeroMotion();
    initBusinessTilt();
    initScrollScenes();
    window.addEventListener("scroll", requestScrollUpdate, { passive: true });
    window.addEventListener("resize", requestScrollUpdate, { passive: true });
    updateScrollScenes();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
}());
