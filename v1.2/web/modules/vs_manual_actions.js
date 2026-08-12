const VS_MANUAL_ATTACKS = [
  ["1c", "扩散"],
  ["2c", "集中"],
  ["1", "符卡1A"],
  ["2", "符卡2A"],
  ["1", "符卡1B"],
  ["2", "符卡2B"],
  ["5", "终符"],
];

function manualAllyCards() {
  return $$("#vsManualAllySlots .vs-ally-slot").filter((card) => $('[data-field="enabled"]', card)?.checked);
}

function normalAllyCards() {
  return $$("#allySlots .ally-slot").filter((card) => $('[data-field="enabled"]', card)?.checked);
}

function isVsManualAllyCard(card) {
  return Boolean(card?.classList?.contains("vs-ally-slot"));
}

function buildVsManualPayload() {
  $("#calcMode").value = "vs";
  updateModeUI();
  const payload = collectConfig();
  payload.mode = "vs";
  payload.process = payload.process || {};
  payload.process.field_buffs = payload.process.field_buffs || {};
  payload.process.field_buffs.realistic = true;
  payload.ally_slots = collectAllySlotsFromCards($$("#vsManualAllySlots .vs-ally-slot"));
  return payload;
}

function refreshVsManualPayloadFromCards() {
  if (!$("#vsManualAllySlots")) return;
  state.vsManualPayload = applyManualRuntimeToPayload(buildVsManualPayload());
}

function cloneManualPayload(payload) {
  return JSON.parse(JSON.stringify(payload || {}));
}

function restoreVsManualPayloadToCards(payload) {
  if (!payload) return;
  Object.entries(payload.enemy_slots || {}).forEach(([pos, row]) => {
    const card = $(`.enemy-slot[data-pos="${pos}"]`);
    if (!card || !row) return;
    $('[data-field="enabled"]', card).checked = Boolean(row.enabled);
    card.classList.toggle("collapsed", !Boolean(row.enabled));
    const collapseBtn = $('[data-collapse-card]', card);
    if (collapseBtn) collapseBtn.textContent = card.classList.contains("collapsed") ? "展开" : "折叠";
    ["character_id", "hp", "yang_atk", "yang_def", "yin_atk", "yin_def", "speed", "barrier_count", "tribe_text"].forEach((key) => {
      const input = $(`[data-field="${key}"]`, card);
      if (input && row[key] !== undefined) input.value = row[key];
    });
    const breakBtn = $('[data-field="is_break_all"]', card);
    if (breakBtn) {
      breakBtn.dataset.value = String(Boolean(row.is_break_all));
      breakBtn.textContent = `完全破盾：${row.is_break_all ? "是" : "否"}`;
    }
    card._manualBarrierTypes = Array.isArray(row.barrier_types) ? row.barrier_types.slice() : [];
    applyQualityToCard(card, row.quality || []);
    applyBuffRows($('[data-role="buffs"]', card), row.buffs || []);
  });
  Object.entries(payload.ally_slots || {}).forEach(([pos, row]) => {
    const card = $(`#vsManualAllySlots .vs-ally-slot[data-pos="${pos}"]`);
    if (!card || !row) return;
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
      const input = $('[data-field="equipment_id"]', eqRow);
      if (input) input.value = row.equipment_ids?.[eqRow.dataset.slot] || "";
      updateEquipmentSummary(eqRow).catch(() => {});
    });
    if (row.character_id) loadCharacterMeta(row.character_id).then((meta) => fillMeta(card, meta)).catch(() => {});
    card._manualBarrierTypes = Array.isArray(row.barrier_types) ? row.barrier_types.slice() : [];
    card._skillCooldowns = {};
  });
}

function enabledEnemyPositions() {
  return $$(".enemy-slot").filter((card) => {
    return $('[data-field="enabled"]', card)?.checked && String($('[data-field="character_id"]', card)?.value || "").trim();
  }).map((card) => Number(card.dataset.pos)).filter((pos) => Number.isInteger(pos));
}

function normalizeManualTarget(card) {
  const input = $('[data-field="target_enemy_pos"]', card);
  const positions = enabledEnemyPositions();
  if (!input || !positions.length) return 0;
  const current = Number(input.value || positions[0]);
  if (!positions.includes(current)) input.value = String(positions[0]);
  return Number(input.value || positions[0]);
}

function cycleManualTarget(card, viewSelector) {
  const input = $('[data-field="target_enemy_pos"]', card);
  const positions = enabledEnemyPositions();
  if (!input || !positions.length) return 0;
  const current = normalizeManualTarget(card);
  const idx = positions.indexOf(current);
  const next = positions[(idx + 1) % positions.length];
  input.value = String(next);
  const view = $(viewSelector);
  if (view) view.textContent = String(next);
  refreshVsManualPayloadFromCards();
  return next;
}

function activeVsMaxBarrierCount() {
  const effects = selectedVsTagEffects();
  const delta = (effects || []).reduce((sum, effect) => {
    return Number(effect.kind || 0) === 3 ? sum + Number(effect.value || 0) : sum;
  }, 0);
  return Math.max(1, Math.min(5, 5 + delta));
}

function maxManualShieldOpen(card) {
  const current = Number($('[data-field="barrier_count"]', card)?.value || 0);
  const maxByCurrent = Math.max(0, current - 1);
  return Math.max(0, Math.min(activeVsMaxBarrierCount() - 1, maxByCurrent));
}

function cycleManualNumber(card, field, max, viewSelector) {
  const input = $(`[data-field="${field}"]`, card);
  if (!input) return 0;
  const next = (Number(input.value || 0) + 1) % (max + 1);
  input.value = String(next);
  const view = $(viewSelector);
  if (view) view.textContent = String(next);
  refreshVsManualPayloadFromCards();
  return next;
}

