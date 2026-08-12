function setQueryTab(id) {
  setActiveTab(id);
  $$(".tabs button").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === "query-hub"));
  if (typeof renderModuleSidebar === "function") renderModuleSidebar("query-hub");
  $$(".query-subtabs [data-query-jump], .query-hub-actions [data-query-jump]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.queryJump === id);
    btn.classList.toggle("secondary", btn.dataset.queryJump !== id);
  });
  if (id === "character-query" && !(state.lastCharacterRows || []).length) searchCharacters().catch((err) => alert(err.message));
  if (id === "equipment-query" && !(state.lastEquipmentRows || []).length) searchEquipment().catch((err) => alert(err.message));
}

function vsEffectDescription(effect = {}) {
  return window.LWVsDisplay?.effectDescription
    ? window.LWVsDisplay.effectDescription(effect, enrichVsEffect)
    : (enrichVsEffect(effect).description || enrichVsEffect(effect).name || "未知效果");
}

function getFilterValues(id) {
  return state.filterTags[id] || [];
}

function setFilterValues(id, values) {
  state.filterTags[id] = Array.from(new Set((values || []).filter(Boolean)));
  renderFilterTags(id);
}

function addFilterValue(id, value, label) {
  if (!value) return;
  const rows = getFilterValues(id);
  if (!rows.some((row) => row.value === value)) {
    rows.push({ value, label: label || value });
  }
  setFilterValues(id, rows);
}

function renderFilterTags(id) {
  const root = $(`#${id}Tags`);
  if (!root) return;
  root.innerHTML = getFilterValues(id).map((row, idx) => `<button type="button" class="tag" data-filter-id="${id}" data-filter-idx="${idx}">${row.label}</button>`).join("");
  const hidden = $(`#${id}`);
  if (hidden && hidden.type === "hidden") hidden.value = selectedFilterValues(id).join(",");
}

function selectedFilterValues(id) {
  return getFilterValues(id).map((row) => row.value);
}

function bindAddFilterButtons() {
  $$("[data-add-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.addFilter;
      const source = $(`#${id}`);
      if (!source || !source.value) return;
      const label = source.selectedOptions?.[0]?.textContent || source.value;
      const targetId = id === "eqStatsSelect" ? "eqStats" : id;
      addFilterValue(targetId, source.value, label);
      if (source.tagName === "SELECT") source.value = "";
    });
  });
  document.addEventListener("click", (event) => {
    const tag = event.target.closest(".tag[data-filter-id]");
    if (!tag) return;
    const rows = getFilterValues(tag.dataset.filterId);
    rows.splice(Number(tag.dataset.filterIdx), 1);
    setFilterValues(tag.dataset.filterId, rows);
  });
}

function buildCharacterLoader(prefix) {
  return `
    <div class="loader-tabs">
      <label>ID<input data-role="${prefix}_id_query" list="characterOptions" placeholder="角色ID"></label>
      <button type="button" class="small secondary" data-load-character-id>载入ID</button>
      <label>世界群<select data-role="${prefix}_world"></select></label>
      <label>角色<select data-role="${prefix}_world_char"></select></label>
      <button type="button" class="small secondary" data-load-character>载入</button>
    </div>
  `;
}

function hydrateCharacterLoader(root, prefix) {
  const world = $(`[data-role="${prefix}_world"]`, root);
  const charSelect = $(`[data-role="${prefix}_world_char"]`, root);
  if (!world || !charSelect) return;
  world.innerHTML = `<option value="">选择世界群</option>${(state.boot.world_group_options || []).map((value) => `<option value="${value}">${value}</option>`).join("")}`;
  world.addEventListener("change", () => refreshCharacterLoaderOptions(root, prefix));
  refreshCharacterLoaderOptions(root, prefix);
}

function refreshCharacterLoaderOptions(root, prefix) {
  const world = $(`[data-role="${prefix}_world"]`, root);
  const charSelect = $(`[data-role="${prefix}_world_char"]`, root);
  if (!world || !charSelect) return;
  const selected = charSelect.value || "";
  const worldValue = world.value || "";
  const rows = (state.boot.character_options || []).filter((row) => !worldValue || row.world_group === worldValue);
  charSelect.innerHTML = `<option value="">选择角色</option>${rows.map((row) => `<option value="${row.id}">${escapeHtml(row.name || row.id)} / ${escapeHtml(row.world_group || "-")}</option>`).join("")}`;
  if (selected && rows.some((row) => String(row.id) === String(selected))) {
    charSelect.value = selected;
  }
}

