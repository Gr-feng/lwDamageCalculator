function arenaRowsForSheet(sheet) {
  return (state.arenaEnemyData?.rows || []).filter((row) => row.sheet === sheet && row.character_id);
}

function arenaEnemyOptions(sheet) {
  return arenaRowsForSheet(sheet).map((row) => `<option value="${row.arena_enemy_id}">${row.arena_enemy_id} / ${escapeHtml(row.name || row.character_id)}</option>`).join("");
}

function arenaEnemyRowByQuery(query, sheet = "") {
  return arenaEnemyRowById(query, sheet);
}

function arenaEnemyRowById(query, sheet = "") {
  const raw = String(query || "").trim();
  if (!raw) return null;
  if (!/^\d+$/.test(raw)) return null;
  const rows = sheet ? arenaRowsForSheet(sheet) : (state.arenaEnemyData?.rows || []);
  return rows.find((row) => String(row.character_id) === raw) || null;
}

function arenaSheetKey(sheet) {
  return sheet === "周擂台2" ? "weekly2" : "weekly1";
}

function arenaPresetSection(charId, sheet = "周擂台1") {
  const preset = state.arenaPresets[String(charId || "").trim()] || {};
  const section = preset[arenaSheetKey(sheet)] || null;
  if (section) return section;
  if (preset.stat_overrides) {
    return {
      stat_overrides: preset.stat_overrides,
      barrier_count: preset.barrier_count,
      quality: preset.quality,
      enemy_skill_effects: preset.enemy_skill_effects,
    };
  }
  return null;
}

function swapYinyangSection(section) {
  const stats = section?.stat_overrides || {};
  return {
    ...section,
    stat_overrides: {
      yang_atk: Number(stats.yin_atk || 0),
      yang_def: Number(stats.yin_def || 0),
      yin_atk: Number(stats.yang_atk || 0),
      yin_def: Number(stats.yang_def || 0),
      speed: Number(stats.speed || 0),
    },
  };
}

function arenaEnemyRowsForWorld(sheet, world) {
  return arenaRowsForSheet(sheet).filter((row) => {
    const option = characterOptionById(row.character_id);
    return !world || option?.world_group === world;
  });
}

function arenaEnemyDisplayName(row) {
  if (!row) return "";
  const option = characterOptionById(row.character_id);
  return option?.name || String(row.name || "").replace(/\(\d+\)\s*$/, "") || String(row.character_id || "");
}

function arenaEnemyWorld(row) {
  return characterOptionById(row?.character_id)?.world_group || "";
}

function arenaEnemyLabel(row) {
  if (!row) return "";
  const option = characterOptionById(row.character_id);
  const world = option?.world_group || "";
  return `${row.character_id} / ${option?.name || row.name || ""}${world ? ` / ${world}` : ""}`;
}

function populateWeeklyEnemyRoleOptions(picker, sheet = "", preferredId = "") {
  const worldSelect = $('[data-role="weekly-enemy-world"]', picker);
  const nameFilter = $('[data-role="weekly-enemy-name-filter"]', picker);
  const roleSelect = $('[data-role="weekly-enemy-character"]', picker);
  const dataList = $('[data-role="weekly-enemy-character-options"]', picker);
  if (!roleSelect) return;
  const world = worldSelect?.value || "";
  const filterText = String(nameFilter?.value || "").trim().toLowerCase();
  const rows = arenaEnemyRowsForWorld(sheet, world).filter((row) => {
    if (!filterText) return true;
    const option = characterOptionById(row.character_id) || {};
    return `${arenaEnemyDisplayName(row)} ${option.label || ""} ${row.character_id} ${arenaEnemyWorld(row) || ""}`.toLowerCase().includes(filterText);
  });
  roleSelect.innerHTML = `<option value="">选择角色</option>${rows.map((row) => {
    const world = arenaEnemyWorld(row) || "-";
    return `<option value="${row.character_id}">${escapeHtml(arenaEnemyDisplayName(row))}/${escapeHtml(world)}</option>`;
  }).join("")}`;
  if (dataList) {
    dataList.innerHTML = rows.map((row) => {
      const world = arenaEnemyWorld(row) || "-";
      const name = arenaEnemyDisplayName(row);
      return `<option value="${escapeHtml(name)}/${escapeHtml(world)}" label="${row.character_id}"></option>`;
    }).join("");
  }
  const id = String(preferredId || picker.dataset.weeklySelectedId || "").trim();
  if (id && rows.some((row) => String(row.character_id) === id)) roleSelect.value = id;
}

