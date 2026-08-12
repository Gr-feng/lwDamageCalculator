(function () {
  async function search(deps) {
    const { $, api, state, selectedFilterValues, renderTable } = deps;
    const params = new URLSearchParams({
      types: selectedFilterValues("cqTypes").join(","),
      world_groups: selectedFilterValues("cqWorlds").join(","),
      elements: selectedFilterValues("cqElements").join(","),
      bullets: selectedFilterValues("cqBullets").join(","),
      killers: $("#cqKillers").value,
      element_logic: $("#cqElementLogic")?.value || "any",
      bullet_logic: $("#cqBulletLogic")?.value || "any",
      killer_logic: $("#cqKillerLogic")?.value || "any",
      re_only: $("#cqRe").value,
      name: $("#cqName")?.value || "",
      ability_kind: $("#cqAbilityKind")?.value || "",
      ability_abnormal: $("#cqAbilityAbnormal")?.value || "",
      ability_status: $("#cqAbilityStatus")?.value || "",
      ability_chain: $("#cqAbilityChain")?.value || "",
    });
    const rows = await api(`/api/characters?${params}`);
    state.lastCharacterRows = rows;
    const count = $("#characterResultCount");
    if (count) count.textContent = `结果：${rows.length} 个角色`;
    renderTable(rows, deps);
  }

  function renderTable(rows, deps) {
    const { $, $$, api, state, buildTable, setQueryTab, loadCharacterDetail, showCharacterDataPic, avatarUrl, attributeIconUrl } = deps;
    const tableWrap = $("#characterTableWrap");
    const thumbGrid = $("#characterThumbGrid");
    const openDetail = (charId) => {
      setQueryTab("character-detail");
      loadCharacterDetail(charId);
    };
    if (state.characterThumbnailMode) {
      if (tableWrap) tableWrap.classList.add("hidden");
      if (thumbGrid) {
        thumbGrid.classList.remove("hidden");
        thumbGrid.innerHTML = rows.map((row) => `
          <button type="button" class="character-query-thumb-card" data-char-id="${row.character_id}" title="${row.name || ""}">
            <img src="${avatarUrl(row.character_id)}" onerror="this.src='/assets/avatars/S0.png'">
            <span>${row.name || row.character_id}</span>
            <small>ID ${row.character_id}</small>
          </button>
        `).join("");
        $$("[data-char-id]", thumbGrid).forEach((btn) => btn.addEventListener("click", () => openDetail(btn.dataset.charId)));
      }
      $("#characterTable").innerHTML = "";
      return;
    }
    if (tableWrap) tableWrap.classList.remove("hidden");
    if (thumbGrid) {
      thumbGrid.classList.add("hidden");
      thumbGrid.innerHTML = "";
    }
    const renderAttack5Elements = (row) => {
      const ids = state.showFullAttack5Elements ? (row.attack5_element_id_sequence || []) : (row.attack5_elements || []);
      return `<span class="element-icons ${state.showFullAttack5Elements ? "element-icons-full" : ""}">${ids.map((id) => `<img src="${attributeIconUrl(id)}" title="${state.boot.element_labels?.[id] || id}">`).join("") || row.attack5_element_sequence || "-"}</span>`;
    };
    const renderAttack5Bullets = (row) => `<span class="bullet-type-icons">${(row.attack5_bullet_types || []).map((id) => `<img src="${bulletTypeIconUrl(id, state.boot.bullet_labels?.[id])}" title="${state.boot.bullet_labels?.[id] || id}" onerror="this.style.display='none'">`).join("") || row.attack5_bullet_sequence || "-"}</span>`;
    const renderStatCell = (key) => (row) => state.debugMode
      ? `<input class="debug-stat-input" data-stat-key="${key}" value="${row[key] ?? 0}" type="number">`
      : `${row[key] ?? ""}`;
    const headers = [
      { key: "character_id", label: "ID" },
      { key: "avatar", label: "头像", render: (row) => `<img class="table-avatar table-avatar-link" data-char-id="${row.character_id}" src="${avatarUrl(row.character_id)}" onerror="this.src='/assets/avatars/S0.png'">` },
      { key: "name", label: "名称", render: (row) => `<span class="linkish character-name-cell" data-char-id="${row.character_id}">${row.name}</span>` },
      { key: "world_group", label: "世界群" },
      { key: "type_label", label: "Type" },
      ...(state.debugMode ? [{ key: "hp", label: "HP", render: renderStatCell("hp") }] : []),
      { key: "yang_atk", label: "阳攻", render: renderStatCell("yang_atk") },
      { key: "yang_def", label: "阳防", render: renderStatCell("yang_def") },
      { key: "yin_atk", label: "阴攻", render: renderStatCell("yin_atk") },
      { key: "yin_def", label: "阴防", render: renderStatCell("yin_def") },
      { key: "speed", label: "速度", render: renderStatCell("speed") },
      { key: "attack5_element_sequence", label: "终符属性", render: renderAttack5Elements },
      { key: "attack5_bullet_sequence", label: "终符弹种", render: renderAttack5Bullets },
      { key: "data_pic", label: "一图", render: (row) => row.data_pic_exists ? `<button type="button" class="small secondary" data-data-pic-id="${row.character_id}">查看</button>` : `<button type="button" class="small secondary" disabled>查看</button>` },
      ...(state.debugMode ? [{ key: "debug_save", label: "保存", render: (row) => `<button type="button" class="small secondary" data-save-char-stats="${row.character_id}">保存</button>` }] : []),
    ];
    buildTable($("#characterTable"), headers, rows, (table) => {
      $$(".linkish, .table-avatar-link", table).forEach((link) => link.addEventListener("click", () => {
        openDetail(link.dataset.charId);
      }));
      $$("[data-data-pic-id]", table).forEach((btn) => btn.addEventListener("click", () => {
        showCharacterDataPic(btn.dataset.dataPicId);
      }));
      $$("[data-save-char-stats]", table).forEach((btn) => btn.addEventListener("click", async () => {
        const tr = btn.closest("tr");
        const stats = {};
        $$("[data-stat-key]", tr).forEach((input) => {
          stats[input.dataset.statKey] = Number(input.value || 0);
        });
        const id = btn.dataset.saveCharStats;
        const data = await api(`/api/characters/${encodeURIComponent(id)}/stats`, {
          method: "POST",
          body: JSON.stringify({ stats }),
        });
        const row = (state.lastCharacterRows || []).find((item) => String(item.character_id) === String(id));
        if (row) Object.assign(row, data.stats || stats);
        btn.textContent = "已保存";
        setTimeout(() => { btn.textContent = "保存"; }, 900);
      }));
    });
  }

  window.LWCharacterQuery = { search, renderTable };
})();
