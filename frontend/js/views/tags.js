// Bulk tag editing, deletion and alert subscriptions (rubric 3.4, 2.3). Owner: Member B.
import { post } from "../api.js";
import { h, parseTagCounts, toast } from "../dom.js";
import { renderGallery } from "../gallery.js";

export function mount(root) {
  const gallery = h("div", { class: "gallery" });
  let picker = { selected: () => [] };

  const loadInput = h("input", { type: "text", id: "t-load", placeholder: "Show files with tag, e.g. fox" });
  const editInput = h("input", { type: "text", id: "t-edit", placeholder: "cat:10, dog:2 (sets minimum counts)" });
  const alertInput = h("input", { type: "text", id: "t-alert", placeholder: "fox, cane toad" });

  const guard = (fn) => async () => {
    try { await fn(); } catch (err) { toast(err.message); }
  };
  const selected = () => {
    const urls = picker.selected();
    if (!urls.length) throw new Error("Tick at least one file");
    return urls;
  };
  const load = async () => {
    const data = await post("/search/tags", { tags: parseTagCounts(loadInput.value) });
    picker = renderGallery(gallery, data.results, { selectable: true });
  };

  root.append(
    h("h2", {}, "Tags and deletion"),
    h("label", { for: "t-load" }, "Find files to edit"),
    loadInput,
    h("div", { class: "row" }, h("button", { type: "button", onclick: guard(load) }, "Load files")),
    gallery,

    h("label", { for: "t-edit" }, "Tags to add or remove on the ticked files"),
    editInput,
    h("div", { class: "row" },
      h("button", { type: "button", onclick: guard(async () => {
        const out = await post("/tags", { urls: selected(), tags: parseTagCounts(editInput.value), operation: 1 });
        toast(`Added tags on ${out.updated.length} file(s)`);
        await load();
      }) }, "Add tags"),
      h("button", { type: "button", class: "secondary", onclick: guard(async () => {
        const out = await post("/tags", { urls: selected(), tags: parseTagCounts(editInput.value), operation: 0 });
        toast(`Updated ${out.updated.length} file(s)`);
        await load();
      }) }, "Remove tags"),
      h("button", { type: "button", class: "danger", onclick: guard(async () => {
        const urls = selected();
        if (!window.confirm(`Permanently delete ${urls.length} file(s)?`)) return;
        const out = await post("/files/delete", { urls });
        toast(`Deleted ${out.deleted.length} file(s)`);
        await load();
      }) }, "Delete files"),
    ),

    h("h2", { style: "margin-top:32px" }, "Email alerts"),
    h("label", { for: "t-alert" }, "Tell me when files with any of these tags are added"),
    alertInput,
    h("div", { class: "row" }, h("button", { type: "button", onclick: guard(async () => {
      const tags = alertInput.value.split(",").map((t) => t.trim()).filter(Boolean);
      const out = await post("/notifications/subscribe", { tags });
      toast(`Check ${out.email} to confirm the subscription`);
    }) }, "Subscribe")),
  );
}