function weeklyEnemyRoleInputLabel(row) {
  if (!row) return "";
  return `${arenaEnemyDisplayName(row)}/${arenaEnemyWorld(row) || "-"}`;
}

function resolveWeeklyEnemyRoleInput(picker, sheet = "") {
  const input = $('[data-role="weekly-enemy-name-filter"]', picker);
  const raw = String(input?.value || "").trim();
  if (!raw) return null;
  const world = $('[data-role="weekly-enemy-world"]', picker)?.value || "";
  const rows = arenaEnemyRowsForWorld(sheet, world);
  return rows.find((row) => String(row.character_id) === raw)
    || rows.find((row) => weeklyEnemyRoleInputLabel(row) === raw)
    || rows.find((row) => arenaEnemyDisplayName(row) === raw)
    || null;
}

function findWeeklyEnemyByNameInWorld(sheet, name, world) {
  const normalized = String(name || "").trim();
  if (!normalized || !world) return null;
  return arenaEnemyRowsForWorld(sheet, world).find((row) => arenaEnemyDisplayName(row) === normalized) || null;
}

function normalizeQualityList(value) {
  if (Array.isArray(value)) return value.map((item) => {
    const num = Number(item);
    return Number.isFinite(num) ? num : 1;
  });
  if (typeof value === "string") {
    const parts = value.includes(",") ? value.split(",") : value.split("");
    return parts.map((item) => Number(String(item).trim() || 1)).filter((item) => Number.isFinite(item));
  }
  return [];
}

function nonEmptyList(value) {
  return Array.isArray(value) && value.length > 0;
}

function weeklyEnemyInfoText(row, sheet = "") {
  if (!row) return "未选择";
  const parts = weeklyEnemyInfoParts(row, sheet);
  return `盾${parts.barrier}，弱${parts.weak || "-"}，耐${parts.resist || "-"}`;
}

function weeklyEnemyInfoParts(row, sheet = "") {
  if (!row) return { barrier: "-", weak: "-", resist: "-" };
  const section = arenaPresetSection(row.character_id, sheet);
  const sectionQuality = normalizeQualityList(section?.quality || []);
  const rowQuality = normalizeQualityList(row.quality || []);
  const quality = sectionQuality.length >= 9 ? sectionQuality : rowQuality;
  const labels = (state.boot.quality_labels || ["日", "月", "火", "水", "木", "金", "土", "星", "无"]).slice(0, 8);
  const weak = labels.map((label, idx) => Number(quality[idx]) === 0 ? label : "").filter(Boolean).join("");
  const resist = labels.map((label, idx) => Number(quality[idx]) === 2 ? label : "").filter(Boolean).join("");
  const barrier = section?.barrier_count ?? row.barrier_count ?? "-";
  return { barrier, weak: weak || "-", resist: resist || "-" };
}

function setWeeklyEnemySelection(picker, row, sheet = "") {
  const input = $('[data-role="weekly-enemy-query"]', picker);
  const select = $('[data-role="weekly-enemy-character"]', picker);
  const nameFilter = $('[data-role="weekly-enemy-name-filter"]', picker);
  const worldSelect = $('[data-role="weekly-enemy-world"]', picker);
  const img = $('[data-role="weekly-enemy-avatar"]', picker);
  const status = $('[data-role="weekly-preset-status"]', picker);
  const selected = $('[data-role="weekly-selected-info"]', picker);
  picker.classList.toggle("weekly-empty", !row);
  if (input) input.value = row?.character_id || "";
  if (nameFilter) nameFilter.value = row ? weeklyEnemyRoleInputLabel(row) : "";
  if (row) {
    picker.dataset.weeklySelectedId = String(row.character_id || "");
    picker.dataset.weeklySelectedName = arenaEnemyDisplayName(row);
    const world = arenaEnemyWorld(row);
    if (worldSelect && (!worldSelect.value || worldSelect.value !== world)) worldSelect.value = world;
    populateWeeklyEnemyRoleOptions(picker, sheet, row.character_id);
  } else {
    delete picker.dataset.weeklySelectedId;
    delete picker.dataset.weeklySelectedName;
    populateWeeklyEnemyRoleOptions(picker, sheet, "");
  }
  if (select && row) select.value = String(row.character_id);
  if (img) {
    img.src = row?.character_id ? avatarUrl(row.character_id) : "/assets/avatars/S0.png";
    img.dataset.charId = row?.character_id || "";
  }
  if (status) status.textContent = row && !state.arenaPresets[String(row.character_id || "").trim()] ? "无预设" : "";
  if (selected) {
    const option = characterOptionById(row?.character_id);
    const parts = weeklyEnemyInfoParts(row, sheet);
    selected.innerHTML = row ? `
      <button type="button" class="small secondary" data-role="weekly-reset-enemy">重选角色</button>
      <b>${row.character_id} ${escapeHtml(option?.name || row.name || "")}</b>
      <span class="weekly-info-line">盾${escapeHtml(parts.barrier)}</span>
      <span class="weekly-info-line">弱${escapeHtml(parts.weak)}</span>
      <span class="weekly-info-line">耐${escapeHtml(parts.resist)}</span>
    ` : "";
  }
  picker.classList.toggle("weekly-enemy-selected", Boolean(row));
}

