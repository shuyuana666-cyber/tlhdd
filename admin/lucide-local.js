(function () {
  const icons = {
    "panel-left-close": '<path d="M4 5h16v14H4z"/><path d="M9 5v14"/><path d="m15 9-3 3 3 3"/>',
    "layout-dashboard": '<rect x="3" y="3" width="7" height="8" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="15" width="7" height="6" rx="1"/>',
    database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    "message-square-text": '<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/><path d="M8 8h8"/><path d="M8 12h6"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
    "messages-square": '<path d="M14 9a4 4 0 0 1-4 4H6l-4 3V5a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4z"/><path d="M22 14a4 4 0 0 1-4 4h-4l-4 3v-4"/>',
    settings: '<path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5z"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1A2 2 0 1 1 4.4 17l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1A2 2 0 1 1 7.1 4.4l.1.1a1.6 1.6 0 0 0 1.8.3h.1a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1A2 2 0 1 1 19.8 7l-.1.1a1.6 1.6 0 0 0-.3 1.8v.1a1.6 1.6 0 0 0 1.5 1h.1a2 2 0 1 1 0 4h-.2a1.6 1.6 0 0 0-1.4 1z"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.9 4.9 1.4 1.4"/><path d="m17.7 17.7 1.4 1.4"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.3 17.7-1.4 1.4"/><path d="m19.1 4.9-1.4 1.4"/>',
    moon: '<path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    "key-round": '<path d="M2 18a6 6 0 1 1 10.6-3.8L22 4.8V8h-3.2v3.2h-3.2v3.2h-3.2A6 6 0 0 1 2 18z"/><circle cx="8" cy="18" r="1"/>',
    "log-out": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
    "upload-cloud": '<path d="M16 16l-4-4-4 4"/><path d="M12 12v9"/><path d="M20.4 18.6A5 5 0 0 0 18 9h-1.3A8 8 0 1 0 4 16.3"/><path d="M16 16l-4-4-4 4"/>',
    images: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-4-4L5 21"/>',
    "car-front": '<path d="M6 15h12"/><path d="M6 15l1.5-5.5A3 3 0 0 1 10.4 7h3.2a3 3 0 0 1 2.9 2.5L18 15"/><path d="M6 15v3"/><path d="M18 15v3"/><circle cx="8" cy="18" r="1"/><circle cx="16" cy="18" r="1"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
    "arrow-left": '<path d="M19 12H5"/><path d="m11 18-6-6 6-6"/>',
    "arrow-up-right": '<path d="M7 17 17 7"/><path d="M7 7h10v10"/>',
    "battery-charging": '<path d="M15 7h4a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-5"/><path d="M4 7h5"/><path d="M4 17h5"/><path d="M2 10v4"/><path d="m11 7-3 5h4l-3 5"/>',
    "badge-check": '<path d="M3.8 8.7 6.6 3.8l5.4.1 5.4-.1 2.8 4.9 2.7 4.9-2.7 4.9-2.8 4.9-5.4-.1-5.4.1-2.8-4.9-2.7-4.9z"/><path d="m8.5 12.5 2.4 2.4 4.8-5"/>',
    bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
    "building-2": '<path d="M6 22V3h12v19"/><path d="M6 12H4v10"/><path d="M18 9h2v13"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>',
    "circle-check": '<circle cx="12" cy="12" r="10"/><path d="m8 12 2.5 2.5L16 9"/>',
    "circle-user-round": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="10" r="3"/><path d="M7 20a5 5 0 0 1 10 0"/>',
    "clipboard-check": '<path d="M9 5h6"/><path d="M9 3h6v4H9z"/><path d="M6 5H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-1"/><path d="m8 14 2.5 2.5L16 11"/>',
    "clipboard-list": '<path d="M9 5h6"/><path d="M9 3h6v4H9z"/><path d="M6 5H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-1"/><path d="M8 12h8"/><path d="M8 16h8"/>',
    "clock-3": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6h5"/>',
    "calendar-days": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4"/><path d="M8 3v4"/><path d="M3 11h18"/><path d="M8 15h.01"/><path d="M12 15h.01"/><path d="M16 15h.01"/>',
    "file-check": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="m8 15 2 2 5-5"/>',
    "file-stack": '<path d="M16 2H8a2 2 0 0 0-2 2v12"/><path d="M20 6H12a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8z"/><path d="M16 6v6h4"/>',
    "file-text": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h6"/>',
    handshake: '<path d="m11 17 2 2a3 3 0 0 0 4.2 0l3.8-3.8"/><path d="m2 12 4-4 5 5"/><path d="m7 17 5-5"/><path d="m16 8 2-2 4 4"/><path d="M2 17l5 5"/>',
    house: '<path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M9 20v-6h6v6"/>',
    landmark: '<path d="M3 10h18"/><path d="M5 10v8"/><path d="M9 10v8"/><path d="M15 10v8"/><path d="M19 10v8"/><path d="M4 18h16"/><path d="M2 22h20"/><path d="m12 2 8 5H4z"/>',
    languages: '<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="M22 22l-5-10-5 10"/><path d="M14 18h6"/>',
    "loader-circle": '<path d="M21 12a9 9 0 1 1-6.2-8.6"/>',
    "lock-keyhole": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/><circle cx="12" cy="16" r="1"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    "map-pin": '<path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
    "map-pinned": '<path d="M18 8c0 4-6 9-6 9S6 12 6 8a6 6 0 1 1 12 0z"/><circle cx="12" cy="8" r="2"/><path d="m8.5 16-5 2v3l8.5-3 8.5 3v-3l-5-2"/>',
    menu: '<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>',
    headset: '<path d="M3 14v-3a9 9 0 0 1 18 0v3"/><rect x="3" y="11" width="4" height="8" rx="2"/><rect x="17" y="11" width="4" height="8" rx="2"/><path d="M21 17v1a4 4 0 0 1-4 4h-5"/>',
    "message-circle": '<path d="M21 11.5a8.5 8.5 0 0 1-12.7 7.4L3 21l2.1-5.3A8.5 8.5 0 1 1 21 11.5z"/>',
    phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.4 19.4 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.8a2 2 0 0 1-.4 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    play: '<path d="m8 5 11 7-11 7z"/>',
    "plus-circle": '<circle cx="12" cy="12" r="10"/><path d="M12 8v8"/><path d="M8 12h8"/>',
    "refresh-ccw": '<path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/>',
    "refresh-cw": '<path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/>',
    "rotate-ccw": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
    route: '<circle cx="6" cy="19" r="3"/><circle cx="18" cy="5" r="3"/><path d="M9 19h5a4 4 0 0 0 0-8H8a4 4 0 0 1 0-8h1"/>',
    save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8"/><path d="M7 3v5h8"/>',
    send: '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
    ship: '<path d="M12 2v7"/><path d="M8 5h8"/><path d="m3 11 9-3 9 3-2 8H5z"/><path d="M2 21c2 1 3 1 5 0s3-1 5 0 3 1 5 0 3-1 5 0"/>',
    "shield-check": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    "train-front": '<path d="M8 3h8a4 4 0 0 1 4 4v8a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4z"/><path d="M8 15h8"/><path d="M9 19l-2 3"/><path d="M15 19l2 3"/><path d="M8 8h8"/>',
    truck: '<path d="M10 17h4V5H2v12h3"/><path d="M14 8h4l4 4v5h-3"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/>',
    "user-round": '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
    "users-round": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
    warehouse: '<path d="M3 21V8l9-5 9 5v13"/><path d="M9 21v-8h6v8"/><path d="M3 10h18"/>',
    wrench: '<path d="M14.7 6.3a4 4 0 0 0-5 5L3 18l3 3 6.7-6.7a4 4 0 0 0 5-5l-2.8 2.8-3-3z"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'
  };

  function renderIcon(name) {
    const body = icons[name] || '<circle cx="12" cy="12" r="9"/><path d="M12 8v8"/><path d="M8 12h8"/>';
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
  }

  window.lucide = {
    createIcons() {
      document.querySelectorAll("[data-lucide]").forEach((node) => {
        const name = node.getAttribute("data-lucide") || "";
        if (node.dataset.renderedLucide === name) return;
        node.innerHTML = renderIcon(name);
        node.dataset.renderedLucide = name;
        node.classList.add("lucide-local");
      });
    }
  };
})();
