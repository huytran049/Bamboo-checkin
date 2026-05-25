(function () {
  const KIOSK_AUDIO_PLAYBACK_RATE = 1.15;
  const KIOSK_AUDIO_GAP_MS = 80;

  function applyAudioPlaybackProfile(audio) {
    if (!audio) return audio;
    audio.playbackRate = KIOSK_AUDIO_PLAYBACK_RATE;
    audio.defaultPlaybackRate = KIOSK_AUDIO_PLAYBACK_RATE;
    audio.preservesPitch = false;
    return audio;
  }

  function createAudioController(state, options) {
    const opts = options || {};
    const log = typeof opts.log === "function" ? opts.log : function () {};
    const getAudioList = typeof opts.getAudioList === "function" ? opts.getAudioList : function () { return []; };
    const onAudioPlayStateChange = typeof opts.onAudioPlayStateChange === "function"
      ? opts.onAudioPlayStateChange
      : function () {};

    function setAudioSpeakingState(isPlaying) {
      state.isAudioPlaying = !!isPlaying;
      onAudioPlayStateChange(!!isPlaying);
    }

    async function processAudioQueue() {
      if (!state.audioQueue.length) {
        setAudioSpeakingState(false);
        return;
      }

      setAudioSpeakingState(true);
      const audio = state.audioQueue.shift();

      try {
        applyAudioPlaybackProfile(audio);
        audio.currentTime = 0;
        await audio.play();

        return new Promise(function (resolve) {
          const onEnded = function () {
            audio.removeEventListener("ended", onEnded);
            window.setTimeout(function () {
              processAudioQueue();
              resolve();
            }, KIOSK_AUDIO_GAP_MS);
          };
          audio.addEventListener("ended", onEnded);
        });
      } catch (error) {
        console.error("Lỗi phát hàng đợi âm thanh:", error);
        setAudioSpeakingState(false);
        processAudioQueue();
      }
    }

    function playQueuedAudio(audio) {
      if (!state.audio || !audio) return;
      state.audioQueue.push(audio);
      if (!state.isAudioPlaying) {
        processAudioQueue();
      }
    }

    function interruptAndClearAudioQueue() {
      state.audioQueue = [];
      setAudioSpeakingState(false);
      const list = getAudioList();
      for (const audio of list) {
        try {
          audio.pause();
          audio.currentTime = 0;
        } catch (_) {}
      }
    }

    function playAudioAndWait(audio, forcePlay) {
      return new Promise(function (resolve) {
        if (forcePlay || audio) interruptAndClearAudioQueue();

        if ((!state.audio && !forcePlay) || !audio) {
          if (!state.audio && forcePlay) {
            log("Cảnh báo khẩn: bỏ qua trạng thái tắt âm thanh.");
          }
          if (!audio) {
            log("Không tìm thấy âm thanh để phát.");
          }
          resolve();
          return;
        }

        let timeoutId = null;
        const done = function () {
          if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
          }
          audio.removeEventListener("ended", done);
          audio.removeEventListener("error", done);
          setAudioSpeakingState(false);
          resolve();
        };

        audio.addEventListener("ended", done);
        audio.addEventListener("error", done);
        timeoutId = setTimeout(done, 12000);

        try {
          applyAudioPlaybackProfile(audio);
          audio.currentTime = 0;
          setAudioSpeakingState(true);
          const promise = audio.play();
          if (promise && typeof promise.catch === "function") {
            promise.catch(function (err) {
              log("Không thể phát âm thanh báo lỗi QR: " + ((err && err.message) || err || ""));
              done();
            });
          }
        } catch (_) {
          done();
        }
      });
    }

    return {
      processAudioQueue: processAudioQueue,
      playQueuedAudio: playQueuedAudio,
      playAudioAndWait: playAudioAndWait,
      interruptAndClearAudioQueue: interruptAndClearAudioQueue,
      applyAudioPlaybackProfile: applyAudioPlaybackProfile,
    };
  }

  window.KioskAudioController = {
    createAudioController: createAudioController,
  };
})();
