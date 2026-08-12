(function () {
  function key(effect = {}) {
    return `${Number(effect.kind || 0)}|${Number(effect.sub_id || 0)}|${Number(effect.value || 0)}`;
  }

  function looseKey(effect = {}) {
    return `${Number(effect.kind || 0)}|${Number(effect.sub_id || 0)}`;
  }

  function inferSide(effect = {}) {
    const side = Number(effect.side || 0);
    if (side) return side;
    const kind = Number(effect.kind || 0);
    if (kind === 1 || kind === 2) return 4;
    return 2;
  }

  function enrich(translations = {}, effect = {}) {
    const translated = translations[key(effect)] || translations[looseKey(effect)] || {};
    const value = Number(effect.value || 0);
    const translatedValue = Number(translated.value || 0);
    const description = effect.description || translated.description || "";
    return {
      ...effect,
      side: inferSide(effect),
      name: effect.name || translated.name || "",
      description: description && translatedValue && translatedValue !== value
        ? description.replace(new RegExp(`${translatedValue}(?=%)`, "g"), String(value))
        : description,
    };
  }

  window.LWVsEffects = { key, looseKey, inferSide, enrich };
})();
