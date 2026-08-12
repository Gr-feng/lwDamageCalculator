(function () {
  async function search(deps) {
    const { $, $$, api, state, selectedFilterValues, renderTable } = deps;
    const buffParams = {};
    $$(".equipment-buff-filter").forEach((box, idx) => {
      const n = idx + 1;
      buffParams[`buff_id_${n}`] = $('[data-field="buff_id"]', box).value;
      buffParams[`sub_ids_${n}`] = selectedValues($('[data-field="sub_ids"]', box)).join(",");
      buffParams[`value_${n}`] = $('[data-field="value"]', box).value;
      buffParams[`target_${n}`] = $('[data-field="target"]', box).value;
      buffParams[`type_conditions_${n}`] = $('[data-field="type_conditions"]', box).value;
    });
    const params = new URLSearchParams({
      q: $("#eqName").value,
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
    renderTable(rows, deps);
  }

  function selectedValues(select) {
    return Array.from(select?.selectedOptions || []).map((option) => option.value).filter(Boolean);
  }

  function renderTable(rows, deps) {
    const { $, state, buildTable } = deps;
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

  window.LWEquipmentQuery = { search, renderTable };
})();