function setManualAttack(card, attackType, button) {
  const input = $('[data-field="attack_type"]', card);
  if (input) input.value = attackType;
  $$("[data-manual-attack]", button.closest(".manual-attack-row")).forEach((item) => item.classList.toggle("active", item === button));
  refreshVsManualPayloadFromCards();
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
  const target = targetType === undefined || targetType === null || targetType === "" ? 1 : Number(targetType);
  const allyCards = isVsManualAllyCard(casterCard) ? manualAllyCards() : normalAllyCards();
  if (target === 0) return allyCards;
  if (target === 1) return [casterCard];
  if (target === 2) return allyCards;
  if (target === 3) {
    const pos = normalizeManualTarget(casterCard);
    return [$(`.enemy-slot[data-pos="${pos}"]`)].filter(Boolean);
  }
  if (target === 4) return $$(".enemy-slot").filter((card) => $('[data-field="enabled"]', card)?.checked);
  return [casterCard];
}

function expandCompoundSubIds(buffId, subId) {
  const id = Number(buffId || 0);
  const raw = Math.abs(Number(subId || 0));
  if (![1, 2, 41, 42].includes(id) || raw <= 100) return [Number(subId || 0)];
  const valid = new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
  const text = String(raw);
  const out = [];
  let idx = 0;
  while (idx < text.length) {
    if (text[idx] === "0") {
      idx += 1;
      continue;
    }
    let picked = null;
    if (idx + 2 <= text.length) {
      const two = Number(text.slice(idx, idx + 2));
      if (valid.has(two)) {
        picked = two;
        idx += 2;
      }
    }
    if (picked === null) {
      const one = Number(text[idx]);
      if (valid.has(one)) picked = one;
      idx += 1;
    }
    if (picked !== null && !out.includes(picked)) out.push(picked);
  }
  return out.length ? out : [Number(subId || 0)];
}

function upsertManualBuffRow(targetCard, buffId, subId, duration, value) {
  const root = $('[data-role="buffs"]', targetCard);
  if (!root) return;
  const existing = $$(".buff-row", root).find((row) => {
    return Number($('[data-field="buff_id"]', row)?.value || 0) === Number(buffId)
      && Number($('[data-field="sub_id"]', row)?.value || 0) === Number(subId);
  });
  if (!existing) {
    addBuffRow(root, [buffId, subId, duration, value]);
    return;
  }
  const durationInput = $('[data-field="duration"]', existing);
  const valueInput = $('[data-field="value"]', existing);
  if (durationInput) durationInput.value = Math.max(Number(durationInput.value || 0), Number(duration || 0));
  if (valueInput) valueInput.value = Number(valueInput.value || 0) + Number(value || 0);
  updateEffectDescription(existing, false).catch(() => {});
}

function addManualBarrier(targetCard, amount) {
  const input = $('[data-field="barrier_count"]', targetCard);
  if (!input) return;
  const max = targetCard.classList?.contains("vs-ally-slot")
    ? activeVsMaxBarrierCount()
    : Number(targetCard._maxBarrierCount || input.dataset.maxBarrier || input.value || 0);
  const next = Math.min(max || 10, Number(input.value || 0) + Number(amount || 0));
  input.value = next;
  targetCard._manualBarrierTypes = (targetCard._manualBarrierTypes || []).slice(0, next);
}

function setManualBarrierType(targetCard, amount, barrierType) {
  const countInput = $('[data-field="barrier_count"]', targetCard);
  const count = Number(countInput?.value || 0);
  const types = Array.isArray(targetCard._manualBarrierTypes) ? targetCard._manualBarrierTypes.slice(0, count) : [];
  while (types.length < count) types.push(0);
  let left = Number(amount || 0);
  for (let i = 0; i < types.length && left > 0; i += 1) {
    if (!types[i]) {
      types[i] = Number(barrierType || 0);
      left -= 1;
    }
  }
  targetCard._manualBarrierTypes = types;
}

function applyManualSkillEffect(casterCard, effect = []) {
  if (!Array.isArray(effect) || effect.length < 5) return;
  const [buffId, subId, targetType, duration, value] = effect.map((v) => Number(v || 0));
  const targets = targetCardsForSkill(casterCard, targetType);
  if ([1, 2, 41, 42].includes(buffId)) {
    targets.forEach((targetCard) => {
      expandCompoundSubIds(buffId, subId).forEach((currentSubId) => {
        upsertManualBuffRow(targetCard, buffId, currentSubId, duration, value);
      });
    });
    return;
  }
  if (buffId === 3) {
    targets.forEach((targetCard) => {
      const input = $('[data-field="hp"]', targetCard);
      if (input) input.value = Math.round(Number(input.value || 0) * (1 + Number(value || 0) / 100));
    });
    return;
  }
  if (buffId === 4) {
    targets.forEach((targetCard) => addManualBarrier(targetCard, value));
    return;
  }
  if (buffId === 5) {
    const delta = Number(value || 0) / 20.0;
    targets.filter((card) => card?.classList?.contains("ally-slot") || card?.classList?.contains("vs-ally-slot")).forEach((card) => {
      const input = $('[data-field="initial_spirit"]', card);
      if (input) input.value = numberText(Number(input.value || 0) + delta);
    });
    return;
  }
  if (buffId === 6) {
    targets.forEach((targetCard) => setManualBarrierType(targetCard, value, subId));
    return;
  }
  targets.forEach((targetCard) => {
    upsertManualBuffRow(targetCard, buffId, subId, duration, value);
  });
}

function manualStateTargetRows(casterCard, targetType) {
  const target = targetType === undefined || targetType === null || targetType === "" ? 1 : Number(targetType);
  const runtime = state.vsManualState || {};
  const allies = runtime.ally_states || [];
  const enemies = runtime.enemy_states || [];
  const casterPos = Number(casterCard?.dataset?.pos ?? -1);
  if (target === 0 || target === 1) return allies.filter((row) => Number(row.pos) === casterPos);
  if (target === 2) return allies;
  if (target === 3) {
    const pos = normalizeManualTarget(casterCard);
    return enemies.filter((row) => Number(row.pos) === pos);
  }
  if (target === 4) return enemies;
  return allies.filter((row) => Number(row.pos) === casterPos);
}

