(function () {
  function effectDescription(effect, enrichEffect) {
    const row = typeof enrichEffect === "function" ? enrichEffect(effect) : effect || {};
    return row.description || row.name || "未知效果";
  }

  function qualityIconRow(quality, labels, temperamentIconUrl) {
    const values = Array.isArray(quality) ? quality : [];
    if (!values.length || typeof temperamentIconUrl !== "function") return "-";
    const safeLabels = (labels || ["日", "月", "火", "水", "木", "金", "土", "星", "无"]).slice(0, 8);
    return `<span class="quality-summary inline">${safeLabels.map((label, idx) => {
      const stateValue = Number(values[idx] ?? 1);
      return `<img src="${temperamentIconUrl(label, stateValue)}" title="${label}" alt="${label}">`;
    }).join("")}</span>`;
  }

  function describeTribes(text, tribeOptions) {
    const map = new Map((tribeOptions || []).map(([id, label]) => [String(id), String(label)]));
    const values = String(text || "").replace(/，/g, ",").split(",").map((item) => item.trim()).filter(Boolean);
    if (!values.length) return "-";
    return values.map((id) => `${id}:${map.get(String(id)) || "未知"}`).join(" / ");
  }

  window.LWVsDisplay = { effectDescription, qualityIconRow, describeTribes };
})();
