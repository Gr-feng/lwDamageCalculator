(function () {
  function renderGallery(container, deps, rows, presetMap, filters, options = {}) {
    if (!container || !window.LWRoleGallery?.render) return;
    const filteredRows = (rows || []).filter((row) => {
      const preset = presetMap[String(row.id)] || null;
      if (filters?.preset === "missing" && preset) return false;
      if (filters?.preset === "exists" && !preset) return false;
      if (options.useRoleFlags) {
        if (filters?.rebirth2 && !preset?.rebirth2) return false;
        if (filters?.unowned && !preset?.unowned) return false;
      }
      return true;
    });
    window.LWRoleGallery.render(container, {
      rows: filteredRows,
      presetMap,
      filters: {},
      useRoleFilters: false,
      withOwnedFlags: options.withOwnedFlags,
      avatarUrl: deps.avatarUrl,
      escapeHtml: deps.escapeHtml,
      onPick: options.onPick,
    });
  }

  function renderRolePreview(deps, onPick) {
    const { $, state } = deps;
    const root = $("#rolePresetPreview");
    if (!root) return;
    root.innerHTML = `
      <details class="card preset-preview" ${state.roleBrowserVisible ? "open" : ""}>
        <summary>角色预览</summary>
        <div class="gallery-filter">
          <label>预设<select data-role="role-filter-preset"><option value="">全部</option><option value="missing">暂无预设</option><option value="exists">已有预设</option></select></label>
          <label class="inline-check"><input data-role="role-filter-rebirth2" type="checkbox">二转</label>
          <label class="inline-check"><input data-role="role-filter-unowned" type="checkbox">未拥有</label>
        </div>
        <div data-role="role-browser" class="character-gallery"></div>
      </details>
    `;
    const details = $("details", root);
    const presetFilter = $('[data-role="role-filter-preset"]', root);
    const rebirthFilter = $('[data-role="role-filter-rebirth2"]', root);
    const unownedFilter = $('[data-role="role-filter-unowned"]', root);
    if (presetFilter) presetFilter.value = state.roleGalleryFilters.preset || "";
    if (rebirthFilter) rebirthFilter.checked = Boolean(state.roleGalleryFilters.rebirth2);
    if (unownedFilter) unownedFilter.checked = Boolean(state.roleGalleryFilters.unowned);
    const refresh = () => {
      renderGallery($('[data-role="role-browser"]', root), deps, state.boot.character_options || [], state.characterPresets, state.roleGalleryFilters, {
        withOwnedFlags: true,
        useRoleFlags: true,
        onPick,
      });
    };
    details?.addEventListener("toggle", () => {
      state.roleBrowserVisible = details.open;
      if (details.open) refresh();
    });
    presetFilter?.addEventListener("change", () => {
      state.roleGalleryFilters.preset = presetFilter.value;
      refresh();
    });
    rebirthFilter?.addEventListener("change", () => {
      state.roleGalleryFilters.rebirth2 = rebirthFilter.checked;
      refresh();
    });
    unownedFilter?.addEventListener("change", () => {
      state.roleGalleryFilters.unowned = unownedFilter.checked;
      refresh();
    });
    if (state.roleBrowserVisible) refresh();
  }

  function renderArenaPreview(deps, onPick) {
    const { $, state } = deps;
    const root = $("#arenaPresetPreview");
    if (!root) return;
    root.innerHTML = `
      <details class="card preset-preview" ${state.arenaBrowserVisible ? "open" : ""}>
        <summary>角色预览</summary>
        <div class="gallery-filter">
          <label>预设<select data-role="arena-filter-preset"><option value="">全部</option><option value="missing">没有预设</option><option value="exists">已有预设</option></select></label>
        </div>
        <div data-role="arena-browser" class="character-gallery"></div>
      </details>
    `;
    const details = $("details", root);
    const presetFilter = $('[data-role="arena-filter-preset"]', root);
    if (presetFilter) presetFilter.value = state.arenaGalleryFilter || "";
    const refresh = () => {
      renderGallery($('[data-role="arena-browser"]', root), deps, state.boot.character_options || [], state.arenaPresets, { preset: state.arenaGalleryFilter }, {
        withOwnedFlags: false,
        onPick,
      });
    };
    details?.addEventListener("toggle", () => {
      state.arenaBrowserVisible = details.open;
      if (details.open) refresh();
    });
    presetFilter?.addEventListener("change", () => {
      state.arenaGalleryFilter = presetFilter.value;
      refresh();
    });
    if (state.arenaBrowserVisible) refresh();
  }

  function renderRolePresets(deps) {
    const {
      $, $$, api, state, PRESET_STAT_ORDER, STAT_LABELS, EQUIPMENT_SLOTS,
      buildCharacterLoader, hydrateCharacterLoader, characterLoaderQuery,
      setCharacterLoaderValue, loadCharacterMeta, fillMeta, cardIconUrl,
      updateEquipmentSummary, saveCharacterPresets, renderRolePresets,
    } = deps;
    const root = $("#rolePresetCards");
    root.innerHTML = "";
    const card = document.createElement("article");
    card.className = "slot-card role-preset-card loaded";
    card.innerHTML = `
      <div class="slot-head">
        <h3>角色预设</h3>
        <div class="head-actions">
          <button class="small secondary" data-load-preset>加载预设</button>
          <button class="small secondary" data-toggle-equipment-detail>${state.rolePresetDetail ? "简略" : "详细"}</button>
          <button class="small secondary" data-save-preset>保存预设</button>
          <button class="small danger" data-delete-preset>删除预设</button>
        </div>
      </div>
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
    renderRolePreview(deps, async (id) => {
      state.loadedRolePresetId = String(id);
      await applyPreset(id);
    });
    $('[data-edit-override]', card)?.addEventListener("click", () => {
      const textarea = $('[data-field="override_note"]', card);
      if (textarea) {
        textarea.readOnly = false;
        textarea.focus();
      }
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

  function renderArenaPresets(deps) {
    const {
      $, $$, state, ARENA_STAT_KEYS, STAT_LABELS,
      buildCharacterLoader, hydrateCharacterLoader, characterLoaderQuery,
      setCharacterLoaderValue, loadCharacterMeta, fillMeta, escapeHtml,
      arenaStatTemplates, arenaPresetSection, renderArenaStatMirror,
      applyQualityToCard, createQualityEditor, resetQuality, addEnemySkillRow,
      applyArenaFixedStats, collectQuality, collectEnemySkillRows,
      swapYinyangSection, saveArenaPresets, loadArenaPresets, loadArenaEnemyData,
      rerenderWeeklyArenaConfigPreservingState,
    } = deps;
    const root = $("#arenaPresetCards");
    root.innerHTML = "";
    const statTemplates = arenaStatTemplates();
    const card = document.createElement("article");
    card.className = "slot-card arena-preset-card loaded";
    card.innerHTML = `
      <div class="slot-head">
        <h3>擂台敌方预设</h3>
        <div class="head-actions">
          <button class="small secondary" data-load-arena>加载预设</button>
          <button class="small secondary" data-save-arena>保存预设</button>
        </div>
      </div>
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
      const section = arenaPresetSection(meta.id, "周擂台1") || {};
      $('[data-field="barrier_count"]', card).value = section.barrier_count ?? 7;
      $$("[data-stat]", card).forEach((input) => (input.value = section.stat_overrides?.[input.dataset.stat] ?? 0));
      $('[data-role="arena-barrier-label"]', card).textContent = $('[data-field="barrier_count"]', card).value;
      applyQualityToCard(card, section.quality || state.boot.quality_default || []);
      const buffRoot = $('[data-role="buffs"]', card);
      buffRoot.innerHTML = "";
      (section.enemy_skill_effects || []).forEach((buff) => addEnemySkillRow(buffRoot, buff));
    };
    renderArenaPreview(deps, async (id) => {
      const meta = await loadCharacterMeta(id).catch(() => null);
      if (meta) applyPreset(meta);
    });
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
      rerenderWeeklyArenaConfigPreservingState();
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

  window.LWPresets = { renderRolePresets, renderArenaPresets };
})();