function characterLoaderQuery(root, prefix) {
  return $(`[data-role="${prefix}_id_query"]`, root)?.value
    || $(`[data-role="${prefix}_world_char"]`, root)?.value
    || "";
}

function characterLoaderSelectionQuery(root, prefix) {
  return $(`[data-role="${prefix}_world_char"]`, root)?.value
    || "";
}

function characterOptionById(charId) {
  const id = String(charId || "").trim();
  return (state.boot.character_options || []).find((row) => String(row.id) === id) || null;
}

function setCharacterLoaderValue(root, prefix, charId) {
  const id = String(charId || "").trim();
  const option = characterOptionById(id);
  const idInput = $(`[data-role="${prefix}_id_query"]`, root);
  const world = $(`[data-role="${prefix}_world"]`, root);
  const charSelect = $(`[data-role="${prefix}_world_char"]`, root);
  if (idInput) idInput.value = id;
  if (world && option) {
    world.value = option.world_group || "";
    world.dispatchEvent(new Event("change"));
  }
  if (charSelect) charSelect.value = id;
  const hidden = $('[data-field="character_id"]', root);
  if (hidden) hidden.value = id;
}

function setActiveTab(id) {
  const sidebarTab = ["character-query", "equipment-query", "character-detail", "character-data-pic"].includes(id) ? "query-hub" : id;
  if (id === "query-hub") {
    setQueryTab("character-query");
    if (typeof renderModuleSidebar === "function") renderModuleSidebar("query-hub");
    return;
  }
  $$(".tabs button").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === id));
  $$(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === id));
  if (typeof renderModuleSidebar === "function") renderModuleSidebar(sidebarTab);
}

function setActiveSubtab(id) {
  $$("#damageSubtabs button").forEach((btn) => btn.classList.toggle("active", btn.dataset.subtab === id));
  $$(".sub-panel").forEach((panel) => panel.classList.toggle("active", panel.id === id));
  setActiveTab("damage");
  if (typeof renderModuleSidebar === "function") renderModuleSidebar("damage");
}

function createDatalists() {
  const charList = document.createElement("datalist");
  charList.id = "characterOptions";
  const charIdList = document.createElement("datalist");
  charIdList.id = "characterIdOptions";
  for (const row of state.boot.character_options || []) {
    const option = document.createElement("option");
    option.value = row.id;
    option.label = row.label;
    charList.appendChild(option);
    const idOption = document.createElement("option");
    idOption.value = row.id;
    idOption.label = row.label || `${row.id} / ${row.name || ""}`;
    charIdList.appendChild(idOption);
    if (row.name) {
      const nameOption = document.createElement("option");
      nameOption.value = row.name;
      nameOption.label = `${row.id} / ${row.world_group || ""}`;
      charList.appendChild(nameOption);
    }
  }
  document.body.appendChild(charList);
  document.body.appendChild(charIdList);

  const eqList = document.createElement("datalist");
  eqList.id = "equipmentOptions";
  for (const [label, value] of state.boot.equipment_options || []) {
    const option = document.createElement("option");
    option.value = value;
    option.label = label;
    eqList.appendChild(option);
  }
  document.body.appendChild(eqList);

  const tribeList = document.createElement("datalist");
  tribeList.id = "tribeOptions";
  for (const [id, label] of state.boot.tribe_options || []) {
    const option = document.createElement("option");
    option.value = id;
    option.label = `${id} ${label}`;
    tribeList.appendChild(option);
  }
  document.body.appendChild(tribeList);
}

async function loadCharacterMeta(query) {
  if (!query) return null;
  return api(`/api/character-resolve?q=${encodeURIComponent(query)}`);
}

async function loadCharacterPresets() {
  state.characterPresets = await api("/api/character-presets");
}

async function loadArenaPresets() {
  state.arenaPresets = await api("/api/arena-presets");
}

async function loadArenaEnemyData() {
  state.arenaEnemyData = await api("/api/arena-enemy-data");
}

async function saveCharacterPresets() {
  return api("/api/character-presets", {
    method: "POST",
    body: JSON.stringify({ character_presets: state.characterPresets }),
  });
}

async function saveArenaPresets() {
  return api("/api/arena-presets", {
    method: "POST",
    body: JSON.stringify({ arena_presets: state.arenaPresets }),
  });
}

