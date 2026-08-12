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
  return window.LWCharacterQuery.search({
    $, $$, api, state, selectedFilterValues, renderTable: renderCharacterTable,
  });
}

function renderCharacterTable(rows) {
  return window.LWCharacterQuery.renderTable(rows, {
    $, $$, state, buildTable, setQueryTab, loadCharacterDetail, showCharacterDataPic, avatarUrl, dataPicUrl, attributeIconUrl,
  });
}

async function searchEquipment() {
  return window.LWEquipmentQuery.search({
    $, $$, api, state, selectedFilterValues, renderTable: renderEquipmentTable,
  });
}

function renderEquipmentTable(rows) {
  return window.LWEquipmentQuery.renderTable(rows, { $, state, buildTable });
}

function filterCharacterGalleryRows(rows, presetMap, options = {}) {
  return window.LWRoleGallery?.filterRows
    ? window.LWRoleGallery.filterRows(rows, presetMap, state.roleGalleryFilters || {}, options.useRoleFilters)
    : rows;
}

function renderCharacterGallery(container, presetMap, onPick, withOwnedFlags = true, options = {}) {
  if (!window.LWRoleGallery?.render) return;
  window.LWRoleGallery.render(container, {
    rows: state.boot.character_options || [],
    presetMap,
    filters: state.roleGalleryFilters || {},
    useRoleFilters: options.useRoleFilters,
    withOwnedFlags,
    avatarUrl,
    escapeHtml,
    onPick,
  });
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

function renderQualityIconRow(quality = []) {
  return window.LWVsDisplay?.qualityIconRow
    ? window.LWVsDisplay.qualityIconRow(quality, state.boot.quality_labels, temperamentIconUrl)
    : "-";
}

function describeTribes(text) {
  return window.LWVsDisplay?.describeTribes
    ? window.LWVsDisplay.describeTribes(text, state.boot.tribe_options)
    : String(text || "-");
}

function renderInlineAttributeIcons(ids = []) {
  return `<span class="element-icons attack-inline-icons">${(ids || []).map((id) => `<img src="${attributeIconUrl(id)}" title="${state.boot.element_labels?.[id] || id}">`).join("") || "-"}</span>`;
}

function renderInlineBulletIcons(ids = []) {
  return `<span class="bullet-type-icons attack-inline-icons">${(ids || []).map((id) => `<img src="${bulletTypeIconUrl(id, state.boot.bullet_labels?.[id])}" title="${state.boot.bullet_labels?.[id] || id}" onerror="this.style.display='none'">`).join("") || "-"}</span>`;
}

function renderKillerPairs(pairs = []) {
  return (pairs || []).length ? pairs.map((item) => `${escapeHtml(item.id)} ${escapeHtml(item.name || item.id)}`).join(" / ") : "-";
}

function renderSpiritCompact(section, summary = {}) {
  const prefix = String(section.target_label || "").startsWith("群") ? "群" : "单";
  const values = summary.spirit_expectation_values || [];
  return `${prefix}*${values.length ? values.map((value) => escapeHtml(value)).join("-") : "0-0-0-0"}`;
}

function renderAttackSummaryCard(section) {
  const summary = section.summary || {};
  return `
    <div class="attack-summary-card">
      <h4>${escapeHtml(section.title)}-${escapeHtml(section.target_label || "")}-${escapeHtml(summary.name || section.name || "-")}</h4>
      <div class="attack-icon-line"><b>属性：</b>${renderInlineAttributeIcons(summary.element_ids || [])}<b>弹种：</b>${renderInlineBulletIcons(summary.bullet_type_ids || [])}</div>
      <p><b>特攻：</b>${renderKillerPairs(summary.killer_pairs || [])}</p>
      <p><b>回灵率：</b>${escapeHtml(summary.power_rate || "0")}</p>
      <p><b>灵力回复期望：</b>${renderSpiritCompact(section, summary)}</p>
      <p><b>攻击前Buff：</b>${escapeHtml(summary.effect_before || "-")}</p>
      <p><b>攻击后Buff：</b>${escapeHtml(summary.effect_after || "-")}</p>
    </div>
  `;
}

function renderAttackOverview(sections) {
  return `<div class="attack-summary-grid">${sections.map(renderAttackSummaryCard).join("")}</div>`;
}

function renderAttackDetail(section) {
  const summary = section.summary || {};
  const orderRows = (section.boost_orders || []).map((row) => `
    <div><b>${row.spirit_level}P</b><span>${escapeHtml(row.order || "-")}</span></div>
  `).join("");
  const hits = (section.hits || []).map((hit) => `
    <div class="attack-hit-card boost-bg-${Number(hit.boost_required || 0)}" style="--segment-bg: url('${bulletSegmentUrl(hit.element_label, hit.yinyang_label)}')">
      <div class="bullet-icon-slot">
        <img src="${bulletTypeIconUrl(hit.bullet_type_id, hit.bullet_label)}" onerror="this.style.display='none'">
      </div>
      <div class="attack-hit-lines">
        <p><b>第${escapeHtml(hit.segment)}段</b> ${escapeHtml(hit.shot_name || "-")} | ${escapeHtml(hit.element_label || "-")}|${escapeHtml(hit.bullet_label || "-")}|${escapeHtml(hit.yinyang_label || "-")} | 需求 ${escapeHtml(hit.boost_required)}P</p>
        <p>威力 ${escapeHtml(hit.power)} | Hit ${escapeHtml(hit.hit_count)} | 总威力 ${escapeHtml(hit.total_power)} | 命中率 ${escapeHtml(hit.accuracy)}% | 会心率 ${escapeHtml(hit.critical)}%</p>
        <p>特攻：${renderKillerPairs(hit.killer_pairs || [])}</p>
        <p>特性：${escapeHtml(hit.traits || "-")} | 效果：${escapeHtml(hit.buffs || "-")}</p>
      </div>
    </div>
  `).join("");
  return `
    <div class="attack-detail-panel">
      ${renderAttackSummaryCard(section)}
      <div class="attack-order-grid">${orderRows}</div>
      <div class="attack-hit-grid">${hits || "<p class=\"hint\">无 hit 详情。</p>"}</div>
    </div>
  `;
}

function renderAttackTabContent(sections, activeKey = "overview") {
  if (activeKey === "overview") return renderAttackOverview(sections);
  const section = sections.find((item) => String(item.attack_type) === String(activeKey));
  return section ? renderAttackDetail(section) : renderAttackOverview(sections);
}

function bindAttackDetailTabs(sections) {
  const root = $("#characterAttackDetail");
  if (!root) return;
  $$("[data-attack-detail-tab]", root).forEach((btn) => {
    btn.addEventListener("click", () => {
      $$("[data-attack-detail-tab]", root).forEach((item) => item.classList.toggle("active", item === btn));
      const body = $("#characterAttackBody");
      if (body) body.innerHTML = renderAttackTabContent(sections, btn.dataset.attackDetailTab);
    });
  });
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
  const dataPicButton = data.data_pic_exists
    ? `<button type="button" class="small secondary" data-show-data-pic="${data.char_id}">一图流</button>`
    : `<button type="button" class="small secondary" disabled>一图流</button>`;
  const attackTabButtons = [
    `<button type="button" class="small secondary active" data-attack-detail-tab="overview">总览</button>`,
    ...sections.map((item) => `<button type="button" class="small secondary" data-attack-detail-tab="${escapeHtml(item.attack_type)}">${escapeHtml(item.title)}-${escapeHtml(item.target_label || "")}</button>`),
  ].join("");
  $("#characterDetail").innerHTML = `
    <div class="card character-profile-card">
      <div class="character-profile-grid">
        <div class="profile-avatar-column">
          <img class="avatar-large" src="${avatarUrl(data.char_id)}" onerror="this.src='/assets/avatars/S0.png'">
          <h2>${escapeHtml(data.name)} <small>ID ${escapeHtml(data.char_id)}</small></h2>
          <p>${escapeHtml(data.subname || "")}</p>
          <div class="profile-world-row"><span>世界群：${escapeHtml(data.world_group || "-")}</span>${dataPicButton}</div>
        </div>
        <div class="profile-stat-column">
          <img class="type-icon-large" src="${characterTypeIconUrl(data.type_label)}" onerror="this.style.display='none'">
          <div class="profile-type-row"><span>Type：${escapeHtml(data.type_label || "-")}</span><span>转生：${data.re ? "是" : "否"}</span></div>
          <div class="profile-stat-grid">
            <div><b>HP</b><span>${escapeHtml(data.hp)}</span></div>
            <div><b>速度</b><span>${escapeHtml(data.speed)}</span></div>
            <div><b>阳攻</b><span>${escapeHtml(data.yang_atk)}</span></div>
            <div><b>阴攻</b><span>${escapeHtml(data.yin_atk)}</span></div>
            <div><b>阳防</b><span>${escapeHtml(data.yang_def)}</span></div>
            <div><b>阴防</b><span>${escapeHtml(data.yin_def)}</span></div>
          </div>
          ${renderQualitySummary(data)}
        </div>
        <div class="profile-ability-column">
          <h3>能力</h3>
          <div class="text-lines ability-lines-small">${(data.ability_entries || []).map((line) => `<p>${escapeHtml(line)}</p>`).join("") || "<p>-</p>"}</div>
        </div>
      </div>
    </div>
    <div class="card"><h3>技能</h3><div class="skill-entry-grid">${(data.skill_entries || []).map((item) => `
      <div class="skill-entry-wrapper">
        <div class="skill-icon-slot">${item.icon ? `<img src="${skillIconUrl(item.icon)}" onerror="this.style.visibility='hidden'">` : ""}</div>
        <div>
          <h4>${escapeHtml(item.title)}</h4>
          <div class="text-lines">${String(item.content || "").split("\n").map((line) => `<p>${escapeHtml(line)}</p>`).join("")}</div>
        </div>
      </div>
    `).join("")}</div></div>
    <div class="card" id="characterAttackDetail">
      <div class="attack-detail-title">
        <h3>攻击类型</h3>
        <div class="attack-detail-tabs">${attackTabButtons}</div>
      </div>
      <div id="characterAttackBody">${renderAttackTabContent(sections, "overview")}</div>
    </div>
  `;
  $('[data-show-data-pic]', $("#characterDetail"))?.addEventListener("click", (event) => showCharacterDataPic(event.currentTarget.dataset.showDataPic, data.name));
  bindAttackDetailTabs(sections);
  setActiveTab("character-detail");
}

function showCharacterDataPic(charId, name = "") {
  const id = String(charId || "").trim();
  if (!id) return;
  const displayName = name || (state.lastCharacterRows || []).find((row) => String(row.character_id) === id)?.name || id;
  $("#characterDataPic").innerHTML = `
    <div class="card">
      <div class="section-title data-pic-title">
        <h2>${escapeHtml(displayName)} <small>ID ${escapeHtml(id)}</small></h2>
        <button type="button" class="small secondary" data-query-jump="character-query">返回角色查询</button>
      </div>
      <img class="data-pic-image" src="${dataPicUrl(id)}" onerror="this.closest('.card').insertAdjacentHTML('beforeend','<p class=&quot;hint&quot;>未找到一图省流资源。</p>'); this.remove();">
    </div>
  `;
  $$("[data-query-jump]", $("#characterDataPic")).forEach((btn) => btn.addEventListener("click", () => setQueryTab(btn.dataset.queryJump)));
  setQueryTab("character-data-pic");
}

async function loadVsPresets() {
  const data = await api("/api/vs-presets");
  state.vsEffectTranslations = {};
  (data.vs_effect_rows || []).forEach((row) => {
    state.vsEffectTranslations[vsEffectKey(row)] = row;
    const loose = window.LWVsEffects?.looseKey?.(row);
    if (loose && !state.vsEffectTranslations[loose]) {
      state.vsEffectTranslations[loose] = row;
    }
  });
  state.vsPresets = data.presets || data.rows || [];
  const status = $("#vsPresetStatus");
  if (status) {
    status.textContent = `已解析 st=${data.st_count || 0}，td=${data.td_count || 0}，effect=${data.vs_effect_count || 0}，JSON: ${data.json_path || "-"}`;
    status.classList.toggle("hidden", !state.debugMode);
  }
  const query = String($("#vsPresetSearch")?.value || "").trim().toLowerCase();
  const sourceRows = state.vsPresets.filter((row) => {
    if (!query) return true;
    const enemyText = (row.enemies || []).map((item) => `${item.enemy?.display_name || ""} ${item.enemy?.name || ""} ${item.enemy?.enemy_id || ""}`).join(" ");
    return `${row.vs_id || ""} ${row.title || ""} ${enemyText}`.toLowerCase().includes(query);
  });
  const enemyNames = (row) => (row.enemies || []).map((item) => item.empty ? `敌方${item.pos}: 空` : `敌方${item.pos}: ${item.enemy?.display_name || item.enemy?.name || item.td_id}`).join("<br>");
  const tagText = (row) => {
    const body = (row.tags || []).map((tag) => {
    const effects = (tag.effects || []).map(vsEffectDescription).join(" / ");
    return `${tag.tag || tag.group_id}: ${effects}`;
    }).join("<br>");
    return `<details><summary>${(row.tags || []).length || 0} 个 tag</summary>${body || "-"}</details>`;
  };
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
    { key: "action", label: "操作", render: (row) => `
      <button class="small secondary" data-apply-vs-damage="${row.vs_id}">载入默认模块</button>
      <button class="small secondary" data-apply-vs-manual="${row.vs_id}">载入复灵模拟</button>
    ` },
  ], sourceRows, (table) => {
    $$("[data-apply-vs-damage]", table).forEach((btn) => {
      btn.addEventListener("click", () => {
        const preset = state.vsPresets.find((row) => String(row.vs_id) === String(btn.dataset.applyVsDamage));
        if (preset) applyVsPreset(preset, { target: "damage" }).catch((err) => alert(err.message));
      });
    });
    $$("[data-apply-vs-manual]", table).forEach((btn) => {
      btn.addEventListener("click", () => {
        const preset = state.vsPresets.find((row) => String(row.vs_id) === String(btn.dataset.applyVsManual));
        if (preset) applyVsPreset(preset, { target: "manual" }).catch((err) => alert(err.message));
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
