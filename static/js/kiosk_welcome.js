(function () {
  function createWelcomeController(state, options) {
    const opts = options || {};
    const timerManager = opts.timerManager || {
      clearNamed() {},
      setNamedTimeout(_state, _key, fn, delayMs) {
        return window.setTimeout(fn, delayMs);
      },
    };
    const querySelector = typeof opts.querySelector === "function"
      ? opts.querySelector
      : function (selector) { return document.querySelector(selector); };
    const onWelcomeVisibilityChange = typeof opts.onWelcomeVisibilityChange === "function"
      ? opts.onWelcomeVisibilityChange
      : function () {};
    const idleEyeDriftEnabled = opts.idleEyeDriftEnabled !== false;

    function computeAvatarMetrics() {
      const eyeL = querySelector(".welcome-eye.left");
      const eyeR = querySelector(".welcome-eye.right");
      const face = querySelector(".welcome-face");
      if (!eyeL || !eyeR || !face) return;
      const rect = eyeL.getBoundingClientRect();
      const faceRect = face.getBoundingClientRect();
      state.avatar.metrics.eyeW = rect.width;
      state.avatar.metrics.eyeH = rect.height;
      state.avatar.metrics.radiusX = rect.width * 0.24;
      state.avatar.metrics.radiusY = rect.height * 0.22;
      state.avatar.metrics.faceW = faceRect.width;
      state.avatar.metrics.faceH = faceRect.height;
    }

    function applyPupil(node, offX, offY) {
      if (!node) return;
      node.style.transform = "translate(calc(-50% + " + offX + "px), calc(-50% + " + offY + "px))";
    }

    function tickAvatar() {
      const overlay = querySelector("#welcome-eyes-overlay");
      if (!state.welcomeEyesVisible) {
        state.avatar.rafId = requestAnimationFrame(tickAvatar);
        return;
      }

      const avatar = state.avatar;
      const lerp = function (a, b, t) { return a + (b - a) * t; };
      const clamp = function (value, min, max) { return Math.max(min, Math.min(max, value)); };
      const now = Date.now();
      const hasTrackedPerson = !!(state.presenceLastHadPerson && state.lastPersonBox && state.lastFrameSize);

      if (!hasTrackedPerson && idleEyeDriftEnabled) {
        avatar.target.x = 0.5 + Math.sin(now / 1700) * 0.08;
        avatar.target.y = 0.5 + Math.cos(now / 2200) * 0.05;
      }

      avatar.cur.x = lerp(avatar.cur.x, avatar.target.x, 0.18);
      avatar.cur.y = lerp(avatar.cur.y, avatar.target.y, 0.18);

      const dx = clamp((avatar.cur.x - 0.5) * 2, -1, 1) * avatar.metrics.radiusX;
      const dy = clamp((avatar.cur.y - 0.5) * 2, -1, 1) * avatar.metrics.radiusY;

      applyPupil(querySelector(".welcome-eye.left .welcome-pupil"), dx, dy);
      applyPupil(querySelector(".welcome-eye.right .welcome-pupil"), dx, dy);

      if (overlay) {
        overlay.style.setProperty("--welcome-face-pan-x", (clamp((avatar.cur.x - 0.5) * 2, -1, 1) * 8).toFixed(2) + "px");
        overlay.style.setProperty("--welcome-face-pan-y", (clamp((avatar.cur.y - 0.5) * 2, -1, 1) * 5).toFixed(2) + "px");
      }

      state.avatar.rafId = requestAnimationFrame(tickAvatar);
    }

    function randomBlink() {
      const overlay = querySelector("#welcome-eyes-overlay");
      if (overlay && state.welcomeEyesVisible) {
        overlay.classList.add("blink");
        window.setTimeout(function () {
          overlay.classList.remove("blink");
        }, 120);
      }
      state.avatar.blinkTimer = window.setTimeout(randomBlink, 1800 + Math.random() * 2600);
    }

    function showWelcomeEyes(show) {
      const overlay = querySelector("#welcome-eyes-overlay");
      if (!overlay) {
        state.welcomeEyesVisible = false;
        onWelcomeVisibilityChange(false);
        return;
      }
      
      // Không hiện welcome eyes nếu returning visitor overlay đang hiển thị
      if (show && isReturningVisitorOverlayVisible()) {
        return;
      }
      
      timerManager.clearNamed(state, "welcomeHideTimer");
      overlay.classList.toggle("is-hidden", !show);
      overlay.setAttribute("aria-hidden", show ? "false" : "true");
      state.welcomeEyesVisible = !!show;
      onWelcomeVisibilityChange(!!show);
      if (show) {
        computeAvatarMetrics();
        overlay.classList.remove("mood-happy", "mood-sad");
        overlay.classList.add("mood-neutral");
        overlay.classList.toggle("speaking", !!state.avatar.isSpeaking);
        overlay.style.setProperty("--welcome-face-pan-x", "0px");
        overlay.style.setProperty("--welcome-face-pan-y", "0px");
      }
    }

    function setSpeakingState(isSpeaking) {
      const overlay = querySelector("#welcome-eyes-overlay");
      state.avatar.isSpeaking = !!isSpeaking;
      if (!overlay) return;
      overlay.classList.toggle("speaking", !!isSpeaking);
    }

    function scheduleHideWelcomeEyes() {
      if (!state.welcomeEyesVisible || state.welcomeHideTimer) return;
      timerManager.setNamedTimeout(state, "welcomeHideTimer", function () {
        showWelcomeEyes(false);
      }, state.welcomeHideDelayMs);
    }

    function clearWelcomeIdleTimer() {
      timerManager.clearNamed(state, "welcomeIdleTimer");
    }

    function hideReturningVisitorOverlay() {
      const overlay = querySelector("#returning-visitor-overlay");
      if (!overlay) return;
      timerManager.clearNamed(state, "faceRecognitionOverlayTimer");
      overlay.classList.add("is-hidden");
      overlay.setAttribute("aria-hidden", "true");
      
      // Sau khi ẩn returning visitor overlay, nếu vẫn còn người thì đảm bảo welcome eyes không hiện lại
      // và trigger logic chuyển sang giao diện chụp ảnh
      if (state.presenceLastHadPerson && !state.welcomeEyesVisible) {
        // Đảm bảo welcome eyes không hiện lại
        state.welcomeEyesVisible = false;
      }
    }

    function isReturningVisitorOverlayVisible() {
      const overlay = querySelector("#returning-visitor-overlay");
      return !!(overlay && !overlay.classList.contains("is-hidden"));
    }

    function showReturningVisitorOverlay(name, subtitle, title) {
      const overlay = querySelector("#returning-visitor-overlay");
      const titleEl = querySelector("#returning-visitor-title");
      const nameEl = querySelector("#returning-visitor-name");
      const subtitleEl = querySelector("#returning-visitor-subtitle");
      if (!overlay || !titleEl || !nameEl) return;

      showWelcomeEyes(false);
      const translate = window.I18N && typeof window.I18N.t === "function"
        ? function (key, fallback) { return window.I18N.t(key, fallback); }
        : function (_key, fallback) { return fallback; };
      titleEl.textContent = title || translate("welcome.returning", "Chào mừng quay lại");
      nameEl.textContent = name || translate("welcome.customer", "Khách");
      if (subtitleEl) {
        subtitleEl.textContent = subtitle || translate("welcome.recognized", "Đã nhận diện khách hàng.");
      }
      overlay.classList.remove("is-hidden");
      overlay.setAttribute("aria-hidden", "false");
      timerManager.setNamedTimeout(state, "faceRecognitionOverlayTimer", function () {
        hideReturningVisitorOverlay();
      }, 3000);
    }

    return {
      computeAvatarMetrics: computeAvatarMetrics,
      tickAvatar: tickAvatar,
      randomBlink: randomBlink,
      showWelcomeEyes: showWelcomeEyes,
      setSpeakingState: setSpeakingState,
      scheduleHideWelcomeEyes: scheduleHideWelcomeEyes,
      clearWelcomeIdleTimer: clearWelcomeIdleTimer,
      hideReturningVisitorOverlay: hideReturningVisitorOverlay,
      isReturningVisitorOverlayVisible: isReturningVisitorOverlayVisible,
      showReturningVisitorOverlay: showReturningVisitorOverlay,
    };
  }

  window.KioskWelcomeController = {
    createWelcomeController: createWelcomeController,
  };
})();
