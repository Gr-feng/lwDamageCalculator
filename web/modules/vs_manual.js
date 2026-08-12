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
    for (let effect of tag.effects || []) {
      effect = enrichVsEffect(effect);
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
        others.push(vsEffectDescription(effect));
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

function selectedVsTagEffects(fallbackTags = null) {
  const tagRows = fallbackTags || state.activeVsPreset?.tags || [];
  const checked = $$("#vsOptions .vs-tag-check:checked");
  if (checked.length) {
    return checked.flatMap((input) => {
      const tag = tagRows[Number(input.dataset.tagIdx)];
      return (tag?.effects || []).map(enrichVsEffect);
    }).concat(state.customVsTagEffects || []);
  }
  return tagRows.flatMap((tag) => (tag.effects || []).map(enrichVsEffect)).concat(state.customVsTagEffects || []);
}

function vsEnemyHpFactor(effects = selectedVsTagEffects()) {
  return (effects || []).reduce((factor, effect) => {
    const side = Number(effect.side || 0);
    const kind = Number(effect.kind || 0);
    const subId = Number(effect.sub_id || 0);
    if (side === 4 && kind === 1 && subId === 1) {
      return factor * Math.max(0, 1 + Number(effect.value || 0) / 100);
    }
    return factor;
  }, 1);
}

function applyVsEnemyHpFactor(stats, effects = selectedVsTagEffects()) {
  const factor = vsEnemyHpFactor(effects);
  return { ...stats, hp: Math.round(Number(stats.hp || 0) * factor) };
}

function runtimeVsTagEffects() {
  return selectedVsTagEffects().filter((effect) => {
    return !(Number(effect.side || 0) === 4 && Number(effect.kind || 0) === 1 && Number(effect.sub_id || 0) === 1);
  });
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
    <details class="vs-tag-category">
      <summary>${escapeHtml(category)}</summary>
      <div class="vs-tag-list">${rows.map(({ tag, idx }) => {
        const text = (tag.effects || []).map(vsEffectDescription).join(" / ");
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
  $$("#vsOptions .vs-tag-check").forEach((input) => {
    input.addEventListener("change", () => refreshVsEnemyStatsFromTags());
  });
  if ($("#arenaOptions")) {
    $("#arenaOptions").innerHTML = "";
  }
  renderVsManualFieldPresetTable();
  updateModeUI();
}

function renderVsManualFieldPresetTable() {
  const root = $("#vsManualFieldPresetTable");
  if (!root) return;
  const tags = state.activeVsPreset?.tags || [];
  if (!tags.length) {
    root.innerHTML = '<p class="hint">未载入复灵预设。请先到“复灵预设”页点击载入。</p>';
    return;
  }
  root.innerHTML = `
    <div class="vs-manual-field-tools">
      <label>复灵层数<input id="vsManualLevel" type="number" min="60" max="100" value="${escapeHtml($("#vsLevel")?.value || 100)}"></label>
      <button type="button" class="small secondary" data-reset-vs-manual-tags>重置tag</button>
    </div>
    <div class="table-wrap">
      <table class="vs-manual-tag-table">
        <thead><tr><th>启用</th><th>tag</th><th>效果</th></tr></thead>
        <tbody>${tags.map((tag, idx) => {
          const text = (tag.effects || []).map(vsEffectDescription).join(" / ");
          return `<tr>
            <td><input class="vs-tag-check" type="checkbox" data-tag-idx="${idx}" checked></td>
            <td>${escapeHtml(tag.tag || tag.group_id || idx)}</td>
            <td>${escapeHtml(text || "-")}</td>
          </tr>`;
        }).join("")}</tbody>
      </table>
    </div>
  `;
  $$(".vs-tag-check", root).forEach((input) => {
    input.addEventListener("change", () => {
      const mirror = $(`#vsOptions .vs-tag-check[data-tag-idx="${input.dataset.tagIdx}"]`);
      if (mirror) mirror.checked = input.checked;
      $("#calcMode").value = "vs";
      updateModeUI();
      refreshVsEnemyStatsFromTags();
    });
  });
  $("#vsManualLevel")?.addEventListener("change", () => {
    $("#calcMode").value = "vs";
    updateModeUI();
    refreshVsEnemyStatsFromTags();
  });
  $("[data-reset-vs-manual-tags]", root)?.addEventListener("click", () => {
    $$(".vs-tag-check", root).forEach((input) => (input.checked = true));
    $$("#vsOptions .vs-tag-check").forEach((input) => (input.checked = true));
    const levelInput = $("#vsManualLevel");
    if (levelInput) levelInput.value = "100";
    refreshVsEnemyStatsFromTags();
  });
  renderVsManualEnemySlots();
}

function refreshVsEnemyStatsFromTags() {
  if (!state.activeVsPreset) return;
  const level = Math.max(60, Math.min(100, Number($("#vsManualLevel")?.value || $("#vsLevel")?.value || 100)));
  $$(".enemy-slot").forEach((card) => {
    const phases = card._enemyPhases || [];
    const phase = phases[Number(card._enemyPhaseIndex || 0)];
    if (!phase) return;
    applyStatsToCard(card, applyVsEnemyHpFactor(interpolateVsStats(phase, level)));
    card._manualBarrierTypes = [];
    saveCurrentEnemyWave();
  });
  renderVsManualEnemySlots();
  renderOverview();
}

function renderVsManualEnemySlots() {
  const root = $("#vsManualEnemySlots");
  if (!root) return;
  const preset = state.activeVsPreset;
  if (!preset) {
    root.innerHTML = '<p class="hint">未载入复灵预设。</p>';
    return;
  }
  const level = Math.max(60, Math.min(100, Number($("#vsManualLevel")?.value || $("#vsLevel")?.value || 100)));
  const effects = selectedVsTagEffects();
  root.innerHTML = (preset.enemies || []).map((item) => {
    if (item.empty || !item.enemy) {
      return `<article class="mini-enemy-card"><h4>敌方${item.pos}</h4><p class="hint">空位</p></article>`;
    }
    const phases = item.phases && item.phases.length ? item.phases : [item.enemy];
    const selectedIdx = Math.max(0, Math.min(phases.length - 1, Number(state.vsManualPreviewPhases[String(item.pos)] || 0)));
    const phase = phases[selectedIdx] || item.enemy;
    const stats = applyVsEnemyHpFactor(interpolateVsStats(phase, level), effects);
    const quality = renderQualityIconRow(phase.quality || []);
    const tribes = describeTribes(phase.tribe_text_ids || (phase.tribe_ids || []).join(",") || phase.tribes_text || "");
    const phaseCount = phases.length || 1;
    const phaseButtons = phases.map((_, idx) => `<button type="button" class="small secondary ${idx === selectedIdx ? "active" : ""}" data-vs-preview-pos="${item.pos}" data-vs-preview-phase="${idx}">血条${idx + 1}</button>`).join("");
    return `
      <article class="mini-enemy-card">
        <div class="mini-enemy-head">
          <img class="avatar-small" src="${avatarUrl(phase.enemy_id)}" onerror="this.src='/assets/avatars/S0.png'">
          <div><h4>敌方${item.pos} ${escapeHtml(phase.display_name || phase.name || phase.enemy_id)}</h4><small>td ${phase.td_id || item.td_id || "-"} / 血条 ${selectedIdx + 1}/${phaseCount}</small></div>
        </div>
        <div class="phase-buttons mini-phase-buttons">${phaseButtons}</div>
        <div class="kv-grid compact">
          <div>HP：${numberText(stats.hp)}</div><div>阳攻：${numberText(stats.yang_atk)}</div><div>阳防：${numberText(stats.yang_def)}</div>
          <div>阴攻：${numberText(stats.yin_atk)}</div><div>阴防：${numberText(stats.yin_def)}</div><div>速度：${numberText(stats.speed)}</div>
          <div>护盾：${phase.barrier_count ?? "-"}</div>
        </div>
        <div class="compact-info-line quality-preview mini-quality-line"><b>气质</b> ${quality}</div>
        <div class="compact-info-line mini-tribe-line"><b>Tribe</b> ${escapeHtml(tribes)}</div>
        <div class="mini-enemy-detail">${renderEnemyInfoHtml(phase)}</div>
      </article>
    `;
  }).join("");
  $$("[data-vs-preview-phase]", root).forEach((btn) => {
    btn.addEventListener("click", () => {
      state.vsManualPreviewPhases[String(btn.dataset.vsPreviewPos)] = Number(btn.dataset.vsPreviewPhase || 0);
      renderVsManualEnemySlots();
    });
  });
}
