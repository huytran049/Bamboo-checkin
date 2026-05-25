(function () {
  function createPresenceController(state, options) {
    const opts = options || {};
    const clearWelcomeIdleTimer = typeof opts.clearWelcomeIdleTimer === "function" ? opts.clearWelcomeIdleTimer : function () {};
    const scheduleHideWelcomeEyes = typeof opts.scheduleHideWelcomeEyes === "function" ? opts.scheduleHideWelcomeEyes : function () {};
    const showWelcomeEyes = typeof opts.showWelcomeEyes === "function" ? opts.showWelcomeEyes : function () {};
    const scheduleWelcomeIdleReturn = typeof opts.scheduleWelcomeIdleReturn === "function" ? opts.scheduleWelcomeIdleReturn : function () {};
    const playQueuedAudio = typeof opts.playQueuedAudio === "function" ? opts.playQueuedAudio : function () {};
    const log = typeof opts.log === "function" ? opts.log : function () {};
    const greetAudio = opts.greetAudio || null;
    const cardGuideAudio = opts.cardGuideAudio || null;

    function handlePresenceReaction(payload) {
      const hasPerson = !!payload.hasPerson;
      const currentFaceCount = Number(payload.currentFaceCount || 0);
      const now = Number(payload.now || Date.now());

      if (currentFaceCount > state.presenceLastFaceCount) {
        state.presenceFaceIncreaseStreak += 1;
      } else {
        state.presenceFaceIncreaseStreak = 0;
      }

      if (hasPerson) {
        clearWelcomeIdleTimer();

        if (state.welcomeEyesVisible && state.lastPersonBox && state.lastFrameSize) {
          const box = state.lastPersonBox;
          const centerX = (box.x + box.w / 2) / state.lastFrameSize.w;
          const centerY = (box.y + box.h / 2) / state.lastFrameSize.h;
          state.avatar.target.x = centerX;
          state.avatar.target.y = centerY;
        }

        if (state.welcomeEyesVisible) {
          scheduleHideWelcomeEyes();
          log("Đã phát hiện người dùng. Chuyển sang giao diện quét danh thiếp và chụp khuôn mặt.");
        }
      } else {
        if (state.autoCyclePhase === "FACE" && state.faceRetryCount < state.faceRetryMaxCount) {
          clearWelcomeIdleTimer();
        } else {
          if (state.welcomeHideTimer) {
            clearTimeout(state.welcomeHideTimer);
            state.welcomeHideTimer = null;
          }
          scheduleWelcomeIdleReturn();
        }
      }

      const hasNewPerson = (hasPerson && !state.presenceLastHadPerson) ||
        (hasPerson &&
          currentFaceCount > state.presenceLastFaceCount &&
          state.presenceFaceIncreaseStreak >= (state.presenceStableIncreaseFrames || 2));

      if (hasNewPerson && state.welcomeEyesVisible) {
        scheduleHideWelcomeEyes();
        log("Phát hiện người mới. Giữ màn chào đón trong chốc lát để avatar bám theo người dùng.");
      }

      if (hasNewPerson && !state.welcomeEyesVisible && !state.suppressGreetingDuringCompletion && state.autoCyclePhase === "IDLE") {
        const greetingBlocked =
          state.returningVisitorGreetingActive ||
          Date.now() < state.returningVisitorGreetingSuppressUntilMs;
        if (greetingBlocked) {
          state.presenceFaceIncreaseStreak = 0;
        } else if (now - state.presenceLastGreetTs > state.presenceGreetCooldownMs) {
          playQueuedAudio(greetAudio);
          window.setTimeout(function () {
            playQueuedAudio(cardGuideAudio);
          }, 1000);
          state.presenceLastGreetTs = now;
          state.presenceFaceIncreaseStreak = 0;
        }
      }

      if (hasPerson) {
        if (!state.faceSeenSinceMs) state.faceSeenSinceMs = now;
      } else {
        state.faceSeenSinceMs = 0;
      }

      state.presenceLastHadPerson = hasPerson;
      state.presenceLastFaceCount = currentFaceCount;
    }

    return {
      handlePresenceReaction: handlePresenceReaction,
    };
  }

  window.KioskPresenceController = {
    createPresenceController: createPresenceController,
  };
})();
