(function () {
  function lines(row) {
    const values = [];
    const pushRows = (rawRows, textRows, baseOrder) => {
      (textRows || []).forEach((text, idx) => {
        const raw = (rawRows || [])[idx] || [];
        const buffId = Array.isArray(raw) ? Number(raw[0] || 0) : 0;
        const subId = Array.isArray(raw) ? Number(raw[1] || 0) : 0;
        const value = String(text || "").trim();
        if (value) values.push({ buffId, subId, order: baseOrder + idx, text: value });
      });
    };
    pushRows((row && row.buffs) || [], (row && row.buffs_text) || [], 0);
    values.sort((a, b) => (a.buffId - b.buffId) || (a.subId - b.subId) || (a.order - b.order));
    const texts = values.map((item) => item.text);
    if (texts.length) return texts;
    const fallback = [
      ...((row && row.buffs_text) || []),
    ].map((item) => String(item || "").trim()).filter(Boolean);
    if (fallback.length) return fallback.sort((a, b) => a.localeCompare(b, "zh-Hans-CN"));
    const rawFallback = ((row && row.buffs) || [])
      .filter((item) => Array.isArray(item) && Number(item[0] || 0) > 0)
      .map((item) => `[${item.join(",")}]`);
    return rawFallback.length ? rawFallback : ["-"];
  }

  function text(row) {
    return lines(row).join("\n");
  }

  function html(row, escapeHtml) {
    const escape = typeof escapeHtml === "function" ? escapeHtml : (value) => String(value ?? "");
    return lines(row).map((line) => `<div>${escape(line)}</div>`).join("");
  }

  window.LWManualBuffs = { lines, text, html };
})();
