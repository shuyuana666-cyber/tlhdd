import { addIcon } from '@vben/icons';

// Local Lucide-style paths shared by menu entries, breadcrumbs and tabs.
const icons = {
  "layout-dashboard": "<rect x=\"3\" y=\"3\" width=\"7\" height=\"8\" rx=\"1\"/><rect x=\"14\" y=\"3\" width=\"7\" height=\"5\" rx=\"1\"/><rect x=\"14\" y=\"12\" width=\"7\" height=\"9\" rx=\"1\"/><rect x=\"3\" y=\"15\" width=\"7\" height=\"6\" rx=\"1\"/>",
  "car-front": "<path d=\"M6 15h12\"/><path d=\"M6 15l1.5-5.5A3 3 0 0 1 10.4 7h3.2a3 3 0 0 1 2.9 2.5L18 15\"/><path d=\"M6 15v3\"/><path d=\"M18 15v3\"/><circle cx=\"8\" cy=\"18\" r=\"1\"/><circle cx=\"16\" cy=\"18\" r=\"1\"/>",
  "wrench": "<path d=\"M14.7 6.3a4 4 0 0 0-5 5L3 18l3 3 6.7-6.7a4 4 0 0 0 5-5l-2.8 2.8-3-3z\"/>",
  "images": "<rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\"/><circle cx=\"9\" cy=\"9\" r=\"2\"/><path d=\"m21 15-4-4L5 21\"/>",
  "file-text": "<path d=\"M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z\"/><path d=\"M14 2v6h6\"/><path d=\"M8 13h8\"/><path d=\"M8 17h6\"/>",
  "clipboard-list": "<path d=\"M9 5h6\"/><path d=\"M9 3h6v4H9z\"/><path d=\"M6 5H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-1\"/><path d=\"M8 12h8\"/><path d=\"M8 16h8\"/>",
  "message-square-text": "<path d=\"M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z\"/><path d=\"M8 8h8\"/><path d=\"M8 12h6\"/>",
  "messages-square": "<path d=\"M14 9a4 4 0 0 1-4 4H6l-4 3V5a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4z\"/><path d=\"M22 14a4 4 0 0 1-4 4h-4l-4 3v-4\"/>",
  "users": "<path d=\"M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2\"/><circle cx=\"9\" cy=\"7\" r=\"4\"/><path d=\"M22 21v-2a4 4 0 0 0-3-3.9\"/><path d=\"M16 3.1a4 4 0 0 1 0 7.8\"/>",
  "settings": "<path d=\"M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5z\"/><path d=\"M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1A2 2 0 1 1 4.4 17l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1A2 2 0 1 1 7.1 4.4l.1.1a1.6 1.6 0 0 0 1.8.3h.1a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1A2 2 0 1 1 19.8 7l-.1.1a1.6 1.6 0 0 0-.3 1.8v.1a1.6 1.6 0 0 0 1.5 1h.1a2 2 0 1 1 0 4h-.2a1.6 1.6 0 0 0-1.4 1z\"/>",
  "file-stack": "<path d=\"M16 2H8a2 2 0 0 0-2 2v12\"/><path d=\"M20 6H12a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8z\"/><path d=\"M16 6v6h4\"/>"
};

export function registerNavigationIcons() {
  for (const [name, paths] of Object.entries(icons)) {
    addIcon(`lucide:${name}`, {
      width: 24,
      height: 24,
      body: `<g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${paths}</g>`,
    });
  }
}
