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
  $("#waveSwitch")?.classList.add("hidden");
  $(".field-buff-card")?.classList.toggle("hidden", mode !== "default");
  $(".vs-extra")?.classList.toggle("hidden", mode !== "vs");
  switchWave(1);
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
      barrier_types: Array.isArray(card._manualBarrierTypes) ? card._manualBarrierTypes.slice(0, Number($('[data-field="barrier_count"]', card).value || 0)) : [],
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
    card._manualBarrierTypes = Array.isArray(row.barrier_types) ? row.barrier_types.slice() : [];
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
    renderSlotTribeText(card);
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
    barrier_types: Array.isArray(card._manualBarrierTypes) ? card._manualBarrierTypes : [],
    enabled: $('[data-field="enabled"]', card).checked,
  };
}

function overviewCard(card, kind) {
  const meta = getSlotMeta(card);
  const className = meta.enabled ? "overview-card" : "overview-card disabled";
  return `
    <button class="${className}" data-kind="${kind}" data-pos="${meta.pos}">
      <img src="${avatarUrl(meta.id)}" onerror="this.src='/assets/avatars/S0.png'">
      <span><b>${meta.name || "-"}</b><small>${meta.world || "-"} / ${meta.type || "-"}</small><small>HP ${meta.hp || "-"}</small><small class="overview-barriers">${renderBarrierIcons(meta.barrier, meta.barrier_types)}</small></span>
    </button>
  `;
}

function renderOverview() {
  $("#enemyOverview")?.classList.remove("arena-current-overview");
  $("#enemyOverview").innerHTML = $$(".enemy-slot").map((card) => overviewCard(card, "enemy")).join("");
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

function collectAllyCardConfig(card) {
  return {
    enabled: $('[data-field="enabled"]', card).checked,
    character_id: $('[data-field="character_id"]', card).value,
    initial_spirit: $('[data-field="initial_spirit"]', card).value,
    barrier_count: $('[data-field="barrier_count"]', card).value,
    barrier_types: Array.isArray(card._manualBarrierTypes) ? card._manualBarrierTypes.slice(0, Number($('[data-field="barrier_count"]', card).value || 0)) : [],
    skill_order_text: $('[data-field="skill_order_text"]', card)?.value || "",
    shield_open_count: $('[data-field="shield_open_count"]', card).value,
    attack_type: $('[data-field="attack_type"]', card).value,
    spirit_level: $('[data-field="spirit_level"]', card).value,
    target_enemy_pos: $('[data-field="target_enemy_pos"]', card).value,
    buffs: collectBuffRows($('[data-role="buffs"]', card)),
    equipment_ids: collectEquipmentIds(card),
  };
}

function collectAllySlotsFromCards(cards) {
  const ally_slots = {};
  cards.forEach((card) => {
    ally_slots[card.dataset.pos] = collectAllyCardConfig(card);
  });
  return ally_slots;
}

function collectConfig() {
  saveCurrentEnemyWave();
  const weeklyConfig = collectWeeklyArenaConfig();
  const mode = $("#calcMode").value;
  const manualFieldBuffsEnabled = mode === "default";
  const enemy_slots = collectEnemyCards();
  const ally_slots = collectAllySlotsFromCards($$("#allySlots .ally-slot"));
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
        vs_tag_effects: runtimeVsTagEffects(),
        arena_type_boosts: selectedButtonValues("#arenaTypeBoosts").slice(0, 2),
        arena_yinyang: selectedButtonValues("#arenaYinyang")[0] || "yang",
        realistic: $("#realisticCalc").checked,
      },
    },
  };
}

function loadCalcPresetsFromStorage() {
  try {
    state.calcPresets = JSON.parse(localStorage.getItem(CALC_PRESET_STORAGE_KEY) || "{}") || {};
  } catch {
    state.calcPresets = {};
  }
  renderCalcPresetOptions();
}

function saveCalcPresetsToStorage() {
  localStorage.setItem(CALC_PRESET_STORAGE_KEY, JSON.stringify(state.calcPresets || {}));
  renderCalcPresetOptions();
}