function buildWorldOptions() {
  return `<option value=""></option>${(state.boot.world_group_options || []).map((value) => `<option value="${value}">${value}</option>`).join("")}`;
}

function buildWeeklyRoleTags(ids) {
  const uniqueIds = [...new Set((ids || []).map((id) => String(id || "").trim()).filter(Boolean))];
  if (!uniqueIds.length) return `<span class="muted">为空时使用已有角色预设作为候选</span>`;
  return uniqueIds.map((id) => {
    const option = characterOptionById(id);
    const rolePreset = state.characterPresets[String(id)] ? "角色预设:有" : "角色预设:无";
    const arenaPreset = state.arenaPresets[String(id)] ? "擂台预设:有" : "擂台预设:无";
    return `<button type="button" class="tag weekly-role-tag" data-role-id="${id}">${id} ${escapeHtml(option?.name || "")} / ${rolePreset} / ${arenaPreset} ×</button>`;
  }).join("");
}

function syncWeeklyRoleTags(waveBox, ids) {
  const uniqueIds = [...new Set((ids || []).map((id) => String(id || "").trim()).filter(Boolean))];
  const hidden = $('[data-role="weekly-role-ids"]', waveBox);
  const root = $('[data-role="weekly-role-tags"]', waveBox);
  if (hidden) hidden.value = uniqueIds.join(",");
  if (root) root.innerHTML = buildWeeklyRoleTags(uniqueIds);
}

function snapshotWeeklyArenaUi() {
  const root = $("#weeklyArenaConfig");
  if (!root || !root.innerHTML.trim()) return null;
  return {
    onlyBoosted: $("#weeklyOnlyBoosted")?.checked !== false,
    simpleMode: state.weeklySimpleMode,
    arenas: $$("#weeklyArenaConfig [data-weekly-arena]").map((arenaBox) => ({
      arena: Number(arenaBox.dataset.weeklyArena),
      types: $$("button.active", $(".weekly-type-select", arenaBox)).map((btn) => btn.dataset.value),
      waves: $$("[data-weekly-wave]", arenaBox).map((waveBox) => ({
        wave: Number(waveBox.dataset.weeklyWave),
        enemies: $$("[data-role='weekly-enemy-query']", waveBox).map((input) => ({
          pos: Number(input.dataset.pos),
          value: input.value || "",
          sheet: waveBox.dataset.sheet || "",
        })),
      })),
    })),
  };
}

function restoreWeeklyArenaUi(snapshot) {
  if (!snapshot) return;
  const onlyBoosted = $("#weeklyOnlyBoosted");
  if (onlyBoosted) onlyBoosted.checked = snapshot.onlyBoosted !== false;
  state.weeklySimpleMode = Boolean(snapshot.simpleMode);
  const root = $("#weeklyArenaConfig");
  if (root) root.classList.toggle("weekly-simple-mode", state.weeklySimpleMode);
  const toggle = $('[data-toggle-weekly-simple]', root);
  if (toggle) toggle.textContent = state.weeklySimpleMode ? "详细模式" : "简略模式";
  for (const arena of snapshot.arenas || []) {
    const arenaBox = $(`#weeklyArenaConfig [data-weekly-arena="${arena.arena}"]`);
    if (!arenaBox) continue;
    const typeSet = new Set((arena.types || []).map(String));
    $$("button[data-value]", $(".weekly-type-select", arenaBox)).forEach((btn) => {
      btn.classList.toggle("active", typeSet.has(String(btn.dataset.value)));
    });
    for (const wave of arena.waves || []) {
      const waveBox = $(`[data-weekly-wave="${wave.wave}"]`, arenaBox);
      if (!waveBox) continue;
      for (const enemy of wave.enemies || []) {
        const input = $(`[data-role="weekly-enemy-query"][data-pos="${enemy.pos}"]`, waveBox);
        if (!input) continue;
        input.value = enemy.value || "";
        const picker = input.closest(".weekly-enemy-picker");
        const row = arenaEnemyRowById(input.value, enemy.sheet || waveBox.dataset.sheet || "");
        setWeeklyEnemySelection(picker, row, enemy.sheet || waveBox.dataset.sheet || "");
      }
    }
  }
}