function fillMeta(card, meta) {
  if (!meta) return;
  const idInput = $('[data-field="character_id"]', card);
  if (idInput) idInput.value = meta.id || "";
  $('[data-role="name"]', card).textContent = meta.name || "-";
  $('[data-role="world"]', card).textContent = meta.world_group || "-";
  $('[data-role="type"]', card).textContent = meta.type_label || "-";
  const img = $('[data-role="avatar"]', card);
  if (img) img.src = avatarUrl(meta.id);
  const tribe = $('[data-field="tribe_text"]', card);
  if (tribe && Array.isArray(meta.tribe)) tribe.value = meta.tribe.join(",");
  card.classList.add("loaded");
}

function applyStatsToCard(card, stats = {}) {
  for (const key of STAT_KEYS) {
    const input = $(`[data-field="${key}"]`, card) || $(`[data-stat="${key}"]`, card);
    if (input && stats[key] !== undefined && stats[key] !== null && stats[key] !== "") {
      input.value = stats[key];
    }
  }
}

function applyQualityToCard(card, quality = []) {
  const qualityButtons = $$(".quality-btn", card);
  (quality || []).forEach((value, idx) => {
    const btn = qualityButtons[idx];
    if (!btn) return;
    btn.dataset.state = String(value);
    const img = $("img", btn);
    if (img) img.src = temperamentIconUrl(btn.dataset.label, value);
  });
}

function applyArenaPresetToEnemyCard(card, charId) {
  const preset = state.arenaPresets[String(charId)];
  if (!preset) return false;
  if (preset.stat_overrides) {
    const stats = { ...preset.stat_overrides };
    delete stats.hp;
    applyStatsToCard(card, stats);
  }
  if (preset.barrier_count !== undefined) $('[data-field="barrier_count"]', card).value = preset.barrier_count;
  if (Array.isArray(preset.quality)) applyQualityToCard(card, preset.quality);
  card._enemySkillEffects = preset.enemy_skill_effects || [];
  renderEnemyInfoBlock(card, { skill_name: "擂台预设技能", skill_buffs_text: (card._enemySkillEffects || []).map((row) => row.join(",")) });
  return true;
}

function enemyInfoLines(enemy = {}) {
  const lines = [];
  if (enemy.skill_name || (enemy.skill_buffs_text || []).length) {
    lines.push(`<b>技能</b> ${escapeHtml(enemy.skill_name || "-")}：${(enemy.skill_buffs_text || []).map(escapeHtml).join(" / ") || "-"}`);
  }
  if (enemy.ex1_name || (enemy.ex1_buffs_text || []).length) {
    lines.push(`<b>EX-1</b> ${escapeHtml(enemy.ex1_name || "-")}：${(enemy.ex1_buffs_text || []).map(escapeHtml).join(" / ") || "-"}`);
  }
  if (enemy.ex2_name || (enemy.ex2_buffs_text || []).length) {
    lines.push(`<b>EX-2</b> ${escapeHtml(enemy.ex2_name || "-")}：${(enemy.ex2_buffs_text || []).map(escapeHtml).join(" / ") || "-"}`);
  }
  (enemy.card_buffs_text || []).forEach((texts, idx) => {
    lines.push(`<b>符卡${idx + 1}</b> ${(texts || []).map(escapeHtml).join(" / ") || "-"}`);
  });
  if (enemy.extra_description) {
    lines.push(`<b>额外说明</b> ${escapeHtml(enemy.extra_description)}`);
  }
  return lines;
}

function renderEnemyInfoHtml(enemy = {}, emptyText = "暂无技能/阶段说明") {
  const lines = enemyInfoLines(enemy);
  return lines.map((line) => `<div class="compact-info-line">${line}</div>`).join("") || `<span class="hint">${escapeHtml(emptyText)}</span>`;
}

function renderEnemyInfoBlock(card, enemy = {}) {
  const root = $('[data-role="enemy_extra_info"]', card);
  if (!root) return;
  const lines = enemyInfoLines(enemy);
  root.innerHTML = lines.map((line) => `<div class="compact-info-line">${line}</div>`).join("") || '<span class="hint">暂无技能/阶段说明</span>';
}

