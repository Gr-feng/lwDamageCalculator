const state = {
  boot: null,
  lastResult: null,
  sort: {},
  globalSkillOrder: [],
  characterPresets: {},
  arenaPresets: {},
  enemyWaves: { 1: {}, 2: {}, 3: {} },
  currentWave: 1,
  resultView: "overview",
  filterTags: {},
  rolePresetDetail: false,
  loadedRolePresetId: "",
  hideCharacterImages: false,
  hideEquipmentImages: false,
  lastCharacterRows: [],
  lastEquipmentRows: [],
  activeVsTagEffects: [],
  customVsTagEffects: [],
  activeVsPreset: null,
  vsPresets: [],
  vsManualPayload: null,
  vsManualState: null,
  vsManualPhase: "idle",
  vsManualSkillUsed: {},
  roleBrowserVisible: false,
  arenaBrowserVisible: false,
  arenaEnemyData: { rows: [] },
  arenaGalleryFilter: "",
  pendingArenaPresetId: "",
  weeklySimpleMode: false,
  roleGalleryFilters: {
    preset: "",
    rebirth2: false,
    unowned: false,
  },
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
const STAT_KEYS = ["hp", "yang_atk", "yang_def", "yin_atk", "yin_def", "speed"];
const STAT_LABELS = { hp: "HP", yang_atk: "阳攻", yang_def: "阳防", yin_atk: "阴攻", yin_def: "阴防", speed: "速度" };
const PRESET_STAT_ORDER = ["hp", "yang_atk", "yang_def", "speed", "yin_atk", "yin_def"];
const ARENA_STAT_KEYS = ["yang_atk", "yang_def", "yin_atk", "yin_def", "speed"];
const ARENA_FIXED_STATS_BY_BARRIER = {
  7: { yang_atk: 7140, yang_def: 4998, yin_atk: 9240, yin_def: 9240 },
  4: { yang_atk: 7140, yang_def: 9240, yin_atk: 9240, yin_def: 9828 },
};
const EQUIPMENT_SLOTS = [["1a", "1符A"], ["2a", "2符A"], ["1b", "1符B"], ["2b", "2符B"], ["5", "终符"]];
const ATTACK_OPTIONS = [["1c", "扩散"], ["2c", "集中"], ["1", "1符"], ["2", "2符"], ["5", "终符"]];
const ATTACK_DETAIL_ORDER = ["扩散", "集中", "1符", "2符", "终符"];
const ELEMENT_ICON_LABELS = { 1: "日", 2: "月", 3: "火", 4: "水", 5: "木", 6: "金", 7: "土", 8: "星", 9: "无" };
const VS_TAGS = ["敌方六维", "弹种倍率", "属性倍率", "Type倍率", "P点回复", "种族特攻受伤", "敌方技能", "血条状态", "结界异常", "额外说明"];

function setQueryTab(id) {
  setActiveTab(id);
  $$(".tabs button").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === "query-hub"));
  $$(".query-subtabs [data-query-jump], .query-hub-actions [data-query-jump]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.queryJump === id);
    btn.classList.toggle("secondary", btn.dataset.queryJump !== id);
  });
  if (id === "character-query" && !(state.lastCharacterRows || []).length) searchCharacters().catch((err) => alert(err.message));
  if (id === "equipment-query" && !(state.lastEquipmentRows || []).length) searchEquipment().catch((err) => alert(err.message));
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const payload = await response.json();
  if (!payload.ok) {
    console.error(payload.traceback || payload);
    throw new Error(payload.error || "请求失败");
  }
  return payload.data;
}

function optionList(mapping, includeBlank = false) {
  const rows = Object.entries(mapping || {}).sort((a, b) => Number(a[0]) - Number(b[0]));
  return `${includeBlank ? '<option value="">全部</option>' : ""}${rows.map(([v, t]) => `<option value="${v}">${v} ${t}</option>`).join("")}`;
}

function tupleOptions(rows, includeBlank = false) {
  return `${includeBlank ? '<option value="">全部</option>' : ""}${(rows || []).map((row) => `<option value="${row[0]}">${row[0]} ${row[1]}</option>`).join("")}`;
}

function selectedValues(select) {
  return Array.from(select.selectedOptions || []).map((option) => option.value).filter(Boolean);
}

function numberText(value) {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) return String(value ?? "");
  return Math.abs(num - Math.round(num)) < 1e-9 ? String(Math.round(num)) : num.toFixed(2);
}

function avatarUrl(charId) {
  const id = String(charId || 0).trim();
  return `/assets/avatars/S${id}01.png`;
}

function cardIconUrl(equipmentId) {
  const id = String(equipmentId || 0).trim();
  return `/assets/card_icons/PTS${id}.png`;
}

function barrierIconUrl(value = 0) {
  return `/assets/barrier_icons/${Number(value || 0)}.png`;
}

function attributeIconUrl(elementId) {
  const label = ELEMENT_ICON_LABELS[Number(elementId)] || "";
  return label ? `/assets/attribute_icons/属性 ${label}.png` : "";
}

function temperamentIconUrl(label, stateValue) {
  if (String(label) === "无") return "/assets/attribute_icons/属性 无.png";
  return `/assets/temperament_icons/气质图标 ${label} ${stateValue}.png`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[ch]));
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
  world.addEventListener("change", () => {
    const rows = (state.boot.character_options || []).filter((row) => row.world_group === world.value);
    charSelect.innerHTML = `<option value="">选择角色</option>${rows.map((row) => `<option value="${row.id}">${row.name}</option>`).join("")}`;
  });
}

function characterLoaderQuery(root, prefix) {
  return $(`[data-role="${prefix}_id_query"]`, root)?.value
    || $(`[data-role="${prefix}_world_char"]`, root)?.value
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
  if (id === "query-hub") {
    setQueryTab("character-query");
    return;
  }
  $$(".tabs button").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === id));
  $$(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === id));
}

function setActiveSubtab(id) {
  $$("#damageSubtabs button").forEach((btn) => btn.classList.toggle("active", btn.dataset.subtab === id));
  $$(".sub-panel").forEach((panel) => panel.classList.toggle("active", panel.id === id));
  setActiveTab("damage");
}