function upsertRuntimeBuff(row, buffId, subId, duration, value) {
  row.buffs = Array.isArray(row.buffs) ? row.buffs : [];
  const existing = row.buffs.find((item) => Array.isArray(item) && Number(item[0] || 0) === Number(buffId) && Number(item[1] || 0) === Number(subId));
  if (!existing) {
    row.buffs.push([Number(buffId), Number(subId), Number(duration), Number(value)]);
  } else {
    existing[2] = Math.max(Number(existing[2] || 0), Number(duration || 0));
    existing[3] = Number(existing[3] || 0) + Number(value || 0);
  }
  row.buffs_text = [];
}

function addRuntimeBarrier(row, amount) {
  const max = row.side === "ally" ? activeVsMaxBarrierCount() : Number(row.max_barrier_count || row.barrier_count || 10);
  const next = Math.min(max || 10, Number(row.barrier_count || 0) + Number(amount || 0));
  row.barrier_count = next;
  row.barrier_types = (Array.isArray(row.barrier_types) ? row.barrier_types : []).slice(0, next);
}

function setRuntimeBarrierType(row, amount, barrierType) {
  const count = Number(row.barrier_count || 0);
  const types = Array.isArray(row.barrier_types) ? row.barrier_types.slice(0, count) : [];
  while (types.length < count) types.push(0);
  let left = Number(amount || 0);
  for (let i = 0; i < types.length && left > 0; i += 1) {
    if (!types[i]) {
      types[i] = Number(barrierType || 0);
      left -= 1;
    }
  }
  row.barrier_types = types;
}

function applyManualSkillEffectToState(casterCard, effect = []) {
  if (!state.vsManualState || !Array.isArray(effect) || effect.length < 5) return false;
  const [buffId, subId, targetType, duration, value] = effect.map((v) => Number(v || 0));
  const targets = manualStateTargetRows(casterCard, targetType);
  if ([1, 2, 41, 42].includes(buffId)) {
    targets.forEach((row) => expandCompoundSubIds(buffId, subId).forEach((currentSubId) => upsertRuntimeBuff(row, buffId, currentSubId, duration, value)));
    return true;
  }
  if (buffId === 3) {
    targets.forEach((row) => {
      row.current_hp = Math.round(Number(row.current_hp ?? row.remaining_hp ?? row.hp ?? 0) * (1 + Number(value || 0) / 100));
      row.remaining_hp = row.current_hp;
    });
    return true;
  }
  if (buffId === 4) {
    targets.forEach((row) => addRuntimeBarrier(row, value));
    return true;
  }
  if (buffId === 5) {
    const delta = Number(value || 0) / 20.0;
    targets.filter((row) => row.side === "ally").forEach((row) => {
      row.spirit = Math.min(5.0, Number(row.spirit || 0) + delta);
    });
    return true;
  }
  if (buffId === 6) {
    targets.forEach((row) => setRuntimeBarrierType(row, value, subId));
    return true;
  }
  targets.forEach((row) => upsertRuntimeBuff(row, buffId, subId, duration, value));
  return true;
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
  delete state.vsManualPendingSkills?.[key];
  card._skillCooldowns = card._skillCooldowns || {};
  card._skillCooldowns[skill] = Number(skillData.cd || skillData.cooltime || skillData.cool_time || 0);
  const name = $('[data-role="name"]', card)?.textContent || charId || `位置${pos}`;
  state.vsManualSkillLog.push(`我方${pos}:${name} 技能${skill + 1}`);
  button.disabled = true;
  button.classList.add("cooldown");
  ["a", "b", "c"].forEach((keyName) => {
    if (!applyManualSkillEffectToState(card, skillData[keyName])) applyManualSkillEffect(card, skillData[keyName]);
  });
  const view = $('[data-role="skill_order_view"]', card);
  if (view) {
    const used = Object.keys(state.vsManualSkillUsed)
      .filter((item) => item.startsWith(`${pos}:`))
      .map((item) => `技能${Number(item.split(":")[1]) + 1}`);
    view.textContent = used.join(" → ") || "不开技能";
  }
  renderVsManualControls();
}

function togglePendingManualSkill(card, skill, button) {
  state.vsManualPendingSkills = state.vsManualPendingSkills || {};
  const key = `${card.dataset.pos}:${skill}`;
  if (state.vsManualSkillUsed[key]) return;
  if (state.vsManualPendingSkills[key]) {
    delete state.vsManualPendingSkills[key];
    button.classList.remove("active");
  } else {
    state.vsManualPendingSkills[key] = true;
    button.classList.add("active");
  }
}

async function applyPendingManualSkills() {
  const pending = Object.keys(state.vsManualPendingSkills || {});
  for (const key of pending) {
    const [pos, skillText] = key.split(":");
    const card = $(`#vsManualAllySlots .vs-ally-slot[data-pos="${pos}"]`);
    const button = $(`#vsManualControls [data-manual-control-pos="${pos}"] [data-manual-skill="${skillText}"]`);
    if (card && button) await useManualSkill(card, Number(skillText), button);
  }
  state.vsManualPendingSkills = {};
  await refreshRuntimeBuffTexts();
  const board = buildVsManualBoardResultFromCards(state.vsManualState);
  state.vsManualPayload = applyManualRuntimeToPayload(buildVsManualPayload());
  state.vsManualState = board.state;
  renderVsManualControls();
  renderVsManualResult(board);
}

