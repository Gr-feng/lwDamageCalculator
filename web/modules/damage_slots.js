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
  $('[data-load-character]', card).addEventListener("click", () => resolveSlotCharacterBySelection(card).catch((err) => alert(err.message)));
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

function renderSlotTribeText(card) {
  const root = $('[data-role="tribe_desc"]', card);
  if (!root) return;
  const value = $('[data-field="tribe_text"]', card)?.value || "";
  root.textContent = describeTribes(value);
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
      <div class="subsection"><div class="subsection-title quality-title-inline"><h4>气质</h4><div data-role="quality"></div><button type="button" class="small secondary" data-reset-quality>归零</button></div></div>
      <div class="subsection"><label>Tribe<input data-field="tribe_text" placeholder="例如 1,2,3"></label><small class="tribe-desc" data-role="tribe_desc">-</small></div>
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
    $('[data-field="tribe_text"]', card).addEventListener("input", () => renderSlotTribeText(card));
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

async function getRecommendedEquipmentForCard(card) {
  const charId = $('[data-field="character_id"]', card)?.value || "";
  return api(`/api/recommended?character_id=${encodeURIComponent(charId)}`);
}

async function fillRecommendedEquipmentForCard(card) {
  const rec = await getRecommendedEquipmentForCard(card);
  for (const row of $$(".equipment-row", card)) {
    $('[data-field="equipment_id"]', row).value = rec[row.dataset.slot] || "";
    await updateEquipmentSummary(row);
  }
  return rec;
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
        <label>初始p点<input data-field="initial_spirit" value="1.0"></label>
        <label>初始护盾数<input data-field="barrier_count" value="5"></label>
        <label>目标敌人<input data-field="target_enemy_pos" value="${state.boot.defaults.target_enemy_pos}"></label>
        <label>开p数<input data-field="spirit_level" type="number" min="0" max="3" step="1" value="0"></label>
        <label>开盾数量<input data-field="shield_open_count" type="number" min="0" max="3" step="1" value="0"></label>
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
        const rec = await getRecommendedEquipmentForCard(card);
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
    recAll.addEventListener("click", () => fillRecommendedEquipmentForCard(card).catch((err) => alert(err.message)));
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

function bindVsManualAllyCard(card) {
  hydrateCharacterLoader(card, "slot");
  $('[data-load-character-id]', card).addEventListener("click", () => resolveSlotCharacter(card, $(`[data-role="slot_id_query"]`, card)?.value || "").catch((err) => alert(err.message)));
  $('[data-load-character]', card).addEventListener("click", () => resolveSlotCharacterBySelection(card).catch((err) => alert(err.message)));
  $('[data-field="character_id"]', card)?.addEventListener("change", () => resolveSlotCharacter(card).catch(() => {}));
  $('[data-field="enabled"]', card)?.addEventListener("change", () => {
    const enabled = $('[data-field="enabled"]', card).checked;
    card.classList.toggle("collapsed", !enabled);
    const collapseBtn = $('[data-collapse-card]', card);
    if (collapseBtn) collapseBtn.textContent = card.classList.contains("collapsed") ? "展开" : "折叠";
  });
  $('[data-collapse-card]', card)?.addEventListener("click", (event) => {
    card.classList.toggle("collapsed");
    event.currentTarget.textContent = card.classList.contains("collapsed") ? "展开" : "折叠";
  });
}

function renderVsManualAllySlots() {
  const root = $("#vsManualAllySlots");
  if (!root) return;
  root.innerHTML = "";
  for (let pos = 0; pos < 3; pos += 1) {
    const card = document.createElement("article");
    card.className = "slot-card vs-ally-slot";
    card.dataset.pos = String(pos);
    card.innerHTML = `
      ${makeCharacterHeader("复灵我方 ", pos)}
      <div class="slot-body">
      <div class="form-grid">
        <label>角色ID<input data-field="character_id" value="${state.boot.defaults.ally_id + pos}"></label>
        <label>初始p点<input data-field="initial_spirit" value="1.0"></label>
        <label>初始护盾数<input data-field="barrier_count" value="5"></label>
        <label>目标敌人<input data-field="target_enemy_pos" value="${state.boot.defaults.target_enemy_pos}"></label>
        <label>开p数<input data-field="spirit_level" value="0"></label>
        <label>开盾数量<input data-field="shield_open_count" value="0"></label>
        <label>攻击类型<select data-field="attack_type">${ATTACK_OPTIONS.map(([v, t]) => `<option value="${v}" ${v === "5" ? "selected" : ""}>${t}</option>`).join("")}</select></label>
        <input data-field="skill_order_text" type="hidden">
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
    bindVsManualAllyCard(card);
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