function rerenderWeeklyArenaConfigPreservingState() {
  const snapshot = snapshotWeeklyArenaUi();
  renderWeeklyArenaConfig();
  restoreWeeklyArenaUi(snapshot);
}

function arenaStatTemplates() {
  const seen = new Set();
  const rows = [];
  for (const row of state.arenaEnemyData?.rows || []) {
    const stats = {};
    for (const key of ARENA_STAT_KEYS) stats[key] = Number(row[key] || 0);
    const barrier = Number(row.barrier_count || 0);
    const sig = `${barrier}|${ARENA_STAT_KEYS.map((key) => stats[key]).join("/")}`;
    if (seen.has(sig) || sig === "0|0/0/0/0/0") continue;
    seen.add(sig);
    rows.push({ sig, stats, barrier_count: barrier, label: `${barrier}盾 / ${row.sheet} / ${ARENA_STAT_KEYS.map((key) => stats[key]).join("/")}` });
  }
  return rows.sort((a, b) => Number(b.barrier_count) - Number(a.barrier_count) || String(a.label).localeCompare(String(b.label), "zh-Hans-CN"));
}

function applyArenaFixedStats(card) {
  const barrier = Number($('[data-field="barrier_count"]', card)?.value || 7);
  const fixed = ARENA_FIXED_STATS_BY_BARRIER[barrier] || ARENA_FIXED_STATS_BY_BARRIER[7];
  for (const key of ["yang_atk", "yang_def", "yin_atk", "yin_def"]) {
    const input = $(`[data-stat="${key}"]`, card);
    if (input) input.value = fixed[key] || 0;
  }
}

function arenaRowsByCharacter(charId) {
  const id = String(charId || "").trim();
  if (!id) return [];
  return (state.arenaEnemyData?.rows || []).filter((row) => String(row.character_id) === id);
}

function renderArenaStatMirror(card, charId) {
  const root = $('[data-role="arena-stat-mirror"]', card);
  if (!root) return;
  const rows = ["周擂台1", "周擂台2"].map((sheet) => {
    const section = arenaPresetSection(charId, sheet);
    if (section) {
      const stats = section.stat_overrides || {};
      return {
        sheet,
        ...stats,
        barrier_count: section.barrier_count,
      };
    }
    return arenaRowsByCharacter(charId).find((row) => row.sheet === sheet);
  });
  root.innerHTML = `
    <table>
      <thead><tr><th>来源</th>${ARENA_STAT_KEYS.map((key) => `<th>${STAT_LABELS[key]}</th>`).join("")}<th>盾</th></tr></thead>
      <tbody>${rows.map((row, idx) => `<tr>
        <td>${idx === 0 ? "周擂台1-阳" : "周擂台2-阴"}</td>
        ${ARENA_STAT_KEYS.map((key) => `<td>${row?.[key] ?? "-"}</td>`).join("")}
        <td>${row?.barrier_count ?? "-"}</td>
      </tr>`).join("")}</tbody>
    </table>
  `;
}

function enemyConfigFromArenaRow(row, wave, sheet = "周擂台1", charId = "") {
  const sourceId = charId || row?.character_id || "";
  const section = arenaPresetSection(sourceId, sheet);
  if (!row && !section) return { enabled: false };
  const stats = section?.stat_overrides || row || {};
  return {
    enabled: true,
    character_id: Number(sourceId || row?.character_id || 0),
    hp: 1,
    yang_atk: stats.yang_atk || 0,
    yang_def: stats.yang_def || 10000,
    yin_atk: stats.yin_atk || 0,
    yin_def: stats.yin_def || 10000,
    speed: stats.speed || 0,
    barrier_count: section?.barrier_count ?? row?.barrier_count ?? 0,
    quality: section?.quality || row?.quality || Array(9).fill(1),
    tribe_text: "",
    is_break_all: false,
    buffs: [],
    enemy_skill_effects: nonEmptyList(section?.enemy_skill_effects) ? section.enemy_skill_effects : (row?.skill_effects || []),
    meta: {
      name: row?.name || characterOptionById(sourceId)?.name || String(sourceId),
      world: sheet || "",
      type: "",
    },
  };
}