function createDatalists() {
  const charList = document.createElement("datalist");
  charList.id = "characterOptions";
  for (const row of state.boot.character_options || []) {
    const option = document.createElement("option");
    option.value = row.id;
    option.label = row.label;
    charList.appendChild(option);
  }
  document.body.appendChild(charList);

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

function renderEnemyInfoBlock(card, enemy = {}) {
  const root = $('[data-role="enemy_extra_info"]', card);
  if (!root) return;
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
  state.vsManualState = null;
  state.vsManualPhase = "idle";
  state.vsManualSkillUsed = {};
  const controls = $("#vsManualControls");
  if (controls) controls.innerHTML = "";
  updateVsManualButtons();
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
  if (card.classList.contains("ally-slot")) applyPresetToAllyCard(card, meta.id);
  if (card.classList.contains("enemy-slot")) {
    clearVsEnemyState(card, { clearBuffs: true });
    if ($("#calcMode")?.value === "vs") {
      state.activeVsPreset = null;
      state.activeVsTagEffects = [];
      state.vsManualPayload = null;
      state.vsManualState = null;
      state.vsManualPhase = "idle";
      state.vsManualSkillUsed = {};
      const controls = $("#vsManualControls");
      if (controls) controls.innerHTML = "";
      renderModeOptions();
      updateVsManualButtons();
    }
    if ($("#calcMode")?.value === "arena") applyArenaPresetToEnemyCard(card, meta.id);
  }
  renderOverview();
  renderGlobalSkillButtons();
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

function makeCharacterHeader(kind, pos) {
  return `
    <div class="slot-head">
      <h3>${kind}${pos}</h3>
      <div class="head-actions">
        <button type="button" class="small secondary" data-collapse-card>折叠</button>
        <label class="inline-check"><input data-field="enabled" type="checkbox" ${pos === 0 ? "checked" : ""}>启用</label>
      </div>
    </div>
    <div class="slot-identity">
      <img data-role="avatar" class="avatar-small" src="/assets/avatars/S0.png" onerror="this.src='/assets/avatars/S0.png'">
      <div class="identity-fields">
        ${buildCharacterLoader("slot")}
        <div class="meta-line">名称：<b data-role="name">-</b>　世界群：<b data-role="world">-</b>　类型：<b data-role="type">-</b></div>
      </div>
    </div>
  `;
}

function bindSlotCommon(card) {
  hydrateCharacterLoader(card, "slot");
  $('[data-load-character-id]', card).addEventListener("click", () => resolveSlotCharacter(card, $(`[data-role="slot_id_query"]`, card)?.value || "").catch((err) => alert(err.message)));
  $('[data-load-character]', card).addEventListener("click", () => resolveSlotCharacter(card).catch((err) => alert(err.message)));
  $('[data-field="character_id"]', card)?.addEventListener("change", () => resolveSlotCharacter(card).catch(() => {}));
  $('[data-field="enabled"]', card)?.addEventListener("change", () => {
    const enabled = $('[data-field="enabled"]', card).checked;
    card.classList.toggle("collapsed", !enabled);
    const collapseBtn = $('[data-collapse-card]', card);
    if (collapseBtn) collapseBtn.textContent = card.classList.contains("collapsed") ? "展开" : "折叠";
    saveCurrentEnemyWave();
    renderOverview();
    renderGlobalSkillButtons();
  });
  $('[data-collapse-card]', card)?.addEventListener("click", (event) => {
    card.classList.toggle("collapsed");
    event.currentTarget.textContent = card.classList.contains("collapsed") ? "展开" : "折叠";
  });
  card.addEventListener("input", () => {
    saveCurrentEnemyWave();
    renderOverview();
  });
}

function renderEnemySlots() {
  const root = $("#enemySlots");
  root.innerHTML = "";
  for (let pos = 0; pos < 3; pos += 1) {
    const card = document.createElement("article");
    card.className = "slot-card enemy-slot";
    card.dataset.pos = String(pos);
    card.innerHTML = `
      ${makeCharacterHeader("敌方位置 ", pos)}
      <div class="slot-body">
      <div class="form-grid">
        <label>角色ID<input data-field="character_id" value="${state.boot.defaults.enemy_id}"></label>
        <label>HP<input data-field="hp" value="50000000"></label>
        <label>阳攻<input data-field="yang_atk" value="0"></label>
        <label>阳防<input data-field="yang_def" value="10000"></label>
        <label>阴攻<input data-field="yin_atk" value="0"></label>
        <label>阴防<input data-field="yin_def" value="10000"></label>
        <label>速度<input data-field="speed" value="0"></label>
        <label>护盾数<input data-field="barrier_count" value="9"></label>
        <button type="button" class="toggle-btn" data-field="is_break_all" data-value="false">完全破盾：否</button>
      </div>
      <div class="subsection"><div class="subsection-title"><h4>气质</h4><button type="button" class="small secondary" data-reset-quality>归零</button></div><div data-role="quality"></div></div>
      <div class="subsection"><label>Tribe<input data-field="tribe_text" placeholder="例如 1,2,3"></label></div>
      <div class="subsection compact-info"><h4>敌方技能 / 阶段效果 / 符卡效果</h4><div data-role="phase_buttons" class="phase-buttons"></div><div data-role="enemy_extra_info"></div></div>
      <div class="subsection">
        <h4>Buffs</h4>
        <div data-role="buffs"></div>
        <button class="small secondary" data-add-buff>添加 buff</button>
        <button class="small secondary" data-clear-buffs>删除全部 buff</button>
      </div>
      </div>
    `;
    $('[data-role="quality"]', card).appendChild(createQualityEditor());
    bindSlotCommon(card);
    if (pos > 0) {
      card.classList.add("collapsed");
      const collapseBtn = $('[data-collapse-card]', card);
      if (collapseBtn) collapseBtn.textContent = "展开";
    }
    $('[data-reset-quality]', card).addEventListener("click", () => resetQuality($('[data-role="quality"]', card)));
    $('[data-field="is_break_all"]', card).addEventListener("click", (event) => {
      const btn = event.currentTarget;
      const next = btn.dataset.value !== "true";
      btn.dataset.value = String(next);
      btn.textContent = `完全破盾：${next ? "是" : "否"}`;
      btn.classList.toggle("active", next);
    });
    $("[data-add-buff]", card).addEventListener("click", () => addBuffRow($('[data-role="buffs"]', card)));
    $("[data-clear-buffs]", card).addEventListener("click", () => ($('[data-role="buffs"]', card).innerHTML = ""));
    root.appendChild(card);
  }
}

function renderSkillButtons(container, prefix, onChange) {
  container.innerHTML = "";
  for (let i = 0; i < 3; i += 1) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "skill-btn secondary";
    btn.dataset.skill = String(i);
    btn.textContent = `${prefix}技能${i + 1}`;
    btn.addEventListener("click", () => {
      btn.classList.toggle("active");
      onChange();
    });
    container.appendChild(btn);
  }
}

function updateAllySkillOrder(card) {
  const order = $$(".skill-btn.active", card).map((btn) => Number(btn.dataset.skill));
  $('[data-field="skill_order_text"]', card).value = order.join(",");
  $('[data-role="skill_order_view"]', card).textContent = order.length ? order.map((i) => `技能${i + 1}`).join(" → ") : "不开技能";
}

function renderAllySlots() {
  const root = $("#allySlots");
  root.innerHTML = "";
  for (let pos = 0; pos < 3; pos += 1) {
    const card = document.createElement("article");
    card.className = "slot-card ally-slot";
    card.dataset.pos = String(pos);
    card.innerHTML = `
      ${makeCharacterHeader("我方位置 ", pos)}
      <div class="slot-body">
      <div class="form-grid">
        <label>角色ID<input data-field="character_id" value="${state.boot.defaults.ally_id + pos}"></label>
        <label>初始p点<input data-field="initial_spirit" value="3.0"></label>
        <label>初始护盾数<input data-field="barrier_count" value="5"></label>
        <label>目标敌人<input data-field="target_enemy_pos" value="${state.boot.defaults.target_enemy_pos}"></label>
        <label>开p数<input data-field="spirit_level" value="${state.boot.defaults.spirit_level}"></label>
        <label>开盾数量<input data-field="shield_open_count" value="${state.boot.defaults.shield_open_count}"></label>
        <label>攻击类型<select data-field="attack_type">${ATTACK_OPTIONS.map(([v, t]) => `<option value="${v}" ${v === "5" ? "selected" : ""}>${t}</option>`).join("")}</select></label>
        <input data-field="skill_order_text" type="hidden">
      </div>
      <div class="subsection">
        <h4>Skills</h4>
        <div data-role="skill_buttons" class="skill-grid mini"></div>
        <div class="hint">开启顺序：<span data-role="skill_order_view">不开技能</span></div>
      </div>
      <div class="subsection">
        <h4>绘卷</h4>
        <div data-role="equipment"></div>
      </div>
      <div class="subsection">
        <h4>Buffs</h4>
        <div data-role="buffs"></div>
        <button class="small secondary" data-add-buff>添加 buff</button>
        <button class="small secondary" data-clear-buffs>删除全部 buff</button>
      </div>
      </div>
    `;
    renderSkillButtons($('[data-role="skill_buttons"]', card), "", () => updateAllySkillOrder(card));
    const eqRoot = $('[data-role="equipment"]', card);
    for (const [key, label] of EQUIPMENT_SLOTS) {
      const row = document.createElement("div");
      row.className = "equipment-row";
      row.dataset.slot = key;
      row.innerHTML = `<span>${label}</span><div><input data-field="equipment_id" list="equipmentOptions" placeholder="ID或名称"><div data-role="equipment_summary" class="equipment-summary"></div></div><button class="small secondary" data-recommend-one>推荐</button><button class="small secondary" data-clear-one>清空</button>`;
      $('[data-field="equipment_id"]', row).addEventListener("change", () => updateEquipmentSummary(row).catch(() => {}));
      $('[data-recommend-one]', row).addEventListener("click", async () => {
        const rec = await api(`/api/recommended?character_id=${encodeURIComponent($('[data-field="character_id"]', card).value)}`);
        $('[data-field="equipment_id"]', row).value = rec[key] || "";
        await updateEquipmentSummary(row);
      });
      $('[data-clear-one]', row).addEventListener("click", () => {
        $('[data-field="equipment_id"]', row).value = "";
        $('[data-role="equipment_summary"]', row).innerHTML = "";
      });
      eqRoot.appendChild(row);
    }
    const recAll = document.createElement("button");
    recAll.className = "small secondary";
    recAll.type = "button";
    recAll.textContent = "填入五张推荐绘卷";
    recAll.addEventListener("click", async () => {
      const rec = await api(`/api/recommended?character_id=${encodeURIComponent($('[data-field="character_id"]', card).value)}`);
      for (const row of $$(".equipment-row", card)) {
        $('[data-field="equipment_id"]', row).value = rec[row.dataset.slot] || "";
        await updateEquipmentSummary(row);
      }
    });
    eqRoot.appendChild(recAll);
    bindSlotCommon(card);
    if (pos > 0) {
      card.classList.add("collapsed");
      const collapseBtn = $('[data-collapse-card]', card);
      if (collapseBtn) collapseBtn.textContent = "展开";
    }
    $("[data-add-buff]", card).addEventListener("click", () => addBuffRow($('[data-role="buffs"]', card)));
    $("[data-clear-buffs]", card).addEventListener("click", () => ($('[data-role="buffs"]', card).innerHTML = ""));
    root.appendChild(card);
  }
}

function renderFullFieldRows() {
  const configs = [
    ["#fieldBulletRows", state.boot.bullet_labels],
    ["#fieldElementRows", state.boot.element_labels],
    ["#fieldTypeRows", state.boot.type_labels],
  ];
  for (const [selector, labels] of configs) {
    const root = $(selector);
    root.innerHTML = "";
    for (const [id, label] of Object.entries(labels || {}).sort((a, b) => Number(a[0]) - Number(b[0]))) {
      const row = document.createElement("label");
      row.className = "field-full-row";
      row.innerHTML = `<span>${label}：</span><input data-sub-id="${id}" value="100">`;
      root.appendChild(row);
    }
  }
  renderModeOptions();
}

function formatVsFactor(value) {
  const factor = 1 + Number(value || 0) / 100;
  return `${factor.toFixed(4).replace(/0+$/, "").replace(/\.$/, "")}x`;
}

function renderVsEffectOverview(activeTags) {
  const statLabels = { 1: "最大体力", 2: "阳攻", 3: "阳防", 4: "阴攻", 5: "阴防", 6: "速度", 7: "命中", 8: "回避" };
  const statFactors = {};
  const fieldRows = [];
  const others = [];
  for (const tag of activeTags || []) {
    for (const effect of tag.effects || []) {
      const side = Number(effect.side || 0);
      const kind = Number(effect.kind || 0);
      const subId = Number(effect.sub_id || 0);
      const factor = Math.max(0, 1 + Number(effect.value || 0) / 100);
      if (side === 4 && kind === 1 && statLabels[subId]) {
        statFactors[subId] = (statFactors[subId] || 1) * factor;
      } else if (side === 2 && kind === 10) {
        fieldRows.push(`弹种伤害倍率：${state.boot.bullet_labels?.[subId] || subId} ${numberText(factor * 100)}%`);
      } else if (side === 2 && kind === 4) {
        fieldRows.push(`Type伤害倍率：${state.boot.type_labels?.[subId] || subId} ${numberText(factor * 100)}%`);
      } else {
        others.push(effect.description || effect.name || String(effect.effect_id || ""));
      }
    }
  }
  const statHtml = Object.entries(statLabels).map(([id, label]) => `<span>${label}：${numberText((statFactors[id] || 1) * 100)}%</span>`).join("");
  const fieldHtml = fieldRows.length ? fieldRows.map((text) => `<span>${escapeHtml(text)}</span>`).join("") : "<span>无</span>";
  const otherHtml = others.length ? others.map((text) => `<span>${escapeHtml(text)}</span>`).join("") : "<span>无</span>";
  return `
    <div class="vs-effect-overview">
      <div><b>敌方六维倍率提升总览</b><div class="result-strip">${statHtml}</div></div>
      <div><b>折算到场地倍率</b><div class="result-strip">${fieldHtml}</div></div>
      <div><b>其他效果</b><div class="result-strip">${otherHtml}</div></div>
    </div>
  `;
}

function vsEffectCategory(effect = {}) {
  const side = Number(effect.side || 0);
  const kind = Number(effect.kind || 0);
  if (side === 4 && kind === 1) return "敌方六维";
  if (kind === 10) return "弹种倍率";
  if (kind === 4) return "Type倍率";
  if (kind === 2) return "种族特攻受伤";
  if (kind === 11 || kind === 12) return "属性倍率";
  return "额外说明";
}

function renderVsTagGroups(activeTags) {
  if (!activeTags.length) {
    return `<div class="mode-option-grid">${VS_TAGS.map((tag) => `<label class="inline-check"><input type="checkbox" value="${tag}" checked>${tag}</label>`).join("")}</div>`;
  }
  const groups = {};
  activeTags.forEach((tag, idx) => {
    const category = vsEffectCategory((tag.effects || [])[0] || {});
    if (!groups[category]) groups[category] = [];
    groups[category].push({ tag, idx });
  });
  return Object.entries(groups).map(([category, rows]) => `
    <details class="vs-tag-category" open>
      <summary>${escapeHtml(category)}</summary>
      <div class="vs-tag-list">${rows.map(({ tag, idx }) => {
        const text = (tag.effects || []).map((effect) => effect.description || effect.name || effect.effect_id).join(" / ");
        return `<label class="vs-tag-item"><input class="vs-tag-check" type="checkbox" data-tag-idx="${idx}" checked><b>${escapeHtml(tag.tag || tag.group_id)}</b><span>${escapeHtml(text)}</span></label>`;
      }).join("")}</div>
    </details>
  `).join("");
}

function renderCustomVsEffects() {
  return `
    <details class="vs-custom-effects">
      <summary>自定义复灵效果</summary>
      <div class="vs-custom-row">
        <label>side<input data-role="vs-custom-side" value="2"></label>
        <label>kind<input data-role="vs-custom-kind" value="10"></label>
        <label>subID<input data-role="vs-custom-subid" value="1"></label>
        <label>value<input data-role="vs-custom-value" value="-95"></label>
        <label>说明<input data-role="vs-custom-desc" placeholder="可选"></label>
        <button type="button" class="small secondary" data-add-vs-custom>添加效果</button>
      </div>
      <div class="tag-row">${state.customVsTagEffects.map((effect, idx) => `<button type="button" class="tag" data-remove-vs-custom="${idx}">${escapeHtml(effect.description || `${effect.side}/${effect.kind}/${effect.sub_id}/${effect.value}`)}</button>`).join("") || '<span class="hint">暂无自定义效果</span>'}</div>
    </details>
  `;
}

function renderModeOptions() {
  const activeTags = state.activeVsPreset?.tags || [];
  $("#vsOptions").innerHTML = `
    ${renderVsEffectOverview(activeTags)}
    ${renderVsTagGroups(activeTags)}
    ${renderCustomVsEffects()}
  `;
  $('[data-add-vs-custom]')?.addEventListener("click", () => {
    const side = Number($('[data-role="vs-custom-side"]')?.value || 0);
    const kind = Number($('[data-role="vs-custom-kind"]')?.value || 0);
    const subId = Number($('[data-role="vs-custom-subid"]')?.value || 0);
    const value = Number($('[data-role="vs-custom-value"]')?.value || 0);
    const desc = $('[data-role="vs-custom-desc"]')?.value || "";
    state.customVsTagEffects.push({ effect_id: `custom-${Date.now()}`, side, kind, sub_id: subId, value, name: desc || "自定义效果", description: desc || `自定义：side=${side} kind=${kind} subID=${subId} value=${value}` });
    renderModeOptions();
  });
  $$("[data-remove-vs-custom]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.customVsTagEffects.splice(Number(btn.dataset.removeVsCustom), 1);
      renderModeOptions();
    });
  });
  $("#arenaOptions").innerHTML = `
    <div class="arena-button-options">
      <div><b>Type八选二</b><div id="arenaTypeBoosts" class="button-select" data-max="2">${Object.entries(state.boot.type_labels || {}).map(([value, label]) => `<button type="button" class="small secondary" data-value="${value}">${label}</button>`).join("")}</div></div>
      <div><b>阴阳种类</b><div id="arenaYinyang" class="button-select" data-max="1"><button type="button" class="small secondary active" data-value="yang">阳</button><button type="button" class="small secondary" data-value="yin">阴</button></div></div>
    </div>
  `;
  bindButtonSelects($("#arenaOptions"));
  updateModeUI();
}

function arenaRowsForSheet(sheet) {
  return (state.arenaEnemyData?.rows || []).filter((row) => row.sheet === sheet && row.character_id);
}

function arenaEnemyOptions(sheet) {
  return arenaRowsForSheet(sheet).map((row) => `<option value="${row.arena_enemy_id}">${row.arena_enemy_id} / ${escapeHtml(row.name || row.character_id)}</option>`).join("");
}