function renderVsManualControls() {
  const root = $("#vsManualControls");
  if (!root) return;
  const rows = manualAllyCards();
  root.innerHTML = rows.map((card) => {
    const pos = card.dataset.pos;
    const name = $('[data-role="name"]', card)?.textContent || `我方${pos}`;
    const activeAttack = $('[data-field="attack_type"]', card)?.value || "5";
    const runtimeAlly = (state.vsManualState?.ally_states || []).find((row) => Number(row.pos) === Number(pos));
    normalizeManualTarget(card);
    return `
      <div class="manual-control-card" data-manual-control-pos="${pos}">
        <div class="manual-control-head"><b>我方${pos} ${escapeHtml(name)}</b></div>
        <div class="hint">当前P：<b>${numberText(runtimeAlly?.spirit ?? $('[data-field="initial_spirit"]', card)?.value ?? 0)}</b></div>
        <div class="hint">技能执行：<span data-role="skill_order_view">${state.vsManualSkillLog.filter((item) => item.startsWith(`我方${pos}:`)).map((item) => item.replace(/^.* (技能\d+)$/, "$1")).join(" → ") || "未释放"}</span></div>
        <div class="manual-control-row">
          <button type="button" class="small secondary" data-manual-target="${pos}">目标敌人 <span data-manual-target-view="${pos}">${$('[data-field="target_enemy_pos"]', card)?.value || 0}</span></button>
          <button type="button" class="small secondary" data-manual-shield="${pos}">开盾 <span data-manual-shield-view="${pos}">${$('[data-field="shield_open_count"]', card)?.value || 0}</span></button>
          <button type="button" class="small secondary" data-manual-spirit="${pos}">开P <span data-manual-spirit-view="${pos}">${$('[data-field="spirit_level"]', card)?.value || 0}</span></button>
        </div>
        <div class="manual-attack-row">${VS_MANUAL_ATTACKS.map(([value, label], idx) => {
          const active = activeAttack === value && (value !== "1" || idx === 2) && (value !== "2" || idx === 3);
          return `<button type="button" class="small secondary ${active ? "active" : ""}" data-manual-attack="${value}">${label}</button>`;
        }).join("")}</div>
        <div class="manual-control-row">${[0, 1, 2].map((skill) => {
          const key = `${pos}:${skill}`;
          const rawCd = card._skillCooldowns?.[skill] || 0;
          const used = state.vsManualSkillUsed[key];
          const pending = state.vsManualPendingSkills?.[key];
          return `<button type="button" class="small secondary ${used ? "cooldown" : ""} ${pending ? "active" : ""}" ${used ? "disabled" : ""} data-manual-skill="${skill}">${used ? `cd${rawCd || "?"}` : `技能${skill + 1}`}</button>`;
        }).join("")}</div>
      </div>
    `;
  }).join("") || '<div class="card hint">无启用我方角色。</div>';
  $$("[data-manual-control-pos]", root).forEach((box) => {
    const card = $(`#vsManualAllySlots .vs-ally-slot[data-pos="${box.dataset.manualControlPos}"]`);
    $('[data-manual-target]', box)?.addEventListener("click", () => cycleManualTarget(card, `[data-manual-target-view="${box.dataset.manualControlPos}"]`));
    $('[data-manual-shield]', box)?.addEventListener("click", () => cycleManualNumber(card, "shield_open_count", maxManualShieldOpen(card), `[data-manual-shield-view="${box.dataset.manualControlPos}"]`));
    $('[data-manual-spirit]', box)?.addEventListener("click", () => cycleManualNumber(card, "spirit_level", 3, `[data-manual-spirit-view="${box.dataset.manualControlPos}"]`));
    $$("[data-manual-attack]", box).forEach((btn) => btn.addEventListener("click", () => setManualAttack(card, btn.dataset.manualAttack, btn)));
    $$("[data-manual-skill]", box).forEach((btn) => btn.addEventListener("click", () => togglePendingManualSkill(card, Number(btn.dataset.manualSkill), btn)));
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

function syncManualEnemyCardsAfterSolve(data) {
  return data;
}

function manualEnemyHasNextPhase(pos) {
  const card = $(`.enemy-slot[data-pos="${pos}"]`);
  const currentPhase = Number(card?._enemyPhaseIndex || 0);
  const phases = card?._enemyPhases || [];
  return phases.length > currentPhase + 1;
}

function removeDeadFinalManualEnemies(data) {
  const removed = [];
  const alive = (data.enemy_states || []).filter((row) => {
    const dead = Number(row.remaining_hp ?? row.hp ?? 0) <= 0;
    if (!dead || manualEnemyHasNextPhase(row.pos)) return true;
    removed.push(row.pos);
    return false;
  });
  if (!removed.length) return data;
  const next = { ...data, enemy_states: alive };
  next.state = { ...(data.state || {}), enemy_states: alive };
  renderOverview();
  return next;
}

function buildInitialVsManualResult(payload) {
  const enemyStates = Object.entries(payload.enemy_slots || {}).map(([pos, slot]) => {
    if (!slot?.enabled) return null;
    const card = $(`.enemy-slot[data-pos="${pos}"]`);
    return {
      side: "enemy",
      pos: Number(pos),
      character_id: slot.character_id,
      name: $('[data-role="name"]', card)?.textContent || slot.character_id || "-",
      hp: Number(slot.hp || 0),
      hp_max: Number(slot.hp || 0),
      current_hp: Number(slot.hp || 0),
      damage: 0,
      remaining_hp: Number(slot.hp || 0),
      barrier_count: Number(slot.barrier_count || 0),
      barrier_types: slot.barrier_types || [],
      quality: slot.quality || [],
      buffs: slot.buffs || [],
      buffs_text: [],
      enemy_skill_effects: slot.enemy_skill_effects || [],
      enemy_skill_effects_text: [],
    };
  }).filter(Boolean);
  const allyStates = Object.entries(payload.ally_slots || {}).map(([pos, slot]) => {
    if (!slot?.enabled) return null;
    const card = $(`#vsManualAllySlots .vs-ally-slot[data-pos="${pos}"]`);
    return {
      side: "ally",
      pos: Number(pos),
      character_id: slot.character_id,
      name: $('[data-role="name"]', card)?.textContent || slot.character_id || "-",
      damage: 0,
      barrier_count: Number(slot.barrier_count || 0),
      barrier_types: [],
      attack_type: slot.attack_type,
      spirit: Number(slot.initial_spirit || 0),
      spirit_level: slot.spirit_level,
      shield_open_count: slot.shield_open_count,
      buffs: slot.buffs || [],
      buffs_text: [],
    };
  }).filter(Boolean);
  return {
    turn: 1,
    total_damage: 0,
    yang_damage_total: 0,
    yin_damage_total: 0,
    ally_states: allyStates,
    enemy_states: enemyStates,
    attack_order: allyStates.map((row) => ({ pos: row.pos, character_id: row.character_id, name: row.name, speed: 0 })),
    attack_steps: [],
    state: { turn: 1, ally_states: allyStates, enemy_states: enemyStates },
  };
}

function buildVsManualBoardResultFromCards(baseState = null) {
  const payload = buildVsManualPayload();
  const board = buildInitialVsManualResult(payload);
  const previousEnemies = new Map((baseState?.enemy_states || []).map((row) => [Number(row.pos), row]));
  const previousAllies = new Map((baseState?.ally_states || []).map((row) => [Number(row.pos), row]));
  board.turn = Number(baseState?.turn || 1);
  board.enemy_states = board.enemy_states.map((row) => {
    const prev = previousEnemies.get(Number(row.pos));
    if (!prev) return row;
    return {
      ...row,
      hp: Number(prev.hp_max ?? prev.hp ?? row.hp),
      hp_max: Number(prev.hp_max ?? prev.hp ?? row.hp),
      current_hp: Number(prev.current_hp ?? prev.remaining_hp ?? row.current_hp),
      remaining_hp: Number(prev.remaining_hp ?? prev.current_hp ?? row.remaining_hp),
      barrier_count: Number(prev.barrier_count ?? row.barrier_count ?? 0),
      barrier_types: Array.isArray(prev.barrier_types) ? prev.barrier_types.slice() : row.barrier_types,
      buffs: Array.isArray(prev.buffs) ? prev.buffs.map((item) => Array.isArray(item) ? item.slice() : item) : row.buffs,
      buffs_text: Array.isArray(prev.buffs_text) ? prev.buffs_text.slice() : row.buffs_text,
      is_break_all: Boolean(prev.is_break_all ?? row.is_break_all),
      damage: 0,
    };
  });
  board.ally_states = board.ally_states.map((row) => {
    const prev = previousAllies.get(Number(row.pos));
    return {
      ...row,
      spirit: Number(prev?.spirit ?? row.spirit ?? 0),
      barrier_count: Number(prev?.barrier_count ?? row.barrier_count ?? 0),
      barrier_types: Array.isArray(prev?.barrier_types) ? prev.barrier_types.slice() : row.barrier_types,
      buffs: Array.isArray(prev?.buffs) ? prev.buffs.map((item) => Array.isArray(item) ? item.slice() : item) : row.buffs,
      buffs_text: Array.isArray(prev?.buffs_text) ? prev.buffs_text.slice() : row.buffs_text,
      damage: 0,
      equipment_name: prev?.equipment_name || "",
    };
  });
  board.state = { turn: board.turn, ally_states: board.ally_states, enemy_states: board.enemy_states };
  return board;
}

function applyManualRuntimeToPayload(payload) {
  const runtime = state.vsManualState || {};
  (runtime.ally_states || []).forEach((row) => {
    const slot = payload.ally_slots?.[row.pos] || payload.ally_slots?.[String(row.pos)];
    if (!slot) return;
    slot.initial_spirit = Math.min(5.0, Number(row.spirit ?? slot.initial_spirit ?? 0));
    slot.barrier_count = Number(row.barrier_count ?? slot.barrier_count ?? 0);
    slot.barrier_types = Array.isArray(row.barrier_types) ? row.barrier_types.slice() : [];
    slot.buffs = Array.isArray(row.buffs) ? row.buffs.map((item) => Array.isArray(item) ? item.slice() : item) : [];
  });
  (runtime.enemy_states || []).forEach((row) => {
    const slot = payload.enemy_slots?.[row.pos] || payload.enemy_slots?.[String(row.pos)];
    if (!slot) return;
    slot.hp = Math.max(0, Number(row.remaining_hp ?? row.current_hp ?? slot.hp ?? 0));
    slot.barrier_count = Number(row.barrier_count ?? slot.barrier_count ?? 0);
    slot.barrier_types = Array.isArray(row.barrier_types) ? row.barrier_types.slice() : [];
    slot.buffs = Array.isArray(row.buffs) ? row.buffs.map((item) => Array.isArray(item) ? item.slice() : item) : [];
    if (Number(slot.hp || 0) <= 0) slot.enabled = false;
  });
  return payload;
}

async function refreshRuntimeBuffTexts() {
  const rows = [...(state.vsManualState?.ally_states || []), ...(state.vsManualState?.enemy_states || [])];
  await Promise.all(rows.map(async (row) => {
    const buffs = Array.isArray(row.buffs) ? row.buffs : [];
    row.buffs_text = await Promise.all(buffs.map(async (buff) => {
      if (!Array.isArray(buff) || Number(buff[0] || 0) <= 0) return "";
      const params = new URLSearchParams({
        buff_id: buff[0] || 0,
        sub_id: buff[1] || 0,
        target: row.side === "enemy" ? 4 : 1,
        duration: buff[2] || 0,
        value: buff[3] || 0,
      });
      try {
        const data = await api(`/api/effect-format?${params}`);
        return data.text || `[${buff.join(",")}]`;
      } catch {
        return `[${buff.join(",")}]`;
      }
    }));
  }));
}

function tickBuffDurations() {
  $$(".ally-slot [data-role='buffs'], .vs-ally-slot [data-role='buffs'], .enemy-slot [data-role='buffs']").forEach((root) => {
    $$(".buff-row", root).forEach((row) => {
      const input = $('[data-field="duration"]', row);
      if (!input) return;
      const current = Number(input.value || 0);
      if (current <= 0) return;
      const next = current - 1;
      if (next <= 0) {
        row.remove();
      } else {
        input.value = next;
        updateEffectDescription(row, false).catch(() => {});
      }
    });
  });
}

function tickRuntimeBuffRows(rows = []) {
  return (rows || []).map((row) => {
    const buffs = (row.buffs || []).map((buff) => {
      if (!Array.isArray(buff)) return buff;
      const next = buff.slice();
      const duration = Number(next[2] || 0);
      if (duration > 0) next[2] = duration - 1;
      return next;
    }).filter((buff) => !Array.isArray(buff) || Number(buff[2] || 0) !== 0);
    return { ...row, buffs, buffs_text: [] };
  });
}

function hasEnabledEnemySlot() {
  return $$(".enemy-slot").some((card) => {
    return $('[data-field="enabled"]', card)?.checked && String($('[data-field="character_id"]', card)?.value || "").trim();
  });
}

function currentEnemySlotsMatchVsPreset(preset) {
  const expected = (preset?.enemies || []).filter((item) => !item.empty && item.enemy);
  if (!expected.length) return hasEnabledEnemySlot();
  return expected.every((item) => {
    const card = $(`.enemy-slot[data-pos="${item.pos}"]`);
    const enabled = $('[data-field="enabled"]', card)?.checked;
    const charId = String($('[data-field="character_id"]', card)?.value || "").trim();
    return enabled && charId === String(item.enemy?.enemy_id || "");
  });
}

function setVsManualAllyLocked(locked) {
  const root = $("#vsManualAllySlots");
  if (!root) return;
  root.classList.toggle("locked", Boolean(locked));
  $$("input, select, button, textarea", root).forEach((el) => {
    el.disabled = Boolean(locked);
  });
  const importBtn = $("#vsManualImportBtn");
  if (importBtn) importBtn.disabled = Boolean(locked);
}

function setVsManualTab(id) {
  $$("#vsManualSubtabs [data-vs-manual-tab]").forEach((btn) => btn.classList.toggle("active", btn.dataset.vsManualTab === id));
  $$("[data-vs-manual-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.vsManualPanel === id));
  if (typeof renderModuleSidebar === "function") renderModuleSidebar("vs-manual");
}

async function prepareVsManualFieldBuffs() {
  $("#calcMode").value = "vs";
  updateModeUI();
  if (state.activeVsPreset && !currentEnemySlotsMatchVsPreset(state.activeVsPreset)) {
    await applyVsPreset(state.activeVsPreset);
  }
  renderVsManualFieldPresetTable();
  refreshVsEnemyStatsFromTags();
  renderVsManualEnemySlots();
  setVsManualTab("enemy");
}

async function importVsManualConfig() {
  $("#calcMode").value = "vs";
  updateModeUI();
  if (state.activeVsPreset && !currentEnemySlotsMatchVsPreset(state.activeVsPreset)) {
    await applyVsPreset(state.activeVsPreset);
  }
  if (state.vsManualInitialPayload && state.vsManualPhase !== "idle") {
    setVsManualTab("turn");
    return;
  }
  const payload = buildVsManualPayload();
  Object.values(payload.ally_slots || {}).forEach((slot) => {
    if (slot) slot.skill_order_text = "";
  });
  Object.values(payload.enemy_slots || {}).forEach((slot) => {
    if (slot) {
      slot.buffs = [];
      slot.barrier_types = [];
    }
  });
  $$("#vsManualAllySlots .vs-ally-slot [data-field='skill_order_text']").forEach((input) => (input.value = ""));
  $$(".enemy-slot [data-role='buffs']").forEach((root) => (root.innerHTML = ""));
  $$(".enemy-slot").forEach((card) => (card._manualBarrierTypes = []));
  state.vsManualInitialPayload = cloneManualPayload(payload);
  state.vsManualPayload = payload;
  const initialResult = buildInitialVsManualResult(payload);
  state.vsManualState = initialResult.state;
  state.vsManualPhase = "ready";
  state.vsManualSkillUsed = {};
  state.vsManualPendingSkills = {};
  state.vsManualSkillLog = [];
  $$("#vsManualAllySlots .vs-ally-slot").forEach((card) => {
    card._skillCooldowns = {};
  });
  renderVsManualControls();
  updateVsManualButtons();
  renderVsManualResult(initialResult);
  setVsManualAllyLocked(true);
  setVsManualTab("turn");
}

function updateVsManualButtons() {
  const calcBtn = $("#vsManualCalcBtn");
  const nextBtn = $("#vsManualNextBtn");
  const resetBtn = $("#vsManualResetBtn");
  if (!calcBtn || !nextBtn) return;
  const phase = state.vsManualPhase || "idle";
  calcBtn.disabled = phase === "calculated";
  nextBtn.disabled = phase !== "calculated";
  if (resetBtn) resetBtn.disabled = phase === "idle";
  setVsManualAllyLocked(phase !== "idle");
}

function resetVsManualSimulation() {
  state.vsManualPayload = null;
  state.vsManualInitialPayload = null;
  state.vsManualState = null;
  state.vsManualPhase = "idle";
  state.vsManualSkillUsed = {};
  state.vsManualPendingSkills = {};
  state.vsManualSkillLog = [];
  $$("#vsManualAllySlots .vs-ally-slot").forEach((card) => {
    card._skillCooldowns = {};
    $('[data-field="skill_order_text"]', card).value = "";
    updateAllySkillOrder(card);
  });
  const controls = $("#vsManualControls");
  if (controls) controls.innerHTML = "";
  const result = $("#vsManualResult");
  if (result) result.innerHTML = "";
  setVsManualAllyLocked(false);
  updateVsManualButtons();
  setVsManualTab("ally");
}

function renderBarrierIcons(count, abnormal = []) {
  const n = Math.max(0, Math.min(10, Number(count || 0)));
  const abnormalList = Array.isArray(abnormal) ? abnormal : [];
  return `<span class="barrier-icons">${Array.from({ length: n }, (_, idx) => `<img src="${barrierIconUrl(abnormalList[idx] || 0)}" alt="盾">`).join("") || "-"}</span>`;
}

function manualBuffLines(row) {
  if (window.LWManualBuffs?.lines) return window.LWManualBuffs.lines(row);
  const lines = [...(row.buffs_text || [])].map((item) => String(item || "").trim()).filter(Boolean);
  return lines.length ? lines : ["-"];
}

function manualBuffText(row) {
  return window.LWManualBuffs?.text ? window.LWManualBuffs.text(row) : manualBuffLines(row).join("\n");
}

function manualBuffLineHtml(row) {
  return window.LWManualBuffs?.html ? window.LWManualBuffs.html(row, escapeHtml) : manualBuffLines(row).map((line) => `<div>${escapeHtml(line)}</div>`).join("");
}

function manualEnemyMetaText(row) {
  const card = $(`.enemy-slot[data-pos="${row.pos}"]`);
  const phases = card?._enemyPhases || [];
  const current = Number(card?._enemyPhaseIndex || 0);
  const remain = phases.length ? Math.max(1, phases.length - current) : 1;
  const cd = Number(card?._manualSpellCd ?? card?._enemyExtra?.spell_gauge ?? 0);
  return `血条*${remain} | 符卡CD ${cd}`;
}

function renderVsManualResult(data) {
  updateVsManualButtons();
  const order = (data.attack_order || []).map((row) => `位置${row.pos}:${escapeHtml(row.name || row.character_id || "-")}`).join(" → ") || "-";
  const skillOrder = state.vsManualSkillLog.length ? state.vsManualSkillLog.join(" → ") : "本回合未手动释放技能";
  const allies = (data.ally_states || []).map((row) => `
    <button type="button" class="manual-unit-card" data-manual-kind="ally" data-manual-pos="${row.pos}" data-buffs="${escapeHtml(manualBuffText(row))}">
      <img src="${avatarUrl(row.character_id)}" onerror="this.src='/assets/avatars/S0.png'">
      <span><b>我方${row.pos}</b><small>${escapeHtml(row.name || row.character_id || "-")}</small><small>P ${numberText(row.spirit ?? 0)}</small><small>伤害 ${numberText(row.damage)}</small><small>${renderBarrierIcons(row.barrier_count, row.barrier_types || [])}</small></span>
    </button>
  `).join("");
  const enemyCards = (data.enemy_states || []).map((row) => `
    <button type="button" class="manual-unit-card" data-manual-kind="enemy" data-manual-pos="${row.pos}" data-buffs="${escapeHtml(manualBuffText(row))}">
      <span class="avatar-stack"><img src="${avatarUrl(row.character_id)}" onerror="this.src='/assets/avatars/S0.png'">${row.is_break_all ? '<em class="fb-badge">FB</em>' : ""}</span>
      <span><b>敌方${row.pos}</b><small>${escapeHtml(row.name || row.character_id || "-")}</small><small>${manualEnemyMetaText(row)}</small><small>HP ${numberText(row.remaining_hp)} / ${numberText(row.hp_max ?? row.hp)}</small><small>${renderBarrierIcons(row.barrier_count, row.barrier_types || [])}</small><small class="manual-quality-line">气质 ${renderQualityIconRow(row.quality || [])}</small></span>
    </button>
  `).join("");
  const enemies = (data.enemy_states || []).map((row) => `
    <tr>
      <td>敌方${row.pos}</td><td>${escapeHtml(row.name || row.character_id || "-")}</td><td>${numberText(row.remaining_hp)} / ${numberText(row.hp_max ?? row.hp)}</td><td>${numberText(row.damage)}</td><td>${row.is_break_all ? "FB" : ""}</td><td>${renderBarrierIcons(row.barrier_count, row.barrier_types || [])}</td>
    </tr>
  `).join("");
  const steps = (data.attack_steps || []).map((row) => `
    <tr><td>${escapeHtml(row.attacker_name || `我方${row.attacker_pos}`)}</td><td>敌方${row.enemy_pos}</td><td>${numberText(row.damage)}</td><td>${numberText(row.remaining_hp)}</td></tr>
  `).join("");
  const buffs = [...(data.ally_states || []), ...(data.enemy_states || [])].map((row) => `
    <div class="manual-buff-group">
      <b>${row.side === "ally" ? "我方" : "敌方"}${row.pos}</b>
      ${manualBuffLineHtml(row)}
    </div>
  `).join("");
  $("#vsManualResult").innerHTML = `
    <div class="summary-grid">
      <div class="summary-card">回合<strong>${numberText(data.turn || 1)}</strong></div>
      <div class="summary-card">总伤害<strong>${numberText(data.total_damage)}</strong></div>
      <div class="summary-card">复灵ID<strong>${escapeHtml(state.activeVsPreset?.vs_id || "-")}</strong></div>
    </div>
    <div class="manual-board">
      <div class="manual-side"><h3>敌方</h3>${enemyCards || '<p class="hint">无启用敌方</p>'}</div>
      <div class="manual-focus"><b>攻击顺序</b><p>${order}</p><b>技能执行顺序</b><p>${escapeHtml(skillOrder)}</p><div data-role="manual-buff-focus" class="compact-info-line">点击任意角色查看 Buff。</div></div>
      <div class="manual-side"><h3>我方</h3>${allies || '<p class="hint">无启用我方</p>'}</div>
    </div>
    <div class="table-wrap"><table><thead><tr><th>位置</th><th>角色名称</th><th>HP</th><th>受到伤害</th><th>完全击破</th><th>盾</th></tr></thead><tbody>${enemies || '<tr><td colspan="6">无启用敌方</td></tr>'}</tbody></table></div>
    <div class="table-wrap"><table><thead><tr><th>我方角色</th><th>目标</th><th>本次伤害</th><th>攻击后敌方剩余HP</th></tr></thead><tbody>${steps || '<tr><td colspan="4">暂无攻击步骤</td></tr>'}</tbody></table></div>
    <details class="card"><summary>运行 Buff 摘要</summary>${buffs || '<p class="hint">无</p>'}</details>
  `;
  $$("#vsManualResult [data-manual-kind]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const focus = $('[data-role="manual-buff-focus"]', $("#vsManualResult"));
      if (focus) {
        const lines = String(btn.dataset.buffs || "-").split("\n").filter(Boolean);
        focus.innerHTML = `<b>${btn.dataset.manualKind === "ally" ? "我方" : "敌方"}${btn.dataset.manualPos}</b>${lines.map((line) => `<div>${escapeHtml(line)}</div>`).join("")}`;
      }
    });
  });
}

async function solveVsManual() {
  if (!state.vsManualPayload) await importVsManualConfig();
  if (state.vsManualPhase === "calculated") return;
  state.vsManualPayload = buildVsManualPayload();
  syncManualEnemyHpBeforeSolve(state.vsManualPayload);
  const data = await api("/api/vs-manual-solve", {
    method: "POST",
    body: JSON.stringify({ ...(state.vsManualPayload || buildVsManualPayload()), manual_state: state.vsManualState || {} }),
  });
  syncManualEnemyCardsAfterSolve(data);
  const filtered = removeDeadFinalManualEnemies(data);
  state.vsManualState = filtered.state || null;
  state.vsManualPhase = "calculated";
  renderVsManualResult(filtered);
}

function advanceVsManualTurn() {
  if (!state.vsManualState) {
    $("#vsManualResult").innerHTML = '<div class="card hint">请先计算本回合。</div>';
    return;
  }
  const next = { ...state.vsManualState, turn: Number(state.vsManualState.turn || 1) + 1 };
  const turnLogs = [];
  next.enemy_states = (next.enemy_states || []).map((row) => {
    const remaining = Math.max(0, Number(row.remaining_hp ?? row.hp ?? 0));
    const card = $(`.enemy-slot[data-pos="${row.pos}"]`);
    const currentPhase = Number(card?._enemyPhaseIndex || 0);
    const phases = card?._enemyPhases || [];
    if (remaining <= 0 && phases.length > currentPhase + 1) {
      const nextBtn = $(`[data-phase-idx="${currentPhase + 1}"]`, card);
      if (nextBtn) nextBtn.click();
      const nextPhase = phases[currentPhase + 1] || {};
      const stats = applyVsEnemyHpFactor(interpolateVsStats(nextPhase, Number($("#vsLevel")?.value || 100)));
      const barrierCount = Number(nextPhase.barrier_count ?? 9);
      const hpInput = $('[data-field="hp"]', card);
      if (hpInput) hpInput.value = Number(stats.hp || row.hp || 0);
      const barrierInput = $('[data-field="barrier_count"]', card);
      if (barrierInput) barrierInput.value = barrierCount;
      if (card) card._manualSpellCd = Number(nextPhase.spell_gauge ?? 0);
      if (card) card._maxBarrierCount = barrierCount;
      if (card) card._manualBarrierTypes = [];
      turnLogs.push(`敌方${row.pos}进入下一血条，应用下一阶段 EX/技能接口。`);
      return { ...row, hp: Number(stats.hp || row.hp || 0), hp_max: Number(stats.hp || row.hp || 0), current_hp: Number(stats.hp || row.hp || 0), damage: 0, remaining_hp: Number(stats.hp || row.hp || 0), barrier_count: barrierCount, barrier_types: [], is_break_all: false, phase_advanced: true };
    }
    if (card) {
      const hpInput = $('[data-field="hp"]', card);
      if (hpInput) hpInput.value = remaining;
      if (remaining <= 0) {
        const enabled = $('[data-field="enabled"]', card);
        if (enabled) enabled.checked = false;
        card.classList.add("collapsed");
        turnLogs.push(`敌方${row.pos}当前血条清空且无下一血条，移出战斗。`);
      } else {
        const baseCd = Number(card._enemyExtra?.spell_gauge ?? 0);
        const currentCd = Number(card._manualSpellCd ?? baseCd);
        if (currentCd > 0) {
          card._manualSpellCd = currentCd - 1;
        }
        if (card._manualSpellCd === 0 && baseCd > 0) {
          turnLogs.push(`敌方${row.pos}符卡CD归零：符卡效果接口已触发，占位等待后续实装插队释放。`);
          card._manualSpellCd = baseCd;
        }
      }
      card._manualBarrierTypes = Array.isArray(row.barrier_types) ? row.barrier_types.slice() : [];
    }
    return { ...row, hp: row.hp_max ?? row.hp, hp_max: row.hp_max ?? row.hp, current_hp: remaining, damage: 0, remaining_hp: remaining };
  });
  next.ally_states = (next.ally_states || []).map((row) => {
    return {
      ...row,
      damage: 0,
      spirit: Math.min(5.0, Number(row.spirit || 0)),
      barrier_count: Number(row.barrier_count || 0),
      barrier_types: Array.isArray(row.barrier_types) ? row.barrier_types.slice(0, Number(row.barrier_count || 0)) : [],
      shield_open_count: 0,
    };
  });
  const filteredNext = removeDeadFinalManualEnemies({ ...next, enemy_states: next.enemy_states, state: next });
  next.enemy_states = filteredNext.enemy_states || [];
  next.ally_states = tickRuntimeBuffRows(next.ally_states);
  next.enemy_states = tickRuntimeBuffRows(next.enemy_states);
  state.vsManualState = next;
  state.vsManualPhase = "ready";
  state.vsManualSkillUsed = {};
  $$("#vsManualAllySlots .vs-ally-slot").forEach((card) => {
    card._skillCooldowns = card._skillCooldowns || {};
    Object.keys(card._skillCooldowns).forEach((skill) => {
      card._skillCooldowns[skill] = Math.max(0, Number(card._skillCooldowns[skill] || 0) - 1);
      if (card._skillCooldowns[skill] > 0) {
        state.vsManualSkillUsed[`${card.dataset.pos}:${skill}`] = true;
      }
    });
  });
  state.vsManualPendingSkills = {};
  state.vsManualSkillLog = [];
  renderVsManualControls();
  renderVsManualResult({ ...next, total_damage: 0, yang_damage_total: 0, yin_damage_total: 0 });
  const focus = $('[data-role="manual-buff-focus"]', $("#vsManualResult"));
  if (focus) focus.textContent = turnLogs.length ? turnLogs.join(" / ") : "过回合：buff 持续回合 -1，敌方符卡 CD 接口保留。";
}