function renderCalcPresetOptions() {
  const select = $("#calcPresetSelect");
  if (!select) return;
  const current = select.value;
  const names = Object.keys(state.calcPresets || {}).sort((a, b) => a.localeCompare(b, "zh-Hans-CN"));
  select.innerHTML = `<option value="">选择伤害预设</option>${names.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("")}`;
  if (current && state.calcPresets[current]) select.value = current;
}

function applyFullFieldRows(selector, rows = []) {
  const values = new Map((rows || []).map((row) => [String(row[0]), String(row[1])]));
  $$(`${selector} [data-sub-id]`).forEach((input) => {
    input.value = values.get(String(input.dataset.subId)) || "100";
  });
}

function applyBuffRows(root, rows = []) {
  if (!root) return;
  root.innerHTML = "";
  (rows || []).forEach((row) => addBuffRow(root, row));
}

function applyAllySlotConfig(card, row = {}) {
  $('[data-field="enabled"]', card).checked = Boolean(row.enabled);
  card.classList.toggle("collapsed", !Boolean(row.enabled));
  const collapseBtn = $('[data-collapse-card]', card);
  if (collapseBtn) collapseBtn.textContent = card.classList.contains("collapsed") ? "展开" : "折叠";
  for (const key of ["character_id", "initial_spirit", "barrier_count", "target_enemy_pos", "spirit_level", "shield_open_count", "attack_type", "skill_order_text"]) {
    const input = $(`[data-field="${key}"]`, card);
    if (input && row[key] !== undefined) input.value = row[key];
  }
  applyBuffRows($('[data-role="buffs"]', card), row.buffs || []);
  $$(".equipment-row", card).forEach((eqRow) => {
    const value = row.equipment_ids?.[eqRow.dataset.slot] || "";
    const input = $('[data-field="equipment_id"]', eqRow);
    if (input) input.value = value;
    updateEquipmentSummary(eqRow).catch(() => {});
  });
  const order = String(row.skill_order_text || "").split(",").map((v) => Number(v)).filter((v) => Number.isInteger(v));
  $$(".skill-btn", card).forEach((btn) => btn.classList.toggle("active", order.includes(Number(btn.dataset.skill))));
  updateAllySkillOrder(card);
  if (row.character_id) {
    loadCharacterMeta(row.character_id).then((meta) => fillMeta(card, meta)).catch(() => {});
  }
}

function applyDamageConfig(config = {}) {
  if (!config || typeof config !== "object") return;
  if (config.mode && $("#calcMode")) $("#calcMode").value = config.mode === "arena" ? "default" : config.mode;
  if (config.enemy_waves) state.enemyWaves = config.enemy_waves;
  state.currentWave = Number(config.current_wave || 1);
  $("#waveCount").value = String(state.currentWave);
  applyEnemyWave(state.currentWave);
  Object.entries(config.ally_slots || {}).forEach(([pos, row]) => {
    const card = $(`.ally-slot[data-pos="${pos}"]`);
    if (card) applyAllySlotConfig(card, row);
  });
  const process = config.process || {};
  $("#useCustomSkillOrder").checked = Boolean(process.use_custom_skill_order);
  $("#customSkillOrder").value = process.custom_skill_order_text || "";
  const field = process.field_buffs || {};
  applyFullFieldRows("#fieldBulletRows", field.bullet_type_modifiers || []);
  applyFullFieldRows("#fieldElementRows", field.element_modifiers || []);
  applyFullFieldRows("#fieldTypeRows", field.type_resist_modifiers || []);
  $("#realisticCalc").checked = Boolean(field.realistic);
  updateModeUI();
  renderOverview();
  renderGlobalSkillButtons();
}

function saveCurrentCalcPreset() {
  const name = String($("#calcPresetName")?.value || $("#calcPresetSelect")?.value || "").trim();
  if (!name) {
    alert("请先输入预设名。");
    return;
  }
  state.calcPresets[name] = collectConfig();
  saveCalcPresetsToStorage();
  $("#calcPresetSelect").value = name;
  alert(`已保存伤害预设：${name}`);
}

function loadSelectedCalcPreset() {
  const name = $("#calcPresetSelect")?.value || "";
  if (!name || !state.calcPresets[name]) {
    alert("请选择要载入的伤害预设。");
    return;
  }
  applyDamageConfig(state.calcPresets[name]);
  $("#calcPresetName").value = name;
}

