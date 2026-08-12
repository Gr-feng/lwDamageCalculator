function resetCharacterFilters() {
  ["cqTypes", "cqWorlds", "cqElements", "cqBullets", "cqKillers"].forEach((id) => setFilterValues(id, []));
  $("#cqKillers").value = "";
  $("#cqKillerInput").value = "";
  $("#cqElementLogic").value = "any";
  $("#cqBulletLogic").value = "any";
  $("#cqKillerLogic").value = "any";
  $("#cqName").value = "";
  $("#cqAbilityKind").value = "";
  $("#cqAbilityAbnormal").value = "";
  $("#cqAbilityStatus").value = "";
  $("#cqAbilityChain").value = "";
  updateCharacterAbilityFilterVisibility();
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

function selectedMultiValues(select) {
  if (!select) return [];
  return Array.from(select.selectedOptions || []).map((option) => option.value).filter(Boolean);
}

async function refreshEquipmentBuffFilterSubIds(box) {
  const buffId = $('[data-field="buff_id"]', box)?.value || "";
  const select = $('[data-field="sub_ids"]', box);
  if (!select) return;
  if (!buffId) {
    select.innerHTML = "";
    return;
  }
  const rows = await api(`/api/equipment-buff-subids?buff_id=${encodeURIComponent(buffId)}`);
  select.innerHTML = tupleOptions(rows, false);
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
      <label>subID<select data-field="sub_ids" multiple size="4"></select></label>
      <label>target<select data-field="target">${tupleOptions(state.boot.equipment_target_options, true)}</select></label>
      <label>type<select data-field="type_conditions"><option value="">Type条件</option>${optionList(state.boot.type_labels)}</select></label>
      <label>值<input data-field="value" placeholder="值"></label>
    `;
    root.appendChild(box);
    $('[data-field="buff_id"]', box).addEventListener("change", () => refreshEquipmentBuffFilterSubIds(box).catch((err) => alert(err.message)));
  }
}

function initFilters() {
  $("#cqTypes").innerHTML = `<option value="">选择Type</option>${optionList(state.boot.type_labels)}`;
  $("#cqWorlds").innerHTML = `<option value="">选择世界群</option>${(state.boot.world_group_options || []).map((value) => `<option value="${value}">${value}</option>`).join("")}`;
  const elementLabels = Object.fromEntries(Object.entries(state.boot.element_labels || {}).filter(([key]) => Number(key) > 0));
  $("#cqElements").innerHTML = `<option value="">选择属性</option>${optionList(elementLabels)}`;
  $("#cqBullets").innerHTML = `<option value="">选择弹种</option>${optionList(state.boot.bullet_labels)}`;
  updateCharacterAbilityFilterVisibility();
  $("#cqAbilityKind")?.addEventListener("change", updateCharacterAbilityFilterVisibility);
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

function updateCharacterAbilityFilterVisibility() {
  const kind = $("#cqAbilityKind")?.value || "";
  $$(".cq-ability-barrier").forEach((el) => el.classList.toggle("hidden", kind !== "barrier"));
  $$(".cq-ability-chain").forEach((el) => el.classList.toggle("hidden", kind !== "chain"));
}
