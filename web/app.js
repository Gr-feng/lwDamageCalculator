const state = {
  boot: null,
  lastResult: null,
  debugMode: false,
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
  showFullAttack5Elements: false,
  characterThumbnailMode: false,
  hideEquipmentImages: false,
  lastCharacterRows: [],
  lastEquipmentRows: [],
  activeVsTagEffects: [],
  customVsTagEffects: [],
  activeVsPreset: null,
  vsPresets: [],
  vsEffectTranslations: {},
  vsManualPayload: null,
  vsManualInitialPayload: null,
  vsManualState: null,
  vsManualPhase: "idle",
  vsManualSkillUsed: {},
  vsManualPendingSkills: {},
  vsManualSkillLog: [],
  vsManualPreviewPhases: {},
  roleBrowserVisible: false,
  arenaBrowserVisible: false,
  arenaEnemyData: { rows: [] },
  arenaGalleryFilter: "",
  pendingArenaPresetId: "",
  weeklySimpleMode: false,
  calcPresets: {},
  roleGalleryFilters: {
    preset: "",
    rebirth2: false,
    unowned: false,
  },
};

function setDebugMode(enabled) {
  state.debugMode = Boolean(enabled);
  document.body.classList.toggle("debug-mode", state.debugMode);
  const btn = $("#debugModeBtn");
  if (btn) {
    btn.classList.toggle("active", state.debugMode);
    btn.textContent = state.debugMode ? "调试开" : "调试";
  }
  const status = $("#vsPresetStatus");
  if (status) status.classList.toggle("hidden", !state.debugMode);
  renderCharacterTable(state.lastCharacterRows || []);
}

const MODULE_SIDEBAR_LINKS = {
  damage: [
    ["overviewPane", "总览"],
    ["enemyPane", "敌方参数"],
    ["allyPane", "我方参数"],
    ["processPane", "计算过程"],
    ["resultPane", "最终结果"],
  ],
  "vs-manual": [
    ["field", "场地 buff"],
    ["enemy", "敌方参数"],
    ["ally", "我方参数"],
    ["turn", "回合模拟"],
  ],
  "query-hub": [
    ["character-query", "角色查询"],
    ["equipment-query", "绘卷查询"],
    ["character-detail", "角色详情"],
    ["character-data-pic", "一图省流"],
  ],
};

function renderModuleSidebar(activeTab = $(".tab-panel.active")?.id || "damage") {
  const root = $("#moduleSidebarLinks");
  if (!root) return;
  const links = MODULE_SIDEBAR_LINKS[activeTab] || [];
  if (!links.length) {
    root.innerHTML = '<p class="hint">当前模块暂无快速导航。</p>';
    return;
  }
  root.innerHTML = links.map(([id, label]) => `<button type="button" class="small secondary" data-sidebar-jump="${id}">${label}</button>`).join("");
  $$("[data-sidebar-jump]", root).forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.sidebarJump;
      if (activeTab === "damage") setActiveSubtab(id);
      else if (activeTab === "vs-manual") setVsManualTab(id);
      else if (activeTab === "query-hub") setQueryTab(id);
    });
  });
}

function presetDeps() {
  return {
    $, $$, api, state,
    PRESET_STAT_ORDER, ARENA_STAT_KEYS, STAT_LABELS, EQUIPMENT_SLOTS,
    buildCharacterLoader, hydrateCharacterLoader, characterLoaderQuery,
    setCharacterLoaderValue, loadCharacterMeta, fillMeta, avatarUrl, cardIconUrl,
    escapeHtml, updateEquipmentSummary, saveCharacterPresets, saveArenaPresets,
    loadArenaPresets, loadArenaEnemyData, renderRolePresets, renderArenaPresets,
    arenaStatTemplates, arenaPresetSection, renderArenaStatMirror,
    applyQualityToCard, createQualityEditor, resetQuality, addEnemySkillRow,
    applyArenaFixedStats, collectQuality, collectEnemySkillRows,
    swapYinyangSection, rerenderWeeklyArenaConfigPreservingState,
  };
}