function clearVsEnemyState(card, { clearBuffs = false } = {}) {
  if (!card?.classList?.contains("enemy-slot")) return;
  card._enemySkillEffects = [];
  card._enemyExtra = null;
  const phaseRoot = $('[data-role="phase_buttons"]', card);
  if (phaseRoot) phaseRoot.innerHTML = "";
  card._enemyPhases = [];
  card._enemyPhaseIndex = 0;
  renderEnemyInfoBlock(card, {});
  if (clearBuffs) {
    const buffRoot = $('[data-role="buffs"]', card);
    if (buffRoot) buffRoot.innerHTML = "";
  }
}

function clearAllVsEnemyState({ clearBuffs = false } = {}) {
  $$(".enemy-slot").forEach((card) => clearVsEnemyState(card, { clearBuffs }));
  state.activeVsPreset = null;
  state.activeVsTagEffects = [];
  state.vsManualPayload = null;
  state.vsManualInitialPayload = null;
  state.vsManualState = null;
  state.vsManualPhase = "idle";
  state.vsManualSkillUsed = {};
  state.vsManualPendingSkills = {};
  state.vsManualSkillLog = [];
  const controls = $("#vsManualControls");
  if (controls) controls.innerHTML = "";
  updateVsManualButtons();
  if (typeof setVsManualAllyLocked === "function") setVsManualAllyLocked(false);
}

async function resolveSlotCharacter(card, forcedQuery = "") {
  const query = forcedQuery || characterLoaderQuery(card, "slot") || $('[data-field="character_id"]', card).value;
  const meta = await loadCharacterMeta(query);
  if (!meta) {
    alert("未找到角色");
    return;
  }
  setCharacterLoaderValue(card, "slot", meta.id);
  fillMeta(card, meta);
  if (card.classList.contains("ally-slot") || card.classList.contains("vs-ally-slot")) applyPresetToAllyCard(card, meta.id);
  if (card.classList.contains("enemy-slot")) {
    clearVsEnemyState(card, { clearBuffs: true });
    if ($("#calcMode")?.value === "vs") {
      state.activeVsPreset = null;
      state.activeVsTagEffects = [];
      state.vsManualPayload = null;
      state.vsManualInitialPayload = null;
      state.vsManualState = null;
      state.vsManualPhase = "idle";
      state.vsManualSkillUsed = {};
      state.vsManualPendingSkills = {};
      state.vsManualSkillLog = [];
      const controls = $("#vsManualControls");
      if (controls) controls.innerHTML = "";
      renderModeOptions();
      updateVsManualButtons();
      if (typeof setVsManualAllyLocked === "function") setVsManualAllyLocked(false);
    }
    if ($("#calcMode")?.value === "arena") applyArenaPresetToEnemyCard(card, meta.id);
    if (typeof renderSlotTribeText === "function") renderSlotTribeText(card);
  }
  renderOverview();
  renderGlobalSkillButtons();
}

async function resolveSlotCharacterBySelection(card) {
  const query = characterLoaderSelectionQuery(card, "slot") || $('[data-field="character_id"]', card).value;
  return resolveSlotCharacter(card, query);
}

function addBuffRow(container, row = []) {
  const node = $("#buffRowTemplate").content.firstElementChild.cloneNode(true);
  const values = { buff_id: row[0] ?? "", sub_id: row[1] ?? "", duration: row[2] ?? "", value: row[3] ?? "" };
  for (const [key, value] of Object.entries(values)) $(`[data-field="${key}"]`, node).value = value;
  $("[data-remove-row]", node).addEventListener("click", () => node.remove());
  node.insertAdjacentHTML("beforeend", '<small data-role="effect_text" class="effect-desc"></small>');
  const refresh = () => updateEffectDescription(node, false).catch(() => {});
  $$("input", node).forEach((input) => input.addEventListener("change", refresh));
  refresh();
  container.appendChild(node);
}

async function updateEffectDescription(row, hasTarget) {
  const buffId = $('[data-field="buff_id"]', row)?.value || "";
  if (!buffId) return;
  const params = new URLSearchParams({
    buff_id: buffId,
    sub_id: $('[data-field="sub_id"]', row)?.value || 0,
    target: hasTarget ? ($('[data-field="target"]', row)?.value || 1) : 1,
    duration: $('[data-field="duration"]', row)?.value || 0,
    value: $('[data-field="value"]', row)?.value || 0,
  });
  const data = await api(`/api/effect-format?${params}`);
  const box = $('[data-role="effect_text"]', row);
  if (box) box.textContent = data.text || "";
}