function arenaEnemyRowByQuery(query, sheet = "") {
  const raw = String(query || "").trim().toLowerCase();
  if (!raw) return null;
  const rows = sheet ? arenaRowsForSheet(sheet) : (state.arenaEnemyData?.rows || []);
  return rows.find((row) => {
    return String(row.character_id).toLowerCase() === raw || String(row.name || "").toLowerCase().includes(raw);
  }) || null;
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

function arenaEnemyLabel(row) {
  if (!row) return "";
  const option = characterOptionById(row.character_id);
  return `${row.character_id} / ${option?.name || row.name || ""}`;
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
    enemy_skill_effects: section?.enemy_skill_effects || row?.skill_effects || [],
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
                ${[0, 1, 2].map((pos) => `<div class="weekly-enemy-picker" data-pos="${pos}">
                  <div class="weekly-avatar-box"><img data-role="weekly-enemy-avatar" src="/assets/avatars/S0.png" onerror="this.src='/assets/avatars/S0.png'"><small data-role="weekly-preset-status"></small></div>
                  <div class="weekly-enemy-fields">
                    <b>敌方${pos}</b>
                    <label>ID<input data-role="weekly-enemy-query" data-pos="${pos}" list="characterOptions" placeholder="角色ID"></label>
                    <label>世界群<select data-role="weekly-enemy-world" data-pos="${pos}">${buildWorldOptions()}</select></label>
                    <label>角色<select data-role="weekly-enemy-character" data-pos="${pos}"><option value="">选择角色</option></select></label>
                  </div>
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
      const roleSelect = $('[data-role="weekly-enemy-character"]', picker);
      const rows = arenaEnemyRowsForWorld(waveBox?.dataset.sheet || "", select.value);
      roleSelect.innerHTML = `<option value="">选择角色</option>${rows.map((row) => `<option value="${row.character_id}">${escapeHtml(arenaEnemyLabel(row))}</option>`).join("")}`;
    };
    select.addEventListener("change", refresh);
    refresh();
  });
  $$("[data-role='weekly-enemy-character']", root).forEach((select) => {
    select.addEventListener("change", () => {
      const picker = select.closest(".weekly-enemy-picker");
      const input = $('[data-role="weekly-enemy-query"]', picker);
      input.value = select.value || "";
      input.dispatchEvent(new Event("input"));
    });
  });
  $$("[data-role='weekly-enemy-query']", root).forEach((input) => {
    const refresh = () => {
      const waveBox = input.closest("[data-weekly-wave]");
      const row = arenaEnemyRowByQuery(input.value, waveBox?.dataset.sheet || "");
      const picker = input.closest(".weekly-enemy-picker");
      const img = $('[data-role="weekly-enemy-avatar"]', picker);
      const status = $('[data-role="weekly-preset-status"]', picker);
      const select = $('[data-role="weekly-enemy-character"]', picker);
      if (img) {
        const charId = row?.character_id || input.value || "";
        img.src = charId ? avatarUrl(charId) : "/assets/avatars/S0.png";
        img.dataset.charId = charId;
      }
      if (status) status.textContent = input.value && !state.arenaPresets[String(row?.character_id || input.value || "").trim()] ? "无预设" : "";
      if (select && row) select.value = String(row.character_id);
    };
    input.addEventListener("change", refresh);
    input.addEventListener("input", refresh);
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
        const row = arenaEnemyRowByQuery(input.value, waveBox.dataset.sheet || "");
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

function bindButtonSelects(root = document) {
  $$(".button-select", root).forEach((box) => {
    box.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-value]");
      if (!btn) return;
      const max = Number(box.dataset.max || 999);
      if (max === 1) {
        $$("button", box).forEach((item) => item.classList.toggle("active", item === btn));
        return;
      }
      btn.classList.toggle("active");
      const active = $$("button.active", box);
      if (active.length > max) active[0].classList.remove("active");
    });
  });
}

function selectedButtonValues(selector) {
  return $$(`${selector} button.active`).map((btn) => btn.dataset.value).filter(Boolean);
}

function updateModeUI() {
  const mode = $("#calcMode").value;
  $("#waveSwitch").classList.toggle("hidden", mode !== "arena");
  $(".field-buff-card")?.classList.toggle("hidden", mode !== "default");
  $(".vs-extra")?.classList.toggle("hidden", mode !== "vs");
  $(".arena-extra")?.classList.toggle("hidden", mode !== "arena");
  if (mode === "arena") $("#realisticCalc").checked = true;
  if (mode !== "arena") switchWave(1);
  if (mode !== "vs") clearAllVsEnemyState({ clearBuffs: true });
  updateVsManualButtons();
}

function collectFullFieldRows(selector) {
  return $$("input[data-sub-id]", $(selector)).map((input) => [Number(input.dataset.subId), Number(input.value || 100)]).filter((row) => row[0] > 0 && row[1] !== 100);
}

function collectEnemyCards() {
  const rows = {};
  $$(".enemy-slot").forEach((card) => {
    rows[card.dataset.pos] = {
      enabled: $('[data-field="enabled"]', card).checked,
      character_id: $('[data-field="character_id"]', card).value,
      hp: $('[data-field="hp"]', card).value,
      yang_atk: $('[data-field="yang_atk"]', card).value,
      yang_def: $('[data-field="yang_def"]', card).value,
      yin_atk: $('[data-field="yin_atk"]', card).value,
      yin_def: $('[data-field="yin_def"]', card).value,
      speed: $('[data-field="speed"]', card).value,
      barrier_count: $('[data-field="barrier_count"]', card).value,
      quality: collectQuality(card),
      tribe_text: $('[data-field="tribe_text"]', card).value,
      is_break_all: $('[data-field="is_break_all"]', card).dataset.value === "true",
      buffs: collectBuffRows($('[data-role="buffs"]', card)),
      enemy_skill_effects: card._enemySkillEffects || [],
      enemy_extra: card._enemyExtra || null,
      meta: {
        name: $('[data-role="name"]', card).textContent,
        world: $('[data-role="world"]', card).textContent,
        type: $('[data-role="type"]', card).textContent,
      },
    };
  });
  return rows;
}

function saveCurrentEnemyWave() {
  if (!$("#enemySlots")) return;
  state.enemyWaves[state.currentWave] = collectEnemyCards();
}

function applyEnemyWave(wave) {
  const rows = state.enemyWaves[wave] || {};
  $$(".enemy-slot").forEach((card) => {
    const row = rows[card.dataset.pos];
    if (!row) return;
    $('[data-field="enabled"]', card).checked = Boolean(row.enabled);
    card.classList.toggle("collapsed", !Boolean(row.enabled));
    const collapseBtn = $('[data-collapse-card]', card);
    if (collapseBtn) collapseBtn.textContent = card.classList.contains("collapsed") ? "展开" : "折叠";
    $('[data-field="character_id"]', card).value = row.character_id || "";
    $('[data-field="hp"]', card).value = row.hp || 50000000;
    $('[data-field="yang_atk"]', card).value = row.yang_atk || 0;
    $('[data-field="yang_def"]', card).value = row.yang_def || 10000;
    $('[data-field="yin_atk"]', card).value = row.yin_atk || 0;
    $('[data-field="yin_def"]', card).value = row.yin_def || 10000;
    $('[data-field="speed"]', card).value = row.speed || 0;
    $('[data-field="barrier_count"]', card).value = row.barrier_count ?? 9;
    $('[data-field="tribe_text"]', card).value = row.tribe_text || "";
    $('[data-field="is_break_all"]', card).dataset.value = String(Boolean(row.is_break_all));
    $('[data-field="is_break_all"]', card).textContent = `完全破盾：${row.is_break_all ? "是" : "否"}`;
    applyQualityToCard(card, row.quality || []);
    const buffRoot = $('[data-role="buffs"]', card);
    buffRoot.innerHTML = "";
    (row.buffs || []).forEach((buff) => addBuffRow(buffRoot, buff));
    if (row.character_id) {
      card.classList.add("loaded");
      $('[data-role="avatar"]', card).src = avatarUrl(row.character_id);
    }
    $('[data-role="name"]', card).textContent = row.meta?.name || "-";
    $('[data-role="world"]', card).textContent = row.meta?.world || "-";
    $('[data-role="type"]', card).textContent = row.meta?.type || "-";
    card._enemySkillEffects = row.enemy_skill_effects || [];
    card._enemyExtra = row.enemy_extra || null;
    renderEnemyInfoBlock(card, row.enemy_extra || {});
  });
}

function switchWave(wave) {
  saveCurrentEnemyWave();
  state.currentWave = Number(wave);
  $("#waveCount").value = String(state.currentWave);
  applyEnemyWave(state.currentWave);
  $$("#waveSwitch button[data-wave]").forEach((btn) => btn.classList.toggle("active", Number(btn.dataset.wave) === state.currentWave));
  $("#overviewWaveLabel").textContent = `第${state.currentWave}波`;
  $("#enemyWaveLabel").textContent = `第${state.currentWave}波`;
  renderOverview();
}

function getSlotMeta(card) {
  return {
    pos: Number(card.dataset.pos),
    id: $('[data-field="character_id"]', card).value,
    name: $('[data-role="name"]', card).textContent,
    world: $('[data-role="world"]', card).textContent,
    type: $('[data-role="type"]', card).textContent,
    hp: $('[data-field="hp"]', card)?.value || "",
    barrier: $('[data-field="barrier_count"]', card)?.value || "",
    enabled: $('[data-field="enabled"]', card).checked,
  };
}

function overviewCard(card, kind) {
  const meta = getSlotMeta(card);
  const className = meta.enabled ? "overview-card" : "overview-card disabled";
  return `
    <button class="${className}" data-kind="${kind}" data-pos="${meta.pos}">
      <img src="${avatarUrl(meta.id)}" onerror="this.src='/assets/avatars/S0.png'">
      <span><b>${meta.name || "-"}</b><small>${meta.world || "-"} / ${meta.type || "-"}</small><small>HP ${meta.hp || "-"} | 盾 ${meta.barrier || "-"}</small></span>
    </button>
  `;
}

function renderOverview() {
  $("#enemyOverview")?.classList.toggle("arena-current-overview", $("#calcMode")?.value === "arena");
  if ($("#calcMode")?.value === "arena") {
    saveCurrentEnemyWave();
    const rows = state.enemyWaves[state.currentWave] || {};
    $("#enemyOverview").innerHTML = [0, 1, 2].map((pos) => {
      const row = rows[String(pos)] || rows[pos] || {};
      const id = row.character_id || "";
      const name = row.meta?.name || `敌方${pos}`;
      return `<button class="overview-card ${row.enabled ? "" : "disabled"}" data-kind="enemy" data-pos="${pos}">
          <img src="${avatarUrl(id)}" onerror="this.src='/assets/avatars/S0.png'">
          <span><b>${escapeHtml(name)}</b><small>${escapeHtml(row.meta?.world || "-")} / ${escapeHtml(row.meta?.type || "-")}</small><small>HP ${row.hp || "-"} | 盾 ${row.barrier_count ?? "-"}</small></span>
        </button>`;
    }).join("");
  } else {
    $("#enemyOverview").innerHTML = $$(".enemy-slot").map((card) => overviewCard(card, "enemy")).join("");
  }
  $("#allyOverview").innerHTML = $$(".ally-slot").map((card) => overviewCard(card, "ally")).join("");
  $$("[data-wave-jump]").forEach((btn) => btn.addEventListener("click", () => switchWave(btn.dataset.waveJump)));
  $$(".overview-card").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.waveJump) return;
      setActiveSubtab(btn.dataset.kind === "enemy" ? "enemyPane" : "allyPane");
      const target = $(`.${btn.dataset.kind}-slot[data-pos="${btn.dataset.pos}"]`);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });
}

function renderGlobalSkillButtons() {
  const root = $("#globalSkillButtons");
  root.innerHTML = "";
  $$(".ally-slot").forEach((card) => {
    if (!$('[data-field="enabled"]', card).checked) return;
    const pos = Number(card.dataset.pos);
    const name = $('[data-role="name"]', card).textContent || `位置${pos}`;
    const group = document.createElement("div");
    group.className = "skill-group";
    group.innerHTML = `<b>${pos}: ${name}</b>`;
    for (let skill = 0; skill < 3; skill += 1) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "skill-btn secondary";
      btn.textContent = `技能${skill + 1}`;
      btn.addEventListener("click", () => toggleGlobalSkill(pos, skill, btn));
      group.appendChild(btn);
    }
    root.appendChild(group);
  });
  updateGlobalSkillText();
}

function toggleGlobalSkill(pos, skill, btn) {
  const idx = state.globalSkillOrder.findIndex((row) => row[0] === pos && row[1] === skill);
  if (idx >= 0) {
    state.globalSkillOrder.splice(idx, 1);
    btn.classList.remove("active");
  } else {
    state.globalSkillOrder.push([pos, skill]);
    btn.classList.add("active");
  }
  updateGlobalSkillText();
}

function updateGlobalSkillText() {
  $("#customSkillOrder").value = state.globalSkillOrder.map((row) => `${row[0]}:${row[1]}`).join(",");
}

function applyPresetToAllyCard(card, charId) {
  const preset = state.characterPresets[String(charId)];
  if (!preset) return;
  if (preset.equipment_ids) {
    $$(".equipment-row", card).forEach((row) => {
      const value = preset.equipment_ids[row.dataset.slot];
      if (value) $('[data-field="equipment_id"]', row).value = value;
    });
  }
}

function collectEquipmentIds(card) {
  const equipment_ids = {};
  $$(".equipment-row", card).forEach((row) => (equipment_ids[row.dataset.slot] = $('[data-field="equipment_id"]', row).value || 0));
  return equipment_ids;
}

function collectConfig() {
  saveCurrentEnemyWave();
  const weeklyConfig = collectWeeklyArenaConfig();
  const mode = $("#calcMode").value;
  const manualFieldBuffsEnabled = mode === "default";
  const enemy_slots = collectEnemyCards();
  const ally_slots = {};
  $$(".ally-slot").forEach((card) => {
    ally_slots[card.dataset.pos] = {
      enabled: $('[data-field="enabled"]', card).checked,
      character_id: $('[data-field="character_id"]', card).value,
      initial_spirit: $('[data-field="initial_spirit"]', card).value,
      barrier_count: $('[data-field="barrier_count"]', card).value,
      skill_order_text: $('[data-field="skill_order_text"]', card).value,
      shield_open_count: $('[data-field="shield_open_count"]', card).value,
      attack_type: $('[data-field="attack_type"]', card).value,
      spirit_level: $('[data-field="spirit_level"]', card).value,
      target_enemy_pos: $('[data-field="target_enemy_pos"]', card).value,
      buffs: collectBuffRows($('[data-role="buffs"]', card)),
      equipment_ids: collectEquipmentIds(card),
    };
  });
  return {
    mode,
    wave_count: $("#waveCount").value,
    current_wave: state.currentWave,
    enemy_waves: state.enemyWaves,
    weekly_arenas: weeklyConfig.map((arena) => arena.waves),
    weekly_arena_meta: weeklyConfig.map((arena) => ({ types: arena.types, only_boosted: arena.only_boosted, yinyang: Number(arena.arena) % 2 === 1 ? "yang" : "yin" })),
    enemy_slots,
    ally_slots,
    character_presets: state.characterPresets,
    process: {
      use_custom_skill_order: $("#useCustomSkillOrder").checked,
      custom_skill_order_text: $("#customSkillOrder").value,
      field_buffs: {
        bullet_type_modifiers: manualFieldBuffsEnabled ? collectFullFieldRows("#fieldBulletRows") : [],
        element_modifiers: manualFieldBuffsEnabled ? collectFullFieldRows("#fieldElementRows") : [],
        type_resist_modifiers: manualFieldBuffsEnabled ? collectFullFieldRows("#fieldTypeRows") : [],
        vs_tags: $$("#vsOptions input[type='checkbox']:checked").map((input) => input.value),
        vs_tag_effects: $$("#vsOptions .vs-tag-check:checked").flatMap((input) => {
          const tag = state.activeVsPreset?.tags?.[Number(input.dataset.tagIdx)];
          return tag?.effects || [];
        }).concat(state.customVsTagEffects || []),
        arena_type_boosts: selectedButtonValues("#arenaTypeBoosts").slice(0, 2),
        arena_yinyang: selectedButtonValues("#arenaYinyang")[0] || "yang",
        realistic: $("#realisticCalc").checked,
      },
    },
  };
}

function interpolateVsStats(enemy, level) {
  const lv60 = enemy?.lv60_stats || {};
  const lv100 = enemy?.lv100_stats || {};
  const n = Math.max(60, Math.min(100, Number(level || 100)));
  const ratio = (n - 60) / 40;
  const stats = {};
  for (const key of STAT_KEYS) {
    const a = Number(lv60[key] || 0);
    const b = Number(lv100[key] || 0);
    stats[key] = Math.round(a + (b - a) * ratio);
  }
  return stats;
}

async function applyVsPreset(preset) {
  const level = Math.max(60, Math.min(100, Number($("#vsLevel")?.value || 100)));
  state.activeVsPreset = preset;
  state.activeVsTagEffects = (preset.tags || []).flatMap((tag) => tag.effects || []);
  for (const item of preset.enemies || []) {
    const card = $(`.enemy-slot[data-pos="${item.pos}"]`);
    if (!card) continue;
    const enabled = !item.empty && item.enemy;
    $('[data-field="enabled"]', card).checked = enabled;
    if (!enabled) {
      card.classList.remove("loaded");
      card.classList.add("collapsed");
      const collapseBtn = $('[data-collapse-card]', card);
      if (collapseBtn) collapseBtn.textContent = "展开";
      continue;
    }
    card.classList.remove("collapsed");
    const collapseBtn = $('[data-collapse-card]', card);
    if (collapseBtn) collapseBtn.textContent = "折叠";
    const phases = item.phases && item.phases.length ? item.phases : [item.enemy];
    const enemy = phases[0] || item.enemy;
    const stats = interpolateVsStats(enemy, level);
    const meta = await loadCharacterMeta(enemy.enemy_id).catch(() => null);
    fillMeta(card, meta || { id: enemy.enemy_id, name: enemy.display_name || enemy.name, world_group: "-", type_label: "-" });
    applyStatsToCard(card, stats);
    $('[data-field="barrier_count"]', card).value = enemy.barrier_count ?? 9;
    $('[data-field="tribe_text"]', card).value = enemy.tribe_text_ids || (enemy.tribe_ids || []).join(",") || enemy.tribes_text || "";
    applyQualityToCard(card, enemy.quality || []);
    card._enemySkillEffects = enemy.skill_buffs || [];
    card._enemyExtra = enemy;
    card._enemyPhases = phases;
    card._enemyPhaseIndex = 0;
    renderEnemyInfoBlock(card, enemy);
    const phaseRoot = $('[data-role="phase_buttons"]', card);
    phaseRoot.innerHTML = phases.map((phase, idx) => `<button type="button" class="small secondary ${idx === 0 ? "active" : ""}" data-phase-idx="${idx}">血条${idx + 1}</button>`).join("");
    $$("[data-phase-idx]", phaseRoot).forEach((btn) => {
      btn.addEventListener("click", async () => {
        $$("[data-phase-idx]", phaseRoot).forEach((item) => item.classList.toggle("active", item === btn));
        const phase = phases[Number(btn.dataset.phaseIdx)] || enemy;
        card._enemyPhaseIndex = Number(btn.dataset.phaseIdx) || 0;
        const phaseStats = interpolateVsStats(phase, Number($("#vsLevel")?.value || 100));
        const phaseMeta = await loadCharacterMeta(phase.enemy_id).catch(() => null);
        fillMeta(card, phaseMeta || { id: phase.enemy_id, name: phase.display_name || phase.name, world_group: "-", type_label: "-" });
        applyStatsToCard(card, phaseStats);
        $('[data-field="barrier_count"]', card).value = phase.barrier_count ?? 9;
        $('[data-field="tribe_text"]', card).value = phase.tribe_text_ids || (phase.tribe_ids || []).join(",") || phase.tribes_text || "";
        applyQualityToCard(card, phase.quality || []);
        card._enemySkillEffects = phase.skill_buffs || [];
        card._enemyExtra = phase;
        renderEnemyInfoBlock(card, phase);
        saveCurrentEnemyWave();
        renderOverview();
      });
    });
    const buffRoot = $('[data-role="buffs"]', card);
    buffRoot.innerHTML = "";
    card.classList.add("loaded");
  }
  $("#calcMode").value = "vs";
  updateModeUI();
  saveCurrentEnemyWave();
  renderOverview();
  renderModeOptions();
  setActiveSubtab("enemyPane");
}

function renderSummary(result) {
  const view = state.resultView || "overview";
  const allyPos = view.startsWith("ally") ? Number(view.replace("ally", "")) : null;
  const segSource = allyPos === null ? result.seg_damage : result.ally_seg_damage?.[allyPos];
  const totalValue = allyPos === null ? result.total_damage : result.ally_totals?.[allyPos] || 0;
  const cards = [
    [allyPos === null ? "总伤害" : `角色${allyPos}伤害`, totalValue],
    ["敌方0", result.enemy_totals?.["0"] ?? 0],
    ["敌方1", result.enemy_totals?.["1"] ?? 0],
    ["敌方2", result.enemy_totals?.["2"] ?? 0],
    ["阳伤害", result.yang_damage_total],
    ["阴伤害", result.yin_damage_total],
  ];
  $("#summaryCards").innerHTML = cards.map(([label, value]) => `<div class="summary-card">${label}<strong>${numberText(value)}</strong></div>`).join("");
  if (result.realistic) {
    $("#summaryCards").insertAdjacentHTML("beforeend", `
      <details class="summary-card summary-collapse">
        <summary>命中/暴击情况</summary>
        <strong>${result.hit_summary || "见明细"}</strong>
        <strong>${result.crit_summary || "见明细"}</strong>
      </details>
    `);
  }
  $("#segmentResult").innerHTML = `<h3>六段伤害</h3><div class="result-strip">${[0, 1, 2, 3, 4, 5].map((i) => `<span>第${i + 1}段 <b>${numberText(segSource?.[`seg${i}`] || 0)}</b></span>`).join("")}</div>`;
  $("#enemyDamageResult").innerHTML = `<h3>敌方受到伤害</h3><div class="result-strip">${[0, 1, 2].map((i) => `<span>敌方${i} <b>${numberText(result.enemy_totals?.[String(i)] || 0)}</b></span>`).join("")}</div>`;
}

function renderDetails(result) {
  const details = (result.details || []).filter((row) => {
    if (!state.resultView || state.resultView === "overview") return true;
    return Number(row.attacker_pos) === Number(state.resultView.replace("ally", ""));
  });
  const headers = ["段落", "段落名", "属性", "弹种", "阴阳", "伤害", "命中", "暴击", "我方基础攻击", "敌方基础防御", "特攻", "弱点"];
  const value = (row, h) => {
    if (h === "段落") return `第${Number(row.seg || 0) + 1}段`;
    if (h === "段落名") return row.shot_name || row.name || "-";
    if (h === "属性") return state.boot.element_labels?.[row.element] || row.element || "-";
    if (h === "弹种") return state.boot.bullet_labels?.[row.bullet_type] || row.bullet_type || "-";
    if (h === "阴阳") return Number(row.yinyang) === 1 ? "阳" : "阴";
    if (h === "伤害") return numberText(row.damage_int);
    if (h === "命中") return row.realistic_hit === false ? "miss" : (row.realistic_hit === true ? "hit" : "");
    if (h === "暴击") return row.realistic_crit === true ? "crit" : (row.realistic_crit === false ? "normal" : "");
    if (h === "我方基础攻击") return numberText(row.base_atk);
    if (h === "敌方基础防御") return numberText(row.base_def);
    if (h === "特攻") return row.hit?.crit_mode === "killer" || row.killer ? "是" : "";
    if (h === "弱点") return row.element_info?.quality_value === 0 || row.element_info?.element_mode === "advantage" ? "是" : "";
    return "";
  };
  const table = (title, rows) => `<div class="result-table-wrap"><table><thead><tr><th colspan="${headers.length}">${title}</th></tr><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${headers.map((h) => `<td>${value(row, h)}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="${headers.length}">无数据</td></tr>`}</tbody></table></div>`;
  $("#detailTables").innerHTML = [table("总计", details), ...[0, 1, 2].map((pos) => table(`敌方${pos}`, details.filter((row) => Number(row.enemy_pos) === pos)))].join("");
}

async function calculate() {
  const result = await api("/api/calculate", { method: "POST", body: JSON.stringify(collectConfig()) });
  state.lastResult = result;
  renderSummary(result);
  renderDetails(result);
  setActiveSubtab("resultPane");
}

async function batchSummary(policy) {
  const data = await api("/api/batch-summary", { method: "POST", body: JSON.stringify({ ...collectConfig(), template_ally_pos: 0, equipment_policy: policy }) });
  alert(`已导出 ${data.row_count} 行：\n${data.csv_path}`);
}

async function solveWeeklyArena(targetArena = null) {
  const payload = collectConfig();
  payload.mode = "arena";
  payload.process.field_buffs.realistic = true;
  if (targetArena) {
    payload.weekly_arenas = payload.weekly_arenas.map((arena, idx) => idx + 1 === targetArena ? arena : {});
    payload.weekly_arena_meta = payload.weekly_arena_meta.map((meta, idx) => idx + 1 === targetArena ? meta : {});
  }
  const data = await api("/api/weekly-arena-solve", { method: "POST", body: JSON.stringify(payload) });
  const recommended = (data.recommended || []).filter((row) => !targetArena || Number(row.arena) === Number(targetArena));
  const recHtml = recommended.map((row) => {
    if (row.status) return `<tr><td>${row.arena}</td><td>${row.wave}</td><td colspan="9">${escapeHtml(row.status)}</td></tr>`;
    return `<tr><td>${row.arena}</td><td>${row.wave}</td><td>${row.character_id}</td><td>${escapeHtml(row.name)}</td><td>${escapeHtml(row.world_group || "-")}</td><td>${escapeHtml(row.type_label)}${row.type_boosted ? " / Type加成" : ""}</td><td>${numberText(row.damage)}</td><td>${numberText(row.enemy_hp_total)}</td><td>${numberText(row.overflow)}</td><td>阳${numberText(row.yang_ratio)}% / 阴${numberText(row.yin_ratio)}%</td></tr>`;
  }).join("");
  const visibleArenas = (data.arenas || []).filter((arena) => !targetArena || Number(arena.arena) === Number(targetArena));
  const arenaHtml = visibleArenas.map((arena) => `
    <details class="card">
      <summary>擂台 ${arena.arena}</summary>
      ${(arena.waves || []).map((wave) => `
        <h4>第 ${wave.wave} 波 HP ${numberText(wave.enemy_hp_total)}</h4>
        <div class="weekly-candidate-row">
          <img src="${avatarUrl((wave.candidates || [])[0]?.character_id)}" onerror="this.src='/assets/avatars/S0.png'">
          <select>${(wave.candidates || []).slice(0, 80).map((row) => `<option value="${row.character_id}">${row.character_id} / ${escapeHtml(row.name)} / ${escapeHtml(row.world_group || "-")} / ${row.type_boosted ? "Type加成 / " : ""}溢出 ${numberText(row.overflow)} / 伤害 ${numberText(row.damage)} / 阳${numberText(row.yang_ratio)}%-阴${numberText(row.yin_ratio)}%</option>`).join("") || '<option>无溢出>-1000候选角色</option>'}</select>
        </div>
      `).join("")}
    </details>
  `).join("");
  $("#weeklyArenaResult").innerHTML = `
    ${data.message ? `<p class="hint">${escapeHtml(data.message)}</p>` : ""}
    <div class="table-wrap"><table><thead><tr><th>擂台</th><th>波次</th><th>角色ID</th><th>名称</th><th>世界群</th><th>Type</th><th>伤害</th><th>敌方HP</th><th>溢出</th><th>阴阳占比</th></tr></thead><tbody>${recHtml || '<tr><td colspan="10">暂无推荐</td></tr>'}</tbody></table></div>
    ${arenaHtml}
  `;
  $$("#weeklyArenaResult .weekly-candidate-row select").forEach((select) => {
    select.addEventListener("change", () => {
      const img = $("img", select.closest(".weekly-candidate-row"));
      if (img) img.src = avatarUrl(select.value);
    });
  });
}

const VS_MANUAL_ATTACKS = [
  ["1c", "扩散"],
  ["2c", "集中"],
  ["1", "符卡1A"],
  ["2", "符卡2A"],
  ["1", "符卡1B"],
  ["2", "符卡2B"],
  ["5", "终符"],
];

function cycleManualNumber(card, field, max, viewSelector) {
  const input = $(`[data-field="${field}"]`, card);
  if (!input) return 0;
  const next = (Number(input.value || 0) + 1) % (max + 1);
  input.value = String(next);
  const view = $(viewSelector);
  if (view) view.textContent = String(next);
  state.vsManualPayload = collectConfig();
  return next;
}

function setManualAttack(card, attackType, button) {
  const input = $('[data-field="attack_type"]', card);
  if (input) input.value = attackType;
  $$("[data-manual-attack]", button.closest(".manual-attack-row")).forEach((item) => item.classList.toggle("active", item === button));
  state.vsManualPayload = collectConfig();
}

async function loadCharacterRawData(charId) {
  const data = await api(`/api/characters/${encodeURIComponent(charId)}`);
  try {
    return JSON.parse(data.raw_json_text || "{}");
  } catch {
    return {};
  }
}

function targetCardsForSkill(casterCard, targetType) {
  const target = Number(targetType || 1);
  if (target === 1) return [casterCard];
  if (target === 2) return $$(".ally-slot").filter((card) => $('[data-field="enabled"]', card)?.checked);
  if (target === 3) {
    const pos = $('[data-field="target_enemy_pos"]', casterCard)?.value || "0";
    return [$(`.enemy-slot[data-pos="${pos}"]`)].filter(Boolean);
  }
  if (target === 4) return $$(".enemy-slot").filter((card) => $('[data-field="enabled"]', card)?.checked);
  return [casterCard];
}

function applyManualSkillEffect(casterCard, effect = []) {
  if (!Array.isArray(effect) || effect.length < 5) return;
  const [buffId, subId, targetType, duration, value] = effect.map((v) => Number(v || 0));
  const targets = targetCardsForSkill(casterCard, targetType);
  if (buffId === 5) {
    const delta = Number(value || 0) / 20.0;
    targets.filter((card) => card?.classList?.contains("ally-slot")).forEach((card) => {
      const input = $('[data-field="initial_spirit"]', card);
      if (input) input.value = numberText(Number(input.value || 0) + delta);
    });
    return;
  }
  targets.forEach((targetCard) => {
    const root = $('[data-role="buffs"]', targetCard);
    if (root) addBuffRow(root, [buffId, subId, duration, value]);
  });
}

async function useManualSkill(card, skill, button) {
  const pos = card.dataset.pos;
  const key = `${pos}:${skill}`;
  if (state.vsManualSkillUsed[key]) return;
  const charId = $('[data-field="character_id"]', card)?.value || "";
  const raw = await loadCharacterRawData(charId);
  const skillData = (raw.skills || [])[skill] || null;
  if (!skillData) {
    alert("未找到该角色技能数据");
    return;
  }
  state.vsManualSkillUsed[key] = true;
  button.disabled = true;
  button.classList.add("cooldown");
  ["a", "b", "c"].forEach((keyName) => applyManualSkillEffect(card, skillData[keyName]));
  const view = $('[data-role="skill_order_view"]', card);
  if (view) {
    const used = Object.keys(state.vsManualSkillUsed)
      .filter((item) => item.startsWith(`${pos}:`))
      .map((item) => `技能${Number(item.split(":")[1]) + 1}`);
    view.textContent = used.join(" → ") || "不开技能";
  }
  state.vsManualPayload = collectConfig();
}

function renderVsManualControls() {
  const root = $("#vsManualControls");
  if (!root) return;
  const rows = $$(".ally-slot").filter((card) => $('[data-field="enabled"]', card)?.checked);
  root.innerHTML = rows.map((card) => {
    const pos = card.dataset.pos;
    const name = $('[data-role="name"]', card)?.textContent || `我方${pos}`;
    const activeAttack = $('[data-field="attack_type"]', card)?.value || "5";
    return `
      <div class="manual-control-card" data-manual-control-pos="${pos}">
        <div class="manual-control-head"><b>我方${pos} ${escapeHtml(name)}</b><span>${renderBarrierIcons($('[data-field="barrier_count"]', card)?.value || 5)}</span></div>
        <div class="manual-control-row">
          <button type="button" class="small secondary" data-manual-shield="${pos}">开盾 <span data-manual-shield-view="${pos}">${$('[data-field="shield_open_count"]', card)?.value || 0}</span></button>
          <button type="button" class="small secondary" data-manual-spirit="${pos}">开P <span data-manual-spirit-view="${pos}">${$('[data-field="spirit_level"]', card)?.value || 0}</span></button>
        </div>
        <div class="manual-attack-row">${VS_MANUAL_ATTACKS.map(([value, label], idx) => {
          const active = activeAttack === value && (value !== "1" || idx === 2) && (value !== "2" || idx === 3);
          return `<button type="button" class="small secondary ${active ? "active" : ""}" data-manual-attack="${value}">${label}</button>`;
        }).join("")}</div>
        <div class="manual-control-row">${[0, 1, 2].map((skill) => {
          const key = `${pos}:${skill}`;
          return `<button type="button" class="small secondary ${state.vsManualSkillUsed[key] ? "cooldown" : ""}" ${state.vsManualSkillUsed[key] ? "disabled" : ""} data-manual-skill="${skill}">技能${skill + 1}</button>`;
        }).join("")}</div>
      </div>
    `;
  }).join("") || '<div class="card hint">无启用我方角色。</div>';
  $$("[data-manual-control-pos]", root).forEach((box) => {
    const card = $(`.ally-slot[data-pos="${box.dataset.manualControlPos}"]`);
    $('[data-manual-shield]', box)?.addEventListener("click", () => cycleManualNumber(card, "shield_open_count", 3, `[data-manual-shield-view="${box.dataset.manualControlPos}"]`));
    $('[data-manual-spirit]', box)?.addEventListener("click", () => cycleManualNumber(card, "spirit_level", 3, `[data-manual-spirit-view="${box.dataset.manualControlPos}"]`));
    $$("[data-manual-attack]", box).forEach((btn) => btn.addEventListener("click", () => setManualAttack(card, btn.dataset.manualAttack, btn)));
    $$("[data-manual-skill]", box).forEach((btn) => btn.addEventListener("click", () => useManualSkill(card, Number(btn.dataset.manualSkill), btn).catch((err) => alert(err.message))));
  });
}

function syncManualEnemyHpBeforeSolve(payload) {
  const states = state.vsManualState?.enemy_states || [];
  states.forEach((row) => {
    const remaining = Number(row.remaining_hp ?? row.hp ?? 0);
    const slot = payload.enemy_slots?.[row.pos] || payload.enemy_slots?.[String(row.pos)];
    if (!slot) return;
    slot.hp = Math.max(0, remaining);
    if (remaining <= 0) slot.enabled = false;
  });
}

function importVsManualConfig() {
  const payload = collectConfig();
  payload.mode = "vs";
  Object.values(payload.ally_slots || {}).forEach((slot) => {
    if (slot) slot.skill_order_text = "";
  });
  $$(".ally-slot [data-field='skill_order_text']").forEach((input) => (input.value = ""));
  $$(".ally-slot [data-role='skill_order_view']").forEach((view) => (view.textContent = "不开技能"));
  state.vsManualPayload = payload;
  state.vsManualState = { turn: 1, enemy_states: [] };
  state.vsManualPhase = "ready";
  state.vsManualSkillUsed = {};
  renderVsManualControls();
  updateVsManualButtons();
  $("#vsManualResult").innerHTML = '<div class="card"><b>已导入当前敌我参数</b><p class="hint">点击“计算本回合”查看本回合伤害和敌我状态。</p></div>';
}

function updateVsManualButtons() {
  const calcBtn = $("#vsManualCalcBtn");
  const nextBtn = $("#vsManualNextBtn");
  if (!calcBtn || !nextBtn) return;
  const phase = state.vsManualPhase || "idle";
  calcBtn.disabled = phase === "calculated";
  nextBtn.disabled = phase !== "calculated";
}

function renderBarrierIcons(count, abnormal = []) {
  const n = Math.max(0, Math.min(10, Number(count || 0)));
  const abnormalList = Array.isArray(abnormal) ? abnormal : [];
  return `<span class="barrier-icons">${Array.from({ length: n }, (_, idx) => `<img src="${barrierIconUrl(abnormalList[idx] || 0)}" alt="盾">`).join("") || "-"}</span>`;
}

function manualBuffText(row) {
  const normal = (row.buffs_text || []).join(" / ");
  const skills = (row.enemy_skill_effects_text || []).join(" / ");
  return [normal, skills].filter(Boolean).join(" / ") || "-";
}

function renderVsManualResult(data) {
  updateVsManualButtons();
  const order = (data.attack_order || []).map((row) => `位置${row.pos}:${escapeHtml(row.name || row.character_id || "-")}`).join(" → ") || "-";
  const allies = (data.ally_states || []).map((row) => `
    <button type="button" class="manual-unit-card" data-manual-kind="ally" data-manual-pos="${row.pos}" data-buffs="${escapeHtml(manualBuffText(row))}">
      <img src="${avatarUrl(row.character_id)}" onerror="this.src='/assets/avatars/S0.png'">
      <span><b>我方${row.pos}</b><small>${escapeHtml(row.name || row.character_id || "-")}</small><small>伤害 ${numberText(row.damage)}</small><small>${renderBarrierIcons(row.barrier_count)}</small></span>
    </button>
  `).join("");
  const enemyCards = (data.enemy_states || []).map((row) => `
    <button type="button" class="manual-unit-card" data-manual-kind="enemy" data-manual-pos="${row.pos}" data-buffs="${escapeHtml(manualBuffText(row))}">
      <img src="${avatarUrl(row.character_id)}" onerror="this.src='/assets/avatars/S0.png'">
      <span><b>敌方${row.pos}</b><small>${escapeHtml(row.name || row.character_id || "-")}</small><small>HP ${numberText(row.remaining_hp)} / ${numberText(row.hp)}</small><small>${renderBarrierIcons(row.barrier_count)}</small></span>
    </button>
  `).join("");
  const enemies = (data.enemy_states || []).map((row) => `
    <tr>
      <td>敌方${row.pos}</td><td>${escapeHtml(row.name || row.character_id || "-")}</td><td>${numberText(row.hp)}</td><td>${numberText(row.damage)}</td><td>${numberText(row.remaining_hp)}</td><td>${renderBarrierIcons(row.barrier_count)}</td>
    </tr>
  `).join("");
  const steps = (data.attack_steps || []).map((row) => `
    <tr><td>${escapeHtml(row.attacker_name || `我方${row.attacker_pos}`)}</td><td>敌方${row.enemy_pos}</td><td>${numberText(row.damage)}</td><td>${numberText(row.remaining_hp)}</td></tr>
  `).join("");
  const buffs = [...(data.ally_states || []), ...(data.enemy_states || [])].map((row) => `<p><b>${row.side === "ally" ? "我方" : "敌方"}${row.pos}</b> ${escapeHtml(manualBuffText(row))}</p>`).join("");
  $("#vsManualResult").innerHTML = `
    <div class="summary-grid">
      <div class="summary-card">回合<strong>${numberText(data.turn || 1)}</strong></div>
      <div class="summary-card">总伤害<strong>${numberText(data.total_damage)}</strong></div>
      <div class="summary-card">复灵ID<strong>${escapeHtml(state.activeVsPreset?.vs_id || "-")}</strong></div>
    </div>
    <div class="manual-board">
      <div class="manual-side"><h3>敌方</h3>${enemyCards || '<p class="hint">无启用敌方</p>'}</div>
      <div class="manual-focus"><b>攻击顺序</b><p>${order}</p><div data-role="manual-buff-focus" class="compact-info-line">点击任意角色查看 Buff。</div></div>
      <div class="manual-side"><h3>我方</h3>${allies || '<p class="hint">无启用我方</p>'}</div>
    </div>
    <div class="table-wrap"><table><thead><tr><th>位置</th><th>角色名称</th><th>HP</th><th>受到伤害</th><th>剩余HP</th><th>盾</th></tr></thead><tbody>${enemies || '<tr><td colspan="6">无启用敌方</td></tr>'}</tbody></table></div>
    <div class="table-wrap"><table><thead><tr><th>我方角色</th><th>目标</th><th>本次伤害</th><th>攻击后敌方剩余HP</th></tr></thead><tbody>${steps || '<tr><td colspan="4">暂无攻击步骤</td></tr>'}</tbody></table></div>
    <details class="card"><summary>敌方 Buff/技能摘要</summary>${buffs || '<p class="hint">无</p>'}</details>
  `;
  $$("#vsManualResult [data-manual-kind]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const focus = $('[data-role="manual-buff-focus"]', $("#vsManualResult"));
      if (focus) focus.textContent = `${btn.dataset.manualKind === "ally" ? "我方" : "敌方"}${btn.dataset.manualPos}: ${btn.dataset.buffs || "-"}`;
    });
  });
}

async function solveVsManual() {
  if (!state.vsManualPayload) importVsManualConfig();
  if (state.vsManualPhase === "calculated") return;
  state.vsManualPayload = { ...collectConfig(), mode: "vs" };
  syncManualEnemyHpBeforeSolve(state.vsManualPayload);
  const data = await api("/api/vs-manual-solve", {
    method: "POST",
    body: JSON.stringify({ ...(state.vsManualPayload || collectConfig()), manual_state: state.vsManualState || {} }),
  });
  state.vsManualState = data.state || null;
  state.vsManualPhase = "calculated";
  renderVsManualResult(data);
}

function advanceVsManualTurn() {
  if (!state.vsManualState) {
    $("#vsManualResult").innerHTML = '<div class="card hint">请先计算本回合。</div>';
    return;
  }
  const next = { ...state.vsManualState, turn: Number(state.vsManualState.turn || 1) + 1 };
  next.enemy_states = (next.enemy_states || []).map((row) => {
    const remaining = Math.max(0, Number(row.remaining_hp ?? row.hp ?? 0));
    const card = $(`.enemy-slot[data-pos="${row.pos}"]`);
    const currentPhase = Number(card?._enemyPhaseIndex || 0);
    const phases = card?._enemyPhases || [];
    if (remaining <= 0 && phases.length > currentPhase + 1) {
      const nextBtn = $(`[data-phase-idx="${currentPhase + 1}"]`, card);
      if (nextBtn) nextBtn.click();
      const nextPhase = phases[currentPhase + 1] || {};
      const stats = interpolateVsStats(nextPhase, Number($("#vsLevel")?.value || 100));
      const hpInput = $('[data-field="hp"]', card);
      if (hpInput) hpInput.value = Number(stats.hp || row.hp || 0);
      return { ...row, hp: Number(stats.hp || row.hp || 0), damage: 0, remaining_hp: Number(stats.hp || row.hp || 0), phase_advanced: true };
    }
    if (card) {
      const hpInput = $('[data-field="hp"]', card);
      if (hpInput) hpInput.value = remaining;
      if (remaining <= 0) {
        const enabled = $('[data-field="enabled"]', card);
        if (enabled) enabled.checked = false;
        card.classList.add("collapsed");
      }
    }
    return { ...row, hp: remaining, damage: 0, remaining_hp: remaining };
  });
  state.vsManualState = next;
  state.vsManualPhase = "ready";
  renderVsManualResult({ ...next, total_damage: 0, yang_damage_total: 0, yin_damage_total: 0 });
}

function buildTable(table, headers, rows, afterRender) {
  table.innerHTML = `<thead><tr>${headers.map((h) => `<th data-key="${h.key}">${h.label}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${headers.map((h) => `<td>${h.render ? h.render(row) : row[h.key] ?? ""}</td>`).join("")}</tr>`).join("")}</tbody>`;
  $$("th", table).forEach((th) => th.addEventListener("click", () => {
    const key = th.dataset.key;
    const next = state.sort[key] === "asc" ? "desc" : "asc";
    state.sort = { [key]: next };
    const sorted = [...rows].sort((a, b) => {
      const numeric = !Number.isNaN(Number(a[key])) && !Number.isNaN(Number(b[key]));
      const cmp = numeric ? Number(a[key]) - Number(b[key]) : String(a[key] ?? "").localeCompare(String(b[key] ?? ""), "zh-Hans-CN");
      return next === "asc" ? cmp : -cmp;
    });
    buildTable(table, headers, sorted, afterRender);
  }));
  if (afterRender) afterRender(table);
}

async function searchCharacters() {
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
  });
  const rows = await api(`/api/characters?${params}`);
  state.lastCharacterRows = rows;
  const count = $("#characterResultCount");
  if (count) count.textContent = `结果：${rows.length} 个角色`;
  renderCharacterTable(rows);
}

function renderCharacterTable(rows) {
  const headers = [
    { key: "character_id", label: "ID" },
    { key: "name", label: "名称", render: (row) => `<span class="linkish" data-char-id="${row.character_id}">${row.name}</span>` },
    { key: "world_group", label: "世界群" },
    { key: "type_label", label: "Type" },
    { key: "yang_atk", label: "阳攻" },
    { key: "yang_def", label: "阳防" },
    { key: "yin_atk", label: "阴攻" },
    { key: "yin_def", label: "阴防" },
    { key: "speed", label: "速度" },
    { key: "attack5_element_sequence", label: "终符属性", render: (row) => `<span class="element-icons">${(row.attack5_elements || []).map((id) => `<img src="${attributeIconUrl(id)}" title="${state.boot.element_labels?.[id] || id}">`).join("") || row.attack5_element_sequence || "-"}</span>` },
  ];
  if (!state.hideCharacterImages) {
    headers.splice(1, 0, { key: "avatar", label: "头像", render: (row) => `<img class="table-avatar table-avatar-link" data-char-id="${row.character_id}" src="${avatarUrl(row.character_id)}" onerror="this.src='/assets/avatars/S0.png'">` });
  }
  buildTable($("#characterTable"), headers, rows, (table) => {
    $$(".linkish, .table-avatar-link", table).forEach((link) => link.addEventListener("click", () => {
      setQueryTab("character-detail");
      loadCharacterDetail(link.dataset.charId);
    }));
  });
}

async function searchEquipment() {
  const buffParams = {};
  $$(".equipment-buff-filter").forEach((box, idx) => {
    const n = idx + 1;
    buffParams[`buff_id_${n}`] = $('[data-field="buff_id"]', box).value;
    buffParams[`sub_ids_${n}`] = $('[data-field="sub_ids"]', box).value;
    buffParams[`value_${n}`] = $('[data-field="value"]', box).value;
    buffParams[`target_${n}`] = $('[data-field="target"]', box).value;
    buffParams[`type_conditions_${n}`] = $('[data-field="type_conditions"]', box).value;
  });
  const params = new URLSearchParams({
    q: $("#eqName")?.value || "",
    stars: selectedFilterValues("eqStars").join(","),
    style_code: selectedFilterValues("eqStyle").join(","),
    stats: $("#eqStats").value,
    buff_logic: $("#eqBuffLogic").value,
    ...buffParams,
  });
  const rows = await api(`/api/equipment?${params}`);
  state.lastEquipmentRows = rows;
  const count = $("#equipmentResultCount");
  if (count) count.textContent = `结果：${rows.length} 张绘卷`;
  renderEquipmentTable(rows);
}

function renderEquipmentTable(rows) {
  const headers = [
    { key: "equipment_id", label: "ID" },
    { key: "name", label: "名称" },
    { key: "stars", label: "星级" },
    { key: "style_label", label: "种类" },
    { key: "stats_text", label: "属性", render: (row) => String(row.stats_text || "").replaceAll("\n", "<br>") },
    { key: "buff_1_text", label: "buff1" },
    { key: "buff_2_text", label: "buff2" },
    { key: "buff_3_text", label: "buff3" },
  ];
  if (!state.hideEquipmentImages) {
    headers.splice(1, 0, { key: "image", label: "图像", render: (row) => `<img class="table-card-icon" src="${row.image_url}" onerror="this.style.display='none'">` });
  }
  buildTable($("#equipmentTable"), headers, rows);
}

function filterCharacterGalleryRows(rows, presetMap, options = {}) {
  if (!options.useRoleFilters) return rows;
  const filters = state.roleGalleryFilters || {};
  return rows.filter((row) => {
    const preset = presetMap[String(row.id)] || null;
    if (filters.preset === "missing" && preset) return false;
    if (filters.preset === "exists" && !preset) return false;
    if (filters.rebirth2 && !preset?.rebirth2) return false;
    if (filters.unowned && !preset?.unowned) return false;
    return true;
  });
}

function renderCharacterGallery(container, presetMap, onPick, withOwnedFlags = true, options = {}) {
  const rows = filterCharacterGalleryRows(state.boot.character_options || [], presetMap, options);
  container.innerHTML = rows.map((row) => {
    const preset = presetMap[String(row.id)] || {};
    const status = presetMap[String(row.id)] ? "已有预设" : "暂无预设";
    const flags = withOwnedFlags ? `${preset.rebirth2 ? " / 二转" : ""}${preset.unowned ? " / 未拥有" : ""}` : "";
    return `
      <button type="button" class="character-gallery-card" data-char-id="${row.id}">
        <img src="${avatarUrl(row.id)}" onerror="this.src='/assets/avatars/S0.png'">
        <span>${escapeHtml(row.name)}</span>
        <small>${escapeHtml(row.world_group || "-")} / ${status}${flags}</small>
      </button>
    `;
  }).join("");
  $$(".character-gallery-card", container).forEach((btn) => btn.addEventListener("click", () => onPick(btn.dataset.charId)));
}

function renderQualitySummary(data) {
  const code = String(data.quality || "");
  const labels = (state.boot.quality_labels || []).slice(0, 8);
  if (!code && !data.quality_name) return "";
  const icons = labels.map((label, idx) => {
    const stateValue = Number(code[idx] || 1);
    return `<img src="${temperamentIconUrl(label, stateValue)}" title="${label}" alt="${label}">`;
  }).join("");
  return `<div class="quality-summary"><b>气质：${escapeHtml(data.quality_name || "-")}</b><span>${icons}</span></div>`;
}

async function loadCharacterDetail(query) {
  const meta = await api(`/api/character-resolve?q=${encodeURIComponent(query || $("#detailCharacterQuery").value)}`);
  if (!meta) {
    alert("未找到角色");
    return;
  }
  const data = await api(`/api/characters/${encodeURIComponent(meta.id)}`);
  $("#detailCharacterQuery").value = data.char_id;
  const sections = [...(data.attack_sections || [])].sort((a, b) => ATTACK_DETAIL_ORDER.indexOf(a.title) - ATTACK_DETAIL_ORDER.indexOf(b.title));
  $("#characterDetail").innerHTML = `
    <div class="card">
      <div class="detail-header">
        <img class="avatar-large" src="${avatarUrl(data.char_id)}" onerror="this.src='/assets/avatars/S0.png'">
        <div>
          <h2>${data.name} <small>ID ${data.char_id}</small></h2>
          <p>${data.subname || ""}</p>
          <div class="kv-grid detail-fixed">
            <div>世界群：${data.world_group}</div><div>Type：${data.type_label}</div><div>转生：${data.re ? "是" : "否"}</div>
            <div>HP：${data.hp}</div><div>阳攻：${data.yang_atk}</div><div>阳防：${data.yang_def}</div>
            <div>速度：${data.speed}</div><div>阴攻：${data.yin_atk}</div><div>阴防：${data.yin_def}</div>
          </div>
          ${renderQualitySummary(data)}
        </div>
      </div>
    </div>
    <div class="card"><h3>能力</h3><div class="text-lines">${(data.ability_entries || []).map((line) => `<p>${escapeHtml(line)}</p>`).join("") || "<p>-</p>"}</div></div>
    <div class="card"><h3>技能</h3>${(data.skill_entries || []).map((item) => `<details open><summary>${item.title}</summary><div class="text-lines">${String(item.content || "").split("\n").map((line) => `<p>${line}</p>`).join("")}</div></details>`).join("")}</div>
    <div class="card"><h3>攻击类型</h3>${sections.map((item) => `<details><summary>${item.title} | ${item.name} | ${item.target_label || ""}</summary><div class="hit">${item.content}</div></details>`).join("")}</div>
  `;
  setActiveTab("character-detail");
}

async function loadVsPresets() {
  const data = await api("/api/vs-presets");
  state.vsPresets = data.presets || data.rows || [];
  $("#vsPresetStatus").textContent = `已解析 st=${data.st_count || 0}，td=${data.td_count || 0}，effect=${data.vs_effect_count || 0}，JSON: ${data.json_path || "-"}`;
  const query = String($("#vsPresetSearch")?.value || "").trim().toLowerCase();
  const sourceRows = state.vsPresets.filter((row) => {
    if (!query) return true;
    const enemyText = (row.enemies || []).map((item) => `${item.enemy?.display_name || ""} ${item.enemy?.name || ""} ${item.enemy?.enemy_id || ""}`).join(" ");
    return `${row.vs_id || ""} ${row.title || ""} ${enemyText}`.toLowerCase().includes(query);
  });
  const enemyNames = (row) => (row.enemies || []).map((item) => item.empty ? `敌方${item.pos}: 空` : `敌方${item.pos}: ${item.enemy?.display_name || item.enemy?.name || item.td_id}`).join("<br>");
  const tagText = (row) => (row.tags || []).map((tag) => {
    const effects = (tag.effects || []).map((effect) => effect.description || effect.name || effect.effect_id).join(" / ");
    return `${tag.tag || tag.group_id}: ${effects}`;
  }).join("<br>");
  const dropText = (row) => {
    if (Number(row.card_id || 0) >= 10000) return "绘祭马";
    if (!row.drop_card) return row.card_id || "-";
    return `<span class="card-drop-cell"><img class="table-card-icon" src="${cardIconUrl(row.drop_card.equipment_id)}" onerror="this.style.display='none'"><span class="linkish" data-equipment-id="${row.drop_card.equipment_id}">${row.drop_card.equipment_id_text || row.drop_card.equipment_id} / ${escapeHtml(row.drop_card.name || "")}</span></span>`;
  };
  buildTable($("#vsPresetTable"), [
    { key: "vs_id", label: "复灵ID" },
    { key: "title", label: "名称" },
    { key: "enemy_td_ids", label: "td位置", render: (row) => (row.enemy_td_ids || []).join("/") },
    { key: "enemies", label: "敌人", render: enemyNames },
    { key: "card_id", label: "掉落绘卷", render: dropText },
    { key: "tags", label: "tag/effect", render: tagText },
    { key: "action", label: "操作", render: (row) => `<button class="small secondary" data-apply-vs="${row.vs_id}">载入</button>` },
  ], sourceRows, (table) => {
    $$("[data-apply-vs]", table).forEach((btn) => {
      btn.addEventListener("click", () => {
        const preset = state.vsPresets.find((row) => String(row.vs_id) === String(btn.dataset.applyVs));
        if (preset) applyVsPreset(preset).catch((err) => alert(err.message));
      });
    });
    $$("[data-equipment-id]", table).forEach((link) => {
      link.addEventListener("click", () => jumpToEquipmentQuery(link.dataset.equipmentId));
    });
  });
}

function jumpToEquipmentQuery(equipmentId) {
  setQueryTab("equipment-query");
  resetEquipmentFilters();
  $("#eqName").value = equipmentId || "";
  searchEquipment().catch((err) => alert(err.message));
}

function renderRolePresets() {
  const root = $("#rolePresetCards");
  root.innerHTML = "";
  const card = document.createElement("article");
  card.className = "slot-card role-preset-card loaded";
  card.innerHTML = `
    <div class="slot-head">
      <h3>角色预设</h3>
      <div class="head-actions">
        <button class="small secondary" data-toggle-role-browser>${state.roleBrowserVisible ? "收起总览" : "角色总览"}</button>
        <button class="small secondary" data-load-preset>加载预设</button>
        <button class="small secondary" data-toggle-equipment-detail>${state.rolePresetDetail ? "简略" : "详细"}</button>
        <button class="small secondary" data-save-preset>保存预设</button>
        <button class="small danger" data-delete-preset>删除预设</button>
      </div>
    </div>
    <div data-role="role-browser-filter" class="${state.roleBrowserVisible ? "gallery-filter" : "hidden"}">
      <label>预设<select data-role="role-filter-preset"><option value="">全部</option><option value="missing">暂无预设</option><option value="exists">已有预设</option></select></label>
      <label class="inline-check"><input data-role="role-filter-rebirth2" type="checkbox">二转</label>
      <label class="inline-check"><input data-role="role-filter-unowned" type="checkbox">未拥有</label>
    </div>
    <div data-role="role-browser" class="${state.roleBrowserVisible ? "character-gallery" : "hidden"}"></div>
    <div class="slot-identity">
      <img data-role="avatar" class="avatar-small" src="/assets/avatars/S0.png" onerror="this.src='/assets/avatars/S0.png'">
      <div>${buildCharacterLoader("preset")}<div class="meta-line">名称：<b data-role="name">-</b>　世界群：<b data-role="world">-</b>　类型：<b data-role="type">-</b></div></div>
    </div>
    <div class="form-grid compact">
      <label>角色ID<input data-field="character_id" list="characterOptions" placeholder="ID / 名称"></label>
      <label>心情<select data-field="mood"><option>粉</option><option>橙</option><option>绿</option><option>蓝</option><option>紫</option></select></label>
      <label class="inline-check"><input data-field="rebirth2" type="checkbox">二转</label>
      <label class="inline-check"><input data-field="unowned" type="checkbox">未拥有</label>
    </div>
    <div class="subsection"><h4 data-role="stat-title">实际六维</h4><div class="form-grid">${PRESET_STAT_ORDER.map((key) => `<label>${STAT_LABELS[key]}<input data-stat="${key}" value="0"></label>`).join("")}</div></div>
    <div class="subsection"><div class="subsection-title"><h4>绘卷预设</h4></div><div data-role="preset-equipment">${EQUIPMENT_SLOTS.map(([key, label]) => `<div class="preset-equipment-row" data-slot="${key}"><span>${label}</span><img src="/assets/card_icons/PTS0.png" onerror="this.style.visibility='hidden'"><div><input data-field="equipment_id" list="equipmentOptions" placeholder="ID或名称"><div data-role="equipment_summary" class="equipment-summary"></div></div></div>`).join("")}</div></div>
    <details class="subsection override-editor"><summary>二转修改接口</summary><button type="button" class="small secondary" data-edit-override>编辑</button><textarea data-field="override_note" readonly placeholder="在这里写入预设 JSON/说明；保存后只进入 presets，不修改默认 datajson"></textarea></details>
  `;
  hydrateCharacterLoader(card, "preset");
  const refreshRoleBrowser = () => {
    if (!state.roleBrowserVisible) return;
    renderCharacterGallery($('[data-role="role-browser"]', card), state.characterPresets, async (id) => {
      state.loadedRolePresetId = String(id);
      await applyPreset(id);
    }, true, { useRoleFilters: true });
  };
  const applyPreset = async (id) => {
    const preset = state.characterPresets[String(id)] || {};
    const meta = await loadCharacterMeta(id).catch(() => null);
    if (meta) {
      setCharacterLoaderValue(card, "preset", meta.id);
      fillMeta(card, meta);
    }
    $('[data-field="character_id"]', card).value = id || "";
    $('[data-field="mood"]', card).value = preset.mood || "粉";
    $('[data-field="rebirth2"]', card).checked = Boolean(preset.rebirth2);
    $('[data-field="unowned"]', card).checked = Boolean(preset.unowned);
    $$("[data-stat]", card).forEach((input) => (input.value = preset.stat_bonuses?.[input.dataset.stat] ?? meta?.[input.dataset.stat] ?? 0));
    $('[data-role="stat-title"]', card).textContent = preset.stat_bonuses ? "实际六维（覆盖）" : "实际六维";
    $$(".preset-equipment-row", card).forEach((row) => {
      const value = preset.equipment_ids?.[row.dataset.slot] || "";
      $('[data-field="equipment_id"]', row).value = value;
      if (value) {
        $("img", row).src = cardIconUrl(value);
        updateEquipmentSummary(row, state.rolePresetDetail).catch(() => {});
      }
    });
    if (preset.override_note) {
      $('[data-field="override_note"]', card).value = preset.override_note;
    } else {
      const detail = await api(`/api/characters/${encodeURIComponent(id)}`).catch(() => null);
      $('[data-field="override_note"]', card).value = detail?.raw_json_text || "";
    }
  };
  const rolePresetFilter = $('[data-role="role-filter-preset"]', card);
  const roleRebirthFilter = $('[data-role="role-filter-rebirth2"]', card);
  const roleUnownedFilter = $('[data-role="role-filter-unowned"]', card);
  if (rolePresetFilter) rolePresetFilter.value = state.roleGalleryFilters.preset || "";
  if (roleRebirthFilter) roleRebirthFilter.checked = Boolean(state.roleGalleryFilters.rebirth2);
  if (roleUnownedFilter) roleUnownedFilter.checked = Boolean(state.roleGalleryFilters.unowned);
  rolePresetFilter?.addEventListener("change", () => {
    state.roleGalleryFilters.preset = rolePresetFilter.value;
    refreshRoleBrowser();
  });
  roleRebirthFilter?.addEventListener("change", () => {
    state.roleGalleryFilters.rebirth2 = roleRebirthFilter.checked;
    refreshRoleBrowser();
  });
  roleUnownedFilter?.addEventListener("change", () => {
    state.roleGalleryFilters.unowned = roleUnownedFilter.checked;
    refreshRoleBrowser();
  });
  $('[data-edit-override]', card)?.addEventListener("click", () => {
    const textarea = $('[data-field="override_note"]', card);
    if (textarea) {
      textarea.readOnly = false;
      textarea.focus();
    }
  });
  if (state.roleBrowserVisible) {
    refreshRoleBrowser();
  }
  $('[data-toggle-role-browser]', card).addEventListener("click", () => {
    state.roleBrowserVisible = !state.roleBrowserVisible;
    $('[data-toggle-role-browser]', card).textContent = state.roleBrowserVisible ? "收起总览" : "角色总览";
    $('[data-role="role-browser-filter"]', card).classList.toggle("hidden", !state.roleBrowserVisible);
    $('[data-role="role-browser"]', card).classList.toggle("hidden", !state.roleBrowserVisible);
    refreshRoleBrowser();
  });
  $('[data-load-preset]', card).addEventListener("click", async () => {
    const meta = await loadCharacterMeta(characterLoaderQuery(card, "preset") || $('[data-field="character_id"]', card).value);
    if (!meta?.id) return alert("未找到角色");
    setCharacterLoaderValue(card, "preset", meta.id);
    state.loadedRolePresetId = String(meta.id);
    await applyPreset(meta.id);
  });
  $('[data-load-character-id]', card).addEventListener("click", async () => {
    const meta = await loadCharacterMeta($(`[data-role="preset_id_query"]`, card)?.value || "");
    if (!meta?.id) return alert("未找到角色");
    setCharacterLoaderValue(card, "preset", meta.id);
    state.loadedRolePresetId = String(meta.id);
    await applyPreset(meta.id);
  });
  $('[data-toggle-equipment-detail]', card).addEventListener("click", () => {
    state.rolePresetDetail = !state.rolePresetDetail;
    renderRolePresets();
  });
  $$(".preset-equipment-row", card).forEach((row) => {
    $('[data-field="equipment_id"]', row).addEventListener("change", async () => {
      await updateEquipmentSummary(row, state.rolePresetDetail);
      $("img", row).src = cardIconUrl($('[data-field="equipment_id"]', row).value);
    });
  });
  $('[data-save-preset]', card).addEventListener("click", async () => {
    const meta = await loadCharacterMeta($('[data-field="character_id"]', card).value || characterLoaderQuery(card, "preset"));
    if (!meta?.id) return alert("请先输入有效角色ID/名称/世界群");
    const id = String(meta.id);
    const stat_bonuses = {};
    $$("[data-stat]", card).forEach((input) => (stat_bonuses[input.dataset.stat] = Number(input.value || 0)));
    const equipment_ids = {};
    $$(".preset-equipment-row", card).forEach((row) => (equipment_ids[row.dataset.slot] = $('[data-field="equipment_id"]', row).value || 0));
    state.characterPresets[id] = {
      mood: $('[data-field="mood"]', card).value,
      rebirth2: $('[data-field="rebirth2"]', card).checked,
      unowned: $('[data-field="unowned"]', card).checked,
      stat_bonuses,
      equipment_ids,
      override_note: $('[data-field="override_note"]', card).value,
    };
    await saveCharacterPresets();
    alert(`已保存角色 ${id} 的预设`);
    renderRolePresets();
  });
  $('[data-delete-preset]', card).addEventListener("click", async () => {
    const id = String($('[data-field="character_id"]', card).value || state.loadedRolePresetId || "");
    if (!id || !state.characterPresets[id]) return alert("当前角色没有预设");
    delete state.characterPresets[id];
    await saveCharacterPresets();
    state.loadedRolePresetId = "";
    renderRolePresets();
  });
  root.appendChild(card);
  if (state.loadedRolePresetId) applyPreset(state.loadedRolePresetId);
}

function renderArenaPresets() {
  const root = $("#arenaPresetCards");
  root.innerHTML = "";
  const statTemplates = arenaStatTemplates();
  const card = document.createElement("article");
  card.className = "slot-card arena-preset-card loaded";
  card.innerHTML = `
    <div class="slot-head">
      <h3>擂台敌方预设</h3>
      <div class="head-actions">
        <button class="small secondary" data-toggle-arena-browser>${state.arenaBrowserVisible ? "收起总览" : "角色总览"}</button>
        <button class="small secondary" data-load-arena>加载预设</button>
        <button class="small secondary" data-save-arena>保存预设</button>
      </div>
    </div>
    <div data-role="arena-browser-filter" class="${state.arenaBrowserVisible ? "gallery-filter" : "hidden"}">
      <label>预设<select data-role="arena-filter-preset"><option value="">全部</option><option value="missing">没有预设</option><option value="exists">已有预设</option></select></label>
    </div>
    <div data-role="arena-browser" class="${state.arenaBrowserVisible ? "character-gallery" : "hidden"}"></div>
    <div class="slot-identity">
      <img data-role="avatar" class="avatar-small" src="/assets/avatars/S0.png" onerror="this.src='/assets/avatars/S0.png'">
      <div class="identity-fields">
        ${buildCharacterLoader("arena")}
        <input data-field="character_id" type="hidden">
        <div class="meta-line">名称：<b data-role="name">-</b>　世界群：<b data-role="world">-</b>　类型：<b data-role="type">-</b></div>
      </div>
      <div class="arena-selected-panel hidden" data-role="arena-selected-panel">
        <button type="button" class="small secondary" data-reset-arena-character>重选角色</button>
        <span>ID：<b data-role="arena-selected-id">-</b></span>
        <span>世界群：<b data-role="arena-selected-world">-</b></span>
        <span>名称：<b data-role="arena-selected-name">-</b></span>
        <span>盾数量：<b data-role="arena-barrier-label">-</b></span>
        <span>弱点/耐性气质见下方图标</span>
      </div>
    </div>
    <div class="form-grid compact"><label>盾数量<select data-field="barrier_count"><option>4</option><option selected>7</option></select></label><label>六维模板<select data-field="stat_template"><option value="">不覆盖</option>${statTemplates.map((row, idx) => `<option value="${idx}">${escapeHtml(row.label)}</option>`).join("")}</select></label></div>
    <div class="subsection"><h4>周擂台1/2五维对照</h4><div class="table-wrap arena-stat-mirror" data-role="arena-stat-mirror"></div></div>
    <div class="subsection"><h4>五维覆盖（默认周擂台1-阳）</h4><div class="form-grid compact">${ARENA_STAT_KEYS.map((key) => `<label>${STAT_LABELS[key]}<input data-stat="${key}" value="0"></label>`).join("")}</div></div>
    <div class="subsection"><div class="subsection-title"><h4>气质</h4><button type="button" class="small secondary" data-reset-quality>归零</button></div><div data-role="quality"></div></div>
    <div class="subsection">
      <h4>敌方技能</h4>
      <div data-role="buffs"></div>
      <button class="small secondary" data-add-buff>添加技能效果</button>
      <button class="small secondary" data-clear-buffs>删除全部技能</button>
    </div>
  `;
  hydrateCharacterLoader(card, "arena");
  $('[data-load-character-id]', card).textContent = "载入预设";
  $('[data-load-character]', card)?.classList.add("hidden");
  $('[data-role="quality"]', card).appendChild(createQualityEditor());
  $('[data-reset-quality]', card).addEventListener("click", () => resetQuality($('[data-role="quality"]', card)));
  $("[data-add-buff]", card).addEventListener("click", () => addEnemySkillRow($('[data-role="buffs"]', card)));
  $("[data-clear-buffs]", card).addEventListener("click", () => ($('[data-role="buffs"]', card).innerHTML = ""));
  const applyPreset = (meta) => {
    if (!meta?.id) return;
    setCharacterLoaderValue(card, "arena", meta.id);
    fillMeta(card, meta);
    card.classList.add("arena-character-selected");
    $('[data-role="arena-selected-panel"]', card)?.classList.remove("hidden");
    $('[data-role="arena-selected-id"]', card).textContent = meta.id || "-";
    $('[data-role="arena-selected-world"]', card).textContent = meta.world_group || "-";
    $('[data-role="arena-selected-name"]', card).textContent = meta.name || "-";
    renderArenaStatMirror(card, meta.id);
    const preset = state.arenaPresets[String(meta.id)] || {};
    const section = arenaPresetSection(meta.id, "周擂台1") || {};
    $('[data-field="barrier_count"]', card).value = section.barrier_count ?? 7;
    $$("[data-stat]", card).forEach((input) => (input.value = section.stat_overrides?.[input.dataset.stat] ?? 0));
    $('[data-role="arena-barrier-label"]', card).textContent = $('[data-field="barrier_count"]', card).value;
    applyQualityToCard(card, section.quality || state.boot.quality_default || []);
    const buffRoot = $('[data-role="buffs"]', card);
    buffRoot.innerHTML = "";
    (section.enemy_skill_effects || []).forEach((buff) => addEnemySkillRow(buffRoot, buff));
  };
  $('[data-field="stat_template"]', card).addEventListener("change", (event) => {
    const tpl = statTemplates[Number(event.currentTarget.value)];
    $$("[data-stat]", card).forEach((input) => (input.value = tpl?.stats?.[input.dataset.stat] ?? 0));
    if (tpl?.barrier_count) $('[data-field="barrier_count"]', card).value = String(tpl.barrier_count);
    applyArenaFixedStats(card);
    $('[data-role="arena-barrier-label"]', card).textContent = $('[data-field="barrier_count"]', card).value;
  });
  $('[data-field="barrier_count"]', card).addEventListener("change", () => {
    applyArenaFixedStats(card);
    $('[data-role="arena-barrier-label"]', card).textContent = $('[data-field="barrier_count"]', card).value;
  });
  $('[data-reset-arena-character]', card).addEventListener("click", () => {
    card.classList.remove("arena-character-selected");
    $('[data-role="arena-selected-panel"]', card)?.classList.add("hidden");
    setCharacterLoaderValue(card, "arena", "");
    fillMeta(card, { id: "", name: "-", world_group: "-", type_label: "-" });
  });
  const arenaFilter = $('[data-role="arena-filter-preset"]', card);
  if (arenaFilter) {
    arenaFilter.value = state.arenaGalleryFilter || "";
    arenaFilter.addEventListener("change", () => {
      state.arenaGalleryFilter = arenaFilter.value;
      renderArenaPresets();
    });
  }
  if (state.arenaBrowserVisible) {
    const presetMap = state.arenaPresets;
    const allOptions = state.boot.character_options || [];
    const filteredOptions = allOptions.filter((row) => {
      const exists = Boolean(presetMap[String(row.id)]);
      if (state.arenaGalleryFilter === "exists") return exists;
      if (state.arenaGalleryFilter === "missing") return !exists;
      return true;
    });
    const originalOptions = state.boot.character_options;
    state.boot.character_options = filteredOptions;
    renderCharacterGallery($('[data-role="arena-browser"]', card), state.arenaPresets, async (id) => {
      const meta = await loadCharacterMeta(id).catch(() => null);
      if (meta) applyPreset(meta);
    }, false);
    state.boot.character_options = originalOptions;
  }
  $('[data-toggle-arena-browser]', card).addEventListener("click", () => {
    state.arenaBrowserVisible = !state.arenaBrowserVisible;
    $('[data-toggle-arena-browser]', card).textContent = state.arenaBrowserVisible ? "收起总览" : "角色总览";
    $('[data-role="arena-browser-filter"]', card).classList.toggle("hidden", !state.arenaBrowserVisible);
    $('[data-role="arena-browser"]', card).classList.toggle("hidden", !state.arenaBrowserVisible);
    if (state.arenaBrowserVisible) {
      renderCharacterGallery($('[data-role="arena-browser"]', card), state.arenaPresets, async (id) => {
        const meta = await loadCharacterMeta(id).catch(() => null);
        if (meta) applyPreset(meta);
      }, false);
    }
  });
  $('[data-load-arena]', card).addEventListener("click", async () => {
    const meta = await loadCharacterMeta(characterLoaderQuery(card, "arena") || $('[data-field="character_id"]', card)?.value);
    if (!meta?.id) return alert("未找到角色");
    setCharacterLoaderValue(card, "arena", meta.id);
    applyPreset(meta);
  });
  $('[data-load-character-id]', card).addEventListener("click", async () => {
    const meta = await loadCharacterMeta($(`[data-role="arena_id_query"]`, card)?.value || "");
    if (!meta?.id) return alert("未找到角色");
    setCharacterLoaderValue(card, "arena", meta.id);
    applyPreset(meta);
  });
  $('[data-save-arena]', card).addEventListener("click", async () => {
    const meta = await loadCharacterMeta(characterLoaderQuery(card, "arena") || $('[data-field="character_id"]', card)?.value);
    if (!meta?.id) return alert("请先输入有效角色ID或通过世界群选择角色");
    setCharacterLoaderValue(card, "arena", meta.id);
    fillMeta(card, meta);
    const weekly1 = {
      stat_overrides: Object.fromEntries($$("[data-stat]", card).map((input) => [input.dataset.stat, Number(input.value || 0)])),
      barrier_count: Number($('[data-field="barrier_count"]', card).value || 7),
      quality: collectQuality(card),
      enemy_skill_effects: collectEnemySkillRows($('[data-role="buffs"]', card)),
    };
    state.arenaPresets[String(meta.id)] = {
      character_id: Number(meta.id),
      name: meta.name || "",
      world_group: meta.world_group || "",
      type_label: meta.type_label || "",
      weekly1,
      weekly2: swapYinyangSection(weekly1),
    };
    await saveArenaPresets();
    await loadArenaPresets();
    await loadArenaEnemyData();
    renderArenaStatMirror(card, meta.id);
    renderWeeklyArenaConfig();
    alert(`已保存擂台敌方 ${meta.id} 的预设`);
  });
  root.appendChild(card);
  if (state.pendingArenaPresetId) {
    const id = state.pendingArenaPresetId;
    state.pendingArenaPresetId = "";
    loadCharacterMeta(id).then((meta) => {
      if (meta) applyPreset(meta);
    }).catch(() => {});
  }
}

function resetCharacterFilters() {
  ["cqTypes", "cqWorlds", "cqElements", "cqBullets", "cqKillers"].forEach((id) => setFilterValues(id, []));
  $("#cqKillers").value = "";
  $("#cqKillerInput").value = "";
  $("#cqElementLogic").value = "any";
  $("#cqBulletLogic").value = "any";
  $("#cqKillerLogic").value = "any";
  $("#cqName").value = "";
  $("#cqRe").value = "";
}

function resetEquipmentFilters() {
  ["eqStars", "eqStyle", "eqStats"].forEach((id) => setFilterValues(id, []));
  $("#eqStats").value = "";
  $("#eqName").value = "";
  $("#eqBuffLogic").value = "and";
  renderEquipmentBuffFilters();
}

async function refreshEquipmentSubIds() {
  const buffId = $("#eqBuffId").value;
  $("#eqSubIds").innerHTML = buffId ? tupleOptions(await api(`/api/equipment-buff-subids?buff_id=${encodeURIComponent(buffId)}`)) : "";
}

function renderEquipmentBuffFilters() {
  const root = $("#eqBuffFilters");
  root.innerHTML = "";
  for (let i = 1; i <= 3; i += 1) {
    const box = document.createElement("div");
    box.className = "equipment-buff-filter";
    box.innerHTML = `
      <b>Buff ${i}</b>
      <label>ID<select data-field="buff_id">${tupleOptions(state.boot.equipment_buff_id_options, true)}</select></label>
      <label>subID<input data-field="sub_ids" placeholder="多选用逗号"></label>
      <label>target<input data-field="target" placeholder="target"></label>
      <label>type<select data-field="type_conditions"><option value="">Type条件</option>${optionList(state.boot.type_labels)}</select></label>
      <label>值<input data-field="value" placeholder="值"></label>
    `;
    root.appendChild(box);
  }
}

function initFilters() {
  $("#cqTypes").innerHTML = `<option value="">选择Type</option>${optionList(state.boot.type_labels)}`;
  $("#cqWorlds").innerHTML = `<option value="">选择世界群</option>${(state.boot.world_group_options || []).map((value) => `<option value="${value}">${value}</option>`).join("")}`;
  const elementLabels = Object.fromEntries(Object.entries(state.boot.element_labels || {}).filter(([key]) => Number(key) > 0));
  $("#cqElements").innerHTML = `<option value="">选择属性</option>${optionList(elementLabels)}`;
  $("#cqBullets").innerHTML = `<option value="">选择弹种</option>${optionList(state.boot.bullet_labels)}`;
  renderEquipmentBuffFilters();
  bindAddFilterButtons();
  $("#addKillerBtn").addEventListener("click", () => {
    const raw = $("#cqKillerInput").value.trim();
    if (!raw) return;
    const match = (state.boot.tribe_options || []).find(([id, label]) => String(id) === raw || String(label).includes(raw));
    const value = match ? String(match[0]) : raw;
    const label = match ? `${match[0]} ${match[1]}` : raw;
    addFilterValue("cqKillers", value, label);
    $("#cqKillers").value = selectedFilterValues("cqKillers").join(",");
    $("#cqKillerInput").value = "";
  });
}

function bindEvents() {
  $("#tabs").addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-tab]");
    if (btn) setActiveTab(btn.dataset.tab);
  });
  $("#damageSubtabs").addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-subtab]");
    if (btn) setActiveSubtab(btn.dataset.subtab);
  });
  $("#calculateBtn").addEventListener("click", () => calculate().catch((err) => alert(err.message)));
  $("#batchPresetBtn").addEventListener("click", () => batchSummary("preset").catch((err) => alert(err.message)));
  $("#batchDefaultBtn").addEventListener("click", () => batchSummary("default").catch((err) => alert(err.message)));
  $("#weeklyArenaSolveBtn").addEventListener("click", () => solveWeeklyArena().catch((err) => alert(err.message)));
  $("#characterSearchBtn").addEventListener("click", () => searchCharacters().catch((err) => alert(err.message)));
  $("#toggleCharacterImagesBtn").addEventListener("click", () => {
    state.hideCharacterImages = !state.hideCharacterImages;
    $("#toggleCharacterImagesBtn").textContent = state.hideCharacterImages ? "展开头像栏" : "折叠头像栏";
    renderCharacterTable(state.lastCharacterRows || []);
  });
  $("#characterResetBtn").addEventListener("click", resetCharacterFilters);
  $("#equipmentSearchBtn").addEventListener("click", () => searchEquipment().catch((err) => alert(err.message)));
  $("#toggleEquipmentImagesBtn").addEventListener("click", () => {
    state.hideEquipmentImages = !state.hideEquipmentImages;
    $("#toggleEquipmentImagesBtn").textContent = state.hideEquipmentImages ? "展开图像栏" : "折叠图像栏";
    renderEquipmentTable(state.lastEquipmentRows || []);
  });
  $("#equipmentResetBtn").addEventListener("click", resetEquipmentFilters);
  $("#loadDetailBtn").addEventListener("click", () => loadCharacterDetail().catch((err) => alert(err.message)));
  $("#loadVsPresetBtn").addEventListener("click", () => loadVsPresets().catch((err) => alert(err.message)));
  $("#vsPresetSearch")?.addEventListener("input", () => {
    if (state.vsPresets.length) loadVsPresets().catch((err) => alert(err.message));
  });
  $$("[data-query-jump]").forEach((btn) => {
    btn.addEventListener("click", () => setQueryTab(btn.dataset.queryJump));
  });
  $("#vsManualImportBtn")?.addEventListener("click", () => importVsManualConfig());
  $("#vsManualCalcBtn")?.addEventListener("click", () => solveVsManual().catch((err) => alert(err.message)));
  $("#vsManualNextBtn")?.addEventListener("click", () => advanceVsManualTurn());
  $("#calcMode").addEventListener("change", () => {
    updateModeUI();
    renderOverview();
  });
  $$("#waveSwitch button[data-wave]").forEach((btn) => btn.addEventListener("click", () => switchWave(btn.dataset.wave)));
  $("#resultTabs").addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-result-view]");
    if (!btn) return;
    state.resultView = btn.dataset.resultView;
    $$("#resultTabs button").forEach((item) => item.classList.toggle("active", item === btn));
    if (state.lastResult) {
      renderSummary(state.lastResult);
      renderDetails(state.lastResult);
    }
  });
}

async function init() {
  state.boot = await api("/api/bootstrap");
  await loadCharacterPresets();
  await loadArenaPresets();
  await loadArenaEnemyData();
  createDatalists();
  renderEnemySlots();
  renderAllySlots();
  renderFullFieldRows();
  renderRolePresets();
  renderArenaPresets();
  renderWeeklyArenaConfig();
  initFilters();
  bindEvents();
  renderOverview();
  renderGlobalSkillButtons();
  updateVsManualButtons();
  await searchCharacters();
  await searchEquipment();
}

init().catch((err) => {
  console.error(err);
  document.body.insertAdjacentHTML("afterbegin", `<div class="card" style="margin:16px;color:#9f2c25">初始化失败：${err.message}</div>`);
});