function renderRolePresets() {
  return window.LWPresets.renderRolePresets(presetDeps());
}

function renderArenaPresets() {
  return window.LWPresets.renderArenaPresets(presetDeps());
}

function bindEvents() {
  $("#tabs").addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-tab]");
    if (btn) {
      setActiveTab(btn.dataset.tab);
      renderModuleSidebar(btn.dataset.tab === "query-hub" ? "query-hub" : btn.dataset.tab);
    }
  });
  $("#damageSubtabs").addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-subtab]");
    if (btn) {
      setActiveSubtab(btn.dataset.subtab);
      renderModuleSidebar("damage");
    }
  });
  $("#calculateBtn").addEventListener("click", () => calculate().catch((err) => alert(err.message)));
  $("#batchPresetBtn").addEventListener("click", () => batchSummary("preset").catch((err) => alert(err.message)));
  $("#batchDefaultBtn").addEventListener("click", () => batchSummary("default").catch((err) => alert(err.message)));
  $("#saveCalcPresetBtn")?.addEventListener("click", saveCurrentCalcPreset);
  $("#loadCalcPresetBtn")?.addEventListener("click", loadSelectedCalcPreset);
  $("#deleteCalcPresetBtn")?.addEventListener("click", deleteSelectedCalcPreset);
  $("#calcPresetSelect")?.addEventListener("change", () => {
    if ($("#calcPresetName")) $("#calcPresetName").value = $("#calcPresetSelect").value || "";
  });
  $("#weeklyArenaSolveBtn").addEventListener("click", () => solveWeeklyArena().catch((err) => alert(err.message)));
  $("#debugModeBtn")?.addEventListener("click", () => setDebugMode(!state.debugMode));
  $("#characterSearchBtn").addEventListener("click", () => searchCharacters().catch((err) => alert(err.message)));
  $("#toggleFullAttack5ElementsBtn")?.addEventListener("click", () => {
    state.showFullAttack5Elements = !state.showFullAttack5Elements;
    $("#toggleFullAttack5ElementsBtn").textContent = state.showFullAttack5Elements ? "显示属性图标" : "显示完整终符属性";
    renderCharacterTable(state.lastCharacterRows || []);
  });
  $("#toggleCharacterThumbModeBtn")?.addEventListener("click", () => {
    state.characterThumbnailMode = !state.characterThumbnailMode;
    $("#toggleCharacterThumbModeBtn").textContent = state.characterThumbnailMode ? "表格" : "缩略图";
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
  $("#vsManualSubtabs")?.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-vs-manual-tab]");
    if (btn) {
      setVsManualTab(btn.dataset.vsManualTab);
      renderModuleSidebar("vs-manual");
    }
  });
  $("#vsManualPrepareFieldBtn")?.addEventListener("click", () => prepareVsManualFieldBuffs().catch((err) => alert(err.message)));
  $("#vsManualImportBtn")?.addEventListener("click", () => importVsManualConfig().catch((err) => alert(err.message)));
  $("#vsManualApplySkillsBtn")?.addEventListener("click", () => applyPendingManualSkills().catch((err) => alert(err.message)));
  $("#vsManualCalcBtn")?.addEventListener("click", () => solveVsManual().catch((err) => alert(err.message)));
  $("#vsManualNextBtn")?.addEventListener("click", () => advanceVsManualTurn());
  $("#vsManualResetBtn")?.addEventListener("click", () => resetVsManualSimulation());
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
  renderVsManualAllySlots();
  renderFullFieldRows();
  loadCalcPresetsFromStorage();
  renderRolePresets();
  renderArenaPresets();
  renderWeeklyArenaConfig();
  initFilters();
  bindEvents();
  renderOverview();
  renderGlobalSkillButtons();
  updateVsManualButtons();
  renderModuleSidebar("damage");
  await searchCharacters();
  await searchEquipment();
}

init().catch((err) => {
  console.error(err);
  document.body.insertAdjacentHTML("afterbegin", `<div class="card" style="margin:16px;color:#9f2c25">初始化失败：${err.message}</div>`);
});



