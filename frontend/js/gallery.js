// Thumbnail gallery shared by the search, lost pet and tag views.
import { h } from "./dom.js";

/**
 * Render result cards into `container`. Clicking the image opens the full-size file in a new tab.
 * Returns {selected(): string[]} with the full-size URLs of ticked cards (when selectable).
 */
export function renderGallery(container, results, { selectable = false } = {}) {
  container.replaceChildren();
  const boxes = [];
  if (!results.length) {
    container.append(h("p", { class: "hint" }, "No matching files."));
    return { selected: () => [] };
  }
  for (const r of results) {
    
  const visual = r.thumb_url
    ? h("img", {
        src: r.thumb_url,
        alt: Object.keys(r.tags).join(", ") || "uploaded file",
        loading: "lazy"
      })
    : r.type === "video"
      ? h("div", { class: "video" },
          h("span", { class: "video-play", "aria-hidden": "true" }, "▶"),
          h("span", {}, "Play video")
        )
      : h("div", { class: "video" }, "Processing");
    const link = h("a", { href: r.url, target: "_blank", rel: "noopener" }, visual);
    const chips = Object.entries(r.tags).map(([tag, n]) => h("span", { class: "chip" }, `${tag} ×${n}`));
    const card = h("div", { class: "card" }, link, h("div", { class: "meta" }, chips.length ? chips : "no tags"));
    if (selectable) {
      const box = h("input", { type: "checkbox", "aria-label": "Select file" });
      box.dataset.url = r.url;
      boxes.push(box);
      card.prepend(box);
    }
    container.append(card);
  }
  return { selected: () => boxes.filter((b) => b.checked).map((b) => b.dataset.url) };
}
