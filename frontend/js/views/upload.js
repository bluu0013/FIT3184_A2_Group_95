// Upload view (rubric 3.1). Owner: Member B.
import { post } from "../api.js";
import { h, sha256Hex, toast } from "../dom.js";

export function mount(root) {
  const input = h("input", { type: "file", id: "upload-files", multiple: true,
    accept: "image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm" });
  const list = h("ul", { class: "status" });
  const button = h("button", { type: "button" }, "Upload");

  
  const addLine = (text, cls = "") => {
    const li = h("li", { class: cls }, text);
    list.append(li);

    return li;
  };

  // Remove completed upload messages after 6 seconds.
  const clearLineLater = (line) => {
    setTimeout(() => {
      line.remove();
    }, 6000);
  };


  button.addEventListener("click", async () => {
    if (!input.files.length) return toast("Choose at least one file");
    button.disabled = true;
    for (const file of input.files) {
      const line = addLine(`${file.name}: hashing...`);
      try {
        const init = await post("/upload/init", {
          filename: file.name,
          content_type: file.type,
          size: file.size,
          sha256: await sha256Hex(file),
        });
        
        if (init.duplicate) {
          line.textContent = `${file.name}: already uploaded, skipped.`;
          line.className = "warn";
          clearLineLater(line);
          continue;
        }

        line.textContent = `${file.name}: uploading...`;
        const put = await fetch(init.upload_url, { method: "PUT", headers: init.required_headers, body: file });
        if (!put.ok) throw new Error(`storage returned ${put.status}`);
        
        line.textContent = `${file.name}: uploaded successfully! Tagging continues in the background.`;
        line.className = "ok";
        clearLineLater(line);

      } catch (err) {
        line.textContent = `${file.name}: ${err.message}`;
        line.className = "warn";
      }
    }
    input.value = "";
    button.disabled = false;
  });

  root.append(
    h("h2", {}, "Upload photos and videos"),
    h("p", { class: "hint" }, "JPEG, PNG, WebP, MP4, MOV or WebM. Files already in the system are detected by content and skipped."),
    h("label", { for: "upload-files" }, "Files"),
    input,
    h("div", { class: "row" }, button),
    list,
  );
}
