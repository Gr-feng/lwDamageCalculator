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
const CALC_PRESET_STORAGE_KEY = "lw_damage_calculator_v1_2_calc_presets";
const EQUIPMENT_SLOTS = [["1a", "1符A"], ["2a", "2符A"], ["1b", "1符B"], ["2b", "2符B"], ["5", "终符"]];
const ATTACK_OPTIONS = [["1c", "扩散"], ["2c", "集中"], ["1", "1符"], ["2", "2符"], ["5", "终符"]];
const ATTACK_DETAIL_ORDER = ["扩散", "集中", "1符", "2符", "终符"];
const ELEMENT_ICON_LABELS = { 1: "日", 2: "月", 3: "火", 4: "水", 5: "木", 6: "金", 7: "土", 8: "星", 9: "无" };
const VS_TAGS = ["敌方六维", "弹种倍率", "属性倍率", "Type倍率", "P点回复", "种族特攻受伤", "敌方技能", "血条状态", "结界异常", "额外说明"];

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

function vsEffectKey(effect = {}) {
  return window.LWVsEffects?.key(effect) || `${Number(effect.kind || 0)}|${Number(effect.sub_id || 0)}|${Number(effect.value || 0)}`;
}

function inferVsEffectSide(effect = {}) {
  return window.LWVsEffects?.inferSide(effect) || 0;
}

function enrichVsEffect(effect = {}) {
  return window.LWVsEffects?.enrich(state.vsEffectTranslations, effect) || {
    ...effect,
    side: inferVsEffectSide(effect),
  };
}

function avatarUrl(charId) {
  const id = String(charId || 0).trim();
  return `/assets/avatars/S${id}01.png`;
}

function dataPicUrl(charId) {
  const id = String(charId || 0).trim();
  return `/assets/data_pic/${id}.png`;
}

function skillIconUrl(icon) {
  const raw = String(icon || "").trim();
  if (!raw) return "";
  const normalized = raw
    .replace(/^skill_icon_/, "Skill icon ")
    .replace(/_/g, " ");
  return `/assets/skill_icons/${encodeURIComponent(normalized)}.png`;
}

function characterTypeIconUrl(typeLabel) {
  const label = String(typeLabel || "").trim();
  return label ? `/assets/character_type_icons/${encodeURIComponent(`式图标 ${label}`)}.png` : "";
}

function bulletTypeIconUrl(typeId, typeLabel) {
  const id = Number(typeId || 0);
  const name = `Bullet Type Icon ${String(id).padStart(2, "0")}`;
  return `/assets/bullet_type_icons/${encodeURIComponent(name)}.png`;
}

function bulletSegmentUrl(elementLabel, yinyangLabel) {
  const element = String(elementLabel || "无").replace(/属性$/, "") || "无";
  const yy = String(yinyangLabel || "阴") === "阳" ? "阳" : "阴";
  return `/assets/bullet_segments/${encodeURIComponent(`弹幕 ${element}属性 ${yy}`)}.png`;
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