function renderWeeklyArenaConfig() {
  const root = $("#weeklyArenaConfig");
  if (!root) return;
  root.classList.toggle("weekly-simple-mode", state.weeklySimpleMode);
  const typeOptions = Object.entries(state.boot.type_labels || {}).map(([value, label]) => `<button type="button" class="small secondary" data-value="${value}">${label}</button>`).join("");
  root.innerHTML = `
    <div class="weekly-toolbar">
      <label class="inline-check"><input type="checkbox" id="weeklyOnlyBoosted" checked>只考虑对应擂台加成 Type</label>
      <button type="button" class="small secondary" data-toggle-weekly-simple>${state.weeklySimpleMode ? "详细模式" : "简略模式"}</button>
    </div>
  ` + [1, 2, 3, 4].map((arena) => {
    const sheet = arena % 2 === 1 ? "周擂台1" : "周擂台2";
    const yinyang = arena % 2 === 1 ? "阳" : "阴";
    return `
      <div class="card weekly-arena-card" data-weekly-arena="${arena}">
        <div class="weekly-arena-head"><b>擂台${arena}-${yinyang}</b><div class="button-select weekly-type-select" data-max="2">${typeOptions}</div><button type="button" class="small secondary" data-solve-weekly-arena="${arena}">求解本擂台</button></div>
        <details open>
          <summary>敌方波次配置（${sheet}）</summary>
        <div class="weekly-wave-grid">
          ${[1, 2, 3].map((wave) => `
            <div class="weekly-wave" data-weekly-wave="${wave}" data-sheet="${sheet}">
              <h4>第 ${wave} 波</h4>
              <div class="weekly-enemy-grid">
                ${[0, 1, 2].map((pos) => `<div class="weekly-enemy-picker weekly-empty" data-pos="${pos}">
                  <div class="weekly-avatar-box"><img data-role="weekly-enemy-avatar" src="/assets/avatars/S0.png" onerror="this.src='/assets/avatars/S0.png'"><small data-role="weekly-preset-status"></small></div>
                  <div class="weekly-enemy-fields">
                    <b>敌方${pos}</b>
                    <label>ID<input data-role="weekly-enemy-query" data-pos="${pos}" list="characterIdOptions" placeholder="角色ID"></label>
                    <label>世界群<select data-role="weekly-enemy-world" data-pos="${pos}">${buildWorldOptions()}</select></label>
                    <label>角色<input data-role="weekly-enemy-name-filter" data-pos="${pos}" list="weeklyEnemyOptions-${arena}-${wave}-${pos}" placeholder="输入角色名筛选/选择"></label>
                    <datalist id="weeklyEnemyOptions-${arena}-${wave}-${pos}" data-role="weekly-enemy-character-options"></datalist>
                    <select data-role="weekly-enemy-character" data-pos="${pos}" class="hidden"><option value="">选择角色/世界群</option></select>
                  </div>
                  <div class="weekly-selected-info" data-role="weekly-selected-info"></div>
                </div>`).join("")}
              </div>
            </div>
          `).join("")}
        </div>
        </details>
      </div>
    `;
  }).join("");
  $('[data-toggle-weekly-simple]', root)?.addEventListener("click", () => {
    state.weeklySimpleMode = !state.weeklySimpleMode;
    root.classList.toggle("weekly-simple-mode", state.weeklySimpleMode);
    $('[data-toggle-weekly-simple]', root).textContent = state.weeklySimpleMode ? "详细模式" : "简略模式";
  });
  bindButtonSelects(root);
  $$("[data-solve-weekly-arena]", root).forEach((btn) => {
    btn.addEventListener("click", () => solveWeeklyArena(Number(btn.dataset.solveWeeklyArena)).catch((err) => alert(err.message)));
  });
  $$("[data-role='weekly-enemy-world']", root).forEach((select) => {
    const refresh = () => {
      const waveBox = select.closest("[data-weekly-wave]");
      const picker = select.closest(".weekly-enemy-picker");
      const sheet = waveBox?.dataset.sheet || "";
      const selectedId = picker.dataset.weeklySelectedId || "";
      const selectedName = picker.dataset.weeklySelectedName || "";
      populateWeeklyEnemyRoleOptions(picker, sheet, selectedId);
      const roleSelect = $('[data-role="weekly-enemy-character"]', picker);
      if (roleSelect?.value) return;
      const row = findWeeklyEnemyByNameInWorld(sheet, selectedName, select.value);
      if (row) setWeeklyEnemySelection(picker, row, sheet);
    };
    select.addEventListener("change", refresh);
    refresh();
  });
  $$("[data-role='weekly-enemy-name-filter']", root).forEach((input) => {
    input.addEventListener("input", () => {
      const picker = input.closest(".weekly-enemy-picker");
      const waveBox = input.closest("[data-weekly-wave]");
      populateWeeklyEnemyRoleOptions(picker, waveBox?.dataset.sheet || "", picker.dataset.weeklySelectedId || "");
    });
    input.addEventListener("change", () => {
      const picker = input.closest(".weekly-enemy-picker");
      const waveBox = input.closest("[data-weekly-wave]");
      const sheet = waveBox?.dataset.sheet || "";
      const row = resolveWeeklyEnemyRoleInput(picker, sheet);
      if (row) setWeeklyEnemySelection(picker, row, sheet);
    });
  });
  $$("[data-role='weekly-enemy-character']", root).forEach((select) => {
    select.addEventListener("change", () => {
      const picker = select.closest(".weekly-enemy-picker");
      const input = $('[data-role="weekly-enemy-query"]', picker);
      input.value = select.value || "";
      const waveBox = select.closest("[data-weekly-wave]");
      const row = arenaEnemyRowById(select.value, waveBox?.dataset.sheet || "");
      setWeeklyEnemySelection(picker, row, waveBox?.dataset.sheet || "");
    });
  });
  $$("[data-role='weekly-enemy-query']", root).forEach((input) => {
    const refresh = () => {
      const waveBox = input.closest("[data-weekly-wave]");
      const row = arenaEnemyRowById(input.value, waveBox?.dataset.sheet || "");
      const picker = input.closest(".weekly-enemy-picker");
      if (row) {
        setWeeklyEnemySelection(picker, row, waveBox?.dataset.sheet || "");
      } else if (!String(input.value || "").trim()) {
        setWeeklyEnemySelection(picker, null, waveBox?.dataset.sheet || "");
      } else {
        picker.classList.remove("weekly-enemy-selected", "weekly-empty");
      }
    };
    input.addEventListener("change", () => {
      const waveBox = input.closest("[data-weekly-wave]");
      const row = arenaEnemyRowById(input.value, waveBox?.dataset.sheet || "");
      setWeeklyEnemySelection(input.closest(".weekly-enemy-picker"), row, waveBox?.dataset.sheet || "");
    });
    input.addEventListener("input", refresh);
  });
  root.addEventListener("click", (event) => {
    const reset = event.target.closest('[data-role="weekly-reset-enemy"]');
    if (!reset) return;
    const picker = reset.closest(".weekly-enemy-picker");
    const input = $('[data-role="weekly-enemy-query"]', picker);
    const select = $('[data-role="weekly-enemy-character"]', picker);
    if (input) input.value = "";
    if (select) select.value = "";
    delete picker.dataset.weeklySelectedId;
    delete picker.dataset.weeklySelectedName;
    setWeeklyEnemySelection(picker, null, picker.closest("[data-weekly-wave]")?.dataset.sheet || "");
  });
  $$("[data-role='weekly-enemy-avatar']", root).forEach((img) => {
    img.addEventListener("click", () => {
      if (!img.dataset.charId) return;
      state.pendingArenaPresetId = img.dataset.charId;
      setActiveTab("arena-preset");
      renderArenaPresets();
    });
  });
}

function collectWeeklyArenaConfig() {
  const arenas = [];
  $$("#weeklyArenaConfig [data-weekly-arena]").forEach((arenaBox) => {
    const waves = {};
    $$("[data-weekly-wave]", arenaBox).forEach((waveBox) => {
      const wave = Number(waveBox.dataset.weeklyWave);
      waves[wave] = {};
      $$("[data-role='weekly-enemy-query']", waveBox).forEach((input) => {
        const row = arenaEnemyRowById(input.value, waveBox.dataset.sheet || "");
        waves[wave][input.dataset.pos] = enemyConfigFromArenaRow(row, wave, waveBox.dataset.sheet || "", input.value);
      });
      waves[wave].role_ids = "";
    });
    arenas.push({
      arena: Number(arenaBox.dataset.weeklyArena),
      types: $$("button.active", $(".weekly-type-select", arenaBox)).map((btn) => btn.dataset.value),
      only_boosted: $("#weeklyOnlyBoosted")?.checked !== false,
      waves,
    });
  });
  return arenas;
}
