(function () {
  function filterRows(rows, presetMap, filters, useRoleFilters) {
    if (!useRoleFilters) return rows || [];
    return (rows || []).filter((row) => {
      const preset = presetMap[String(row.id)] || null;
      if (filters.preset === "missing" && preset) return false;
      if (filters.preset === "exists" && !preset) return false;
      if (filters.rebirth2 && !preset?.rebirth2) return false;
      if (filters.unowned && !preset?.unowned) return false;
      return true;
    });
  }

  function render(container, options) {
    const {
      rows = [],
      presetMap = {},
      filters = {},
      useRoleFilters = false,
      withOwnedFlags = true,
      avatarUrl,
      escapeHtml,
      onPick,
    } = options || {};
    const escape = typeof escapeHtml === "function" ? escapeHtml : (value) => String(value ?? "");
    const avatar = typeof avatarUrl === "function" ? avatarUrl : (id) => `/assets/avatars/S${id}01.png`;
    const visibleRows = filterRows(rows, presetMap, filters, useRoleFilters);
    container.innerHTML = visibleRows.map((row) => {
      const preset = presetMap[String(row.id)] || {};
      const status = presetMap[String(row.id)] ? "已有预设" : "暂无预设";
      const flags = withOwnedFlags ? `${preset.rebirth2 ? " / 二转" : ""}${preset.unowned ? " / 未拥有" : ""}` : "";
      return `
        <button type="button" class="character-gallery-card" data-char-id="${row.id}">
          <img src="${avatar(row.id)}" onerror="this.src='/assets/avatars/S0.png'">
          <span>${escape(row.name)}</span>
          <small>${escape(row.world_group || "-")} / ${status}${flags}</small>
        </button>
      `;
    }).join("");
    Array.from(container.querySelectorAll(".character-gallery-card")).forEach((btn) => {
      btn.addEventListener("click", () => {
        if (typeof onPick === "function") onPick(btn.dataset.charId);
      });
    });
  }

  window.LWRoleGallery = { render, filterRows };
})();
