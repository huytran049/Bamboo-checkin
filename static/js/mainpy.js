(() => {
    const $ = (sel) => document.querySelector(sel);
    const getVal = (sel) => (($(sel) || {}).value || "").trim();
    const setVal = (sel, v) => { const el = $(sel); if (el) el.value = v || ""; };
    const HAS_WELCOME_OVERLAY = !!document.querySelector("#welcome-eyes-overlay");
    const timerManager = window.KioskTimerManager || {
        clearNamed(state, key) {
            if (!state || !key || !state[key]) return;
            clearTimeout(state[key]);
            clearInterval(state[key]);
            state[key] = null;
        },
        setNamedTimeout(state, key, fn, delayMs) {
            this.clearNamed(state, key);
            state[key] = setTimeout(() => {
                state[key] = null;
                fn();
            }, delayMs);
            return state[key];
        },
        setNamedInterval(state, key, fn, delayMs) {
            this.clearNamed(state, key);
            state[key] = setInterval(fn, delayMs);
            return state[key];
        },
        clearMany(state, keys) {
            (keys || []).forEach((key) => this.clearNamed(state, key));
        },
    };
    const welcomeControllerFactory = window.KioskWelcomeController || null;
    const audioControllerFactory = window.KioskAudioController || null;
    const asyncControllerFactory = window.KioskAsyncController || null;
    const presenceControllerFactory = window.KioskPresenceController || null;
    function t(key, replacements) {
        let text = window.I18N && typeof window.I18N.t === "function" ? window.I18N.t(key) : key;
        if (replacements) {
            Object.keys(replacements).forEach((name) => {
                text = text.replace(new RegExp("\\{" + name + "\\}", "g"), String(replacements[name]));
            });
        }
        return text;
    }

    const logEl = $("#log");
    const appointmentPromptOverlay = document.getElementById("appointment-prompt-overlay");
    const appointmentFormOverlay = document.getElementById("appointment-form-overlay");
    const appointmentConfirmOverlay = document.getElementById("appointment-confirm-overlay");
    const appointmentPromptYesBtn = document.getElementById("appointmentPromptYesBtn");
    const appointmentPromptQABtn = document.getElementById("appointmentPromptQABtn");
    const appointmentPromptNoBtn = document.getElementById("appointmentPromptNoBtn");
    const sideAppointmentBtn = document.getElementById("sideAppointmentBtn");
    const sideQaBtn = document.getElementById("sideQaBtn");
    const languageSwitchButtons = Array.from(document.querySelectorAll("[data-lang-value]"));
    const appointmentDateInput = document.getElementById("appointmentDateInput");
    const appointmentStartTimeSelect = document.getElementById("appointmentStartTimeSelect");
    const appointmentEndTimeSelect = document.getElementById("appointmentEndTimeSelect");
    const appointmentPurposeSelect = document.getElementById("appointmentPurposeSelect");
    const appointmentNoteTextarea = document.getElementById("appointmentNoteTextarea");
    const appointmentMicBtn = document.getElementById("appointmentMicBtn");
    const appointmentSubmitBtn = document.getElementById("appointmentSubmitBtn");
    const appointmentCancelBtn = document.getElementById("appointmentCancelBtn");
    const appointmentFormStatus = document.getElementById("appointmentFormStatus");
    const appointmentDayScheduleEmpty = document.getElementById("appointmentDayScheduleEmpty");
    const appointmentDayScheduleList = document.getElementById("appointmentDayScheduleList");
    const appointmentConfirmMessage = document.getElementById("appointmentConfirmMessage");
    const appointmentConfirmYesBtn = document.getElementById("appointmentConfirmYesBtn");
    const appointmentConfirmNoBtn = document.getElementById("appointmentConfirmNoBtn");
    const appointmentNoticeOverlay = document.getElementById("appointment-notice-overlay");
    const appointmentNoticeTitle = document.getElementById("appointmentNoticeTitle");
    const appointmentNoticeMessage = document.getElementById("appointmentNoticeMessage");
    const appointmentNoticeCloseBtn = document.getElementById("appointmentNoticeCloseBtn");
    const state = {
        audio: true,
        faceDataUrl: null,
        sourceImages: [],
        serverQRUrl: null,
        qrScanner: null,

        // プレゼント検知 (Cam2 → Python)
        presenceSending: false,
        // Mac Mini M4 向け: 応答性を優先したphát hiệnレート
        presenceFps: 25,
        // 顔phát hiệnエンドポイント (顔の bbox)
        presenceEndpoint: "/api/presence/frame",
        faceEndpoint: "/api/face/frame",
        // ボックス描画済みのフレームを返すエンドポイント (drawBoxesOnStream=true の場合に使用)
        presenceEndpointWithBoxes: "/api/face/frame_with_boxes",
        drawBoxesOnStream: false,  // true = サーバーからのフレームに直接ボックスを描画
        /** 顔を連続してphát hiệnしてから自動撮影するまでの時間 (ms) — この変数を変更して時間を調整してください。 */
        faceAutoCaptureMs: 650,
        faceSeenSinceMs: 0,
        faceAutoCaptured: false,
        faceCaptureReadyAtMs: 0,
        faceGuideLostAtMs: 0,

        // quétライフサイクル
        scanLockedCam1: false,
        scanLockedCam2: false,
        isSubmitting: false,

        // Cam2 ズーム
        video2ZoomRunning: false,
        video2ZoomHandle: null,
        video2Frozen: false,
        video2ZoomFactor: 1,    // 2.5x zoom
        video2LastFrameDrawAt: 0,
        _video2RestoreGeneration: 0,
        _cam2RestoreInFlight: false,
        cam2LastVideoTime: 0,
        cam2LastVideoAdvanceAt: 0,

        // 生バッファ / 構造化データ
        lastQRRaw: null,
        lastBCardText: null,
        lastBCardFields: null,
        bcardImageDataUrl: null,
        registrationId: null,
        cccdFlowActive: false,
        qrResolvedProfile: null,

        // OCR & danh thiếp自動撮影
        allowPresence: true,        // 初めからオンにしてngười dùngを歓迎する
        emptyGapCount: 0,           // đặt lại用に空のフレームをカウント
        emptyGapRequired: 2,       // đặt lạiするために連続した空のフレーム（10フレーム）が必要
        removingGapRequired: 4,    // REMOVING 中も十分安定しつつ、カード取り出し後は早めに戻す
        cardAutoSending: false,     // danh thiếp自動phát hiệnフレームを送信中
        cardAutoDone: false,        // 安定したdanh thiếpを1つ受信済み
        cardAutoFps: 12,            // Tracking bbox を遅らせないよう card detect の送信レートを少し上げる
        cardDetectWidth: 512,       // Tracking 用は軽量化のため低めの幅で送る
        cardDetectSensitiveWidth: 640, // REMOVING / Welcome 中も 1280 ではなく 640 に抑える
        cardDetectJpegQuality: 0.42,
        cardDetectSensitiveJpegQuality: 0.55,

        // エンドポイント
        payloadEndpoint: "/api/presence/payload",
        bcardOCREndpoint: "/api/ocr/bcard",
        bcardOCRAsyncStartEndpoint: "/api/ocr/bcard_async/start",
        bcardOCRAsyncQuickStartEndpoint: "/api/ocr/bcard_async/quick",
        bcardOCRAsyncStatusBase: "/api/ocr/bcard_async/status",
        cccdAnalyzeEndpoint: "/api/ocr/cccd_qr_ocr",
        cccdDraftEndpoint: "/api/cccd/draft",
        cardAutoEndpoint: "/api/card/frame",
        kioskSettingsEndpoint: "/api/kiosk/settings",
        appointmentDayEndpoint: "/api/appointments/day",
        appointmentCreateEndpoint: "/api/appointments",
        autoCyclePhase: "IDLE", // IDLE, CARD, FACE, SUBMITTING
        presenceGreetCooldownMs: 8000,      // 挨拶の間のクールダウン 2s
        presenceLastGreetTs: 0,
        presenceLastHadPerson: false,
        presenceLastFaceCount: 0,
        presenceFaceIncreaseStreak: 0,
        presenceStableIncreaseFrames: 1,
        suppressGreetingDuringCompletion: false,
        audioQueue: [],             // âm thanh再生キュー
        isAudioPlaying: false,       // 再生状態
        cardRetryCount: 0,           // カード読み取り失敗回数
        handlingInvalidQr: false,
        welcomeIdleTimeoutMs: 30000,
        welcomeIdleTimer: null,
        welcomeHideDelayMs: 900,
        welcomeHideTimer: null,
        welcomeEyesVisible: HAS_WELCOME_OVERLAY,
        pageVisible: true,
        interactionResumeAtMs: 0,
        ignoreVisibilityGuard: true,
        ocrTaskId: null,
        ocrStatus: "idle", // idle, processing, done, error
        ocrPollHandle: null,
        sessionFinalizeTriggered: false,
        cardRetryRequested: false,
        faceGuideAudioTimer: null,
        faceRetryCount: 0,           // 顔撮影リトライ回数 (最大 3)
        faceRetryMaxCount: 15,        // リトライ制限
        faceRetryTimer: null,        // âm thanh後の確認待ちタイマー 2s
        thankYouResetTimer: null,    // 感謝バッジ表示後のđặt lạiタイマー
        removingForceResetTimer: null,
        removingRequiresCompletionAudio: false,
        cardDetectSuppressUntilMs: 0,
        completionAudioDone: false,  // 完了âm thanhの再生thoátを待ってからđặt lạiする
        audioPrimed: false,
        faceProcessingBadgeShownAt: 0,
        faceProcessingBadgeMinMs: 1500,
		faceRecognizeStartEndpoint: "/api/face/recognize_async",
        faceJobStatusBase: "/api/face/job",
        faceRecognitionJobId: null,
        faceRecognitionStatus: "idle",
        faceRecognitionPollHandle: null,
        faceRecognitionSending: false,
        faceRecognitionCooldownMs: 8000,
        faceRecognitionLastAttemptAt: 0,
        faceRecognitionSeenSinceMs: 0,
        faceRecognitionStableMs: 600,
        faceRecognitionOverlayTimer: null,
        faceRecognitionAwaitFaceExit: false,
        faceGuideEnabled: true,
        faceGuideLastInside: false,
        faceGuideOvalWidthRatio: 0.50,
        faceGuideOvalHeightRatio: 1.12,
        faceGuideCenterYRatio: 0.54,
        faceGuideMinFaceHeightRatio: 0.10,
        faceGuideEllipseSlack: 0.18,
        faceGuideHoldToleranceMs: 280,
        _resetRestartTimer: null,    // resetAll 後のcamerakhởi động lạiタイマー（即座のđặt lạiをキャンセルするため）
        _presenceGeneration: 0,      // 二重の presence ループ防止用の世代カウンター
        speculativeTextThreshold: 20, // リトライケースで「情報あり」とみなす最小文字数
        appointmentOverlayEnabled: !!(window.KIOSK_CONFIG && window.KIOSK_CONFIG.appointmentOverlayEnabled),
        appointmentConfirmCallback: null,
        appointmentConfirmCancelCallback: null,
        appointmentNoticeTimer: null,
        appointmentDayItems: [],
        appointmentSpeechRecognition: null,
        appointmentMicActive: false,
        appointmentPendingFinalizePayload: null,
        appointmentPendingFinalizeSource: "",
        appointmentPromptTimer: null,
        pendingCardRemovalReset: false,
        isResetting: false,
        returningVisitorGreetingActive: false,
        returningVisitorGreetingSuppressUntilMs: 0,
        // ロボットアバターロジック
        avatar: {
            target: { x: 0.5, y: 0.5 },
            cur: { x: 0.5, y: 0.5 },
            rafId: null,
            blinkTimer: null,
            isSpeaking: false,
            metrics: { eyeW: 0, eyeH: 0, radiusX: 0, radiusY: 0, faceW: 0, faceH: 0 }
        }
    };

    function isPageInteractionActive() {
        return document.visibilityState === "visible" && state.pageVisible;
    }

    function suppressAutoCaptureForTabChange(reason = "") {
        const now = Date.now();
        state.pageVisible = false;
        state.interactionResumeAtMs = now + 1500;
        state.faceSeenSinceMs = 0;
        state.faceAutoCaptured = false;
        state.faceCaptureReadyAtMs = now + 1500;
        state.faceGuideLostAtMs = 0;
        state.cardDetectSuppressUntilMs = Math.max(state.cardDetectSuppressUntilMs || 0, now + 1500);
        state.lastPersonBox = null;
        state.lastFrameSize = null;
        // Giữ nguyên frame cuối trên zoom canvas để tránh lộ raw video và mất crop/orientation.
        stopVideo2ZoomLoop(false);
        setVideo2PreviewMode(true);
        if (reason) log(`Đã bật bảo vệ khi chuyển tab: ${reason}.`);
    }

    function scheduleCam2Restore(reason = "", delayMs = 60) {
        timerManager.setNamedTimeout(state, "cam2RestoreHandle", () => {
            restoreCam2PreviewAfterVisibilityChange(reason);
        }, delayMs);
    }

    function ensureCam2HealthMonitor() {
        timerManager.setNamedInterval(state, "cam2HealthCheckHandle", async () => {
            if (document.visibilityState !== "visible" || !state.pageVisible) return;
            if (state._cam2RestoreInFlight) return;
            const vid = $("#video2");
            if (!vid || !vid.srcObject) return;

            const now = Date.now();
            const currentTime = Number(vid.currentTime || 0);
            if (currentTime > (state.cam2LastVideoTime || 0) + 0.01) {
                state.cam2LastVideoAdvanceAt = now;
                state.cam2LastVideoTime = currentTime;
            }

            const noRecentZoomFrame = now - (state.video2LastFrameDrawAt || 0) > 1200;
            const noRecentVideoAdvance = now - (state.cam2LastVideoAdvanceAt || 0) > 1600;
            const notReady = (vid.readyState || 0) < 2;
            if (!noRecentZoomFrame && !noRecentVideoAdvance && !notReady) return;

            log("Cam2 health monitor phát hiện preview bị treo. Đang khôi phục camera 2.");
            scheduleCam2Restore("health monitor", 0);
        }, 1200);
    }
    function computeAvatarMetrics() {
        return kioskWelcomeController?.computeAvatarMetrics();
    }

    function tickAvatar() {
        return kioskWelcomeController?.tickAvatar();
    }

    function randomBlink() {
        return kioskWelcomeController?.randomBlink();
    }


    state.cam1Facing = "user"; // または "user"
    state.cam2Facing = "user"; // または "user"

    const ui = {
        btnRegister: document.querySelector("#btn-register"),
        btnPrintQR: document.querySelector("#btn-print-qr"),
        btnPrint3D: document.querySelector("#btn-print-3d"),
    };

    let kioskAudioController = null;
    let kioskWelcomeController = null;
    let kioskAsyncController = null;
    let kioskPresenceController = null;

    function setDisabled(el, disabled) {
        if (!el) return;
        if (disabled) {
            el.setAttribute('disabled', '');
            el.classList.add('is-disabled');
        } else {
            el.removeAttribute('disabled');
            el.classList.remove('is-disabled');
        }
    }

    function hasCccdData() {
        const name = getVal("#fullName");
        const id = getVal("#idNumber");
        return !!(name && id);
    }

    function isCccdFlowActive() {
        // CCCD flow có thể đã lưu draft từ OCR ngay cả khi input UI chưa kịp/không được fill.
        // Ta dùng thêm cờ trạng thái để không bỏ qua bước gửi `face_image`/embedding.
        return !!state.cccdFlowActive || hasCccdData();
    }

    function hasBcardData() {
        const f = state.lastBCardFields || collectBCardFields();
        if (!f) return false;
        const vals = [
            f.full_name || f.name,
            f.email,
            f.phone || f.tel,
            f.title || f.position || f.role,
            f.company || f.org,
            f.address,
        ];
        return vals.some(v => (v || "").trim().length > 0);
    }

    function updateActionButtons() {
        const readyForRegister = hasCccdData() || hasBcardData();
        setDisabled(ui.btnRegister, !readyForRegister || state.isSubmitting);
        setDisabled(ui.btnPrintQR, !state.serverQRUrl);
        setDisabled(ui.btnPrint3D, !state.faceDataUrl);
        updateStepRail();
    }

    // オーバーレイNguồn用の cam1 状態を出力
    window.cam1Started = false;

    function makeKioskAudio(fileName) {
        const audio = new Audio();
        audio.preload = "auto";
        audio.dataset.soundFile = fileName;
        audio.playbackRate = 1.15;
        audio.defaultPlaybackRate = 1.15;
        audio.preservesPitch = false;
        refreshKioskAudioSource(audio);
        return audio;
    }

    function refreshKioskAudioSource(audio) {
        if (!audio || !audio.dataset || !audio.dataset.soundFile) return;
        const fileName = audio.dataset.soundFile;
        const nextSrc = window.I18N && typeof window.I18N.soundUrl === "function"
            ? window.I18N.soundUrl(fileName)
            : "/static/sound/" + fileName;
        if (audio.getAttribute("src") !== nextSrc) {
            audio.setAttribute("src", nextSrc);
            try { audio.load(); } catch (_) {}
        }
    }

    const sndThank = makeKioskAudio("camonjp.mp3");
    const sndFaceGuide = makeKioskAudio("huongdanchupface.mp3");
    const sndGreet = makeKioskAudio("chaobanjp.mp3");
    const sndCardQrGuide = makeKioskAudio("huongdanchupcardvaqr.mp3");
    const sndRegisterDone = makeKioskAudio("camonjp.mp3");
    const sndQrInvalid = makeKioskAudio("qrkohople.mp3");
    const sndCardUnread = makeKioskAudio("ChuadocdcDanhthiep.mp3");
    const sndFaceNotReady = makeKioskAudio("chuaromat.mp3");
    const allAudio = [
        sndThank,
        sndFaceGuide,
        sndGreet,
        sndCardQrGuide,
        sndRegisterDone,
        sndQrInvalid,
        sndCardUnread,
        sndFaceNotReady,
    ];

    function refreshAllKioskAudioSources() {
        allAudio.forEach(refreshKioskAudioSource);
    }

    window.addEventListener("i18n:languagechange", refreshAllKioskAudioSources);

    function log(msg) {
        const t = new Date().toLocaleTimeString();
        if (logEl) logEl.innerText = `[${t}] ${msg}\n` + logEl.innerText;
        else console.log(msg);
    }

    if (welcomeControllerFactory && typeof welcomeControllerFactory.createWelcomeController === "function") {
        kioskWelcomeController = welcomeControllerFactory.createWelcomeController(state, {
            timerManager,
            querySelector: (selector) => document.querySelector(selector),
            onWelcomeVisibilityChange: (visible) => {
                state.welcomeEyesVisible = !!visible;
            },
        });
    }

    if (audioControllerFactory && typeof audioControllerFactory.createAudioController === "function") {
        kioskAudioController = audioControllerFactory.createAudioController(state, {
            log,
            getAudioList: () => allAudio,
            onAudioPlayStateChange: (isPlaying) => {
                if (kioskWelcomeController && typeof kioskWelcomeController.setSpeakingState === "function") {
                    kioskWelcomeController.setSpeakingState(isPlaying);
                }
            },
        });
    }

    if (asyncControllerFactory && typeof asyncControllerFactory.createAsyncController === "function") {
        kioskAsyncController = asyncControllerFactory.createAsyncController(state, {
            timerManager,
            fetchImpl: (url, init) => fetch(url, init),
            log,
            isFaceRecognitionEligible: () => isFaceRecognitionEligible(),
            onFaceRecognitionMatched: async ({ name, subtitle, audioUrl, score }) => {
                state.faceRecognitionAwaitFaceExit = true;
                showReturningVisitorOverlayThenPlayGreeting(name, subtitle, audioUrl);
                log(`Nhận diện khuôn mặt khớp: ${name} (${Number(score || 0).toFixed(4)})`);
            },
            onFaceRecognitionNotMatched: ({ score }) => {
                state.faceRecognitionAwaitFaceExit = true;
                log(`Nhận diện khuôn mặt: không tìm thấy khách đã đăng ký. score=${Number(score || 0).toFixed(4)}. Tạm dừng xác thực cho đến khi khuôn mặt rời khỏi khung hình.`);
            },
            onFaceRecognitionError: ({ error, rawOutput }) => {
                log(`Lỗi nhận diện khuôn mặt: ${error || "Lỗi không xác định"}`);
                if (rawOutput) {
                    log(`Dữ liệu thô nhận diện khuôn mặt: ${rawOutput}`);
                }
            },
            onBcardOcrDone: async ({ fields, text }) => {
                finishBCardProcessingUI(fields, text);
                await tryFinalizeSessionAfterFaceAndOcr("ocr-done");
            },
            onBcardOcrError: ({ taskId, error }) => {
                log(`OCR Task ${taskId} error: ${error}`);
            },
        });
    }

    if (presenceControllerFactory && typeof presenceControllerFactory.createPresenceController === "function") {
        kioskPresenceController = presenceControllerFactory.createPresenceController(state, {
            clearWelcomeIdleTimer: () => clearWelcomeIdleTimer(),
            scheduleHideWelcomeEyes: () => scheduleHideWelcomeEyes(),
            showWelcomeEyes: (show) => showWelcomeEyes(show),
            scheduleWelcomeIdleReturn: () => scheduleWelcomeIdleReturn(),
            playQueuedAudio: (audio) => playQueuedAudio(audio),
            log,
            greetAudio: sndGreet,
            cardGuideAudio: sndCardQrGuide,
        });
    }

function isFaceRecognitionEligible() {
        return (
            state.autoCyclePhase === "IDLE" &&
            !state.faceDataUrl &&
            !state.isSubmitting &&
            !state.faceRecognitionSending &&
            !state.faceRecognitionJobId &&
            !state.faceRecognitionAwaitFaceExit &&
            !hasBcardData() &&
            !hasCccdData() &&
            !state.scanLockedCam2
        );
    }

    function stopFaceRecognitionPolling() {
        return kioskAsyncController?.stopFaceRecognitionPolling();
    }

    function hideReturningVisitorOverlay() {
        return kioskWelcomeController?.hideReturningVisitorOverlay();
    }

    function isReturningVisitorOverlayVisible() {
        return !!kioskWelcomeController?.isReturningVisitorOverlayVisible();
    }

    function showReturningVisitorOverlay(name, subtitle, title = "") {
        return kioskWelcomeController?.showReturningVisitorOverlay(name, subtitle, title);
    }

    const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition || null;
    const APPOINTMENT_REASON_MAX_LEN = 500;
    const APPOINTMENT_DESC_MAX_LEN = 2000;

    function setAppointmentOverlayVisible(overlay, visible) {
        if (!overlay) return;
        overlay.classList.toggle("is-hidden", !visible);
        overlay.setAttribute("aria-hidden", visible ? "false" : "true");
    }

    function closeAppointmentConfirm() {
        state.appointmentConfirmCallback = null;
        state.appointmentConfirmCancelCallback = null;
        setAppointmentOverlayVisible(appointmentConfirmOverlay, false);
    }

    function openAppointmentConfirm(options, onConfirm, onCancel) {
        let message = typeof options === 'string' ? options : (options.message || "");
        let title = typeof options === 'object' && options.title ? options.title : t("appt.confirm.title");
        let yesText = typeof options === 'object' && options.yesText ? options.yesText : t("btn.confirm");
        let noText = typeof options === 'object' && options.noText ? options.noText : t("btn.close");

        if (appointmentConfirmMessage) {
            if (message) {
                appointmentConfirmMessage.textContent = message;
                appointmentConfirmMessage.hidden = false;
            } else {
                appointmentConfirmMessage.textContent = "";
                appointmentConfirmMessage.hidden = true;
            }
        }
        const confirmTitle = document.getElementById("appointmentConfirmTitle");
        if (confirmTitle) {
            confirmTitle.textContent = title;
        }
        const yesBtn = document.getElementById("appointmentConfirmYesBtn");
        if (yesBtn) yesBtn.textContent = yesText;
        
        const noBtn = document.getElementById("appointmentConfirmNoBtn");
        if (noBtn) noBtn.textContent = noText;

        state.appointmentConfirmCallback = typeof onConfirm === "function" ? onConfirm : null;
        state.appointmentConfirmCancelCallback = typeof onCancel === "function" ? onCancel : null;
        setAppointmentOverlayVisible(appointmentFormOverlay, false);
        setAppointmentOverlayVisible(appointmentConfirmOverlay, true);
    }

    function closeAppointmentNotice() {
        timerManager.clearNamed(state, "appointmentNoticeTimer");
        setAppointmentOverlayVisible(appointmentNoticeOverlay, false);
    }

    function openAppointmentNotice(message, { title = "", isError = false, autoCloseMs = 0 } = {}) {
        timerManager.clearNamed(state, "appointmentNoticeTimer");
        if (appointmentNoticeTitle) {
            appointmentNoticeTitle.textContent = title || t("appt.notice.title");
        }
        if (appointmentNoticeMessage) {
            appointmentNoticeMessage.textContent = String(message || "").trim() || t("appt.error.default");
            appointmentNoticeMessage.style.color = isError ? "#b91c1c" : "var(--text)";
        }
        if (appointmentNoticeCloseBtn) {
            appointmentNoticeCloseBtn.hidden = Number(autoCloseMs) > 0;
        }
        setAppointmentOverlayVisible(appointmentNoticeOverlay, true);
        if (Number(autoCloseMs) > 0) {
            return new Promise((resolve) => {
                timerManager.setNamedTimeout(state, "appointmentNoticeTimer", () => {
                    closeAppointmentNotice();
                    resolve();
                }, Number(autoCloseMs));
            });
        }
        return Promise.resolve();
    }

    function formatAppointmentDateValue(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    function formatAppointmentTimeRange(item) {
        const start = String(item && item.start_time ? item.start_time : "").trim();
        const end = String(item && item.end_time ? item.end_time : "").trim();
        if (start && end) return `${start} - ${end}`;
        if (start) return start;
        if (end) return end;
        return t("dash.appt.all.day", "Cả ngày");
    }

    function getAppointmentContactName() {
        const bcard = collectBCardFields() || state.lastBCardFields || {};
        const name = (bcard.full_name || bcard.name || "").trim();
        if (name) return name;
        return (collectFormData().fullName || "").trim();
    }

    function getAppointmentDefaultDescription() {
        const bcard = collectBCardFields() || state.lastBCardFields || {};
        const company = (bcard.company || bcard.org || "").trim();
        return company ? `${t("dash.table.company", "Công ty")}: ${company}` : "";
    }

    function showAppointmentFormStatus(message, isError = false) {
        if (!appointmentFormStatus) return;
        appointmentFormStatus.hidden = !message;
        appointmentFormStatus.textContent = message || "";
        appointmentFormStatus.style.borderColor = isError ? "rgba(220, 38, 38, 0.24)" : "rgba(13, 143, 143, 0.22)";
        appointmentFormStatus.style.background = isError ? "rgba(254, 242, 242, 0.94)" : "rgba(13, 143, 143, 0.08)";
        appointmentFormStatus.style.color = isError ? "#b91c1c" : "var(--primary)";
    }

    function fillSelectOptions(selectEl, values, placeholder) {
        if (!selectEl) return;
        const openSize = Number(selectEl.getAttribute("size") || "1");
        const currentValue = String(selectEl.value || "");
        selectEl.innerHTML = "";
        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = placeholder;
        selectEl.appendChild(defaultOption);
        (values || []).forEach((value) => {
            if (value && typeof value === "object" && Array.isArray(value.values)) {
                const group = document.createElement("optgroup");
                group.label = String(value.label || "").trim() || t("appt.time.window", "Khung giờ");
                value.values.forEach((groupValue) => {
                    const option = document.createElement("option");
                    option.value = groupValue;
                    option.textContent = groupValue;
                    if (groupValue === currentValue) option.selected = true;
                    group.appendChild(option);
                });
                if (group.children.length) {
                    selectEl.appendChild(group);
                }
                return;
            }
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value;
            if (value === currentValue) option.selected = true;
            selectEl.appendChild(option);
        });
        selectEl.setAttribute("size", String(openSize > 1 ? openSize : 1));
    }

    function slotOverlaps(item, startTime, endTime) {
        const itemStart = String(item && item.start_time ? item.start_time : "").trim();
        const itemEnd = String(item && item.end_time ? item.end_time : "").trim();
        if (!itemStart || !itemEnd || !startTime || !endTime) return false;
        return itemStart < endTime && itemEnd > startTime;
    }

    function appointmentTimeToMinutes(value) {
        const raw = String(value || "").trim();
        if (!/^\d{2}:\d{2}$/.test(raw)) return -1;
        const [hour, minute] = raw.split(":").map(Number);
        if (!Number.isFinite(hour) || !Number.isFinite(minute)) return -1;
        return (hour * 60) + minute;
    }

    function appointmentMinutesToTime(totalMinutes) {
        const hour = Math.floor(totalMinutes / 60);
        const minute = totalMinutes % 60;
        return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
    }

    function roundUpToNextHalfHour(dateObj) {
        const next = new Date(dateObj.getTime());
        next.setSeconds(0, 0);
        const minutes = next.getMinutes();
        const remainder = minutes % 30;
        if (remainder !== 0) {
            next.setMinutes(minutes + (30 - remainder));
        }
        return appointmentMinutesToTime((next.getHours() * 60) + next.getMinutes());
    }

    function getAppointmentTimeWindows(kind = "start") {
        if (kind === "end") {
            return [
                { label: t("appt.period.morning"), start: "09:00", end: "12:00" },
                { label: t("appt.period.afternoon"), start: "13:30", end: "17:30" },
            ];
        }
        return [
            { label: t("appt.period.morning"), start: "08:30", end: "11:30" },
            { label: t("appt.period.afternoon"), start: "13:00", end: "17:00" },
        ];
    }

    function buildAppointmentTimeOptions(kind = "start") {
        const options = [];
        getAppointmentTimeWindows(kind).forEach((windowDef) => {
            const startMinutes = appointmentTimeToMinutes(windowDef.start);
            const endMinutes = appointmentTimeToMinutes(windowDef.end);
            for (let current = startMinutes; current <= endMinutes; current += 30) {
                options.push(appointmentMinutesToTime(current));
            }
        });
        return options;
    }

    function buildAppointmentTimeGroups(kind = "start", values = []) {
        const valueSet = new Set(values || []);
        return getAppointmentTimeWindows(kind)
            .map((windowDef) => {
                const startMinutes = appointmentTimeToMinutes(windowDef.start);
                const endMinutes = appointmentTimeToMinutes(windowDef.end);
                const groupedValues = [];
                for (let current = startMinutes; current <= endMinutes; current += 30) {
                    const slot = appointmentMinutesToTime(current);
                    if (valueSet.has(slot)) {
                        groupedValues.push(slot);
                    }
                }
                return { label: windowDef.label, values: groupedValues };
            })
            .filter((group) => group.values.length);
    }

    function getAppointmentCurrentStartFloor(dateValue) {
        if (!dateValue) return "";
        const today = new Date();
        if (dateValue !== formatAppointmentDateValue(today)) return "";
        return roundUpToNextHalfHour(today);
    }

    function getAvailableAppointmentSlots() {
        const dateValue = String(appointmentDateInput ? appointmentDateInput.value : "").trim();
        const currentFloor = getAppointmentCurrentStartFloor(dateValue);
        const allSlots = buildAppointmentTimeOptions("start");
        return allSlots.filter((slot, index) => {
            const nextSlot = allSlots[index + 1];
            if (!nextSlot) return false;
            if (currentFloor && slot < currentFloor) return false;
            return !state.appointmentDayItems.some((item) => slotOverlaps(item, slot, nextSlot));
        });
    }

    function updateAppointmentTimeSelects() {
        const availableSlots = getAvailableAppointmentSlots();
        const currentStart = String(appointmentStartTimeSelect ? appointmentStartTimeSelect.value : "").trim();
        const currentEnd = String(appointmentEndTimeSelect ? appointmentEndTimeSelect.value : "").trim();
        fillSelectOptions(appointmentStartTimeSelect, buildAppointmentTimeGroups("start", availableSlots), t("appt.select.start"));
        const endCandidates = buildAppointmentTimeOptions("end").filter((slot) => slot > String(appointmentStartTimeSelect ? appointmentStartTimeSelect.value : "").trim());
        fillSelectOptions(appointmentEndTimeSelect, buildAppointmentTimeGroups("end", endCandidates), t("appt.select.end"));
        if (appointmentStartTimeSelect && availableSlots.includes(currentStart)) {
            appointmentStartTimeSelect.value = currentStart;
        }
        const selectedStart = String(appointmentStartTimeSelect ? appointmentStartTimeSelect.value : "").trim();
        const filteredEndCandidates = buildAppointmentTimeOptions("end").filter((slot) => {
            if (!selectedStart || slot <= selectedStart) return false;
            return !state.appointmentDayItems.some((item) => slotOverlaps(item, selectedStart, slot));
        });
        fillSelectOptions(appointmentEndTimeSelect, buildAppointmentTimeGroups("end", filteredEndCandidates), t("appt.select.end"));
        if (appointmentEndTimeSelect && filteredEndCandidates.includes(currentEnd)) {
            appointmentEndTimeSelect.value = currentEnd;
        }
    }

    function setAppointmentTimeSelectExpanded(selectEl, expanded) {
        if (!selectEl) return;
        selectEl.classList.toggle("is-open", !!expanded);
        selectEl.setAttribute("size", expanded ? "4" : "1");
    }

    function normalizeSpeechTimeHourMinute(hourValue, minuteValue) {
        const hour = Number(hourValue);
        const minute = Number(minuteValue || 0);
        if (!Number.isFinite(hour) || !Number.isFinite(minute)) return "";
        if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return "";
        return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
    }

    function applyParsedDateTimeFromNote(textValue) {
        const text = String(textValue || "").trim();
        if (!text) return;
        const dateMatch = text.match(/(\d{1,2})[\/\-](\d{1,2})(?:[\/\-](\d{2,4}))?/);
        if (dateMatch && appointmentDateInput) {
            const current = new Date();
            const day = Number(dateMatch[1]);
            const month = Number(dateMatch[2]);
            let year = dateMatch[3] ? Number(dateMatch[3]) : current.getFullYear();
            if (year < 100) year += 2000;
            const parsedDate = new Date(year, month - 1, day);
            if (!Number.isNaN(parsedDate.getTime())) {
                appointmentDateInput.value = formatAppointmentDateValue(parsedDate);
                loadAppointmentDaySchedule(appointmentDateInput.value);
            }
        }

        const rangeMatch = text.match(/(?:từ\s*)?(\d{1,2})(?:[:h](\d{1,2}))?\s*(?:đến|\-)\s*(\d{1,2})(?:[:h](\d{1,2}))?/i);
        if (!rangeMatch) return;
        const startValue = normalizeSpeechTimeHourMinute(rangeMatch[1], rangeMatch[2]);
        const endValue = normalizeSpeechTimeHourMinute(rangeMatch[3], rangeMatch[4]);
        if (appointmentStartTimeSelect && startValue) {
            appointmentStartTimeSelect.value = startValue;
            updateAppointmentTimeSelects();
        }
        if (appointmentEndTimeSelect && endValue) {
            appointmentEndTimeSelect.value = endValue;
        }
    }

    function stopAppointmentMic(force = false) {
        if (state.appointmentSpeechRecognition) {
            try {
                state.appointmentSpeechRecognition.stop();
            } catch (_err) {
                // ignore stop race
            }
        }
        if (force || !state.appointmentSpeechRecognition) {
            state.appointmentMicActive = false;
            if (appointmentMicBtn) appointmentMicBtn.classList.remove("is-recording");
        }
    }

    function startAppointmentMic() {
        if (!SpeechRecognitionCtor || !appointmentNoteTextarea) {
            showAppointmentFormStatus(t("appt.voice.unsupported"), true);
            return;
        }
        if (state.appointmentMicActive) return;
        const recognition = new SpeechRecognitionCtor();
        recognition.lang = "vi-VN";
        recognition.interimResults = true;
        recognition.continuous = true;
        const baseText = String(appointmentNoteTextarea.value || "").trim();
        state.appointmentSpeechRecognition = recognition;
        state.appointmentMicActive = true;
        if (appointmentMicBtn) appointmentMicBtn.classList.add("is-recording");
        showAppointmentFormStatus(t("appt.voice.listening"), false);
        recognition.onresult = function (event) {
            let transcript = "";
            for (let index = event.resultIndex; index < event.results.length; index += 1) {
                transcript += event.results[index][0].transcript || "";
            }
            appointmentNoteTextarea.value = [baseText, transcript.trim()].filter(Boolean).join(baseText ? "\n" : "");
            applyParsedDateTimeFromNote(appointmentNoteTextarea.value);
        };
        recognition.onerror = function () {
            showAppointmentFormStatus(t("appt.voice.no.speech"), true);
            stopAppointmentMic(true);
        };
        recognition.onend = function () {
            state.appointmentSpeechRecognition = null;
            state.appointmentMicActive = false;
            if (appointmentMicBtn) appointmentMicBtn.classList.remove("is-recording");
        };
        try {
            recognition.start();
        } catch (_err) {
            showAppointmentFormStatus(t("appt.voice.error"), true);
            stopAppointmentMic(true);
        }
    }

    function renderAppointmentDayItems(items) {
        if (!appointmentDayScheduleList || !appointmentDayScheduleEmpty) return;
        appointmentDayScheduleList.innerHTML = "";
        const safeItems = Array.isArray(items) ? items : [];
        appointmentDayScheduleEmpty.style.display = safeItems.length ? "none" : "block";
        safeItems.forEach((item) => {
            const card = document.createElement("article");
            card.className = "appointment-day-item";
            const contact = String(item.contact_name || item.title || "Cuộc hẹn").trim();
            card.innerHTML = `<strong>${contact} - ${formatAppointmentTimeRange(item)}</strong>`;
            appointmentDayScheduleList.appendChild(card);
        });
    }

    async function refreshKioskAppointmentSetting() {
        try {
            const res = await fetch(`${state.kioskSettingsEndpoint}?t=${Date.now()}`, { method: "GET" });
            const js = await res.json().catch(() => ({}));
            if (res.ok && js?.ok && js.settings) {
                state.appointmentOverlayEnabled = !!js.settings.appointment_overlay_enabled;
            }
        } catch (_err) {
            // Keep the last known value if the setting endpoint is temporarily unavailable.
        }
        return state.appointmentOverlayEnabled;
    }

    async function loadAppointmentDaySchedule(dateValue) {
        if (!dateValue) {
            state.appointmentDayItems = [];
            renderAppointmentDayItems([]);
            return [];
        }
        showAppointmentFormStatus(t("appt.schedule.loading"), false);
        try {
            const res = await fetch(`${state.appointmentDayEndpoint}?date=${encodeURIComponent(dateValue)}`, { method: "GET" });
            const js = await res.json().catch(() => ({}));
            if (!res.ok || !js?.ok) {
                throw new Error(js?.error || t("dash.appt.error.load.day"));
            }
            state.appointmentDayItems = Array.isArray(js.items) ? js.items : [];
            renderAppointmentDayItems(state.appointmentDayItems);
            updateAppointmentTimeSelects();
            showAppointmentFormStatus("", false);
            return state.appointmentDayItems;
        } catch (err) {
            state.appointmentDayItems = [];
            renderAppointmentDayItems([]);
            updateAppointmentTimeSelects();
            showAppointmentFormStatus(err?.message || t("dash.appt.error.load.day"), true);
            return [];
        }
    }

    function resetAppointmentForm() {
        fillSelectOptions(appointmentStartTimeSelect, [], t("appt.select.start"));
        fillSelectOptions(appointmentEndTimeSelect, [], t("appt.select.end"));
        if (appointmentDateInput) {
            appointmentDateInput.value = formatAppointmentDateValue(new Date());
            appointmentDateInput.min = formatAppointmentDateValue(new Date());
        }
        if (appointmentPurposeSelect) appointmentPurposeSelect.value = "";
        if (appointmentNoteTextarea) appointmentNoteTextarea.value = "";
        if (appointmentStartTimeSelect) appointmentStartTimeSelect.value = "";
        if (appointmentEndTimeSelect) appointmentEndTimeSelect.value = "";
        state.appointmentDayItems = [];
        stopAppointmentMic(true);
        renderAppointmentDayItems([]);
        showAppointmentFormStatus("", false);
    }

    function clearAppointmentPromptTimer() {
        timerManager.clearNamed(state, "appointmentPromptTimer");
    }

    function isOverlayVisible(overlay) {
        return !!(overlay && !overlay.classList.contains("is-hidden"));
    }

    function hasBlockingCompletionOverlay() {
        return (
            isOverlayVisible(appointmentPromptOverlay) ||
            isOverlayVisible(appointmentFormOverlay) ||
            isOverlayVisible(appointmentConfirmOverlay) ||
            isOverlayVisible(appointmentNoticeOverlay)
        );
    }

    async function maybeResetAfterCardRemoval(reason = "") {
        if (!state.pendingCardRemovalReset) return false;
        if (state.isResetting) return false;
        if (state.autoCyclePhase !== "REMOVING") return false;
        if (hasBlockingCompletionOverlay()) {
            if (reason) {
                log(`Đã rút danh thiếp nhưng đang chờ đóng popup trước khi đặt lại${reason ? ` (${reason})` : ""}.`);
            }
            return false;
        }
        state.pendingCardRemovalReset = false;
        clearCardBbox();
        showRemoveCardOverlay(false);
        await resetAll(true);
        return true;
    }

    function openAppointmentPrompt() {
        resetAppointmentForm();
        clearAppointmentPromptTimer();
        setAppointmentOverlayVisible(appointmentPromptOverlay, true);
        setAppointmentOverlayVisible(appointmentFormOverlay, false);
        closeAppointmentConfirm();
        timerManager.setNamedTimeout(state, "appointmentPromptTimer", async function () {
            if (!appointmentPromptOverlay || appointmentPromptOverlay.classList.contains("is-hidden")) return;
            await continueFinalizeAfterAppointment("appointment-timeout");
        }, 4000);
    }

    function openAppointmentForm() {
        clearAppointmentPromptTimer();
        setAppointmentOverlayVisible(appointmentPromptOverlay, false);
        setAppointmentOverlayVisible(appointmentFormOverlay, true);
        closeAppointmentConfirm();
        if (appointmentDateInput && appointmentDateInput.value) {
            loadAppointmentDaySchedule(appointmentDateInput.value);
        }
    }

    function closeAllAppointmentOverlays() {
        clearAppointmentPromptTimer();
        setAppointmentOverlayVisible(appointmentPromptOverlay, false);
        setAppointmentOverlayVisible(appointmentFormOverlay, false);
        closeAppointmentConfirm();
        closeAppointmentNotice();
        stopAppointmentMic(true);
        showAppointmentFormStatus("", false);
        state.appointmentDayItems = [];
        renderAppointmentDayItems([]);
    }

    function playRecognizedVisitorGreeting(audioUrl) {
        const raw = String(audioUrl || "").trim();
        if (!raw) return Promise.resolve();
        let resolvedPath = raw;
        try {
            const parsed = new URL(raw, window.location.origin);
            if (parsed.origin === window.location.origin && parsed.pathname.startsWith("/static/sound/")) {
                const fileName = parsed.pathname.split("/").pop();
                if (fileName && window.I18N && typeof window.I18N.soundUrl === "function") {
                    resolvedPath = window.I18N.soundUrl(fileName);
                }
            }
        } catch { }
        const src = resolvedPath.startsWith("http") ? resolvedPath : new URL(resolvedPath, window.location.origin).toString();
        state.returningVisitorGreetingActive = true;
        state.audioQueue = state.audioQueue.filter((queuedAudio) => queuedAudio !== sndGreet);
        try {
            sndGreet.pause();
            sndGreet.currentTime = 0;
        } catch { }
        const audio = new Audio(src);
        audio.preload = "auto";
        audio.playbackRate = 1.15;
        audio.defaultPlaybackRate = 1.15;
        audio.preservesPitch = false;
        return playAudioAndWait(audio, true)
            .catch(() => { })
            .finally(() => {
                state.returningVisitorGreetingActive = false;
                state.returningVisitorGreetingSuppressUntilMs = Date.now() + 15000;
            });
    }

    function showReturningVisitorOverlayThenPlayGreeting(name, subtitle, audioUrl, title = "") {
        // Ẩn welcome eyes trước khi hiện returning visitor overlay
        showWelcomeEyes(false);
        showReturningVisitorOverlay(name, subtitle, title);
        requestAnimationFrame(() => {
            playRecognizedVisitorGreeting(audioUrl);
        });
    }

    function clearReturningVisitorRecognitionHold() {
        state.faceRecognitionSeenSinceMs = 0;
        state.faceRecognitionAwaitFaceExit = false;
        hideReturningVisitorOverlay();
    }

    function enterFacePhaseBasic() {
        clearReturningVisitorRecognitionHold();
        state.autoCyclePhase = "FACE";
        updateStepRail();
        state.allowPresence = true;
        state.faceAutoCaptured = false;
        state.faceSeenSinceMs = 0;
        state.faceGuideLostAtMs = 0;
        state.faceCaptureReadyAtMs = Date.now() + 300;
        state.suppressGreetingDuringCompletion = true;
        if (!state.faceDataUrl && !state.presenceSending) {
            startPresenceStream();
        }
    }

    async function pollFaceRecognitionStatus(jobId) {
        return kioskAsyncController?.pollFaceRecognitionStatus(jobId);
    }

    async function startFaceRecognitionFromBlob(blob) {
        return kioskAsyncController?.startFaceRecognitionFromBlob(blob);
    }
    
        async function primeAudioPlayback() {
        if (state.audioPrimed) return;
        state.audioPrimed = true;
        for (const audio of allAudio) {
            try {
                const prevMuted = audio.muted;
                const prevTime = audio.currentTime;
                audio.muted = true;
                audio.currentTime = 0;
                const p = audio.play();
                if (p && typeof p.then === "function") {
                    await p;
                }
                audio.pause();
                audio.currentTime = prevTime || 0;
                audio.muted = prevMuted;
            } catch (err) {
                audio.muted = false;
                log("Bỏ qua khởi tạo âm thanh: " + (err?.message || err));
            }
        }
    }

    function installAudioPrimer() {
        const unlockOnce = () => {
            primeAudioPlayback();
            window.removeEventListener("pointerdown", unlockOnce, true);
            window.removeEventListener("keydown", unlockOnce, true);
        };
        window.addEventListener("pointerdown", unlockOnce, true);
        window.addEventListener("keydown", unlockOnce, true);
    }

    function showWelcomeEyes(show) {
        return kioskWelcomeController?.showWelcomeEyes(show);
    }

    function scheduleHideWelcomeEyes() {
        return kioskWelcomeController?.scheduleHideWelcomeEyes();
    }

    function clearWelcomeIdleTimer() {
        return kioskWelcomeController?.clearWelcomeIdleTimer();
    }

    function shouldResetToWelcome() {
        return (
            state.autoCyclePhase !== "IDLE" ||
            !!state.faceDataUrl ||
            !!state.serverQRUrl ||
            !!state.lastQRRaw ||
            !!state.lastBCardText ||
            hasCccdData() ||
            hasBcardData()
        );
    }

    function scheduleWelcomeIdleReturn() {
        if (state.welcomeEyesVisible || state.welcomeIdleTimer) return;
        timerManager.setNamedTimeout(state, "welcomeIdleTimer", async () => {
            if (state.presenceLastHadPerson) return;

            // 問題 3: カード認識đặt lại - Cam1 トレイにカードが残っている場合はđặt lạiをブロック
            if (state.cardAutoDone || state.autoCyclePhase === "REMOVING") {
                log("Hết thời gian chờ nhưng vẫn còn thẻ trên khay. Đang yêu cầu người dùng lấy thẻ ra.");
                if (state.autoCyclePhase !== "REMOVING") {
                    enterRemovingPhase({ requireCompletionAudio: false, keepOverlayVisible: true });
                } else {
                    showRemoveCardOverlay(true, true);
                }
                return;
            }

            if (shouldResetToWelcome()) {
                await resetAll(true);
            }
            showWelcomeEyes(true);
            log("Không phát hiện người dùng trong 60 giây. Trả về màn hình chào (đặt lại mềm).");
        }, state.welcomeIdleTimeoutMs);
    }

    function handlePresenceReaction({ hasPerson, currentFaceCount, now }) {
        return kioskPresenceController?.handlePresenceReaction({ hasPerson, currentFaceCount, now });
    }

    // function speak(text) {
    //     if (!state.audio) return;
    //     try {
    //         const u = new SpeechSynthesisUtterance(text);
    //         u.lang = "vi-VN";
    //         speechSynthesis.cancel();
    //         speechSynthesis.speak(u);
    //     } catch { }
    // }

    /**
     * âm thanhキュー: 挨拶や案内が重ならないようにします。
     */
    function playQueuedAudio(audio) {
        return kioskAudioController?.playQueuedAudio(audio);
    }

    async function processAudioQueue() {
        return kioskAudioController?.processAudioQueue();
    }

    function playAudioAndWait(audio, forcePlay = false) {
        return kioskAudioController?.playAudioAndWait(audio, forcePlay) || Promise.resolve();
    }

    function interruptAndClearAudioQueue() {
        return kioskAudioController?.interruptAndClearAudioQueue();
    }

    document.addEventListener("visibilitychange", () => {
        const isVisible = document.visibilityState === "visible";
        state.pageVisible = isVisible;
        if (!isVisible) {
            suppressAutoCaptureForTabChange("document hidden");
            return;
        }
        state.interactionResumeAtMs = Date.now() + 1800;
        state.faceSeenSinceMs = 0;
        state.faceAutoCaptured = false;
        state.faceCaptureReadyAtMs = Date.now() + 1800;
        state.faceGuideLostAtMs = 0;
        scheduleCam2Restore("document visible", 60);
    });

    window.addEventListener("pagehide", () => {
        suppressAutoCaptureForTabChange("pagehide");
    });

    window.addEventListener("pageshow", () => {
        state.pageVisible = true;
        state.interactionResumeAtMs = Date.now() + 1800;
        state.faceSeenSinceMs = 0;
        state.faceAutoCaptured = false;
        state.faceCaptureReadyAtMs = Date.now() + 1800;
        scheduleCam2Restore("pageshow", 60);
    });

    window.addEventListener("focus", () => {
        if (document.visibilityState !== "visible") return;
        state.pageVisible = true;
        state.interactionResumeAtMs = Date.now() + 1800;
        state.faceSeenSinceMs = 0;
        state.faceAutoCaptured = false;
        state.faceCaptureReadyAtMs = Date.now() + 1800;
        scheduleCam2Restore("window focus", 60);
    });

    async function startFaceGuidanceAndArmCapture() {
        enterFacePhaseBasic();
        state.presenceFps = 20;
        // Stop Cam1 auto-card loop while waiting for face capture.
        // CCCD flow can otherwise drift back into card detection and abandon the face step.
        state.cardAutoSending = false;

        interruptAndClearAudioQueue();
        if (!state.presenceSending) {
            startPresenceStream();
        }
        // âm thanh遅延 3s — カードlỗiの場合に OCR が失敗するのに十分な時間
        timerManager.clearNamed(state, "faceGuideAudioTimer");
        timerManager.setNamedTimeout(state, "faceGuideAudioTimer", async () => {
            if (state.autoCyclePhase !== "FACE") return; // すでにキャンセル済み
            await playAudioAndWait(sndFaceGuide, true);
            if (state.autoCyclePhase === "FACE") {

                // N = 2s: 撮影許可から 1s 後、さらに 2s 待っても撮影できない場合に通知
                timerManager.clearNamed(state, "faceRetryTimer");
                timerManager.setNamedTimeout(state, "faceRetryTimer", async () => {
                    if (state.autoCyclePhase === "FACE" && !state.faceAutoCaptured) {
                        log(`Không thể chụp ảnh khuôn mặt (thử lại ${state.faceRetryCount + 1})...`);
                        // 問題 1: リマインドâm thanhは最大 3 回までに制限
                        if (state.faceRetryCount < state.faceRetryMaxCount) {
                            await playAudioAndWait(sndFaceNotReady, true);
                        }
                        state.faceRetryCount++;

                        // 常に繰り返します。リトライ回数による resetAll は行いません。
                        state.faceSeenSinceMs = 0;
                        state.faceCaptureReadyAtMs = Date.now() + 500;
                        state.faceGuideLostAtMs = 0;
                        startFaceRetryTimer();
                    }
                }, 2000); // 1s (ready) + 2s (N) = 3s
            }
        }, 1000);
    }

    function startFaceRetryTimer() {
        timerManager.clearNamed(state, "faceRetryTimer");
        timerManager.setNamedTimeout(state, "faceRetryTimer", async () => {
            if (state.autoCyclePhase === "FACE" && !state.faceAutoCaptured) {
                // 最大リトライ回数に達した場合は、中止してđặt lại
                if (state.faceRetryCount >= state.faceRetryMaxCount) {
                    log("Đã vượt quá số lần thử cho phép. Quay lại màn hình chờ.");
                    resetAll(true);
                    return;
                }

                log(`Vẫn chưa chụp được ảnh khuôn mặt (thử lại ${state.faceRetryCount + 1})...`);
                // 問題 1: リマインドâm thanhは最大 3 回までに制限
                if (state.faceRetryCount < 3) {
                    await playAudioAndWait(sndFaceNotReady, true);
                }
                state.faceRetryCount++;

                state.faceSeenSinceMs = 0;
                startFaceRetryTimer();
            }
        }, 5000); // 撮影できない場合、5giâyごとにリマインド
    }

    // ====== フォームエリアのヘルパー ======
    function getInfoSection() {
        const full = $("#fullName");
        if (full) {
            const form = full.closest(".form");
            const sec = form ? form.closest("section.panel") : null;
            return sec || document.querySelector(".right-pane") || document.body;
        }
        return document.querySelector(".right-pane") || document.body;
    }

    function ensureBCardPane() {
        let pane = document.getElementById("bcard-pane");
        if (pane) return pane;

        const infoSec = getInfoSection();
        if (!infoSec) return null;

        pane = document.createElement("div");
        pane.id = "bcard-pane";
        pane.className = "form form-12";
        pane.style.display = "none";
        pane.innerHTML = `
      <label class="span-3"><input id="bcardFullName" type="text" data-i18n="bcard.placeholder.name" data-i18n-attr="placeholder" placeholder="${t("bcard.placeholder.name")}"></label>
      <label class="span-3"><input id="bcardTitle" type="text" data-i18n="bcard.placeholder.title" data-i18n-attr="placeholder" placeholder="${t("bcard.placeholder.title")}"></label>
      <label class="span-3"><input id="bcardEmail" type="text" data-i18n="bcard.placeholder.email" data-i18n-attr="placeholder" placeholder="${t("bcard.placeholder.email")}"></label>
      <label class="span-3"><input id="bcardPhone" type="text" data-i18n="bcard.placeholder.phone" data-i18n-attr="placeholder" placeholder="${t("bcard.placeholder.phone")}"></label>
      <label class="span-3"><input id="bcardCompany" type="text" data-i18n="bcard.placeholder.company" data-i18n-attr="placeholder" placeholder="${t("bcard.placeholder.company")}"></label>
      <label class="span-3"><input id="bcardAddress" type="text" data-i18n="bcard.placeholder.address" data-i18n-attr="placeholder" placeholder="${t("bcard.placeholder.address")}"></label>
      <div id="bcard-raw" class="mono small muted span-3"></div>
      `;
        const cccdForm = infoSec.querySelector(".form");
        if (cccdForm && cccdForm.parentNode === infoSec) {
            cccdForm.after(pane);
        } else {
            infoSec.appendChild(pane);
        }
        return pane;
    }

    function toggleCCCDForm(show) {
        const infoSec = getInfoSection();
        if (!infoSec) return;
        const cccdForm = Array.from(infoSec.querySelectorAll(".form"))
            .find(f => f.querySelector("#fullName"));
        if (cccdForm) cccdForm.style.display = show ? "" : "none";
    }

    function toggleBCardPane(show) {
        const pane = ensureBCardPane();
        if (pane) pane.style.display = "none"; // người dùngの要求により常に非表示
    }

    function fillBCardPane(fields = {}, rawText = "") {
        setVal("#bcardFullName", fields.full_name || fields.name || "");
        setVal("#bcardEmail", fields.email || "");
        setVal("#bcardPhone", fields.phone || fields.tel || "");
        setVal("#bcardTitle", fields.title || fields.position || fields.role || "");
        setVal("#bcardCompany", fields.company || fields.org || "");
        setVal("#bcardAddress", fields.address || "");
        setVal("#bcardOtherinfo", fields.other_info || fields.info || rawText || "");

        const raw = $("#bcard-raw");
        if (raw) raw.textContent = (rawText || "").trim();
    }

    function normalizeBCardFields(fields = {}) {
        return {
            full_name: String(fields.full_name || fields.name || "").trim(),
            email: String(fields.email || "").trim(),
            phone: String(fields.phone || fields.tel || "").trim(),
            title: String(fields.title || fields.position || fields.role || "").trim(),
            company: String(fields.company || fields.org || "").trim(),
            address: String(fields.address || "").trim(),
            other_info: String(fields.other_info || fields.info || "").trim(),
        };
    }

    function mergeBCardFields(preferred = {}, fallback = {}) {
        const next = normalizeBCardFields(preferred);
        const prev = normalizeBCardFields(fallback);
        return {
            full_name: next.full_name || prev.full_name || "",
            email: next.email || prev.email || "",
            phone: next.phone || prev.phone || "",
            title: next.title || prev.title || "",
            company: next.company || prev.company || "",
            address: next.address || prev.address || "",
            other_info: next.other_info || prev.other_info || "",
        };
    }

    // ====== UI: カード取り出し要求オーバーレイ ======
    function ensureRemoveCardOverlay() {
        let el = document.getElementById("remove-card-overlay");
        if (el) return el;

        const infoSec = document.querySelector(".right-pane") || getInfoSection() || document.body;
        if (infoSec && getComputedStyle(infoSec).position === "static") {
            infoSec.style.position = "relative";
        }
        el = document.createElement("div");
        el.id = "remove-card-overlay";
        Object.assign(el.style, {
            position: "absolute",
            inset: "0",
            background: "rgba(0,0,0,0.75)",
            display: "none",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            zIndex: "1001",
            color: "#fff",
            textAlign: "center",
            backdropFilter: "blur(4px)",
        });

        el.innerHTML = `
            <div style="font-size:24px; font-weight:bold; color:#ff9800; margin-bottom:10px;">
                ${t("remove.card.thanks")}
            </div>
            <div id="remove-card-text" style="font-size:18px; line-height:1.5;">
                <b>${t("remove.card.message")}</b>
            </div>
        `;
        infoSec.appendChild(el);
        return el;
    }

    function showRemoveCardOverlay(show, hasCard = true) {
        const el = ensureRemoveCardOverlay();
        el.style.display = show ? "flex" : "none";
        if (show) {
            const txt = document.getElementById("remove-card-text");
            const title = el.firstElementChild;
            if (title) title.textContent = t("remove.card.thanks");
            if (txt) txt.innerHTML = `<b>${t("remove.card.message")}</b>`;
            if (txt) txt.style.display = hasCard ? "block" : "none";
        }
    }

    function enterRemovingPhase({ requireCompletionAudio = false, minVisibleMs = 0, keepOverlayVisible = true } = {}) {
        state.autoCyclePhase = "REMOVING";
        state.emptyGapCount = 0;
        state.removingRequiresCompletionAudio = !!requireCompletionAudio;
        state.removingPhaseMinUntil = minVisibleMs > 0 ? Date.now() + minVisibleMs : 0;
        state.completionAudioDone = !requireCompletionAudio;
        if (keepOverlayVisible) {
            showRemoveCardOverlay(true, true);
        }
    }

    const btnAudio = $("#btn-audio-toggle");
    if (btnAudio) btnAudio.addEventListener("click", () => {
        state.audio = !state.audio;
        btnAudio.textContent = state.audio ? t("bcard.audio.off") : t("bcard.audio.on");
    });
    installAudioPrimer();

    // ====== Camera defaults + localStorage key ======
    const CAM1_PREF_KEY = "kiosk_cam1_deviceId";
    const CAM2_PREF_KEY = "kiosk_cam2_deviceId";

    function getSavedCam(key) {
        try { return localStorage.getItem(key) || ""; }
        catch { return ""; }
    }
    function saveCam(key, value) {
        try { localStorage.setItem(key, value || ""); }
        catch { }
    }

    // ====== cameraリスト (Cam1 & Cam2) ======
    async function populateCameras() {
        try {
            if (!window.QrScanner) throw new Error("qr-scanner chưa được tải.");
            const cams = await window.QrScanner.listCameras(true);

            const cam1Sel = $("#cam1-select");
            const cam2Sel = $("#cam2-select");
            if (cam1Sel) cam1Sel.innerHTML = "";
            if (cam2Sel) cam2Sel.innerHTML = "";

            const savedCam1 = getSavedCam(CAM1_PREF_KEY);
            const savedCam2 = getSavedCam(CAM2_PREF_KEY);

            let cam1ByLabel = null;
            let cam2ByLabel = null;

            cams.forEach((c, idx) => {
                const label = c.label || c.id;

                if (cam1Sel) {
                    const o1 = document.createElement("option");
                    o1.value = c.id;
                    o1.textContent = label;
                    cam1Sel.appendChild(o1);
                }

                if (cam2Sel) {
                    const o2 = document.createElement("option");
                    o2.value = c.id;
                    o2.textContent = label;
                    cam2Sel.appendChild(o2);
                }

                // ヒューリスティック: QR/danh thiếpcameraは "USB 2.0 Camera" を優先
                if (!cam1ByLabel && /USB\s*2\.0\s*Camera/i.test(label)) {
                    cam1ByLabel = c.id;
                }
                // ヒューリスティック: 顔camera — 常にラベル "HD Webcam C525" を優先
                // Raspberry Pi の DeviceId は起動ごとに変わるため、デフォルトとして savedCam2 は使用しない
                if (!cam2ByLabel && /HD\s*Webcam\s*C525/i.test(label)) {
                    cam2ByLabel = c.id;
                }
            });

            // Cam1: label match → saved → first camera
            let defaultCam1Id = cam1ByLabel || savedCam1 || (cams[0] ? cams[0].id : "");

            // Cam2: 常にラベル "HD Webcam C525" を優先 (khởi động lại後に deviceId が変わるため)
            // ラベルの一致が見つからない場合にのみ savedCam2 を使用
            let defaultCam2Id = cam2ByLabel || savedCam2 || (cams[1] ? cams[1].id : defaultCam1Id);

            if (cam1Sel && defaultCam1Id) {
                cam1Sel.value = defaultCam1Id;
                saveCam(CAM1_PREF_KEY, defaultCam1Id);
                if (!cam1Sel.dataset.bound) {
                    cam1Sel.addEventListener("change", () => {
                        saveCam(CAM1_PREF_KEY, cam1Sel.value || "");
                    });
                    cam1Sel.dataset.bound = "1";
                }
            }

            if (cam2Sel && defaultCam2Id) {
                cam2Sel.value = defaultCam2Id;
                // ラベル経由で見つかった最新の deviceId で localStorage を更新
                saveCam(CAM2_PREF_KEY, defaultCam2Id);
                if (!cam2Sel.dataset.bound) {
                    cam2Sel.addEventListener("change", () => {
                        saveCam(CAM2_PREF_KEY, cam2Sel.value || "");
                    });
                    cam2Sel.dataset.bound = "1";
                }
            }

            log(`Đã tìm thấy ${cams.length} camera.`);
        } catch (e) {
            log("Không thể lấy danh sách camera: " + e.message);
        }
    }

    function uiSetScanLockedCam1(locked) {
        state.scanLockedCam1 = locked;
        const badge = $("#cam1-paused");
        if (badge) badge.hidden = !locked;
        const el = $("#scan-bcard"); if (el) el.disabled = locked;
    }
    function uiSetScanLockedCam2(locked) {
        state.scanLockedCam2 = locked;
        const badge = $("#cam2-paused");
        if (badge) badge.hidden = !locked;
        const el = $("#scan-qr"); if (el) el.disabled = locked;
    }

    async function lockScanCam1(reason = "") {
        if (state.scanLockedCam1) return;
        uiSetScanLockedCam1(true);
        log("Đã khóa quét Cam 1" + (reason ? `: ${reason}` : "") + ".");
    }
    async function unlockScanCam1() {
        uiSetScanLockedCam1(false);
        log("Đã mở lại quét Cam 1.");
        // オートサイクルが完了していない場合は、自動phát hiệnを自動的に再実行
        if (!state.cardAutoDone) {
            startAutoCardFromCam1();
        }
    }

    async function lockScanCam2(reason = "") {
        if (state.scanLockedCam2) return;
        uiSetScanLockedCam2(true);
        // qrScanner.stop() は使用しません。cameraトラックがすべてオフになり、自動ảnh khuôn mặt撮影ができなくなるためです。
        // ロックロジックは state.scanLockedCam2 フラグを使用して QrScanner のコールバックで処理されています。
        log("Đã khóa quét Cam 2" + (reason ? `: ${reason}` : "") + ".");
    }

    async function unlockScanCam2() {
        uiSetScanLockedCam2(false);
        try {
            if (state.qrScanner) await state.qrScanner.start();
            else await startCam2();
            resumeVideo2Frame();
            log("Đã mở lại quét Cam 2.");
        } catch (e) { log("Không thể khởi động lại camera2 (QR): " + e.message); }
    }

    function collectFormData() {
        return {
            fullName: getVal("#fullName"),
            idNumber: getVal("#idNumber"),
            dob: getVal("#dob"),
            issued: getVal("#issued"),
            address: getVal("#address"),
            oldId: getVal("#oldId"),
            gender: getVal("#gender"),
            expiry: getVal("#expiry")
        };
    }

    function applyCccdFields(data = {}) {
        setVal("#fullName", data.fullName || "");
        setVal("#idNumber", data.idNumber || "");
        setVal("#dob", data.dob || "");
        setVal("#issued", data.issued || "");
        setVal("#address", data.address || "");
        setVal("#oldId", data.oldId || "");
        setVal("#gender", data.gender || "");
        setVal("#expiry", data.expiry || "");
        updateActionButtons();
    }

    function collectBCardFields() {
        const pane = document.querySelector("#bcard-pane");
        if (!pane) return null;
        const visible = pane.offsetParent !== null && getComputedStyle(pane).display !== "none";
        if (!visible) return null;

        return {
            full_name: getVal("#bcardFullName"),
            email: getVal("#bcardEmail"),
            phone: getVal("#bcardPhone"),
            title: getVal("#bcardTitle"),
            company: getVal("#bcardCompany"),
            address: getVal("#bcardAddress"),
            other_info: getVal("#bcardOtherinfo"),
        };
    }

    function buildScannedPayload() {
        const bcf = collectBCardFields();
        const isPendingBcardOcr = !!(
            state.bcardImageDataUrl &&
            !hasCccdData() &&
            !hasBcardData() &&
            (state.ocrTaskId || state.ocrStatus === "processing")
        );
        return {
            data: collectFormData(),
            face_image: state.faceDataUrl,
            bcard_fields: bcf || state.lastBCardFields || null,
            bcard_image: state.bcardImageDataUrl || null,
            source_images: state.sourceImages || [],
            last_qr_raw: state.lastQRRaw,
            last_bcard_text: state.lastBCardText,
            registration_id: state.registrationId,
            pending_bcard_ocr: isPendingBcardOcr,
            ts: Date.now()
        };
    }

    function buildCccdDraftPayload(imageDataUrl = null, extra = {}) {
        return {
            registration_id: extra.registration_id || state.registrationId,
            data: extra.data || collectFormData(),
            face_image: extra.face_image !== undefined ? extra.face_image : (state.faceDataUrl || null),
            image_data_url: imageDataUrl || extra.image_data_url || state.bcardImageDataUrl || null,
            cccd_qr_raw: extra.cccd_qr_raw || extra.last_qr_raw || state.lastQRRaw || "",
            cccd_ocr_text: extra.cccd_ocr_text || "",
            cccd_field_meta: extra.cccd_field_meta || {},
            cccd_scan_status: extra.cccd_scan_status || "draft",
            side: extra.side || "front",
            ts: Date.now(),
        };
    }

    /**
     * Fire-and-forget: UI をブロックせずにバックグラウンドでサーバーにペイロードを送信します。
     */
    function _saveRegistrationInBackground(payload) {
        fetch(state.payloadEndpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        })
            .then(r => r.json())
            .then(js => {
                if (js?.qr_url) {
                    const abs = js.qr_url.startsWith("http")
                        ? js.qr_url
                        : new URL(js.qr_url, window.location.origin).toString();
                    state.serverQRUrl = abs;
                    updateActionButtons();
                }
                log(`Lưu đăng ký nền ${js?.registration_id ? "OK: " + js.registration_id : "xong."}`);
            })
            .catch(err => log("Lỗi lưu đăng ký nền: " + (err?.message || err)));
    }

    function saveCccdDraftInBackground(payloadOrResult, imageDataUrl = null) {
        const extra = (payloadOrResult && payloadOrResult.data && payloadOrResult.qr)
            ? {
                registration_id: payloadOrResult?.registration_id || state.registrationId,
                data: payloadOrResult?.data || collectFormData(),
                face_image: payloadOrResult?.face_image,
                image_data_url: payloadOrResult?.image_data_url,
                cccd_qr_raw: payloadOrResult?.qr?.raw || "",
                cccd_ocr_text: payloadOrResult?.ocr?.text || "",
                cccd_field_meta: { keywords: payloadOrResult?.ocr?.keywords || [] },
                cccd_scan_status: payloadOrResult?.cccd_scan_status || (payloadOrResult?.is_cccd ? "draft" : "unknown"),
            }
            : (payloadOrResult || {});
        const payload = buildCccdDraftPayload(imageDataUrl, extra);
        return fetch(state.cccdDraftEndpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        })
            .then(r => r.json())
            .then(js => {
                if (js?.registration_id) state.registrationId = js.registration_id;
                return js;
            })
            .catch(err => {
                log("CCCD draft save error: " + (err?.message || err));
                return null;
            });
    }

    async function continueFinalizeAfterAppointment(source = "") {
        state.appointmentPendingFinalizePayload = null;
        state.appointmentPendingFinalizeSource = "";
        closeAllAppointmentOverlays();
        if (state.autoCyclePhase === "REMOVING") {
            await unlockScanCam1();
            await unlockScanCam2();
            showRemoveCardOverlay(true, true);
            armRemovingForceResetTimer();
            if (await maybeResetAfterCardRemoval(source || "appointment-finalize")) {
                return;
            }
            return;
        }
        resetAll(true);
    }

    async function maybeStartAppointmentFlow(source = "") {
        const overlayEnabled = await refreshKioskAppointmentSetting();
        if (!overlayEnabled) {
            return false;
        }
        state.appointmentPendingFinalizePayload = buildScannedPayload();
       state.appointmentPendingFinalizeSource = source || "";
        timerManager.clearNamed(state, "thankYouResetTimer");
        timerManager.clearNamed(state, "removingForceResetTimer");
        await lockScanCam1("appointment prompt");
        await lockScanCam2("appointment prompt");
        openAppointmentPrompt();
        return true;
    }

    async function submitAppointmentFromOverlay() {
        const appointmentDate = String(appointmentDateInput ? appointmentDateInput.value : "").trim();
        const startTime = String(appointmentStartTimeSelect ? appointmentStartTimeSelect.value : "").trim();
        const endTime = String(appointmentEndTimeSelect ? appointmentEndTimeSelect.value : "").trim();
        const appointmentPurpose = String(appointmentPurposeSelect ? appointmentPurposeSelect.value : "").trim();
        const appointmentNote = String(appointmentNoteTextarea ? appointmentNoteTextarea.value : "").trim();
        const contactName = getAppointmentContactName();
        const todayDateKey = formatAppointmentDateValue(new Date());
        const now = new Date();
        const nowTime = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
        const appointmentReasonText = appointmentPurpose || appointmentNote;
        const descriptionParts = [appointmentNote, getAppointmentDefaultDescription()].filter(Boolean);
        const normalizedDescription = descriptionParts.join("\n");
        const reopenAppointmentFormWithError = async (message, reloadDate = "") => {
            setAppointmentOverlayVisible(appointmentConfirmOverlay, false);
            setAppointmentOverlayVisible(appointmentPromptOverlay, false);
            setAppointmentOverlayVisible(appointmentFormOverlay, true);
            showAppointmentFormStatus("", false);
            if (reloadDate) {
                await loadAppointmentDaySchedule(reloadDate);
            }
            await openAppointmentNotice(message, { title: t("appt.error.title"), isError: true });
        };

        if (!appointmentPurpose && !appointmentNote) {
            await reopenAppointmentFormWithError(t("appt.error.missing.reason"));
            return;
        }
        if (!appointmentDate) {
            await reopenAppointmentFormWithError(t("appt.error.missing.date"));
            return;
        }
        if (appointmentDate < todayDateKey) {
            await reopenAppointmentFormWithError(t("appt.error.past.date"));
            return;
        }
        if (!startTime || !endTime) {
            await reopenAppointmentFormWithError(t("appt.error.missing.time"));
            return;
        }
        if (endTime <= startTime) {
            await reopenAppointmentFormWithError(t("appt.error.end.after.start"));
            return;
        }
        if (appointmentDate === todayDateKey) {
            if (startTime <= nowTime) {
                await reopenAppointmentFormWithError(t("appt.error.past.time"));
                return;
            }
        }
        if (appointmentReasonText.length > APPOINTMENT_REASON_MAX_LEN) {
            await reopenAppointmentFormWithError(t("appt.error.reason.long", { max: APPOINTMENT_REASON_MAX_LEN }));
            return;
        }
        if (normalizedDescription.length > APPOINTMENT_DESC_MAX_LEN) {
            await reopenAppointmentFormWithError(t("appt.error.desc.long", { max: APPOINTMENT_DESC_MAX_LEN }));
            return;
        }
        if (state.appointmentDayItems.some((item) => slotOverlaps(item, startTime, endTime))) {
            await reopenAppointmentFormWithError(t("appt.error.slot.busy"), appointmentDate);
            updateAppointmentTimeSelects();
            return;
        }

        setAppointmentOverlayVisible(appointmentFormOverlay, true);
        showAppointmentFormStatus("", false);
        try {
            const payload = {
                appointment_date: appointmentDate,
                start_time: startTime,
                end_time: endTime,
                title: contactName || appointmentReasonText || "Cuộc hẹn",
                description: normalizedDescription,
                contact_name: contactName,
                appointment_type: "Kiosk",
                appointment_reason: appointmentReasonText,
                registration_id: state.registrationId || "",
                source: "kiosk",
            };
            const res = await fetch(state.appointmentCreateEndpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const js = await res.json().catch(() => ({}));
            if (!res.ok || !js?.ok) {
                throw new Error(js?.error || t("appt.error.create"));
            }
            showAppointmentFormStatus("", false);
            await openAppointmentNotice(t("appt.success.created"), { title: t("appt.success.title"), autoCloseMs: 2000 });
            await continueFinalizeAfterAppointment("appointment");
        } catch (err) {
            await reopenAppointmentFormWithError(err?.message || t("appt.error.create"), appointmentDate);
        }
    }

    function getAppointmentValidationError() {
        const appointmentDate = String(appointmentDateInput ? appointmentDateInput.value : "").trim();
        const startTime = String(appointmentStartTimeSelect ? appointmentStartTimeSelect.value : "").trim();
        const endTime = String(appointmentEndTimeSelect ? appointmentEndTimeSelect.value : "").trim();
        const appointmentPurpose = String(appointmentPurposeSelect ? appointmentPurposeSelect.value : "").trim();
        const appointmentNote = String(appointmentNoteTextarea ? appointmentNoteTextarea.value : "").trim();
        const todayDateKey = formatAppointmentDateValue(new Date());
        const now = new Date();
        const nowTime = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
        const appointmentReasonText = appointmentPurpose || appointmentNote;
        const normalizedDescription = [appointmentNote, getAppointmentDefaultDescription()].filter(Boolean).join("\n");

        if (!appointmentPurpose && !appointmentNote) {
            return t("appt.error.missing.reason");
        }
        if (!appointmentDate) {
            return t("appt.error.missing.date");
        }
        if (appointmentDate < todayDateKey) {
            return t("appt.error.past.date");
        }
        if (!startTime || !endTime) {
            return t("appt.error.missing.time");
        }
        if (endTime <= startTime) {
            return t("appt.error.end.after.start");
        }
        if (appointmentDate === todayDateKey && startTime <= nowTime) {
            return t("appt.error.past.time");
        }
        if (appointmentReasonText.length > APPOINTMENT_REASON_MAX_LEN) {
            return t("appt.error.reason.long", { max: APPOINTMENT_REASON_MAX_LEN });
        }
        if (normalizedDescription.length > APPOINTMENT_DESC_MAX_LEN) {
            return t("appt.error.desc.long", { max: APPOINTMENT_DESC_MAX_LEN });
        }
        if (state.appointmentDayItems.some((item) => slotOverlaps(item, startTime, endTime))) {
            return t("appt.error.slot.busy");
        }
        return "";
    }

    async function sendPayloadToPython(tag = "") {
        if (state.isSubmitting) { log("Đang gửi..."); return; }
        state.isSubmitting = true;
        updateActionButtons();

        try {
            const payload = buildScannedPayload();

            // ảnh khuôn mặtがまだない場合は、先に中間データだけ保存して顔撮影を継続する
            if (state.autoCyclePhase === "FACE" && !state.faceDataUrl) {
                if (hasBcardData()) _saveRegistrationInBackground(payload);
                else if (isCccdFlowActive()) saveCccdDraftInBackground({
                    cccd_qr_raw: state.lastQRRaw || "",
                    cccd_ocr_text: "",
                    cccd_scan_status: "draft",
                });
                log("Đã lưu dữ liệu QR. Tiếp tục chụp ảnh khuôn mặt...");
                return;
            }

            state.sessionFinalizeTriggered = true;
            state.cardRetryRequested = false;
            await _showThankYouAndDeferredSave(null, `manual${tag ? `:${tag}` : ""}`);
        } catch (e) {
            log("đăng ký UI lỗi: " + e.message);
        } finally { state.isSubmitting = false; updateActionButtons(); }
    }

    // ====== camera 1: Danh thiếp (danh thiếpphát hiện) ======
    let cam1Started = false;
    async function startCam1() {
        try {
            const video1 = $("#video1"); if (!video1) { log("Không tìm thấy #video1"); return; }

            const devId = $("#cam1-select") ? $("#cam1-select").value : undefined;
            const videoConstraints = devId
                ? { deviceId: { exact: devId }, width: { ideal: 1280 }, height: { ideal: 720 } }
                : { facingMode: { ideal: state.cam1Facing || "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } };
            video1.setAttribute("playsinline", ""); video1.muted = true;
            const stream = await navigator.mediaDevices.getUserMedia({ video: videoConstraints, audio: false });
            video1.srcObject = stream;
            await video1.play().catch(() => { });

            cam1Started = true; window.cam1Started = true;
            const p1 = $("#cam1-power"); if (p1) p1.classList.add("on");

            await bumpCam1Resolution(video1);
            log("Đã khởi động camera 1 (danh thiếp).");

            startAutoCardFromCam1();
        } catch (e) { log("Lỗi khởi động camera1: " + e.message); }
    }

    async function stopCam1() {
        try {
            const v1 = $("#video1");
            if (v1 && v1.srcObject) {
                v1.srcObject.getTracks().forEach(t => t.stop());
                v1.srcObject = null;
            }
            cam1Started = false; window.cam1Started = false;
            const p1 = $("#cam1-power"); if (p1) p1.classList.remove("on");
            log("Đã dừng camera 1.");
        } catch (e) { log("Lỗi dừng camera 1: " + e.message); }
    }

    const btnCam1Start = $("#cam1-start"); if (btnCam1Start) btnCam1Start.addEventListener("click", startCam1);
    const btnCam1Stop = $("#cam1-stop"); if (btnCam1Stop) btnCam1Stop.addEventListener("click", stopCam1);

    // ====== camera2: QR（Nimiq）+ nhận diện khuôn mặt ======
    const btnScanQR = $("#scan-qr"); if (btnScanQR) btnScanQR.addEventListener("click", async () => {
        if (state.scanLockedCam2) { log("Quét Cam 2 đang bị khóa. Hãy đặt lại hoặc hoàn tất đăng ký để tiếp tục."); return; }
        const v2 = $("#video2");
        if (!v2 || !v2.srcObject) { await startCam2(); }
        log("Đang quét QR...");
    });

    async function bumpCam1Resolution(videoEl) {
        const track = videoEl?.srcObject?.getVideoTracks?.()[0];
        if (!track) return;

        try {
            const caps = track.getCapabilities ? track.getCapabilities() : {};
            console.log("Cam1 capabilities:", caps);

            const canContinuousFocus =
                caps.focusMode && Array.isArray(caps.focusMode) &&
                caps.focusMode.includes("continuous");

            const constraints = {
                width: { min: 640, ideal: 1280, max: 1920 },
                height: { min: 480, ideal: 720, max: 1080 },
                advanced: []
            };

            if (canContinuousFocus) {
                constraints.advanced.push({ focusMode: "continuous" });
            }

            await track.applyConstraints(constraints);
        } catch (e) {
            console.warn("applyConstraints Cam1 failed:", e);
        }

        const s = track.getSettings?.() || {};
        log(`Cam1 settings: ${s.width}x${s.height}, focus=${s.focusMode || "-"}`);
    }

    const sharedCanvas1 = document.createElement("canvas");
    async function grabFromVideo1(targetWidth = 0) {
        const v = $("#video1");
        if (!v || !v.videoWidth) throw new Error("camera1 chưa sẵn sàng");

        const c = sharedCanvas1;
        let tw = v.videoWidth;
        let th = v.videoHeight;

        if (targetWidth > 0 && targetWidth < tw) {
            const scale = targetWidth / tw;
            tw = targetWidth;
            th = Math.round(v.videoHeight * scale);
        }

        if (c.width !== tw || c.height !== th) {
            c.width = tw;
            c.height = th;
        }

        const ctx = c.getContext("2d", { alpha: false });
        ctx.drawImage(v, 0, 0, tw, th);
        return c;
    }

    function getProgressColor(progress) {
        const p = Math.max(0, Math.min(progress || 0, 1));
        if (p <= 0.33) return "#ff3b30";
        if (p <= 0.66) return "#ffb000";
        return "#22c55e";
    }

    function drawProgressLabel(ctx, x, y, text, color) {
        ctx.font = "bold 14px system-ui";
        const padX = 8;
        const padY = 5;
        const width = ctx.measureText(text).width + padX * 2;
        const height = 24;
        const drawY = y > height + 6 ? y - height - 6 : y + 6;

        ctx.fillStyle = "rgba(10, 14, 24, 0.78)";
        ctx.fillRect(x, drawY, width, height);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(x, drawY, width, height);
        ctx.fillStyle = color;
        ctx.fillText(text, x + padX, drawY + height - padY - 1);
    }

    function getVideoCoverMetrics(videoEl, canvasEl) {
        const dispW = videoEl.clientWidth || canvasEl.width || 1;
        const dispH = videoEl.clientHeight || canvasEl.height || 1;
        const vidW = videoEl.videoWidth || dispW;
        const vidH = videoEl.videoHeight || dispH;
        const scale = Math.max(dispW / vidW, dispH / vidH);
        const renderW = vidW * scale;
        const renderH = vidH * scale;
        const offsetX = (dispW - renderW) / 2;
        const offsetY = (dispH - renderH) / 2;
        return { dispW, dispH, scale, offsetX, offsetY };
    }

    function updateStepRail() {
        const card = document.getElementById("step-chip-card");
        const face = document.getElementById("step-chip-face");
        const complete = document.getElementById("step-chip-complete");
        if (!card || !face || !complete) return;

        const chips = [card, face, complete];
        chips.forEach((el) => el.classList.remove("is-active", "is-done", "is-complete"));

        const phase = state.autoCyclePhase;
        if (phase === "IDLE") {
            card.classList.add("is-active");
            return;
        }
        if (phase === "CARD") {
            card.classList.add("is-active");
            face.classList.add("is-active");
            return;
        }
        if (phase === "FACE") {
            card.classList.add("is-active");
            face.classList.add("is-active");
            return;
        }
        if (phase === "SUBMITTING" || phase === "REMOVING") {
            card.classList.add("is-active");
            face.classList.add("is-active");
            complete.classList.add("is-complete");
            return;
        }

        card.classList.add("is-active");
    }

    function getFaceGuideRegion() {
        const wrap = $("#video2")?.closest(".video-wrap") || $("#video2")?.parentElement;
        if (!wrap) return null;
        const rect = wrap.getBoundingClientRect();
        const width = rect.width || 0;
        const height = rect.height || 0;
        if (!width || !height) return null;

        const guideEl = wrap.querySelector(".face-guide-oval");
        if (guideEl) {
            const guideRect = guideEl.getBoundingClientRect();
            const rx = guideRect.width / 2;
            const ry = guideRect.height / 2;
            const cx = (guideRect.left - rect.left) + rx;
            const cy = (guideRect.top - rect.top) + ry;
            return {
                cx,
                cy,
                rx,
                ry,
                width,
                height,
            };
        }

        const rx = width * (state.faceGuideOvalWidthRatio || 0.42) / 2;
        const ry = height * (state.faceGuideOvalHeightRatio || 0.60) / 2;
        const cy = height * (state.faceGuideCenterYRatio || 0.5);
        return {
            cx: width / 2,
            cy,
            rx,
            ry,
            width,
            height,
        };
    }

    function mapFaceBoxToGuide(best, frameSize, dispW, dispH) {
        if (!best || !frameSize || !dispW || !dispH) return null;
        const sourceW = frameSize.w || dispW;
        const sourceH = frameSize.h || dispH;
        const scale = Math.max(dispW / sourceW, dispH / sourceH);
        const offsetX = (dispW - sourceW * scale) / 2;
        const offsetY = (dispH - sourceH * scale) / 2;
        return {
            x: best.x * scale + offsetX,
            y: best.y * scale + offsetY,
            w: best.w * scale,
            h: best.h * scale,
            scale,
            offsetX,
            offsetY,
        };
    }

    function updateFaceGuideOverlay(isInside = false) {
        const overlay = document.getElementById("face-guide-overlay");
        if (!overlay) return;
        const active = !!state.faceGuideEnabled;
        overlay.classList.toggle("is-active", active);
        overlay.classList.toggle("is-valid", active && !!isInside);
        const copy = overlay.querySelector(".face-guide-copy span");
        if (copy) {
            copy.textContent = isInside
                ? t("face.guide.inside")
                : t("face.guide");
        }
    }

    function isFaceInsideGuide(best, frameSize) {
        if (!state.faceGuideEnabled) return !!best;
        const vid = $("#video2");
        const wrap = $("#video2")?.closest(".video-wrap") || $("#video2")?.parentElement;
        if (!best || !frameSize || !vid || !wrap) return false;
        const guide = getFaceGuideRegion();
        if (!guide) return false;

        const mapped = mapFaceBoxToGuide(best, frameSize, guide.width, guide.height);
        if (!mapped) return false;
        const centerX = mapped.x + mapped.w / 2;
        const centerY = mapped.y + mapped.h / 2;
        const dx = (centerX - guide.cx) / Math.max(guide.rx, 1);
        const dy = (centerY - guide.cy) / Math.max(guide.ry, 1);
        const slack = 1 + (state.faceGuideEllipseSlack || 0);
        const inOval = (dx * dx + dy * dy) <= (slack * slack);
        const faceHeightRatio = best.h / Math.max(frameSize.h || 1, 1);
        return inOval && faceHeightRatio >= (state.faceGuideMinFaceHeightRatio || 0.16);
    }

    // ====== キャンバスオーバーレイへのdanh thiếpphát hiện境界ボックス (bbox) の描画 ======
    function drawCardBbox(bbox, stableCount, required, triggered, frameSize = null) {
        const vid = $("#video1");
        const cvs = $("#card-bbox-canvas");
        if (!cvs || !vid) return;

        // Sync canvas size với video element (display size)
        const dispW = vid.clientWidth;
        const dispH = vid.clientHeight;
        if (cvs.width !== dispW || cvs.height !== dispH) {
            cvs.width = dispW;
            cvs.height = dispH;
        }

        const ctx = cvs.getContext("2d");
        ctx.clearRect(0, 0, dispW, dispH);

        if (!bbox) return;

        // 元のフレーム座標からの bbox を表示キャンバス座標にマップ
        const sourceW = frameSize?.w || vid.videoWidth || dispW;
        const sourceH = frameSize?.h || vid.videoHeight || dispH;
        const cardScale = Math.max(dispW / sourceW, dispH / sourceH);
        const cardOffsetX = (dispW - sourceW * cardScale) / 2;
        const cardOffsetY = (dispH - sourceH * cardScale) / 2;
        const rx = bbox.x1 * cardScale + cardOffsetX;
        const ry = bbox.y1 * cardScale + cardOffsetY;
        const rw = (bbox.x2 - bbox.x1) * cardScale;
        const rh = (bbox.y2 - bbox.y1) * cardScale;
        const ratio = triggered ? 1 : Math.min((stableCount || 0) / Math.max(required || 1, 1), 1);
        const percent = Math.round(ratio * 100);
        const color = getProgressColor(ratio);

        ctx.strokeStyle = color;
        ctx.lineWidth = 4;
        ctx.shadowColor = color;
        ctx.shadowBlur = 12;
        ctx.strokeRect(rx, ry, rw, rh);
        ctx.shadowBlur = 0;

        let label = t("bcard.progress", { percent });
        if (state.autoCyclePhase === "REMOVING") {
            label = t("bcard.remove.progress", { percent });
        } else if (triggered) {
            label = t("bcard.progress", { percent: 100 });
        }
        drawProgressLabel(ctx, rx, ry, label, color);
    }

    function clearCardBbox() {
        const cvs = $("#card-bbox-canvas");
        if (!cvs) return;
        cvs.getContext("2d").clearRect(0, 0, cvs.width, cvs.height);
    }

    // ====== Camera 1 からのdanh thiếp自動phát hiệnループ (YOLOv8) ======
    async function startAutoCardFromCam1() {
        const vid = $("#video1");
        if (!vid) return;

        // 現在のライフサイクルですでに結果がある場合は、実行しない
        if (state.cardAutoSending || (state.cardAutoDone && state.autoCyclePhase !== "REMOVING")) return;

        // cameraが準備できていない場合は、1giâychờしてから再試行
        if (!vid.srcObject) {
            setTimeout(startAutoCardFromCam1, 300);
            return;
        }

        state.cardAutoSending = true;
        const frameDelay = Math.max(1, Math.round(1000 / (state.cardAutoFps || 1)));

        log("Đã bật tự động phát hiện danh thiếp trên camera1 (YOLOv8).");

        while (state.cardAutoSending && vid.srcObject) {
            if (!isPageInteractionActive() || Date.now() < (state.interactionResumeAtMs || 0)) {
                clearCardBbox();
                await new Promise((r) => setTimeout(r, 180));
                continue;
            }
            if (Date.now() < (state.cardDetectSuppressUntilMs || 0)) {
                clearCardBbox();
                await new Promise((r) => setTimeout(r, 150));
                continue;
            }
            // Cam 1 がロックされているか、danh thiếpを取り出している最中ではないのにquétが完了している場合は、ループを一時休止（ポーズ）
            if (state.scanLockedCam1 || state.cardAutoDone) {
                if (state.autoCyclePhase !== "REMOVING") {
                    await new Promise((r) => setTimeout(r, 600));
                    continue;
                }
            }
            const loopStartedAt = performance.now();
            try {
                // レイヤーの彩度不足による誤認を避けるため解像度を上げる:
                // danh thiếp取り出し画面 (REMOVING) または挨拶画面でも、bbox tracking を優先して 640px に抑える。
                // 通常のquétフェーズ (IDLE) では、さらに軽い 512px を使用する。
                const isSensitivePhase = state.welcomeEyesVisible || state.autoCyclePhase === "REMOVING";
                const grabRes = isSensitivePhase ? state.cardDetectSensitiveWidth : state.cardDetectWidth;
                const imgQuality = isSensitivePhase ? state.cardDetectSensitiveJpegQuality : state.cardDetectJpegQuality;
                const reducedCanvas = await grabFromVideo1(grabRes);

                const blob = await new Promise((resolve) =>
                    reducedCanvas.toBlob(resolve, "image/jpeg", imgQuality)
                );
                const fd = new FormData();
                fd.append("frame", blob, `card-${Date.now()}.jpg`);
                fd.append("ts", String(Date.now()));
                if (state.autoCyclePhase === "REMOVING") {
                    fd.append("check_only", "true");
                }

                const res = await fetch(state.cardAutoEndpoint, {
                    method: "POST",
                    body: fd,
                });
                const js = await res.json().catch(() => null);

                if (js && js.ok) {
                    const bboxConf = Number(js?.bbox?.conf || 0);
                    const hasBbox = state.autoCyclePhase === "REMOVING"
                        ? (!!js.bbox && bboxConf >= 0.82)
                        : !!js.bbox;

                    // --- 新規: 挨拶画面（Welcome Eyes）中の衛生チェック ---
                    if (state.welcomeEyesVisible && hasBbox) {
                        log("Phát hiện thẻ không cần thiết trên khay khi đang ở màn hình chờ. Đang yêu cầu lấy thẻ ra.");
                        enterRemovingPhase({ requireCompletionAudio: false, keepOverlayVisible: true });
                        showWelcomeEyes(false); // Ẩn mắt đi
                        // Sẽ lọt xuống nhánh REMOVING xử lý tiếp
                    }


                    if (state.autoCyclePhase === "REMOVING") {
                        // ... (REMOVING ロジックを維持)
                        if (hasBbox) {
                            if (state.emptyGapCount > 0) {
                                log("Vẫn còn phát hiện thẻ (đặt lại bộ đếm).");
                                state.emptyGapCount = 0;
                            }
                            drawCardBbox(js.bbox, js.required, js.required, true, js.frame_size);
                        } else {
                            clearCardBbox();
                            state.emptyGapCount++;
                            // REMOVING 中は bbox の瞬断が起きやすいので、より多くの連続空フレームを要求する
                            const actualGapRequired = state.autoCyclePhase === "REMOVING"
                                ? state.removingGapRequired
                                : state.emptyGapRequired;

                            if (state.emptyGapCount % 5 === 0 || state.emptyGapCount === 1) {
                                log(`Đang đợi lấy thẻ... Gap count: ${state.emptyGapCount}/${actualGapRequired}`);
                            }
                            if (state.emptyGapCount >= actualGapRequired) {
                                log("Đã xác nhận thẻ đã được lấy ra. Đang kiểm tra thời gian hiển thị badge cảm ơn...");
                                state.pendingCardRemovalReset = true;
                                const waitTime = (state.removingPhaseMinUntil || 0) - Date.now();
                                if (waitTime > 0) {
                                    log(`Chờ thêm ${waitTime}ms để badge cảm ơn hiển thị đủ thời gian...`);
                                    await new Promise(r => setTimeout(r, waitTime));
                                }
                                if (state.removingRequiresCompletionAudio && !state.completionAudioDone) {
                                    log("Đang chờ phát xong âm thanh hoàn tất...");
                                    continue;
                                }
                                if (state.autoCyclePhase === "REMOVING") {
                                    const resetDone = await maybeResetAfterCardRemoval("card-removed");
                                    if (!resetDone && !hasBlockingCompletionOverlay()) {
                                        showRemoveCardOverlay(false);
                                        log("Badge đã hiển thị xong. Hệ thống quay về trạng thái IDLE.");
                                        state.pendingCardRemovalReset = false;
                                        resetAll(true);
                                    }
                                }
                            }
                        }
                    } else {
                        // Nếu vẫn đang bật Đôi mắt (chưa có người) mà không có lỗi rác ở trên, thì chỉ pause nhẹ và quét tiếp
                        if (state.welcomeEyesVisible) {
                            await new Promise((r) => setTimeout(r, 600));
                            continue;
                        }

                        // Phase bình thường: Chờ trigger capture
                        if (js.card_detected) {
                            drawCardBbox(js.bbox, js.required, js.required, true, js.frame_size);
                            setTimeout(clearCardBbox, 800);

                            log("✅ Đã chụp ảnh card. Sẽ phân tích CCCD trước, nếu không phải mới chạy OCR danh thiếp.");
                            state.autoCyclePhase = "CARD";
                            state.suppressGreetingDuringCompletion = true;

                            // 重複キャプチャを防ぐため Cam 1 をロック。顔/プレゼンスを継続させるため Cam 2 は開いたままにする
                            try {
                                await lockScanCam1("Đã tự động chụp danh thiếp");
                                state.cardAutoDone = true;
                                state.cardRetryRequested = false;
                            } catch { }

                            const captureCanvas = await grabFromVideo1(1280);

                            captureCanvas.toBlob((blob) => {
                                if (!blob) return;
                                const reader = new FileReader();
                                reader.onloadend = () => {
                                    state.bcardImageDataUrl = reader.result;
                                    const bcardPreview = $("#bcard-preview");
                                    if (bcardPreview) bcardPreview.src = state.bcardImageDataUrl;
                                };
                                reader.readAsDataURL(blob);
                            }, "image/jpeg", 0.85);

                            state.sessionFinalizeTriggered = false;

                            await processCapturedCardCanvas(captureCanvas, { source: "auto" });
                            await startFaceGuidanceAndArmCapture();
                        } else {
                            // Chưa trigger – vẽ bbox tracking
                            const stableCount = js.stable_count || 0;
                            const required = js.required || 15;
                            drawCardBbox(js.bbox, stableCount, required, false, js.frame_size);
                        }
                    }
                }
            } catch (err) {
                log("Auto card detect lỗi: " + (err?.message || err));
            }

            // Fetch が target FPS より遅いときは追加で待たず、そのまま次のフレームへ進む
            const remainingDelay = frameDelay - (performance.now() - loopStartedAt);
            if (remainingDelay > 0) {
                await new Promise((r) => setTimeout(r, remainingDelay));
            }
        }

        state.cardAutoSending = false;
    }



    function startBCardProcessingUI() {
        if (btnScanBCard) {
            btnScanBCard.disabled = true;
            btnScanBCard.textContent = t("bcard.processing");
        }
        toggleBCardPane(false);
        fillBCardPane({}, t("bcard.ocr.loading"));
    }

    function finishBCardProcessingUI(fields, text) {
        if (fields) {
            state.lastBCardFields = mergeBCardFields(fields, state.lastBCardFields || {});
            state.lastBCardText = text || "";
            fillBCardPane(state.lastBCardFields, text || "");
        }
        updateActionButtons();
        if (btnScanBCard) {
            btnScanBCard.disabled = false;
            btnScanBCard.textContent = t("bcard.scan");
        }
        // ✅ Chuyển sang phase FACE nếu đã đủ thông tin (cả cho trường hợp quét tay)
        if (state.autoCyclePhase === "IDLE" && (hasBcardData() || hasCccdData())) {
            enterFacePhaseBasic();
        } else {
            // ✅ Luôn đảm bảo presence sẵn sàng
            state.allowPresence = true;
            if (!state.faceDataUrl && !state.presenceSending) {
                startPresenceStream();
            }
        }
    }

    function _bcardIdentity(fields = {}) {
        const name = (fields.full_name || fields.name || "").trim();
        const company = (fields.company || fields.org || "").trim();
        return { name, company };
    }

    function hasRequiredBcardIdentity(fields = {}) {
        const idf = _bcardIdentity(fields);
        // 制限緩和: データの漏れを防ぐため、名前またはメール/電話番号のいずれかがあれば保存を許可
        return !!(idf.name || fields.email || fields.phone || fields.tel);
    }


    function stopBcardOcrPolling() {
        return kioskAsyncController?.stopBcardOcrPolling();
    }

    async function requestCardRecapture(reason = "") {
        if (state.cardRetryRequested) return;
        state.cardRetryRequested = true;
        state.cardRetryCount++;
        state.sessionFinalizeTriggered = false;
        stopBcardOcrPolling();
        state.ocrTaskId = null;
        state.ocrStatus = "idle";
        state.lastBCardFields = null;
        state.lastBCardText = "";
        state.bcardImageDataUrl = null;
        state.registrationId = null;
        const bcardPreview = $("#bcard-preview");
        if (bcardPreview) bcardPreview.src = "";

        const isRetry = state.cardRetryCount > 1;

        log(`Thiếu thông tin danh thiếp (họ tên/công ty)${reason ? `: ${reason}` : ""}. Vui lòng chụp lại danh thiếp.`);
        interruptAndClearAudioQueue();

        if (!isRetry) {
            // まだ再生されていない場合は、顔撮影の案内âm thanhをキャンセル (初回のみ)
            timerManager.clearNamed(state, "faceGuideAudioTimer");
            timerManager.clearNamed(state, "faceRetryTimer");
            state.faceRetryCount = 0;
            state.faceCaptureReadyAtMs = Number.MAX_SAFE_INTEGER;
        }

        await playAudioAndWait(sndCardUnread, true);

        state.cardAutoDone = false;
        state.cardAutoSending = false;
        state.autoCyclePhase = "IDLE";
        state.allowPresence = true;

        await unlockScanCam1();
        startAutoCardFromCam1();
    }

    async function tryFinalizeSessionAfterFaceAndOcr(source = "") {
        if (state.sessionFinalizeTriggered || state.isSubmitting) return;
        if (!state.faceDataUrl) return;

        log(`[Finalize] Face OK. Hiện Badge ngay${source ? ` (${source})` : ""}.`);
        state.sessionFinalizeTriggered = true;
        state.cardRetryRequested = false;
        await _showThankYouAndDeferredSave(null, source);
    }

    function armRemovingForceResetTimer() {
        timerManager.setNamedTimeout(state, "removingForceResetTimer", () => {
            if (state.autoCyclePhase === "REMOVING") {
                if (state.emptyGapCount >= state.removingGapRequired) {
                    clearCardBbox();
                    showRemoveCardOverlay(false);
                    resetAll(true);
                } else {
                    showRemoveCardOverlay(true, true);
                }
            }
        }, 8000);
    }

    /**
     * 感謝バッジを即座に表示しますが、đăng kýの保存は OCR が完了するまでchờします。
     * đặt lại (resetAll) によるデータ消失や新しいセッションによる上書きを防ぐため、クロージャスナップショットを使用します。
     */
    async function _showThankYouAndDeferredSave(payloadOverride = null, source = "") {
        // 0. バッジを最速で表示するため、現在再生中のâm thanh (例: huongdanchupface.mp3) を即座にdừng
        interruptAndClearAudioQueue();

        // 1. 現在の全データをローカル変数 (クロージャ) にスナップショットとして保存
        const snapshotBase = payloadOverride || buildScannedPayload();
        const snapshot = {
            ...snapshotBase,
            source_images: [...(snapshotBase.source_images || [])],
            ts: snapshotBase.ts || Date.now(),
        };
        const isResolvedQrCheckin = !!(
            state.qrResolvedProfile &&
            snapshot.last_qr_raw &&
            snapshot.registration_id &&
            snapshot.last_qr_raw === snapshot.registration_id
        );
        const resolvedQrName =
            state.qrResolvedProfile?.display_name ||
            snapshot.data?.fullName ||
            snapshot.registration_id ||
            "Khách";
        const resolvedQrGreeting = state.qrResolvedProfile?.greeting_audio_url || "";

        // 2. 即座に感謝 UI を表示 (Fire-and-forget UI)
        await unlockScanCam2();
        const hasCard = !!state.cardAutoDone;

        if (isResolvedQrCheckin) {
            await lockScanCam1("Lời chào khách QR");
            await lockScanCam2("Lời chào khách QR");
            state.completionAudioDone = false;
            timerManager.clearNamed(state, "thankYouResetTimer");
            showReturningVisitorOverlay(resolvedQrName, t("qr.checkin.done"), t("welcome.short"));
            requestAnimationFrame(async () => {
                showRemoveCardOverlay(false, false);
                if (resolvedQrGreeting) {
                    await playRecognizedVisitorGreeting(resolvedQrGreeting);
                } else {
                    await playAudioAndWait(sndRegisterDone);
                }
                state.completionAudioDone = true;
                const appointmentStarted = await maybeStartAppointmentFlow(source);
                if (!appointmentStarted) {
                    timerManager.setNamedTimeout(state, "thankYouResetTimer", () => resetAll(true), 2000);
                }
            });
        } else if (hasCard) {
            enterRemovingPhase({ requireCompletionAudio: true, minVisibleMs: 1500, keepOverlayVisible: false });
            if (!state.cardAutoSending) {
                startAutoCardFromCam1();
            }
            timerManager.clearNamed(state, "thankYouResetTimer");
            armRemovingForceResetTimer();
            timerManager.setNamedTimeout(state, "thankYouResetTimer", async () => {
                if (state.autoCyclePhase !== "REMOVING") return;
                showRemoveCardOverlay(true, true);
                await playAudioAndWait(sndRegisterDone);
                state.completionAudioDone = true;
                await maybeStartAppointmentFlow(source);
            }, 3000);
        } else {
            await lockScanCam1("Hiển thị cảm ơn");
            await lockScanCam2("Hiển thị cảm ơn");
            state.completionAudioDone = false;
            timerManager.clearNamed(state, "thankYouResetTimer");
            timerManager.setNamedTimeout(state, "thankYouResetTimer", async () => {
                showRemoveCardOverlay(true, false);
                await playAudioAndWait(sndRegisterDone);
                state.completionAudioDone = true;
                const appointmentStarted = await maybeStartAppointmentFlow(source);
                if (!appointmentStarted) {
                    timerManager.setNamedTimeout(state, "thankYouResetTimer", () => resetAll(true), 3000);
                }
            }, 3000);
        }

        // 3. サーバーに直ちにđăng kýを送信 (シェルデータ)
        // OCR 結果は完了後、(registrationId に基づいて) サーバーによってこのレコードに自動的に更新されます
        log(`[Nền] Đang gửi thông tin đăng ký lên máy chủ${source ? ` (${source})` : ""} (reg_id: ${snapshot.registration_id || state.registrationId})...`);
        if (hasBcardData() || snapshot.pending_bcard_ocr) {
            _saveRegistrationInBackground(snapshot);
        } else if (isCccdFlowActive()) {
            saveCccdDraftInBackground({
                registration_id: snapshot.registration_id,
                data: snapshot.data,
                face_image: snapshot.face_image,
                image_data_url: snapshot.bcard_image,
                cccd_qr_raw: snapshot.last_qr_raw || "",
                cccd_scan_status: "done",
            }, snapshot.bcard_image);
        }
    }

    async function pollBcardOcrStatus(taskId) {
        return kioskAsyncController?.pollBcardOcrStatus(taskId);
    }


    async function startAsyncBcardOcrFromCanvas(canvas) {
        return kioskAsyncController?.startAsyncBcardOcrFromCanvas(canvas);
    }

    async function handleScanBCard() {
        try {
            if (state.scanLockedCam1) { log("Đang khoá quét Cam 1. Reset/Đăng ký để tiếp tục."); return; }

            const c = await grabFromVideo1();
            await lockScanCam1("Đã chụp danh thiếp");

            state.cardAutoDone = true;
            state.cardRetryRequested = false;
            state.sessionFinalizeTriggered = false;
            const processed = await processCapturedCardCanvas(c, { source: "manual" });

            if (!state.faceDataUrl) {
                await startFaceGuidanceAndArmCapture();
            } else {
                await tryFinalizeSessionAfterFaceAndOcr(processed?.kind === "cccd" ? "manual-cccd" : "manual-card");
            }

        } catch (e) {
            log("Lỗi OCR danh thiếp: " + e.message);
            toggleBCardPane(false); toggleCCCDForm(true);
            if (btnScanBCard) {
                btnScanBCard.disabled = false;
                btnScanBCard.textContent = t("bcard.scan");
            }
        }
    }
    const btnScanBCard = $("#scan-bcard");
    if (btnScanBCard) btnScanBCard.addEventListener("click", handleScanBCard);

    function ddMMyyyyToISO(s) {
        if (!s) return "";
        s = s.replace(/[^\d]/g, "").trim();
        if (s.length === 8) {
            const dd = s.slice(0, 2), mm = s.slice(2, 4), yyyy = s.slice(4, 8);
            return `${yyyy}-${mm}-${dd}`;
        }
        const m = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
        if (m) {
            const dd = m[1].padStart(2, "0"), mm = m[2].padStart(2, "0"), yyyy = m[3];
            return `${yyyy}-${mm}-${dd}`;
        }
        return "";
    }

    function parseVNIdQr(text) {
        const parts = (text || "").trim().split("|");
        if (parts.length < 7) return null;
        const cccd = (parts[0] || "").trim();
        const oldId = (parts[1] || "").trim();
        const fullName = (parts[2] || "").trim();
        const dob = ddMMyyyyToISO((parts[3] || "").trim());
        let gender = (parts[4] || "").trim();
        if (/^(m|nam)$/i.test(gender)) gender = "Nam";
        else if (/^(f|nu|nữ)$/i.test(gender)) gender = "Nữ";
        const address = (parts[5] || "").trim();
        const expiry = ddMMyyyyToISO((parts[6] || "").trim());
        if (!/^\d{9,12}$/.test(cccd)) return null;
        return { cccd, oldId, fullName, dob, gender, address, expiry };
    }

    function mergeCccdData(base = {}, extra = {}) {
        const out = { ...(base || {}) };
        for (const [key, value] of Object.entries(extra || {})) {
            if ((value || "").toString().trim()) out[key] = value;
        }
        return out;
    }

    function ensureRegistrationId(logPrefix = "") {
        if (state.registrationId) return state.registrationId;
        const now = new Date();
        const dateStr = [
            now.getDate().toString().padStart(2, "0"),
            (now.getMonth() + 1).toString().padStart(2, "0"),
            now.getFullYear()
        ].join("-");
        const timeStr = [
            now.getHours().toString().padStart(2, "0"),
            now.getMinutes().toString().padStart(2, "0"),
            now.getSeconds().toString().padStart(2, "0")
        ].join("-");
        const suffix = Math.random().toString(36).substring(2, 6);
        state.registrationId = `REG_${dateStr}_${timeStr}_${suffix}`;
        log(`${logPrefix || "Đã tạo"} Registration ID: ${state.registrationId}`);
        return state.registrationId;
    }

    function isLikelyCccdResult(js = {}) {
        const parsedQr = js?.qr?.parsed || parseVNIdQr(js?.qr?.raw || "");
        if (parsedQr && (parsedQr.idNumber || parsedQr.cccd)) return true;

        const data = js?.data || {};
        const strong = [
            data.idNumber,
            data.fullName,
            data.dob,
            data.gender,
            data.address,
        ].filter(v => (v || "").toString().trim().length > 0).length;
        const hasCoreIdentity = !!(
            (data.idNumber || "").toString().trim() &&
            (data.fullName || "").toString().trim()
        );
        if (js?.is_cccd && hasCoreIdentity && strong >= 4) return true;

        const lower = (js?.ocr?.text || "").toLowerCase();
        const keywords = [
            "can cuoc",
            "identity card",
            "citizen identity",
            "personal identification",
            "personal identification number",
            "full name",
            "date of birth",
            "sex",
            "ngay sinh",
            "gioi tinh",
            "noi thuong tru",
            "place of residence",
        ].filter(token => lower.includes(token));
        return keywords.length >= 2;
    }

    async function analyzeCardCanvasForCccd(canvas) {
        try {
            const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
            const fd = new FormData();
            fd.append("image", blob, `cccd-${Date.now()}.jpg`);
            const res = await fetch(state.cccdAnalyzeEndpoint, { method: "POST", body: fd });
            const js = await res.json().catch(() => ({}));
            if (!res.ok || !js?.ok) return null;

            const qrParsed = js?.qr?.parsed || parseVNIdQr(js?.qr?.raw || "");
            const mergedData = mergeCccdData(js?.data || {}, qrParsed ? {
                idNumber: qrParsed.idNumber || qrParsed.cccd || "",
                oldId: qrParsed.oldId || "",
                fullName: qrParsed.fullName || "",
                dob: qrParsed.dob || "",
                gender: qrParsed.gender || "",
                address: qrParsed.address || "",
                expiry: qrParsed.expiry || "",
            } : {});
            js.data = mergedData;
            return isLikelyCccdResult(js) ? js : null;
        } catch (e) {
            log("CCCD analyze error: " + e.message);
            return null;
        }
    }

    async function processCapturedCardCanvas(canvas, { source = "manual" } = {}) {
        ensureRegistrationId(source === "auto" ? "[Tự động] Đã tạo" : "Đã tạo");

        const imageDataUrl = canvas.toDataURL("image/jpeg", 0.9);
        state.bcardImageDataUrl = imageDataUrl;

        const cccdResult = await analyzeCardCanvasForCccd(canvas);
        if (cccdResult) {
            state.lastQRRaw = cccdResult?.qr?.raw || state.lastQRRaw || "";
            state.lastBCardFields = null;
            state.lastBCardText = "";
            state.ocrTaskId = null;
            state.ocrStatus = null;
            stopBcardOcrPolling();

            applyCccdFields(cccdResult.data || {});
            toggleBCardPane(false);
            toggleCCCDForm(true);
            state.cccdFlowActive = true;
            saveCccdDraftInBackground({
                ...cccdResult,
                registration_id: state.registrationId,
                cccd_scan_status: "draft",
            }, imageDataUrl);

            log("Đã nhận diện CCCD. Bỏ qua flow OCR danh thiếp.");
            return { kind: "cccd", result: cccdResult, imageDataUrl };
        }

        startBCardProcessingUI();
        await startAsyncBcardOcrFromCanvas(canvas);
        return { kind: "bcard", imageDataUrl };
    }

    function normalizeRegistrationQrPayload(obj = {}) {
        if (!obj || typeof obj !== "object") return null;
        const type = String(obj.type || obj.t || "").trim().toLowerCase();
        const regId = String(obj.registration_id || obj.r || "").trim();
        if (!regId || (type && !["registration_qr", "reg"].includes(type))) return null;
        const compactBcard = obj.b || {};
        const bcardFields = obj.bcard_fields || {
            full_name: compactBcard.n || "",
            company: compactBcard.c || "",
            email: compactBcard.m || "",
            phone: compactBcard.p || "",
            title: compactBcard.t || "",
            address: compactBcard.a || "",
            other_info: compactBcard.o || "",
        };
        return {
            registration_id: regId,
            display_name: String(obj.display_name || obj.fullName || obj.n || "").trim(),
            fullName: String(obj.fullName || obj.n || "").trim(),
            data: obj.data || {
                fullName: obj.n || "",
                idNumber: obj.idNumber || obj.i || "",
                oldId: obj.oldId || obj.o || "",
                dob: obj.dob || obj.d || "",
                issued: obj.issued || obj.u || "",
                gender: obj.gender || obj.g || "",
                address: obj.address || obj.a || "",
                expiry: obj.expiry || obj.e || "",
            },
            bcard_fields: bcardFields,
            last_bcard_text: obj.last_bcard_text || compactBcard.o || "",
            greeting_audio_url: obj.greeting_audio_url || "",
        };
    }

    function parseRegistrationQrText(text = "") {
        const raw = String(text || "").trim();
        if (!raw) return null;
        const regMatch = raw.match(/(?:^|\n)\s*ID:\s*(REG_[A-Za-z0-9_-]+)\s*(?:\n|$)/i);
        if (!regMatch) return null;
        const readLine = (label) => {
            const match = raw.match(new RegExp(`(?:^|\\n)\\s*${label}:\\s*(.+?)\\s*(?:\\n|$)`, "i"));
            return match ? match[1].trim() : "";
        };
        const fullName = readLine("Họ tên");
        const company = readLine("Công ty");
        const email = readLine("Email");
        const phone = readLine("Điện thoại");
        const title = readLine("Chức vụ");
        const address = readLine("Địa chỉ");
        return {
            registration_id: regMatch[1].trim(),
            display_name: fullName,
            fullName,
            data: {
                fullName,
                address,
            },
            bcard_fields: {
                full_name: fullName,
                company,
                email,
                phone,
                title,
                address,
            },
            last_bcard_text: raw,
        };
    }

    function applyResolvedRegistrationQr(obj = {}) {
        const normalized = normalizeRegistrationQrPayload(obj) || obj;
        const data = normalized.data || {};
        const regId = (normalized.registration_id || "").trim();
        const bcf = normalized.bcard_fields || {};
        if (regId) state.registrationId = regId;
        state.qrResolvedProfile = {
            registration_id: regId,
            display_name: (normalized.display_name || normalized.fullName || data.fullName || "").trim(),
            greeting_audio_url: normalized.greeting_audio_url || "",
        };

        if (data.fullName) setVal("#fullName", data.fullName);
        if (data.idNumber) setVal("#idNumber", data.idNumber);
        if (data.oldId) setVal("#oldId", data.oldId);
        if (data.dob) setVal("#dob", data.dob);
        if (data.issued) setVal("#issued", data.issued);
        if (data.gender) setVal("#gender", data.gender);
        if (data.address) setVal("#address", data.address);
        if (data.expiry) setVal("#expiry", data.expiry);
        if (normalized.fullName) setVal("#fullName", normalized.fullName);
        if (bcf.full_name || bcf.name) {
            setVal("#fullName", bcf.full_name || bcf.name);
        }
        state.lastBCardFields = bcf;
        state.lastBCardText = normalized.last_bcard_text || "";
        toggleCCCDForm(false);
        state.cccdFlowActive = false;
        toggleBCardPane(true);
        fillBCardPane(bcf, normalized.last_bcard_text || "");
        updateActionButtons();
        return hasCccdData() || hasBcardData();
    }

    async function resolveRegistrationQr(text) {
        const raw = (text || "").trim();
        if (!/^REG_[A-Za-z0-9_-]+$/.test(raw)) return null;
        try {
            const res = await fetch(`/api/registrations/${encodeURIComponent(raw)}/qr`, { cache: "no-store" });
            const js = await res.json().catch(() => ({}));
            if (!res.ok || !js?.ok) {
                log(`QR registration lookup thất bại: ${js?.error || res.status}`);
                return null;
            }
            return js;
        } catch (e) {
            log("Không thể tra cứu registration từ QR: " + (e?.message || e));
            return null;
        }
    }

    async function tryFillFromQR(text) {
        let parsedSomething = false;
        const vn = parseVNIdQr(text);
        if (vn) {
            parsedSomething = true;
            if (vn.fullName) setVal("#fullName", vn.fullName);
            if (vn.cccd) setVal("#idNumber", vn.cccd);
            setVal("#oldId", vn.oldId || "");
            setVal("#dob", vn.dob || "");
            setVal("#gender", vn.gender || "");
            setVal("#address", vn.address || "");
            setVal("#expiry", vn.expiry || "");
            updateActionButtons();
            return hasCccdData() || hasBcardData();
        }

        const parsedRegistrationText = parseRegistrationQrText(text);
        if (parsedRegistrationText) {
            parsedSomething = true;
            const sufficient = applyResolvedRegistrationQr(parsedRegistrationText);
            if (sufficient && state.autoCyclePhase === "IDLE") {
                enterFacePhaseBasic();
            }
            return sufficient;
        }

        const resolvedRegistration = await resolveRegistrationQr(text);
        if (resolvedRegistration) {
            parsedSomething = true;
            const sufficient = applyResolvedRegistrationQr(resolvedRegistration);
            if (sufficient && state.autoCyclePhase === "IDLE") {
                enterFacePhaseBasic();
            }
            return sufficient;
        }

        try {
            const obj = JSON.parse(text);
            parsedSomething = true;
            const registrationQrPayload = normalizeRegistrationQrPayload(obj);
            if (registrationQrPayload) {
                const sufficient = applyResolvedRegistrationQr(registrationQrPayload);
                if (sufficient && state.autoCyclePhase === "IDLE") {
                    enterFacePhaseBasic();
                }
                return sufficient;
            }

            if (obj.fullName) setVal("#fullName", obj.fullName);
            else if (obj.bcard_fields && (obj.bcard_fields.full_name || obj.bcard_fields.name)) {
                setVal("#fullName", obj.bcard_fields.full_name || obj.bcard_fields.name);
            }
            if (obj.idNumber) setVal("#idNumber", obj.idNumber);
            if (obj.oldId) setVal("#oldId", obj.oldId);
            if (obj.dob) setVal("#dob", obj.dob);
            if (obj.gender) setVal("#gender", obj.gender);
            if (obj.address) setVal("#address", obj.address);
            if (obj.expiry) setVal("#expiry", obj.expiry);

            if (obj.bcard_fields) {
                state.lastBCardFields = obj.bcard_fields;
                toggleCCCDForm(false);
                state.cccdFlowActive = false;
                toggleBCardPane(true);
                fillBCardPane(obj.bcard_fields, obj.last_bcard_text || "");
            } else if (obj.bcard_name || obj.bcard_company || obj.bcard_email || obj.bcard_phone) {
                // Support flattened keys from older/alternative versions
                const bcf = {
                    full_name: obj.bcard_name,
                    company: obj.bcard_company,
                    email: obj.bcard_email,
                    phone: obj.bcard_phone,
                    title: obj.bcard_title || "",
                    address: obj.bcard_address || "",
                    other_info: obj.bcard_info || obj.other_info || ""
                };
                state.lastBCardFields = bcf;
                toggleCCCDForm(false);
                state.cccdFlowActive = false;
                toggleBCardPane(true);
                fillBCardPane(bcf, obj.last_bcard_text || "");
                // ✅ Chuyển sang phase FACE nếu quét QR có đủ thông tin
                if (state.autoCyclePhase === "IDLE" && (hasBcardData() || hasCccdData())) {
                    enterFacePhaseBasic();
                }
            }
        } catch { }
        // Fallback id regex chỉ để hỗ trợ điền form, KHÔNG dùng để xác thực QR hợp lệ.
        const idMatch = text.match(/\b\d{9,12}\b/);
        if (idMatch) {
            parsedSomething = true;
            setVal("#idNumber", idMatch[0]);
        }

        updateActionButtons();
        const sufficient = hasCccdData() || hasBcardData();
        if (!sufficient && parsedSomething) {
            log("QR đã đọc nhưng chưa đủ dữ liệu hợp lệ cho quy trình.");
        }
        return sufficient;
    }

    function syncVideo2Aspect() {
        const vid = $("#video2"); if (!vid) return;
        vid.style.objectFit = "contain";
        if (vid.videoWidth && vid.videoHeight) vid.style.aspectRatio = `${vid.videoWidth} / ${vid.videoHeight}`;
        else vid.style.aspectRatio = "auto";
    }

    function ensureVideo2ZoomCanvas() {
        const vid = $("#video2");
        if (!vid) return null;
        const wrap = vid.closest(".video-wrap") || vid.parentElement;
        if (!wrap) return null;

        // đảm bảo wrapper có position
        const cs = getComputedStyle(wrap);
        if (!cs.position || cs.position === "static") {
            wrap.style.position = "relative";
        }

        let cvs = document.getElementById("video2-zoom");
        if (!cvs) {
            cvs = document.createElement("canvas");
            cvs.id = "video2-zoom";
            Object.assign(cvs.style, {
                position: "absolute",
                inset: "0",
                width: "100%",
                height: "100%",
                display: "block",
                zIndex: "1",
                opacity: "0",
                transition: "opacity 120ms ease",
                pointerEvents: "none",
            });
            // cho canvas zoom nằm dưới canvas2 (vẽ khung xanh)
            wrap.insertBefore(cvs, wrap.firstChild);
        }

        // Trạng thái hiển thị Cam2 được điều khiển bởi setVideo2PreviewMode().
        vid.style.pointerEvents = "none";

        return cvs;
    }

    function setVideo2PreviewMode(useZoomCanvas) {
        const vid = $("#video2");
        const cvs = document.getElementById("video2-zoom");
        if (vid) {
            vid.style.opacity = useZoomCanvas ? "0" : "1";
            vid.style.pointerEvents = "none";
        }
        if (cvs) {
            cvs.style.opacity = useZoomCanvas ? "1" : "0";
            cvs.style.pointerEvents = "none";
        }
    }

    function stopVideo2ZoomLoop(clearCanvas = true) {
        state.video2ZoomRunning = false;
        if (state.video2ZoomHandle) {
            cancelAnimationFrame(state.video2ZoomHandle);
            state.video2ZoomHandle = null;
        }
        if (clearCanvas) {
            const cvs = document.getElementById("video2-zoom");
            if (cvs) {
                const ctx = cvs.getContext("2d");
                ctx.clearRect(0, 0, cvs.width, cvs.height);
            }
            state.video2LastFrameDrawAt = 0;
        }
    }

    function freezeVideo2Frame(sourceCanvas) {
        const vid = $("#video2");
        const cvs = ensureVideo2ZoomCanvas();
        if (!vid || !cvs || !sourceCanvas) return;

        state.video2ZoomRunning = false;
        if (state.video2ZoomHandle) {
            cancelAnimationFrame(state.video2ZoomHandle);
            state.video2ZoomHandle = null;
        }

        const wrap = vid.closest(".video-wrap") || vid.parentElement;
        if (!wrap) return;
        const rect = wrap.getBoundingClientRect();
        if (cvs.width !== rect.width || cvs.height !== rect.height) {
            cvs.width = rect.width;
            cvs.height = rect.height;
        }
        const ctx = cvs.getContext("2d");
        ctx.clearRect(0, 0, cvs.width, cvs.height);
        ctx.drawImage(sourceCanvas, 0, 0, sourceCanvas.width, sourceCanvas.height, 0, 0, cvs.width, cvs.height);
        setVideo2PreviewMode(true);
        state.video2LastFrameDrawAt = Date.now();
        state.video2Frozen = true;
    }

    function resumeVideo2Frame() {
        state.video2Frozen = false;
        setVideo2PreviewMode(true);
        const vid = $("#video2");
        if (vid && vid.srcObject && !state.video2ZoomRunning) {
            startVideo2ZoomLoop();
        }
    }

    async function restoreCam2PreviewAfterVisibilityChange(reason = "") {
        const vid = $("#video2");
        if (!vid || !vid.srcObject) return;
        if (state._cam2RestoreInFlight) return;
        state._cam2RestoreInFlight = true;
        const restoreStartedAt = Date.now();
        const restoreGeneration = (state._video2RestoreGeneration || 0) + 1;
        state._video2RestoreGeneration = restoreGeneration;
        const lastFrameBeforeRestore = state.video2LastFrameDrawAt || 0;
        const videoTimeBeforeRestore = Number(vid.currentTime || 0);
        try {
            setVideo2PreviewMode(true);

            try {
                syncVideo2Aspect();
            } catch { }

            try {
                await vid.play();
            } catch (err) {
                log(`Không thể play lại Cam2 sau khi quay lại tab${reason ? ` (${reason})` : ""}: ${err?.message || err}`);
            }

            state.video2Frozen = false;
            state.video2ZoomRunning = false;
            if (state.video2ZoomHandle) {
                cancelAnimationFrame(state.video2ZoomHandle);
                state.video2ZoomHandle = null;
            }

            resumeVideo2Frame();

            const hardRestartCam2IfNeeded = async (checkLabel = "") => {
                if (state._video2RestoreGeneration !== restoreGeneration) return false;
                if (document.visibilityState !== "visible" || !state.pageVisible) return false;
                const noNewZoomFrame = (state.video2LastFrameDrawAt || 0) <= lastFrameBeforeRestore;
                const currentTimeNow = Number(vid.currentTime || 0);
                const videoNotAdvancing = currentTimeNow <= videoTimeBeforeRestore + 0.01;
                const notReady = (vid.readyState || 0) < 2;
                if (!noNewZoomFrame && !videoNotAdvancing && !notReady) {
                    return false;
                }
                try {
                    log(`Cam2 không hồi stream sau khi quay lại tab${checkLabel ? ` (${checkLabel})` : ""}. Đang restart camera 2.`);
                    await stopCam2();
                    if (state._video2RestoreGeneration !== restoreGeneration) return true;
                    await startCam2();
                    return true;
                } catch (err) {
                    log(`Restart Cam2 thất bại${checkLabel ? ` (${checkLabel})` : ""}: ${err?.message || err}`);
                    return false;
                }
            };

            const retryIfPreviewStale = async (delayMs) => {
                setTimeout(async () => {
                    if (state._video2RestoreGeneration !== restoreGeneration) return;
                    if (document.visibilityState !== "visible" || !state.pageVisible) return;
                    if (!vid.srcObject) return;
                    if ((state.video2LastFrameDrawAt || 0) > lastFrameBeforeRestore) return;
                    try {
                        state.video2ZoomRunning = false;
                        if (state.video2ZoomHandle) {
                            cancelAnimationFrame(state.video2ZoomHandle);
                            state.video2ZoomHandle = null;
                        }
                        await vid.play();
                    } catch { }
                    startVideo2ZoomLoop();
                }, delayMs);
            };

            retryIfPreviewStale(260);
            setTimeout(async () => {
                if (state._video2RestoreGeneration !== restoreGeneration) return;
                await hardRestartCam2IfNeeded(`${reason || "visibility restore"} watchdog`);
            }, 850);

            try {
                if (state.qrScanner && !state.scanLockedCam2) {
                    await state.qrScanner.start();
                }
            } catch (err) {
                log(`Không thể khôi phục QR scanner sau khi quay lại tab${reason ? ` (${reason})` : ""}: ${err?.message || err}`);
            }
        } finally {
            state._cam2RestoreInFlight = false;
        }
    }

    // ズーム 3x のフレームをキャンバスに描画するループ
    function startVideo2ZoomLoop() {
        const vid = $("#video2");
        if (!vid) return;
        const cvs = ensureVideo2ZoomCanvas();
        if (!cvs) return;

        if (state.video2ZoomRunning) return;
        if (state.video2Frozen) return;
        state.video2ZoomRunning = true;

        const ctx = cvs.getContext("2d");
        const wrap = vid.closest(".video-wrap") || vid.parentElement;
        const targetMs = 1000 / 24; // Mac Mini M4 ではプレビューをより滑らかに更新
        let last = 0;

        function loop(now) {
            if (!state.video2ZoomRunning || !vid.srcObject) {
                state.video2ZoomRunning = false;
                return;
            }

            if (!last || now - last >= targetMs) {
                last = now;

                const vw = vid.videoWidth || 0;
                const vh = vid.videoHeight || 0;
                if (vw && vh) {
                    const rect = wrap.getBoundingClientRect();
                    if (cvs.width !== rect.width || cvs.height !== rect.height) {
                        cvs.width = rect.width;
                        cvs.height = rect.height;
                    }

                    const zoom = state.video2ZoomFactor || 1;
                    const cropW = Math.floor(vw / zoom);
                    const cropH = Math.floor(vh / zoom);
                    const cropX = Math.floor((vw - cropW) / 2);
                    const cropY = Math.floor((vh - cropH) / 2);

                    ctx.clearRect(0, 0, cvs.width, cvs.height);

                    const isMirrored = wrap.classList.contains("mirror");
                    if (isMirrored) {
                        ctx.save();
                        ctx.translate(cvs.width, 0);
                        ctx.scale(-1, 1);
                    }

                    ctx.drawImage(
                        vid,
                        cropX, cropY, cropW, cropH,   // 中央領域 (ズーム)
                        0, 0, cvs.width, cvs.height   // フル表示フレーム
                    );
                    state.video2LastFrameDrawAt = Date.now();
                    setVideo2PreviewMode(true);

                    if (isMirrored) ctx.restore();
                }
            }

            state.video2ZoomHandle = requestAnimationFrame(loop);
        }

        state.video2ZoomHandle = requestAnimationFrame(loop);
    }

    async function startCam2() {
        try {
            if (!window.QrScanner) { log("qr-scanner chưa sẵn sàng."); return; }
            const vid = $("#video2"); if (!vid) { log("Không tìm thấy #video2"); return; }

            if (state.qrScanner) { try { await state.qrScanner.destroy(); } catch { } state.qrScanner = null; }
            const overlay = $("#scan-overlay");

            state.qrScanner = new window.QrScanner(
                vid,
                async (result) => {
                    if (!isPageInteractionActive() || Date.now() < (state.interactionResumeAtMs || 0)) return;
                    // chờ画面が表示されている場合、または Cam 2 がロックされている場合は QR quétを無視
                    if (state.welcomeEyesVisible || state.scanLockedCam2) return;

                    const content = (typeof result === "string") ? result : (result?.data || "");
                    if (!content) return;
                    state.lastQRRaw = content;
                    log("QR: " + content);
                    const isValidQr = await tryFillFromQR(content);
                    if (!isValidQr) {
                        if (state.handlingInvalidQr) return;
                        state.handlingInvalidQr = true;
                        await lockScanCam2("QR không hợp lệ");
                        await lockScanCam1("QR không hợp lệ");
                        log("QR không hợp lệ. Sau khi thông báo sẽ đặt lại hệ thống.");
                        await playAudioAndWait(sndQrInvalid, true);
                        await new Promise((r) => setTimeout(r, 2000));
                        await resetAll(true);
                        state.handlingInvalidQr = false;
                        return;
                    }
                    await lockScanCam2("Đọc QR hoàn tất");
                    await lockScanCam1("Đọc QR hoàn tất");

                    // state bcardImageDataUrl を更新 (cameraからのảnhを一時保存)
                    const v2 = $("#video2");
                    if (v2 && v2.videoWidth) {
                        const off = document.createElement("canvas");
                        off.width = v2.videoWidth;
                        off.height = v2.videoHeight;
                        const ctx = off.getContext("2d");
                        ctx.drawImage(v2, 0, 0, off.width, off.height);
                        state.bcardImageDataUrl = off.toDataURL("image/jpeg", 0.9);
                        const bcardPreview = $("#bcard-preview");
                        if (bcardPreview) bcardPreview.src = state.bcardImageDataUrl;
                    }


                    // 自動的に顔撮影フェーズに移行 (すぐには保存せず、顔撮影完了後に同時保存)
                    if (state.autoCyclePhase === "IDLE") {
                        enterFacePhaseBasic();
                        log("Đã nhận QR. Đang chờ nhận diện khuôn mặt để hoàn tất...");
                    }
                },
                {
                    returnDetailedScanResult: true,
                    highlightScanRegion: true,
                    highlightCodeOutline: true,
                    overlay: overlay,
                    preferredCamera: ($("#cam2-select") && $("#cam2-select").value) || state.cam2Facing,
                    maxScansPerSecond: 15,
                }
            );
            vid.setAttribute("playsinline", ""); vid.muted = true;
            const onMeta = async () => {
                syncVideo2Aspect();
                try { await vid.play(); } catch { }
                setCam2MirrorUI();
                state.cam2LastVideoTime = Number(vid.currentTime || 0);
                state.cam2LastVideoAdvanceAt = Date.now();
                startVideo2ZoomLoop();
                ensureCam2HealthMonitor();
                if (!state.presenceSending) {
                    startPresenceStream();
                }
                vid.removeEventListener("loadedmetadata", onMeta);
            };
            vid.addEventListener("loadedmetadata", onMeta);

            await state.qrScanner.start();
            await bumpCam2Resolution(vid);

            const p2 = $("#cam2-power"); if (p2) p2.classList.add("on");
            log("Đã khởi động camera 2 (QR + khuôn mặt).");
        } catch (e) { log("Lỗi khởi động camera2: " + e.message); }
    }

    async function bumpCam2Resolution(videoEl) {
        const track = videoEl?.srcObject?.getVideoTracks?.()[0];
        if (!track) return;
        try {
            const caps = track.getCapabilities ? track.getCapabilities() : {};
            const canContinuousFocus = caps.focusMode && Array.isArray(caps.focusMode) && caps.focusMode.includes("continuous");
            const constraints = {
                width: { min: 640, ideal: 1280, max: 1920 },
                height: { min: 480, ideal: 720, max: 1080 },
                advanced: canContinuousFocus ? [{ focusMode: "continuous" }] : []
            };
            await track.applyConstraints(constraints);
        } catch (e) { console.warn("applyConstraints Cam2 failed:", e); }
        const s = track.getSettings?.() || {};
        log(`Thiết lập Cam2: ${s.width}x${s.height}`);
    }

    async function stopCam2() {
        const vid = $("#video2"); if (!vid) return;
        state.presenceSending = false;
        state.video2Frozen = false;
        state._cam2RestoreInFlight = false;
        state.cam2LastVideoTime = 0;
        state.cam2LastVideoAdvanceAt = 0;
        timerManager.clearMany(state, ["cam2RestoreHandle", "cam2HealthCheckHandle"]);
        if (state.qrScanner) {
            try { await state.qrScanner.stop(); await state.qrScanner.destroy(); } catch { }
            state.qrScanner = null;
        }
        const s = vid.srcObject; if (s) { s.getTracks().forEach(t => t.stop()); vid.srcObject = null; }
        const p2 = $("#cam2-power"); if (p2) p2.classList.remove("on");
        stopVideo2ZoomLoop();
        log("Đã dừng camera 2.");
    }

    async function flipCam1() {
        state.cam1Facing = state.cam1Facing === "user" ? "environment" : "user";
        try {
            await stopCam1(); await startCam1();
            log("Cam1 facing: " + state.cam1Facing);
        } catch (e) { log("Cam1 Lậtlỗi: " + e.message); }
    }

    async function flipCam2() {
        state.cam2Facing = state.cam2Facing === "user" ? "environment" : "user";
        try {
            if (state.qrScanner && state.qrScanner.setCamera) {
                await state.qrScanner.setCamera(state.cam2Facing).catch(async () => {
                    await stopCam2();
                    const sel = $("#cam2-select"); if (sel) sel.value = "";
                    await startCam2();
                });
            } else {
                await stopCam2();
                const sel = $("#cam2-select"); if (sel) sel.value = "";
                await startCam2();
            }
            setCam2MirrorUI();
            log("Cam2 facing: " + state.cam2Facing);
        } catch (e) { log("Cam2 Lậtlỗi: " + e.message); }
    }

    function setCam2MirrorUI() {
        const wrap = $("#video2")?.closest(".video-wrap");
        if (!wrap) return;
        if (state.cam2Facing === "user") wrap.classList.add("mirror");
        else wrap.classList.remove("mirror");
    }

    window.flipCam1 = flipCam1;
    window.flipCam2 = flipCam2;

    /**
     * ビデオ用のLậtボタンを作成します。
     * @param {string} videoSel ビデオ要素のセレクター
     * @param {string} btnId ボタンの ID
     * @param {string} title ボタンのツールチップ
     * @param {string} label ボタンのラベル
     */
    function ensureFlipButtonForVideo(videoSel, btnId, title = "Lật", label = "↺") {
        const v = document.querySelector(videoSel);
        if (!v) return null;
        const wrap = v.closest('.video-wrap') || v.parentElement;
        if (!wrap) return null;

        let btn = document.getElementById(btnId);
        if (!btn) {
            btn = document.createElement('button');
            btn.id = btnId;
            btn.className = 'power-btn';
            btn.title = title;
            btn.type = 'button';
            btn.textContent = label;
            btn.style.right = '72px'; // Nguồnボタンと重ならないように調整
            wrap.appendChild(btn);
        }
        return btn;
    }

    const cam1Flip = ensureFlipButtonForVideo('#video1', 'cam1-flip', 'Flip Cam1');
    if (cam1Flip) cam1Flip.addEventListener('click', flipCam1);

    const cam2Flip = ensureFlipButtonForVideo('#video2', 'cam2-flip', 'Flip Cam2');
    if (cam2Flip) cam2Flip.addEventListener('click', flipCam2);

    async function startPresenceStream() {
        const vid = $("#video2"); if (!vid) return;
        if (!vid.srcObject) { log("Không có luồng Cam2 cho Presence."); return; }

        if (!state.allowPresence) {
            log("Presence đang tạm tắt (allowPresence=false).");
            return;
        }

        // Đã có ảnh khuôn mặt rồi thì khỏi nhận diện nữa
        if (state.faceDataUrl) {
            log("Đã có ảnh khuôn mặt nên không khởi động Presence.");
            return;
        }

        if (state.presenceSending) {
            log("Luồng Presence đang chạy.");
            return;
        }

        // 世代カウンター: bắt đầuごとに +1。
        // 古いループが実行中のまま世代が変わった場合、古いループは自動dừngします。
        const myGen = ++state._presenceGeneration;

        state.presenceSending = true;
        state.lastPersonBox = null; state.lastFrameSize = null;
        //123
        state.faceSeenSinceMs = 0;
        state.faceAutoCaptured = false;

        state.presenceLastHadPerson = false;
        state.presenceLastGreetTs = 0;
        state.presenceLastFaceCount = 0;
        state.presenceFaceIncreaseStreak = 0;
        //123
        // Haar cascade には標準的な信頼度がないため、0.0 に設定 — 最良の結果があれば顔とみなします
        state.presenceMinConf = 0.0;

        const targetW = 640;
        const sharedPresenceCanvas = document.createElement("canvas");

        const getBlobAndSize = () => new Promise((resolve) => {
            const off = sharedPresenceCanvas;
            const vw = vid.videoWidth || 640, vh = vid.videoHeight || 360;

            const zoom = state.video2ZoomFactor || 1;
            const cropW = Math.floor(vw / zoom);
            const cropH = Math.floor(vh / zoom);
            const cropX = Math.floor((vw - cropW) / 2);
            const cropY = Math.floor((vh - cropH) / 2);

            const tw = targetW;
            const th = Math.round(cropH * (tw / cropW));

            off.width = tw; off.height = th;
            const ctx = off.getContext("2d");
            ctx.drawImage(
                vid,
                cropX, cropY, cropW, cropH,  // 中央（ズーム）領域
                0, 0, tw, th                 // Python へ送信するためにリサイズ
            );

            off.toBlob((b) => resolve({ blob: b, size: { w: tw, h: th } }), "image/jpeg", 0.78);
        });

        const drawBestBox = (best, frameSize) => {
            const canvas = $("#canvas2"); const wrap = $("#video2");
            if (!canvas || !wrap || !best || !frameSize) {
                if (canvas) { const c2 = canvas.getContext("2d"); c2.clearRect(0, 0, canvas.width, canvas.height); }
                updateFaceGuideOverlay(false);
                return;
            }
            const rect = wrap.getBoundingClientRect();
            canvas.width = rect.width; canvas.height = rect.height;
            const ctx = canvas.getContext("2d"); ctx.clearRect(0, 0, canvas.width, canvas.height);
            const mapped = mapFaceBoxToGuide(best, frameSize, canvas.width, canvas.height);
            const insideGuide = isFaceInsideGuide(best, frameSize);
            state.faceGuideLastInside = insideGuide;
            updateFaceGuideOverlay(insideGuide);

            // Tính toán countdown progress
            let ratio = best ? 1 : 0;
            let color = insideGuide ? getProgressColor(ratio) : "#f7a24b";
            let label = insideGuide ? t("face.progress.full") : t("face.move.into.frame");
            if (state.autoCyclePhase === "FACE" && !state.faceAutoCaptured && state.faceSeenSinceMs) {
                const now = Date.now();
                const total = state.faceAutoCaptureMs ?? 1200;
                const elapsed = now - state.faceSeenSinceMs;
                ratio = Math.min(elapsed / total, 1);
                const remainingSec = Math.max(0, Math.ceil((total - elapsed) / 1000));

                color = insideGuide ? getProgressColor(ratio) : "#f7a24b";
                label = insideGuide
                    ? t("face.progress.countdown", { percent: Math.round(ratio * 100), seconds: remainingSec })
                    : t("face.move.into.frame");
            }

            ctx.lineWidth = 4;
            ctx.strokeStyle = color;
            ctx.shadowColor = color;
            ctx.shadowBlur = 8;
            const rx = mapped?.x ?? 0;
            const ry = mapped?.y ?? 0;
            const rw = mapped?.w ?? 0;
            const rh = mapped?.h ?? 0;
            ctx.strokeRect(rx, ry, rw, rh);

            ctx.shadowBlur = 0;
            drawProgressLabel(ctx, rx, ry, label, color);
        };

        const drawFrameWithBoxes = (imgBlob, frameSize) => {
            const canvas = $("#canvas2"); const wrap = $("#video2");
            if (!canvas || !wrap || !imgBlob) {
                if (canvas) { const c2 = canvas.getContext("2d"); c2.clearRect(0, 0, canvas.width, canvas.height); }
                updateFaceGuideOverlay(false);
                return;
            }
            const rect = wrap.getBoundingClientRect();
            canvas.width = rect.width; canvas.height = rect.height;
            createImageBitmap(imgBlob).then((bitmap) => {
                const ctx = canvas.getContext("2d");
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(bitmap, 0, 0, bitmap.width, bitmap.height, 0, 0, canvas.width, canvas.height);
                const insideGuide = isFaceInsideGuide(state.lastPersonBox, frameSize);
                state.faceGuideLastInside = insideGuide;
                updateFaceGuideOverlay(insideGuide);

                // サーバーが既にボックスを描画したフレームを返している場合でも、カウントダウンテキストを表示
                if (state.autoCyclePhase === "FACE" && !state.faceAutoCaptured && state.faceSeenSinceMs && insideGuide) {
                    const now = Date.now();
                    const total = state.faceAutoCaptureMs ?? 1200;
                    const elapsed = now - state.faceSeenSinceMs;
                    const remainingSec = Math.max(0, Math.ceil((total - elapsed) / 1000));
                    const ratio = Math.min(elapsed / total, 1);
                    const color = getProgressColor(ratio);

                    ctx.font = "bold 20px system-ui";
                    ctx.fillStyle = color;
                    ctx.shadowColor = "black"; ctx.shadowBlur = 4;
                    ctx.fillText(t("face.progress.countdown", { percent: Math.round(ratio * 100), seconds: remainingSec }), 20, 40);
                    ctx.shadowBlur = 0;
                }

                bitmap.close();
            }).catch(() => { });
        };

        const frameDelay = Math.max(1, Math.round(1000 / state.presenceFps));

        while (state.presenceSending && vid.srcObject && myGen === state._presenceGeneration) {
            if (!isPageInteractionActive() || Date.now() < (state.interactionResumeAtMs || 0)) {
                state.faceSeenSinceMs = 0;
                state.lastPersonBox = null;
                state.lastFrameSize = null;
                state.faceGuideLastInside = false;
                drawBestBox(null, null);
                await new Promise((r) => setTimeout(r, 180));
                continue;
            }

            // 実行中に以下の状態になった場合:
            // 1) OCR が再開された、または
            // 2) すでにảnh khuôn mặtがある
            // → ループをdừngし、phát hiệnの送信を中止
            if (!state.allowPresence) {
                log("Đã dừng Presence vì allowPresence=false.");
                break;
            }

            try {
                const { blob, size } = await getBlobAndSize();
                const fd = new FormData();
                fd.append("frame", blob, `frame-${Date.now()}.jpg`);
                fd.append("ts", String(Date.now()));
                const isFacePhase = state.autoCyclePhase === "FACE";
                const shouldKeepTrackingRecognizedFace = state.faceRecognitionAwaitFaceExit || isReturningVisitorOverlayVisible();
                const shouldUseFaceDetection = isFacePhase || (!state.welcomeEyesVisible && (isFaceRecognitionEligible() || shouldKeepTrackingRecognizedFace));
                const useFrameWithBoxes = isFacePhase && !!state.drawBoxesOnStream && !!state.presenceEndpointWithBoxes;
                const detectUrl = useFrameWithBoxes
                    ? state.presenceEndpointWithBoxes
                    : (shouldUseFaceDetection ? state.faceEndpoint : state.presenceEndpoint);
                const res = await fetch(detectUrl, { method: "POST", body: fd });

                let currentFaceCount = 0;
                if (useFrameWithBoxes) {
                    if (res.ok && res.headers.get("Content-Type")?.includes("image")) {
                        const imgBlob = await res.blob();
                        const bestHeader = res.headers.get("X-Face-Best");
                        const sizeHeader = res.headers.get("X-Frame-Size");
                        state.lastPersonBox = bestHeader ? JSON.parse(bestHeader) : null;
                        state.lastFrameSize = sizeHeader ? JSON.parse(sizeHeader) : size;
                        currentFaceCount = state.lastPersonBox ? 1 : 0;
                        drawFrameWithBoxes(imgBlob, state.lastFrameSize);
                    } else {
                        state.lastPersonBox = null; state.lastFrameSize = null;
                        currentFaceCount = 0;
                        drawFrameWithBoxes(null, null);
                    }
                } else {
                    const js = await res.json().catch(() => null);
                    if (js && js.ok) {
                        state.lastPersonBox = js.best || null;
                        state.lastFrameSize = js.frame_size || size;
                        currentFaceCount = Array.isArray(js.boxes)
                            ? js.boxes.length
                            : (state.lastPersonBox ? 1 : 0);
                        drawBestBox(state.lastPersonBox, state.lastFrameSize);
                    } else {
                        state.lastPersonBox = null; state.lastFrameSize = null;
                        currentFaceCount = 0;
                        drawBestBox(null, null);
                    }
                }
                //123
                const hasDetectedFace = shouldUseFaceDetection && !!state.lastPersonBox;
                const hasGuidedFace = hasDetectedFace && isFaceInsideGuide(state.lastPersonBox, state.lastFrameSize);
                state.faceGuideLastInside = hasGuidedFace;
                updateFaceGuideOverlay(hasGuidedFace);
                const hasFace = isFacePhase && hasGuidedFace;

                // Auto-capture sau khi thấy face liên tục đủ faceAutoCaptureMs (Chỉ khi phase = FACE)
                if (!state.faceAutoCaptured && state.autoCyclePhase === "FACE") {
                    const nowMs = Date.now();
                    const readyAtMs = state.faceCaptureReadyAtMs || 0;
                    const delayMs = state.faceAutoCaptureMs ?? 1000;
                    const holdToleranceMs = state.faceGuideHoldToleranceMs ?? 0;
                    if (nowMs < readyAtMs) {
                        state.faceSeenSinceMs = 0;
                        state.faceGuideLostAtMs = 0;
                    } else if (hasFace) {
                        state.faceGuideLostAtMs = 0;
                        if (!state.faceSeenSinceMs) state.faceSeenSinceMs = nowMs;
                        if (nowMs - state.faceSeenSinceMs >= delayMs) {
                            const captureStarted = await handleCaptureFace();
                            if (captureStarted) {
                                state.faceAutoCaptured = true;
                                // 撮影後にループをdừng
                                state.presenceSending = false;
                            } else {
                                state.faceSeenSinceMs = 0;
                                state.faceGuideLostAtMs = 0;
                            }
                        }
                    } else {
                        if (!state.faceGuideLostAtMs) state.faceGuideLostAtMs = nowMs;
                        if (nowMs - state.faceGuideLostAtMs > holdToleranceMs) {
                            state.faceSeenSinceMs = 0;
                        }
                    }
                }

                const hasPerson = isFacePhase ? hasFace : !!state.lastPersonBox;
                const now = Date.now();
				if (!isFacePhase && shouldUseFaceDetection && isFaceRecognitionEligible()) {
                    if (hasGuidedFace) {
                        if (!state.faceRecognitionSeenSinceMs) {
                            state.faceRecognitionSeenSinceMs = now;
                        }
                        const cooldownElapsed = now - (state.faceRecognitionLastAttemptAt || 0);
                        if (
                            cooldownElapsed >= state.faceRecognitionCooldownMs &&
                            now - state.faceRecognitionSeenSinceMs >= state.faceRecognitionStableMs
                        ) {
                            startFaceRecognitionFromBlob(blob);
                            state.faceRecognitionSeenSinceMs = 0;
                        }
                    } else {
                        state.faceRecognitionSeenSinceMs = 0;
                        state.faceRecognitionAwaitFaceExit = false;
                        hideReturningVisitorOverlay();
                    }
                } else if (!isFacePhase) {
                    state.faceRecognitionSeenSinceMs = 0;
                    if (!state.lastPersonBox) {
                        hideReturningVisitorOverlay();
                    }
                    if (!hasPerson) {
                        state.faceRecognitionAwaitFaceExit = false;
                    }
                }                
                
                handlePresenceReaction({ hasPerson, currentFaceCount, now });

            } catch (err) {
                log("Presence lỗi: " + (err?.message || err));
            }
            await new Promise(r => setTimeout(r, frameDelay));
        }

        state.presenceSending = false;
        state.faceGuideLastInside = false;
        updateFaceGuideOverlay(false);
        // dừng時にフレームをクリア
        const canvas = $("#canvas2");
        if (canvas) {
            const c2 = canvas.getContext("2d");
            c2.clearRect(0, 0, canvas.width, canvas.height);
        }
    }

    const btnCam2Start = $("#cam2-start"); if (btnCam2Start) btnCam2Start.addEventListener("click", startCam2);
    const btnCam2Stop = $("#cam2-stop"); if (btnCam2Stop) btnCam2Stop.addEventListener("click", stopCam2);

    function showFaceProcessingBadge(show) {
        const el = document.getElementById("face-processing-badge");
        if (!el) return;
        if (show) {
            state.faceProcessingBadgeShownAt = Date.now();
        }
        el.hidden = !show;
    }

    function hideFaceProcessingBadgeAfterMinimum() {
        const shownAt = state.faceProcessingBadgeShownAt || 0;
        const remaining = Math.max(0, state.faceProcessingBadgeMinMs - (Date.now() - shownAt));
        setTimeout(() => {
            showFaceProcessingBadge(false);
        }, remaining);
    }

    function rearmFaceCapture(reason = "", delayMs = 500) {
        if (reason) {
            log(reason);
        }
        if (state.autoCyclePhase !== "FACE") {
            state.autoCyclePhase = "FACE";
            updateStepRail();
        }
        state.faceAutoCaptured = false;
        state.faceSeenSinceMs = 0;
        state.faceGuideLostAtMs = 0;
        state.faceCaptureReadyAtMs = Date.now() + Math.max(0, delayMs);
        timerManager.clearNamed(state, "faceRetryTimer");
        if (!state.presenceSending && state.allowPresence && !state.faceDataUrl) {
            startPresenceStream();
        }
    }

    async function handleCaptureFace() {
        if (!isPageInteractionActive() || Date.now() < (state.interactionResumeAtMs || 0)) {
            log("Không chụp ảnh khuôn mặt ngay sau khi chuyển tab.");
            return false;
        }
        const vid = $("#video2");

        // Capture trực tiếp từ frame gốc của video2 để giữ chi tiết tốt nhất
        if (!vid || !vid.srcObject || !vid.videoWidth || !vid.videoHeight) {
            log("Khung hình gốc của camera 2 chưa sẵn sàng");
            return false;
        }

        // 青い枠内に顔があることを確認するため、顔phát hiệnの bbox を使用
        const best = state.lastPersonBox;
        const fsz = state.lastFrameSize;
        if (!best || !fsz) {
            log("Chưa phát hiện khuôn mặt - vui lòng đưa mặt vào trong khung xanh.");
            return false;
        }
        if (!isFaceInsideGuide(best, fsz)) {
            log("Khuôn mặt đang ở ngoài khung nhận diện - vui lòng căn mặt vào bên trong khung.");
            updateFaceGuideOverlay(false);
            return false;
        }

        // CPU がビジーになる前にレンダリングtác vụを優先するため、requestAnimationFrame を使用
        return await new Promise((resolve) => {
            requestAnimationFrame(async () => {
                const off = document.createElement("canvas");
                off.width = vid.videoWidth;
                off.height = vid.videoHeight;
                const ctx = off.getContext("2d");
                const wrap = vid.closest(".video-wrap") || vid.parentElement;
                const isMirrored = !!wrap && wrap.classList.contains("mirror");
                if (isMirrored) {
                    ctx.save();
                    ctx.translate(off.width, 0);
                    ctx.scale(-1, 1);
                }
                ctx.drawImage(vid, 0, 0, off.width, off.height);
                if (isMirrored) ctx.restore();
                freezeVideo2Frame(off);

                log(`Đang xử lý ảnh khuôn mặt (${off.width}x${off.height})...`);
                showFaceProcessingBadge(true);

                // メインスレッドをブロックしないよう、非同期の toBlob を使用
                off.toBlob((blob) => {
                    if (!blob) {
                        hideFaceProcessingBadgeAfterMinimum();
                        rearmFaceCapture("Chụp ảnh khuôn mặt thất bại, đang thử lại...", 500);
                        resolve(false);
                        return;
                    }

                    if (state.autoCyclePhase === "FACE") {
                        state.autoCyclePhase = "SUBMITTING";
                        updateStepRail();
                        timerManager.clearNamed(state, "faceRetryTimer");
                        state.faceRetryCount = 0;
                    }

                    // 1. Blob URL を使用して即座にプレビューを表示 (非常に高速)
                    const previewUrl = URL.createObjectURL(blob);
                    const facePrev = $("#face-preview");
                    if (facePrev) {
                        // メモリリークを防ぐため、古い URL を解放
                        if (facePrev._blobUrl) URL.revokeObjectURL(facePrev._blobUrl);
                        facePrev._blobUrl = previewUrl;
                        facePrev.src = previewUrl;
                        facePrev.style.maxWidth = "100%";
                        facePrev.style.transform = "none";
                    }

                    // 2. サーバー送信用の Base64 変換をバックグラウンドで実行
                    const reader = new FileReader();
                    reader.onerror = () => {
                        hideFaceProcessingBadgeAfterMinimum();
                        state.faceDataUrl = null;
                        rearmFaceCapture("Đọc ảnh khuôn mặt thất bại, đang thử lại...", 600);
                    };
                    reader.onloadend = async () => {
                        if (!reader.result) {
                            hideFaceProcessingBadgeAfterMinimum();
                            state.faceDataUrl = null;
                            rearmFaceCapture("Không thể tạo dữ liệu ảnh khuôn mặt, đang thử lại...", 600);
                            return;
                        }

                        state.faceDataUrl = reader.result;

                        state.presenceFps = 10;
                        hideFaceProcessingBadgeAfterMinimum();
                        log("Đã chụp xong ảnh khuôn mặt (Base64 sẵn sàng).");
                        if (isCccdFlowActive() && !hasBcardData()) {
                            const js = await saveCccdDraftInBackground({
                                registration_id: state.registrationId,
                                data: collectFormData(),
                                face_image: state.faceDataUrl,
                                image_data_url: state.bcardImageDataUrl || null,
                                cccd_qr_raw: state.lastQRRaw || "",
                                cccd_ocr_text: "",
                                cccd_scan_status: "done",
                            }, state.bcardImageDataUrl || null);
                            if (js?.saved?.face || js?.face_register_job_id) {
                                log("Đã lưu xong ảnh khuôn mặt CCCD.");
                            } else {
                                log("Phản hồi lưu ảnh khuôn mặt CCCD không có thông tin face.");
                            }
                        }
                        updateActionButtons();
                        tryFinalizeSessionAfterFaceAndOcr("face-captured");
                    };
                    reader.readAsDataURL(blob);
                    resolve(true);
                }, "image/jpeg", 0.8);
            });
        });
    }
    const btnCapture = $("#capture-face");
    if (btnCapture) btnCapture.addEventListener("click", handleCaptureFace);

    async function resetAll(soft = false) {
        state.isResetting = true;
        clearWelcomeIdleTimer();
        interruptAndClearAudioQueue(); // 問題 2: 再生中のâm thanhをクリア
        timerManager.clearMany(state, [
            "thankYouResetTimer",
            "removingForceResetTimer",
            "_resetRestartTimer",
            "faceRecognitionOverlayTimer",
            "faceGuideAudioTimer",
            "faceRetryTimer",
            "appointmentPromptTimer",
            "appointmentNoticeTimer",
            "welcomeHideTimer",
            "cam2RestoreHandle",
        ]);
        stopBcardOcrPolling();
		stopFaceRecognitionPolling();
        hideReturningVisitorOverlay();
        closeAllAppointmentOverlays();
        state.faceRecognitionJobId = null;
        state.faceRecognitionStatus = "idle";
        state.faceRecognitionSending = false;
        state.faceRecognitionSeenSinceMs = 0;
        state.faceRecognitionAwaitFaceExit = false;
        state.qrResolvedProfile = null;
        
        // 1. Dừng presence + auto-card + camera
        try {
            if (!soft) {
                state._presenceGeneration++;    // 古い presence ループを強制thoát
                state.presenceSending = false;  // presence 内の while ループをdừng
                state.cardAutoSending = false;
                await stopCam1();
                await stopCam2();
            } else {
                state.cardAutoSending = false;
            }
            state.cardAutoDone = false;
        } catch (err) {
            log("Lỗi dừng camera trong lúc đặt lại: " + (err?.message || err));
        }

        // 2. canvas2 上のkhung nhận diệnを消去
        const canvas2 = $("#canvas2");
        if (canvas2) {
            const c2 = canvas2.getContext("2d");
            c2.clearRect(0, 0, canvas2.width, canvas2.height);
        }

        // 3. 状態ロジックのđặt lại
        state.faceDataUrl = null;
        state.serverQRUrl = null;
        state.bcardImageDataUrl = null;
        state.lastBCardFields = null;
        state.lastBCardText = null;
        state.registrationId = null;
        state.cccdFlowActive = false;
        state.lastQRRaw = null;
        state.allowPresence = true;
        state.autoCyclePhase = "IDLE"; // chờ状態にđặt lại
        state.removingRequiresCompletionAudio = false;
        state.removingPhaseMinUntil = 0;
        state.faceAutoCaptured = false;
        state.faceCaptureReadyAtMs = 0;
        state.faceGuideLostAtMs = 0;
        state.completionAudioDone = false;
        state.emptyGapCount = 0;
        state.cardRetryCount = 0;
        state.presenceLastHadPerson = false;
        state.presenceLastFaceCount = 0;
        state.presenceFaceIncreaseStreak = 0;
        state.suppressGreetingDuringCompletion = false;
        state.ocrTaskId = null;
        state.ocrStatus = "idle";
        state.sessionFinalizeTriggered = false;
        state.cardRetryRequested = false;
        state.appointmentDayItems = [];
        state.appointmentConfirmCallback = null;
        state.appointmentConfirmCancelCallback = null;
        state.appointmentPendingFinalizePayload = null;
        state.appointmentPendingFinalizeSource = "";
        state.pendingCardRemovalReset = false;
        closeAppointmentNotice();
        state.faceRetryCount = 0;
        showFaceProcessingBadge(false);
        resumeVideo2Frame();
        showRemoveCardOverlay(false);
        clearCardBbox();
        state.faceSeenSinceMs = 0;
        state.lastPersonBox = null;
        state.lastFrameSize = null;
        state.faceGuideLastInside = false;
        updateFaceGuideOverlay(false);
        showWelcomeEyes(true);

        // 4. フォーム情報の消去
        ["#fullName", "#idNumber", "#oldId", "#dob", "#gender", "#expiry", "#address", "#issued"]
            .forEach(sel => setVal(sel, ""));

        fillBCardPane({}, "");
        toggleBCardPane(false);
        toggleCCCDForm(true);

        const facePrev = $("#face-preview");
        if (facePrev) facePrev.src = "";

        const bcardPreview = $("#bcard-preview");
        if (bcardPreview) bcardPreview.src = "";

        // 5. UI 更新
        if (!soft) {
            window.cam1Started = false;
            const p1 = $("#cam1-power"); if (p1) p1.classList.remove("on");
            const p2 = $("#cam2-power"); if (p2) p2.classList.remove("on");
        }

        uiSetScanLockedCam1(false);
        uiSetScanLockedCam2(false);
        state.cardAutoDone = false; // 新しいdanh thiếpのquétを常に許可
        updateActionButtons();
        log(soft ? "Đã đặt lại mềm về trạng thái IDLE (giữ nguyên camera)." : "Đã đặt lại hệ thống về trạng thái IDLE.");

        if (soft) {
            // Soft reset vẫn giữ camera, nhưng phải cưỡng bức kết thúc vòng presence cũ
            // để tránh state bị kẹt sau khi timeout rồi quay lại màn hình robot.
            state._presenceGeneration++;
            state.presenceSending = false;
            state.cardDetectSuppressUntilMs = Date.now() + 2500;
            setTimeout(async () => {
                const v2 = $("#video2");
                const hasCam2Stream = !!(v2 && v2.srcObject);
                if (!hasCam2Stream) {
                    try {
                        await startCam2();
                    } catch (err) {
                        log("Không thể khởi động lại camera 2 sau khi đặt lại mềm: " + (err?.message || err));
                    }
                } else if (state.allowPresence && !state.faceDataUrl) {
                    startPresenceStream();
                }
                if (!state.cardAutoSending && state.autoCyclePhase === "IDLE") {
                    startAutoCardFromCam1();
                }
            }, 300);
            state.isResetting = false;
            return;
        }

        // 6. 2giây後に両方のcameraをkhởi động lại（resetAll が再度呼ばれた場合にキャンセルできるようタイマー ID を保存）
        timerManager.setNamedTimeout(state, "_resetRestartTimer", async () => {
            try {
                // camera 1 がオフの場合はkhởi động lại
                if (!window.cam1Started) {
                    await startCam1();
                }
            } catch (err) {
                log("Không thể khởi động lại camera 1 sau khi đặt lại: " + (err?.message || err));
            }

            try {
                // camera 2 がオフの場合はkhởi động lại
                const v2 = $("#video2");
                const isOn = v2 && v2.srcObject;
                if (!isOn) {
                    await startCam2();
                }
            } catch (err) {
                log("Không thể khởi động lại camera 2 sau khi đặt lại: " + (err?.message || err));
            }
        }, 2000);
        state.isResetting = false;
    }

    // === フルスクリーンthoát / ウェブアプリ閉鎖 / đặt lạiの処理 ===
    function createSystemButtons() {
        // --- 1. thoátボタン ---
        const btnExit = document.createElement("button");
        btnExit.innerText = t("btn.exit");
        btnExit.setAttribute("data-runtime-i18n", "btn.exit");
        Object.assign(btnExit.style, {
            position: "fixed",
            bottom: "10px",
            right: "10px",
            padding: "5px 10px",
            backgroundColor: "rgba(200, 200, 200, 0.3)",
            color: "rgba(100, 100, 100, 0.5)",
            border: "none",
            borderRadius: "4px",
            fontSize: "12px",
            zIndex: "9999",
            cursor: "pointer"
        });

        btnExit.addEventListener('click', function (e) {
            e.preventDefault();
            log("Đang đóng ứng dụng...");
            window.close();
        });

        document.body.appendChild(btnExit);

        // --- 2. 一括đặt lạiボタン ---
        const btnResetManual = document.createElement("button");
        btnResetManual.innerText = t("btn.reset");
        btnResetManual.setAttribute("data-runtime-i18n", "btn.reset");
        Object.assign(btnResetManual.style, {
            position: "fixed",
            bottom: "10px",
            right: "60px", // Nhích sang trái so với nút thoát
            padding: "5px 10px",
            backgroundColor: "rgba(200, 200, 200, 0.3)",
            color: "rgba(100, 100, 100, 0.5)",
            border: "none",
            borderRadius: "4px",
            fontSize: "12px",
            zIndex: "9999",
            cursor: "pointer"
        });

        btnResetManual.addEventListener('click', function (e) {
            e.preventDefault();
            log("Đã đặt lại hệ thống thủ công...");
            resetAll();
        });

        document.body.appendChild(btnResetManual);
    }
    createSystemButtons();

    function refreshRuntimeI18nLabels() {
        document.querySelectorAll("[data-runtime-i18n]").forEach((el) => {
            const key = el.getAttribute("data-runtime-i18n");
            if (key) el.textContent = t(key);
        });
        const cam1PowerBtn = document.getElementById("cam1-power");
        const cam2PowerBtn = document.getElementById("cam2-power");
        if (cam1PowerBtn) {
            cam1PowerBtn.title = t("camera.power.1");
            cam1PowerBtn.setAttribute("aria-label", t("camera.power.1"));
        }
        if (cam2PowerBtn) {
            cam2PowerBtn.title = t("camera.power.2");
            cam2PowerBtn.setAttribute("aria-label", t("camera.power.2"));
        }
        if (btnAudio) {
            btnAudio.textContent = state.audio ? t("bcard.audio.off") : t("bcard.audio.on");
        }
        if (btnScanBCard && !btnScanBCard.disabled) {
            btnScanBCard.textContent = t("bcard.scan");
        }
        updateFaceGuideOverlay(!!state.faceGuideLastInside);
        updateAppointmentTimeSelects();
        if (window.I18N && typeof window.I18N.updateLanguageSwitchers === "function") {
            window.I18N.updateLanguageSwitchers();
        }
    }
    window.addEventListener("i18n:languagechange", refreshRuntimeI18nLabels);

    function bindLanguageSwitcher() {
        if (!languageSwitchButtons.length || !window.I18N) return;
        if (typeof window.I18N.updateLanguageSwitchers === "function") {
            window.I18N.updateLanguageSwitchers();
        }
        languageSwitchButtons.forEach((button) => {
            button.addEventListener("click", async function () {
                const nextLang = String(button.getAttribute("data-lang-value") || "vi").toLowerCase();
                if (nextLang === window.I18N.getLang()) return;
                button.disabled = true;
                try {
                    await window.I18N.persistLang(nextLang);
                    window.location.reload();
                } catch (error) {
                    console.error("update kiosk language failed:", error);
                } finally {
                    button.disabled = false;
                }
            });
        });
    }
    bindLanguageSwitcher();

    const btnReset = $("#btn-reset"); if (btnReset) btnReset.addEventListener("click", resetAll);

    if (appointmentPromptYesBtn) {
        appointmentPromptYesBtn.addEventListener("click", function () {
            openAppointmentForm();
        });
    }

    if (appointmentPromptQABtn) {
        appointmentPromptQABtn.addEventListener("click", function () {
            clearAppointmentPromptTimer();
            closeAllAppointmentOverlays();
            window.location.href = "/qa?autostart=1";
        });
    }

    if (sideAppointmentBtn) {
        sideAppointmentBtn.addEventListener("click", function () {
            openAppointmentForm();
        });
    }

    if (sideQaBtn) {
        sideQaBtn.addEventListener("click", function () {
            clearAppointmentPromptTimer();
            closeAllAppointmentOverlays();
            window.location.href = "/qa?autostart=1";
        });
    }

    if (appointmentPromptNoBtn) {
        appointmentPromptNoBtn.addEventListener("click", async function () {
            clearAppointmentPromptTimer();
            await continueFinalizeAfterAppointment("appointment-skip");
        });
    }

    if (appointmentPurposeSelect && appointmentNoteTextarea) {
        appointmentPurposeSelect.addEventListener("change", function () {
            // Keep purpose and note independent to avoid duplicated content in saved description.
        });
    }

    if (appointmentDateInput) {
        appointmentDateInput.addEventListener("change", async function () {
            await loadAppointmentDaySchedule(String(appointmentDateInput.value || "").trim());
        });
    }

    if (appointmentStartTimeSelect) {
        appointmentStartTimeSelect.addEventListener("focus", function () {
            setAppointmentTimeSelectExpanded(appointmentStartTimeSelect, true);
        });
        appointmentStartTimeSelect.addEventListener("change", function () {
            updateAppointmentTimeSelects();
            setAppointmentTimeSelectExpanded(appointmentStartTimeSelect, false);
        });
        appointmentStartTimeSelect.addEventListener("blur", function () {
            setAppointmentTimeSelectExpanded(appointmentStartTimeSelect, false);
        });
    }

    if (appointmentEndTimeSelect) {
        appointmentEndTimeSelect.addEventListener("focus", function () {
            setAppointmentTimeSelectExpanded(appointmentEndTimeSelect, true);
        });
        appointmentEndTimeSelect.addEventListener("change", function () {
            setAppointmentTimeSelectExpanded(appointmentEndTimeSelect, false);
        });
        appointmentEndTimeSelect.addEventListener("blur", function () {
            setAppointmentTimeSelectExpanded(appointmentEndTimeSelect, false);
        });
    }

    if (appointmentNoteTextarea) {
        appointmentNoteTextarea.addEventListener("input", function () {
            applyParsedDateTimeFromNote(appointmentNoteTextarea.value);
        });
    }

    if (appointmentMicBtn) {
        const startHold = function (event) {
            if (event) event.preventDefault();
            startAppointmentMic();
        };
        const stopHold = function (event) {
            if (event) event.preventDefault();
            stopAppointmentMic();
        };
        appointmentMicBtn.addEventListener("mousedown", startHold);
        appointmentMicBtn.addEventListener("touchstart", startHold, { passive: false });
        appointmentMicBtn.addEventListener("mouseup", stopHold);
        appointmentMicBtn.addEventListener("mouseleave", stopHold);
        appointmentMicBtn.addEventListener("touchend", stopHold);
        appointmentMicBtn.addEventListener("touchcancel", stopHold);
    }

    if (appointmentCancelBtn) {
        appointmentCancelBtn.addEventListener("click", function () {
            openAppointmentConfirm(
                {
                    title: t("appt.confirm.cancel.title"),
                    message: "",
                    yesText: t("btn.confirm"),
                    noText: t("btn.no")
                },
                async function () {
                    await continueFinalizeAfterAppointment("appointment-cancel");
                },
                function () {
                    setAppointmentOverlayVisible(appointmentConfirmOverlay, false);
                    setAppointmentOverlayVisible(appointmentFormOverlay, true);
                }
            );
        });
    }

    if (appointmentSubmitBtn) {
        appointmentSubmitBtn.addEventListener("click", function () {
            const validationError = getAppointmentValidationError();
            if (validationError) {
                openAppointmentNotice(validationError, { title: t("appt.error.title"), isError: true });
                return;
            }
            openAppointmentConfirm(
                {
                    title: t("appt.confirm.title"),
                    message: t("appt.confirm.create.msg"),
                    yesText: t("btn.confirm"),
                    noText: t("btn.close")
                },
                async function () {
                    closeAppointmentConfirm();
                    await submitAppointmentFromOverlay();
                },
                function () {
                    setAppointmentOverlayVisible(appointmentConfirmOverlay, false);
                    setAppointmentOverlayVisible(appointmentFormOverlay, true);
                }
            );
        });
    }

    if (appointmentConfirmYesBtn) {
        appointmentConfirmYesBtn.addEventListener("click", async function () {
            const cb = state.appointmentConfirmCallback;
            closeAppointmentConfirm();
            if (cb) await cb();
        });
    }

    if (appointmentConfirmNoBtn) {
        appointmentConfirmNoBtn.addEventListener("click", function () {
            const cb = state.appointmentConfirmCancelCallback;
            closeAppointmentConfirm();
            if (cb) cb();
        });
    }

    if (appointmentNoticeCloseBtn) {
        appointmentNoticeCloseBtn.addEventListener("click", function () {
            closeAppointmentNotice();
        });
    }

    async function handleRegister(e) {
        if (e) e.preventDefault();
        const readyForRegister = (hasCccdData() || hasBcardData()) && !state.isSubmitting;
        if (!readyForRegister) {
            log("Thiếu dữ liệu cần thiết để đăng ký hoặc đang trong quá trình gửi.");
            return;
        }
        await sendPayloadToPython("register");
    }
    const btnRegister = $("#btn-register");
    if (btnRegister) btnRegister.addEventListener("click", handleRegister);

    const btnPrint = $("#btn-print-qr");
    if (btnPrint) btnPrint.addEventListener("click", (e) => {
        if (!state.serverQRUrl) {
            e.preventDefault();
            alert(t("print.qr.missing"));
            return;
        }
        const src = state.serverQRUrl;
        if (!src) { alert(t("print.qr.missing")); return; }

        const abs = src.startsWith("http") ? src : new URL(src, window.location.origin).toString();
        const url = abs + (abs.includes("?") ? "&" : "?") + "t=" + Date.now();

        const iframe = document.createElement("iframe");
        iframe.style.position = "fixed";
        iframe.style.right = "0"; iframe.style.bottom = "0";
        iframe.style.width = "0"; iframe.style.height = "0";
        iframe.style.border = "0";
        document.body.appendChild(iframe);

        const html = `
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>Đăng ký QR</title>
          <base href="${window.location.origin}/">
          <style>
            @page { size:auto; margin:10mm; }
            html, body { height:100%; margin:0; background:#fff; }
            body { display:flex; align-items:center; justify-content:center; }
            img  { width:45mm; height:45mm; object-fit:contain; }
          </style>
        </head>
        <body>
          <img id="qr" src="${url}" alt="QR" />
          <script>
            const img = document.getElementById('qr');
            img.onload = () => {
              window.focus(); window.print();
              setTimeout(() => { parent.document.body.removeChild(frameElement); }, 300);
            };
          <\/script>
        </body>
      </html>`;
        const doc = iframe.contentWindow.document;
        doc.open(); doc.write(html); doc.close();
    });

    function ensurePowerButtonForVideo(videoSel, btnId, title = "Nguồn", icon = "⏻") {
        const v = document.querySelector(videoSel);
        if (!v) return null;
        const wrap = v.closest('.video-wrap') || v.parentElement;
        if (!wrap) return null;

        let btn = document.getElementById(btnId);
        if (!btn) {
            btn = document.createElement('button');
            btn.id = btnId;
            btn.className = 'power-btn';
            btn.title = title;
            btn.type = 'button';
            btn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
             width="26" height="26" aria-hidden="true">
          <path d="M12 3 v7"
                stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>
          <path d="M7.5 6.5
                  a7 7 0 1 0 9 0"
                stroke="currentColor" stroke-width="2" stroke-linecap="round"
                fill="none"/>
        </svg>`;
            wrap.appendChild(btn);
        }
        return btn;
    }

    const cam1Power = ensurePowerButtonForVideo('#video1', 'cam1-power', t('camera.power.1'));
    const cam2Power = ensurePowerButtonForVideo('#video2', 'cam2-power', t('camera.power.2'));
    refreshRuntimeI18nLabels();

    if (cam1Power) cam1Power.addEventListener('click', async () => {
        try {
            if (!window.cam1Started) {
                const btn = document.querySelector('#cam1-start');
                if (btn) btn.click(); else await startCam1();
                cam1Power.classList.add('on');
            } else {
                const btn = document.querySelector('#cam1-stop');
                if (btn) btn.click(); else await stopCam1();
                cam1Power.classList.remove('on');
            }
        } catch { }
    });

    if (cam2Power) cam2Power.addEventListener('click', async () => {
        try {
            const v2 = document.querySelector('#video2');
            const isOn = v2 && v2.srcObject;
            if (!isOn) {
                const btn = document.querySelector('#cam2-start');
                if (btn) btn.click(); else await startCam2();
                cam2Power.classList.add('on');
            } else {
                const btn = document.querySelector('#cam2-stop');
                if (btn) btn.click(); else await stopCam2();
                cam2Power.classList.remove('on');
            }
        } catch { }
    });

    // Nút điều khiển cửa sổ (fullscreen browser: Chrome/Firefox)
    (function setupWindowButton() {
        const btn = document.createElement('button');
        btn.id = 'win-ctl-btn';
        btn.type = 'button';
        btn.title = 'Bật/tắt toàn màn hình (có thể dùng F11)';
        btn.className = 'floating-win-btn';
        btn.textContent = '⛶';

        document.body.appendChild(btn);

        // ---- Helpers Fullscreen ----
        function isFullscreen() {
            return !!(
                document.fullscreenElement ||
                document.webkitFullscreenElement ||
                document.mozFullScreenElement ||
                document.msFullscreenElement
            );
        }

        function requestFs(elem) {
            const el = elem || document.documentElement;
            if (el.requestFullscreen) return el.requestFullscreen();
            if (el.webkitRequestFullscreen) return el.webkitRequestFullscreen();
            if (el.mozRequestFullScreen) return el.mozRequestFullScreen();
            if (el.msRequestFullscreen) return el.msRequestFullscreen();
            return Promise.resolve();
        }

        function exitFs() {
            if (document.exitFullscreen) return document.exitFullscreen();
            if (document.webkitExitFullscreen) return document.webkitExitFullscreen();
            if (document.mozCancelFullScreen) return document.mozCancelFullScreen();
            if (document.msExitFullscreen) return document.msExitFullscreen();
            return Promise.resolve();
        }

        async function toggleFullscreen() {
            try {
                if (!isFullscreen()) {
                    await requestFs(document.documentElement);
                } else {
                    await exitFs();
                }
            } catch (err) {
                console.error('Fullscreen error:', err);
            }
        }

        // Cập nhật trạng thái nút khi fullscreen thay đổi
        function onFsChange() {
            if (isFullscreen()) {
                btn.classList.add('is-fullscreen');
                btn.title = 'Thoát toàn màn hình (F11 hoặc bấm lại)';
            } else {
                btn.classList.remove('is-fullscreen');
                btn.title = 'Toàn màn hình (F11 hoặc nút ⛶)';
            }
        }

        document.addEventListener('fullscreenchange', onFsChange);
        document.addEventListener('webkitfullscreenchange', onFsChange);
        document.addEventListener('mozfullscreenchange', onFsChange);
        document.addEventListener('MSFullscreenChange', onFsChange);

        // Click nút: bật/tắt fullscreen
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            await toggleFullscreen();
        });

        // Chuột phải: chỉ thoát fullscreen (nếu đang full)
        btn.addEventListener('contextmenu', async (e) => {
            e.preventDefault();
            if (isFullscreen()) {
                await exitFs();
            }
        });

        // F11: chặn mặc định, dùng Fullscreen API cho đồng nhất
        document.addEventListener('keydown', async (e) => {
            if (e.key === 'F11' || e.keyCode === 122) {
                e.preventDefault();
                await toggleFullscreen();
            }
        });
    })();

    // ====== INIT ======
    (async () => {
        await populateCameras();
        updateActionButtons();

        // Init robot avatar
        const eyeL = document.querySelector(".welcome-eye.left");
        if (eyeL) {
            computeAvatarMetrics();
            new ResizeObserver(computeAvatarMetrics).observe(eyeL);
            window.addEventListener("resize", computeAvatarMetrics);
            randomBlink();
            tickAvatar();
        }

        showWelcomeEyes(true);
        clearWelcomeIdleTimer();

        // cameraの自動起動
        try {
            await startCam1();
            await startCam2();
            log("Hệ thống đang tự động khởi động camera...");
        } catch (err) {
            log("Lỗi tự động khởi động camera: " + err.message);
        }

        log("Sẵn sàng. Hệ thống quét tự động và đăng ký đã khởi động.");
    })();

})();
