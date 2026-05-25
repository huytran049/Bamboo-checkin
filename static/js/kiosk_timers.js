(function () {
  function clearNamed(state, key) {
    if (!state || !key || !state[key]) return;
    const handle = state[key];
    if (handle && handle.__timerKind === "interval") {
      window.clearInterval(handle.id);
    } else if (handle && handle.__timerKind === "timeout") {
      window.clearTimeout(handle.id);
    } else {
      window.clearTimeout(handle);
      window.clearInterval(handle);
    }
    state[key] = null;
  }

  function setNamedTimeout(state, key, fn, delayMs) {
    clearNamed(state, key);
    const id = window.setTimeout(function () {
      state[key] = null;
      fn();
    }, Math.max(0, Number(delayMs) || 0));
    state[key] = { __timerKind: "timeout", id: id };
    return id;
  }

  function setNamedInterval(state, key, fn, delayMs) {
    clearNamed(state, key);
    const id = window.setInterval(fn, Math.max(1, Number(delayMs) || 1));
    state[key] = { __timerKind: "interval", id: id };
    return id;
  }

  function clearMany(state, keys) {
    (Array.isArray(keys) ? keys : []).forEach(function (key) {
      clearNamed(state, key);
    });
  }

  window.KioskTimerManager = {
    clearNamed: clearNamed,
    setNamedTimeout: setNamedTimeout,
    setNamedInterval: setNamedInterval,
    clearMany: clearMany,
  };
})();
