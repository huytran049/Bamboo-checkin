(function () {
  function createAsyncController(state, options) {
    const opts = options || {};
    const timerManager = opts.timerManager || {
      clearNamed() {},
      setNamedInterval(_state, _key, fn, delayMs) {
        return window.setInterval(fn, delayMs);
      },
    };
    const fetchImpl = typeof opts.fetchImpl === "function" ? opts.fetchImpl : fetch.bind(window);
    const log = typeof opts.log === "function" ? opts.log : function () {};
    const isFaceRecognitionEligible = typeof opts.isFaceRecognitionEligible === "function"
      ? opts.isFaceRecognitionEligible
      : function () { return true; };
    const onFaceRecognitionMatched = typeof opts.onFaceRecognitionMatched === "function"
      ? opts.onFaceRecognitionMatched
      : function () {};
    const onFaceRecognitionNotMatched = typeof opts.onFaceRecognitionNotMatched === "function"
      ? opts.onFaceRecognitionNotMatched
      : function () {};
    const onFaceRecognitionError = typeof opts.onFaceRecognitionError === "function"
      ? opts.onFaceRecognitionError
      : function () {};
    const onBcardOcrDone = typeof opts.onBcardOcrDone === "function"
      ? opts.onBcardOcrDone
      : async function () {};
    const onBcardOcrError = typeof opts.onBcardOcrError === "function"
      ? opts.onBcardOcrError
      : function () {};

    function stopFaceRecognitionPolling() {
      timerManager.clearNamed(state, "faceRecognitionPollHandle");
    }

    function stopBcardOcrPolling() {
      timerManager.clearNamed(state, "ocrPollHandle");
    }

    async function pollFaceRecognitionStatus(jobId) {
      if (!jobId) return;
      stopFaceRecognitionPolling();

      timerManager.setNamedInterval(state, "faceRecognitionPollHandle", async function () {
        try {
          if (state.faceRecognitionJobId !== jobId) {
            stopFaceRecognitionPolling();
            return;
          }

          const url = state.faceJobStatusBase + "/" + encodeURIComponent(jobId) + "?t=" + Date.now();
          const res = await fetchImpl(url, { method: "GET" });
          const js = await res.json().catch(function () { return {}; });
          if (!res.ok || !js || !js.ok) return;

          const status = String(js.status || "").toLowerCase();
          state.faceRecognitionStatus = status || "processing";
          if (status === "queued" || status === "processing") {
            return;
          }

          stopFaceRecognitionPolling();
          state.faceRecognitionSending = false;
          state.faceRecognitionJobId = null;
          state.faceRecognitionLastAttemptAt = Date.now();

          if (status === "done") {
            if (js.matched && js.visitor) {
              await onFaceRecognitionMatched({
                name: js.visitor.display_name || js.visitor.registration_id || (window.I18N ? window.I18N.t("welcome.customer") : "Khách"),
                subtitle: window.I18N ? window.I18N.t("welcome.recognized") : "Đã nhận diện khách hàng.",
                audioUrl: js.visitor.greeting_audio_url,
                score: Number(js.score || 0),
                visitor: js.visitor,
              });
            } else {
              onFaceRecognitionNotMatched({
                score: Number(js.score || 0),
              });
            }
            return;
          }

          if (status === "error") {
            onFaceRecognitionError({
              error: js.error || "Lỗi không xác định",
              rawOutput: js.raw_output || "",
            });
          }
        } catch (err) {
          console.warn("poll face recognition status error:", err);
        }
      }, 500);
    }

    async function startFaceRecognitionFromBlob(blob) {
      if (!blob || !isFaceRecognitionEligible()) return;
      state.faceRecognitionSending = true;
      state.faceRecognitionStatus = "processing";

      try {
        const fd = new FormData();
        fd.append("image", blob, "face-recognize-" + Date.now() + ".jpg");
        const res = await fetchImpl(state.faceRecognizeStartEndpoint, { method: "POST", body: fd });
        const js = await res.json().catch(function () { return {}; });
        if (!res.ok || !js || !js.ok || !js.job_id) {
          throw new Error((js && js.error) || "Không thể bắt đầu nhận diện khuôn mặt");
        }

        state.faceRecognitionJobId = js.job_id;
        pollFaceRecognitionStatus(js.job_id);
      } catch (err) {
        state.faceRecognitionSending = false;
        state.faceRecognitionStatus = "error";
        state.faceRecognitionLastAttemptAt = Date.now();
        log("Không thể bắt đầu nhận diện khuôn mặt: " + ((err && err.message) || err));
      }
    }

    async function pollBcardOcrStatus(taskId) {
      if (!taskId) return;
      stopBcardOcrPolling();

      timerManager.setNamedInterval(state, "ocrPollHandle", async function () {
        try {
          if (state.ocrTaskId !== taskId) {
            stopBcardOcrPolling();
            return;
          }

          const url = state.bcardOCRAsyncStatusBase + "/" + encodeURIComponent(taskId) + "?t=" + Date.now();
          const res = await fetchImpl(url, { method: "GET" });
          const js = await res.json().catch(function () { return {}; });
          if (!res.ok || !js || !js.ok) return;

          const status = String(js.status || "").toLowerCase();
          if (status === "processing") {
            state.ocrStatus = "processing";
            return;
          }
          if (status === "done" || status === "success") {
            stopBcardOcrPolling();
            state.ocrStatus = "done";
            state.ocrTaskId = null;
            await onBcardOcrDone({
              fields: js.fields || {},
              text: js.text || "",
              payload: js,
            });
            return;
          }
          if (status === "error") {
            stopBcardOcrPolling();
            state.ocrStatus = "error";
            onBcardOcrError({
              taskId: taskId,
              error: js.error || "Lỗi OCR không xác định",
            });
          }
        } catch (err) {
          console.warn("poll OCR status error:", err);
        }
      }, 800);
    }

    async function startAsyncBcardOcrFromCanvas(canvas) {
      try {
        const blob = await new Promise(function (resolve) {
          canvas.toBlob(resolve, "image/jpeg", 0.9);
        });
        const fd = new FormData();
        fd.append("image", blob, "bcard-" + Date.now() + ".jpg");
        if (state.registrationId) {
          fd.append("reg_id", state.registrationId);
        }

        console.log("[OCR Start] Sending req to " + state.bcardOCRAsyncStartEndpoint + " with reg_id=" + state.registrationId);
        const res = await fetchImpl(state.bcardOCRAsyncStartEndpoint, { method: "POST", body: fd });
        const js = await res.json().catch(function () { return {}; });
        if (!res.ok || !js || !js.ok || !js.task_id) {
          throw new Error((js && js.error) || "Cannot start async OCR");
        }

        state.ocrTaskId = js.task_id;
        state.ocrStatus = "processing";
        pollBcardOcrStatus(js.task_id);
        return js.task_id;
      } catch (err) {
        state.ocrStatus = "error";
        log("Lỗi khởi tạo OCR: " + err.message);
        return null;
      }
    }

    return {
      stopFaceRecognitionPolling: stopFaceRecognitionPolling,
      pollFaceRecognitionStatus: pollFaceRecognitionStatus,
      startFaceRecognitionFromBlob: startFaceRecognitionFromBlob,
      stopBcardOcrPolling: stopBcardOcrPolling,
      pollBcardOcrStatus: pollBcardOcrStatus,
      startAsyncBcardOcrFromCanvas: startAsyncBcardOcrFromCanvas,
    };
  }

  window.KioskAsyncController = {
    createAsyncController: createAsyncController,
  };
})();