function deleteSelectedCalcPreset() {
  const name = $("#calcPresetSelect")?.value || "";
  if (!name || !state.calcPresets[name]) return;
  delete state.calcPresets[name];
  saveCalcPresetsToStorage();
  $("#calcPresetName").value = "";
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

async function applyVsPreset(preset, options = {}) {
  const target = options.target || "manual";
  const level = Math.max(60, Math.min(100, Number($("#vsLevel")?.value || 100)));
  state.activeVsPreset = preset;
  state.vsManualPreviewPhases = {};
  state.vsManualInitialPayload = null;
  state.activeVsTagEffects = (preset.tags || []).flatMap((tag) => (tag.effects || []).map(enrichVsEffect));
  const presetEffects = state.activeVsTagEffects.concat(state.customVsTagEffects || []);
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
    const stats = applyVsEnemyHpFactor(interpolateVsStats(enemy, level), presetEffects);
    const meta = await loadCharacterMeta(enemy.enemy_id).catch(() => null);
    fillMeta(card, meta || { id: enemy.enemy_id, name: enemy.display_name || enemy.name, world_group: "-", type_label: "-" });
    applyStatsToCard(card, stats);
    $('[data-field="barrier_count"]', card).value = enemy.barrier_count ?? 9;
    card._maxBarrierCount = Number(enemy.barrier_count ?? 9);
    card._manualBarrierTypes = [];
    $('[data-field="tribe_text"]', card).value = enemy.tribe_text_ids || (enemy.tribe_ids || []).join(",") || enemy.tribes_text || "";
    renderSlotTribeText(card);
    applyQualityToCard(card, enemy.quality || []);
    card._enemySkillEffects = enemy.skill_buffs || [];
    card._enemyExtra = enemy;
    card._enemyPhases = phases;
    card._enemyPhaseIndex = 0;
    card._manualSpellCd = Number(enemy.spell_gauge ?? 0);
    renderEnemyInfoBlock(card, enemy);
    const phaseRoot = $('[data-role="phase_buttons"]', card);
    phaseRoot.innerHTML = phases.map((phase, idx) => `<button type="button" class="small secondary ${idx === 0 ? "active" : ""}" data-phase-idx="${idx}">血条${idx + 1}</button>`).join("");
    $$("[data-phase-idx]", phaseRoot).forEach((btn) => {
      btn.addEventListener("click", async () => {
        $$("[data-phase-idx]", phaseRoot).forEach((item) => item.classList.toggle("active", item === btn));
        const phase = phases[Number(btn.dataset.phaseIdx)] || enemy;
        card._enemyPhaseIndex = Number(btn.dataset.phaseIdx) || 0;
        const phaseStats = applyVsEnemyHpFactor(interpolateVsStats(phase, Number($("#vsLevel")?.value || 100)));
        const phaseMeta = await loadCharacterMeta(phase.enemy_id).catch(() => null);
        fillMeta(card, phaseMeta || { id: phase.enemy_id, name: phase.display_name || phase.name, world_group: "-", type_label: "-" });
        applyStatsToCard(card, phaseStats);
        $('[data-field="barrier_count"]', card).value = phase.barrier_count ?? 9;
        card._maxBarrierCount = Number(phase.barrier_count ?? 9);
        card._manualBarrierTypes = [];
        $('[data-field="tribe_text"]', card).value = phase.tribe_text_ids || (phase.tribe_ids || []).join(",") || phase.tribes_text || "";
        renderSlotTribeText(card);
        applyQualityToCard(card, phase.quality || []);
        card._enemySkillEffects = phase.skill_buffs || [];
        card._enemyExtra = phase;
        card._manualSpellCd = Number(phase.spell_gauge ?? 0);
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
  renderVsManualFieldPresetTable();
  renderVsManualEnemySlots();
  if (target === "manual") {
    setActiveTab("vs-manual");
    setVsManualTab("field");
  } else {
    setActiveTab("damage");
    setActiveSubtab("enemyPane");
    if (typeof renderModuleSidebar === "function") renderModuleSidebar("damage");
  }
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
  const spiritRows = Object.values(result.spirit_recovery_summary || {}).filter((row) => row && Number(row.potential_hits || 0) > 0);
  if (spiritRows.length) {
    $("#summaryCards").insertAdjacentHTML("beforeend", `
      <details class="summary-card summary-collapse">
        <summary>灵力变化</summary>
        ${spiritRows.map((row) => `
          <strong>角色${row.pos}: ${numberText(row.spirit_before_recovery)} + ${numberText(row.spirit_recovery)} = ${numberText(row.spirit_after_recovery)}</strong>
          <small>命中 ${numberText(row.actual_hits)} / ${numberText(row.potential_hits)}，回收率 ${numberText(row.power_rate)}%，倍率 ${numberText(row.multiplier)}x</small>
        `).join("")}
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
  payload.process.field_buffs.realistic = false;
  if (targetArena) {
    payload.weekly_arenas = payload.weekly_arenas.map((arena, idx) => idx + 1 === targetArena ? arena : {});
    payload.weekly_arena_meta = payload.weekly_arena_meta.map((meta, idx) => idx + 1 === targetArena ? meta : {});
  }
  const data = await api("/api/weekly-arena-solve", { method: "POST", body: JSON.stringify(payload) });
  const recommended = (data.recommended || []).filter((row) => !targetArena || Number(row.arena) === Number(targetArena));
  const recHtml = recommended.map((row) => {
    if (row.status) return `<tr><td>${row.arena}</td><td>${row.wave}</td><td colspan="9">${escapeHtml(row.status)}</td></tr>`;
    return `<tr><td>${row.arena}</td><td>${row.wave}</td><td>${row.character_id}</td><td>${escapeHtml(row.name)}</td><td>${escapeHtml(row.world_group || "-")}</td><td>${escapeHtml(row.type_label)}${row.type_boosted ? " / Type加成" : ""}</td><td>${numberText(row.spirit_level ?? 0)}P</td><td>${numberText(row.damage)}</td><td>${numberText(row.enemy_hp_total)}</td><td>${numberText(row.overflow)}</td><td>阳${numberText(row.yang_ratio)}% / 阴${numberText(row.yin_ratio)}%</td></tr>`;
  }).join("");
  const visibleArenas = (data.arenas || []).filter((arena) => !targetArena || Number(arena.arena) === Number(targetArena));
  const arenaHtml = visibleArenas.map((arena) => `
    <details class="card">
      <summary>擂台 ${arena.arena}</summary>
      ${(arena.waves || []).map((wave) => `
        <h4>第 ${wave.wave} 波 HP ${numberText(wave.enemy_hp_total)}</h4>
        <div class="weekly-candidate-row">
          <img src="${avatarUrl((wave.candidates || [])[0]?.character_id)}" onerror="this.src='/assets/avatars/S0.png'">
          <select>${(wave.candidates || []).slice(0, 80).map((row) => `<option value="${row.character_id}">${row.character_id} / ${escapeHtml(row.name)} / ${escapeHtml(row.world_group || "-")} / ${row.type_boosted ? "Type加成 / " : ""}${numberText(row.spirit_level ?? 0)}P / 溢出 ${numberText(row.overflow)} / 伤害 ${numberText(row.damage)} / 阳${numberText(row.yang_ratio)}%-阴${numberText(row.yin_ratio)}%</option>`).join("") || '<option>无满足溢出条件的候选角色</option>'}</select>
        </div>
      `).join("")}
    </details>
  `).join("");
  $("#weeklyArenaResult").innerHTML = `
    ${data.message ? `<p class="hint">${escapeHtml(data.message)}</p>` : ""}
    <div class="table-wrap"><table><thead><tr><th>擂台</th><th>波次</th><th>角色ID</th><th>名称</th><th>世界群</th><th>Type</th><th>实际P</th><th>伤害</th><th>敌方HP</th><th>溢出</th><th>阴阳占比</th></tr></thead><tbody>${recHtml || '<tr><td colspan="11">暂无推荐</td></tr>'}</tbody></table></div>
    ${arenaHtml}
  `;
  $$("#weeklyArenaResult .weekly-candidate-row select").forEach((select) => {
    select.addEventListener("change", () => {
      const img = $("img", select.closest(".weekly-candidate-row"));
      if (img) img.src = avatarUrl(select.value);
    });
  });
}