function collectBuffRows(container) {
  return $$(".buff-row", container).map((row) => [
    Number($('[data-field="buff_id"]', row).value || 0),
    Number($('[data-field="sub_id"]', row).value || 0),
    Number($('[data-field="duration"]', row).value || 0),
    Number($('[data-field="value"]', row).value || 0),
  ]).filter((row) => row[0] > 0);
}

function addEnemySkillRow(container, row = []) {
  const node = document.createElement("div");
  node.className = "enemy-skill-row";
  node.innerHTML = `
    <input data-field="buff_id" placeholder="ID">
    <input data-field="sub_id" placeholder="subID">
    <input data-field="target" placeholder="target">
    <input data-field="duration" placeholder="回合">
    <input data-field="value" placeholder="值">
    <button class="small danger" data-remove-row>删除</button>
    <small data-role="effect_text" class="effect-desc"></small>
  `;
  const values = { buff_id: row[0] ?? "", sub_id: row[1] ?? "", target: row[2] ?? "", duration: row[3] ?? "", value: row[4] ?? "" };
  for (const [key, value] of Object.entries(values)) $(`[data-field="${key}"]`, node).value = value;
  $("[data-remove-row]", node).addEventListener("click", () => node.remove());
  const refresh = () => updateEffectDescription(node, true).catch(() => {});
  $$("input", node).forEach((input) => input.addEventListener("change", refresh));
  refresh();
  container.appendChild(node);
}

function collectEnemySkillRows(container) {
  return $$(".enemy-skill-row", container).map((row) => [
    Number($('[data-field="buff_id"]', row).value || 0),
    Number($('[data-field="sub_id"]', row).value || 0),
    Number($('[data-field="target"]', row).value || 0),
    Number($('[data-field="duration"]', row).value || 0),
    Number($('[data-field="value"]', row).value || 0),
  ]).filter((row) => row[0] > 0);
}

function createQualityEditor() {
  const wrap = document.createElement("div");
  wrap.className = "quality-grid";
  (state.boot.quality_labels || []).slice(0, 8).forEach((label, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "quality-btn";
    btn.dataset.idx = String(idx);
    btn.dataset.state = "1";
    btn.dataset.label = label;
    btn.innerHTML = `<img src="${temperamentIconUrl(label, 1)}" alt="${label}"><span>${label}</span>`;
    btn.addEventListener("click", () => {
      const current = Number(btn.dataset.state || 1);
      const next = current === 1 ? 2 : current === 2 ? 0 : 1;
      btn.dataset.state = String(next);
      $("img", btn).src = temperamentIconUrl(label, next);
    });
    wrap.appendChild(btn);
  });
  return wrap;
}

function resetQuality(wrap) {
  $$(".quality-btn", wrap).forEach((btn) => {
    btn.dataset.state = "1";
    const label = btn.dataset.label || btn.textContent.trim();
    const img = $("img", btn);
    if (img) img.src = temperamentIconUrl(label, 1);
  });
}

function collectQuality(card) {
  const values = $$(".quality-btn", card).filter((btn) => btn.dataset.idx !== undefined)
    .sort((a, b) => Number(a.dataset.idx) - Number(b.dataset.idx))
    .map((btn) => Number(btn.dataset.state || 1));
  while (values.length < 9) values.push(1);
  return values.slice(0, 9);
}

async function updateEquipmentSummary(row, detailed = false) {
  const input = $('[data-field="equipment_id"]', row);
  const box = $('[data-role="equipment_summary"]', row);
  if (!input || !box) return;
  const query = input.value.trim();
  if (!query) {
    box.innerHTML = "";
    return;
  }
  const info = await api(`/api/equipment-resolve?q=${encodeURIComponent(query)}`);
  if (!info) {
    box.textContent = "未找到绘卷";
    return;
  }
  input.value = info.equipment_id;
  const buffHtml = detailed ? `<div class="equipment-buffs">${(info.buffs || []).map((text) => `<small>${text || "-"}</small>`).join("")}</div>` : "";
  const summaryText = `${info.equipment_id_text || info.equipment_id}/${info.name}，${info.style_label || "-"}-${info.stats_text || "无面板"}`;
  box.innerHTML = `
    <small title="${escapeHtml(summaryText)}">${escapeHtml(summaryText).slice(0, 32)}${summaryText.length > 32 ? "..." : ""}</small>
    ${buffHtml}
  `;
}
