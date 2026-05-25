/* qa_voice_demo.js — i18n-aware, song ngữ Việt/Nhật */
(() => {
    // Hàm tiện ích dịch — dùng I18N nếu có, fallback về key
    const t = (key) => (window.I18N ? window.I18N.t(key) : key);

    const micBtn = document.getElementById("qaMicBtn");
    const resetBtn = document.getElementById("qaResetBtn");
    const statusTextEl = document.getElementById("qaStatusText");
    const statusRowEl = document.getElementById("qaStatusRow");
    const conversationGridEl = document.getElementById("qaConversationGrid");
    const languageSwitchButtons = Array.from(document.querySelectorAll("[data-lang-value]"));
    const RecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition || null;
    const speechSynthesisApi = window.speechSynthesis || null;
    const urlParams = new URLSearchParams(window.location.search);
    const autoStartQa = urlParams.get("autostart") !== "0";

    let recognition = null;
    let recognitionActive = false;
    let listeningEnabled = false;
    let micPermissionGranted = false;
    let recognitionRestartTimer = null;
    let idleReturnTimer = null;
    let idleReturnStartedAtMs = 0;
    let currentRequestController = null;
    let currentAudio = null;
    let currentPlaybackToken = 0;
    let segmentPauseMs = 60;
    let playbackRate = 1.15;
    let audioPlaybackUnlocked = false;
    let browserTtsAvailable = Boolean(speechSynthesisApi);
    let activeUtterance = null;
    let speakingActive = false;
    let qaBusy = false;
    let pendingQuestionDraft = "";
    let pendingQuestionInterim = "";
    let stableQuestionPreview = "";
    let pendingQuestionCommitTimer = null;
    let currentAnswer = "";
    let pendingAnswerDraft = "";
    let lastResultKey = "";
    let lastResultAtMs = 0;
    let lastSubmittedQuestionKey = "";
    let lastSubmittedAtMs = 0;
    let qaSessionKey = "";
    const pendingAudioControllers = new Set();
    const audioUrlCache = new Map();
    const audioPromiseCache = new Map();
    const questionHistory = [];
    const answerHistory = [];
    const QUESTION_COMMIT_BASE_MS = 2000;
    const QUESTION_COMMIT_FAST_MS = 1500;
    const QUESTION_COMMIT_PUNCT_MS = 1200;
    const QA_IDLE_RETURN_MS = 10000;

    function appendSystemAnswer(message) {
        const normalized = String(message || "").trim();
        if (!normalized) return;
        const lastItem = String(answerHistory[answerHistory.length - 1] || "").trim();
        if (lastItem === normalized) return;
        answerHistory.push(normalized);
        renderAnswerHistory();
    }

    function setStatus(text) {
        if (statusTextEl) statusTextEl.textContent = text;
    }

    function setStatusState(state) {
        if (!statusRowEl) return;
        statusRowEl.classList.remove(
            "qa-status-idle",
            "qa-status-listening",
            "qa-status-processing",
            "qa-status-speaking",
            "qa-status-error"
        );
        statusRowEl.classList.add("qa-status-" + (state || "idle"));
    }

    // Wrapper tiện lợi: setStatus với key i18n
    function setStatusI18n(key) {
        const statusStateMap = {
            "qa.status.ready": "idle",
            "qa.status.idle": "idle",
            "qa.status.paused": "idle",
            "qa.status.listening": "listening",
            "qa.status.recording": "listening",
            "qa.status.waiting": "listening",
            "qa.status.processing": "processing",
            "qa.status.generating": "processing",
            "qa.status.speaking": "speaking",
            "qa.status.error": "error",
            "qa.status.mic.unsupported": "error",
            "qa.status.mic.denied": "error",
            "qa.status.mic.unavailable": "error",
            "qa.status.mic.error": "error",
        };
        setStatusState(statusStateMap[key] || "idle");
        setStatus(t(key));
    }

    function createQaSessionKey() {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID();
        }
        return "qa-" + Date.now() + "-" + Math.random().toString(36).slice(2, 10);
    }

    function renderQuestionHistory() {
        renderConversationGrid();
    }

    function syncStableQuestionPreview(forceClear = false) {
        const liveDraft = [pendingQuestionDraft, pendingQuestionInterim]
            .map((item) => String(item || "").trim())
            .filter(Boolean)
            .join(" ")
            .trim();
        if (liveDraft) {
            stableQuestionPreview = liveDraft;
        } else if (forceClear) {
            stableQuestionPreview = "";
        }
    }

    function renderAnswerHistory() {
        renderConversationGrid();
    }

    function buildConversationTurns() {
        const turns = [];
        const total = Math.max(questionHistory.length, answerHistory.length);
        for (let index = 0; index < total; index += 1) {
            turns.push({
                question: String(questionHistory[index] || "").trim(),
                answer: String(answerHistory[index] || "").trim(),
                isLive: false,
            });
        }

        const liveQuestion = String(stableQuestionPreview || "").trim();
        const liveAnswer = String(pendingAnswerDraft || "").trim();
        if (!liveQuestion && !liveAnswer) {
            return turns;
        }

        let liveIndex = turns.length;
        if (liveAnswer && answerHistory.length < questionHistory.length) {
            liveIndex = Math.max(0, questionHistory.length - 1);
        } else if (liveQuestion && questionHistory.length > answerHistory.length) {
            liveIndex = Math.max(0, questionHistory.length - 1);
        }
        while (turns.length <= liveIndex) {
            turns.push({ question: "", answer: "", isLive: false });
        }
        turns[liveIndex] = {
            question: liveQuestion || turns[liveIndex].question,
            answer: liveAnswer || turns[liveIndex].answer,
            isLive: true,
        };
        return turns;
    }

    function buildConversationMessages() {
        const turns = buildConversationTurns();
        const messages = [];
        turns.forEach(function (turn, index) {
            if (turn.question) {
                messages.push({
                    role: "user",
                    label: t("qa.label.user"),
                    text: turn.question,
                    isLive: turn.isLive,
                });
            }
            if (turn.answer) {
                messages.push({
                    role: "assistant",
                    label: t("qa.label.assistant"),
                    text: turn.answer,
                    isLive: turn.isLive,
                });
            }
        });
        return messages;
    }

    function createConversationMessage(message) {
        const row = document.createElement("article");
        row.className = `qa-chat-row qa-chat-row-${message.role}`;

        const bubble = document.createElement("div");
        bubble.className = `qa-chat-bubble qa-chat-bubble-${message.role}${message.isLive ? " is-live" : ""}`;

        const meta = document.createElement("div");
        meta.className = "qa-chat-meta";
        // Dịch label theo role
        const labelKey = message.role === "user" ? "qa.label.user" : "qa.label.assistant";
        meta.textContent = t(labelKey);
        bubble.appendChild(meta);

        const body = document.createElement("p");
        body.className = "qa-chat-text";
        body.textContent = String(message.text || "");
        bubble.appendChild(body);

        row.appendChild(bubble);
        return row;
    }

    function scrollConversationToLatest() {
        if (!conversationGridEl) return;
        window.requestAnimationFrame(function () {
            conversationGridEl.scrollTop = conversationGridEl.scrollHeight;
        });
    }

    function renderConversationGrid() {
        if (!conversationGridEl) return;
        const messages = buildConversationMessages();
        if (!messages.length) {
            conversationGridEl.innerHTML = `<div class="qa-conversation-empty qa-placeholder">${t("qa.empty")}</div>`;
            scrollConversationToLatest();
            return;
        }
        conversationGridEl.innerHTML = "";
        messages.forEach(function (message) {
            conversationGridEl.appendChild(createConversationMessage(message));
        });
        scrollConversationToLatest();
    }

    function updateMicButton() {
        if (!micBtn) return;
        micBtn.textContent = listeningEnabled ? t("qa.btn.stop") : t("qa.btn.start");
    }

    function refreshLanguageSensitiveUi() {
        updateMicButton();
        renderConversationGrid();
        if (!recognitionActive && !qaBusy) {
            setStatusI18n("qa.status.ready");
        }
    }

    function bindLanguageSwitcher() {
        if (!languageSwitchButtons.length || !window.I18N) return;
        if (typeof window.I18N.updateLanguageSwitchers === "function") {
            window.I18N.updateLanguageSwitchers();
        }
        languageSwitchButtons.forEach(function (button) {
            button.addEventListener("click", async function () {
                const nextLang = String(button.getAttribute("data-lang-value") || "vi").toLowerCase();
                if (nextLang === window.I18N.getLang()) return;
                button.disabled = true;
                try {
                    await window.I18N.persistLang(nextLang);
                    window.location.reload();
                } catch (error) {
                    console.warn("update kiosk language failed:", error);
                } finally {
                    button.disabled = false;
                }
            });
        });
    }

    function normalizeQuestionKey(text) {
        return String(text || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^\p{L}\p{N}\s]/gu, " ")
            .replace(/\s{2,}/g, " ")
            .trim();
    }

    function clearPendingQuestionCommitTimer() {
        if (!pendingQuestionCommitTimer) return;
        window.clearTimeout(pendingQuestionCommitTimer);
        pendingQuestionCommitTimer = null;
    }

    function clearIdleReturnTimer(resetWindow = false) {
        if (idleReturnTimer) {
            window.clearTimeout(idleReturnTimer);
            idleReturnTimer = null;
        }
        if (resetWindow) {
            idleReturnStartedAtMs = 0;
        }
    }

    function resetIdleReturnWindow() {
        clearIdleReturnTimer(true);
    }

    function shouldReturnHomeForIdleListening() {
        return (
            autoStartQa &&
            listeningEnabled &&
            document.visibilityState === "visible" &&
            !qaBusy &&
            !speakingActive &&
            !String(pendingQuestionDraft || "").trim() &&
            !String(pendingQuestionInterim || "").trim()
        );
    }

    function scheduleIdleReturnHome() {
        clearIdleReturnTimer();
        if (!shouldReturnHomeForIdleListening()) {
            idleReturnStartedAtMs = 0;
            return;
        }
        if (!idleReturnStartedAtMs) {
            idleReturnStartedAtMs = Date.now();
        }
        const elapsedMs = Date.now() - idleReturnStartedAtMs;
        const remainingMs = QA_IDLE_RETURN_MS - elapsedMs;
        if (remainingMs <= 0) {
            window.location.href = "/";
            return;
        }
        idleReturnTimer = window.setTimeout(function () {
            idleReturnTimer = null;
            if (shouldReturnHomeForIdleListening()) {
                window.location.href = "/";
            }
        }, remainingMs);
    }

    function stopSpeaking() {
        currentPlaybackToken += 1;
        speakingActive = false;
        if (speechSynthesisApi) {
            try {
                speechSynthesisApi.cancel();
            } catch (error) {
                console.warn("cancel browser speech failed:", error);
            }
        }
        activeUtterance = null;
        if (currentAudio) {
            try {
                currentAudio.pause();
            } catch (error) {
                console.warn("pause qa audio failed:", error);
            }
            currentAudio = null;
        }
        pendingAudioControllers.forEach(function (controller) {
            try {
                controller.abort();
            } catch (error) {
                console.warn("abort qa audio request failed:", error);
            }
        });
        pendingAudioControllers.clear();
        audioPromiseCache.clear();
    }

    function pickBrowserVoice() {
        if (!speechSynthesisApi || typeof window.SpeechSynthesisUtterance !== "function") {
            return null;
        }
        const voices = speechSynthesisApi.getVoices() || [];
        if (!voices.length) {
            return null;
        }
        return (
            voices.find(function (voice) { return /^vi[-_]/i.test(String(voice.lang || "")); }) ||
            voices.find(function (voice) { return /Vietnam/i.test(String(voice.name || "")); }) ||
            voices[0]
        );
    }

    function speakSegmentWithBrowserTts(text, token) {
        return new Promise(function (resolve) {
            if (!browserTtsAvailable || !speechSynthesisApi || typeof window.SpeechSynthesisUtterance !== "function") {
                resolve(false);
                return;
            }
            const normalized = String(text || "").trim();
            if (!normalized) {
                resolve(true);
                return;
            }
            try {
                const utterance = new window.SpeechSynthesisUtterance(normalized);
                const voice = pickBrowserVoice();
                if (voice) {
                    utterance.voice = voice;
                    utterance.lang = voice.lang || "vi-VN";
                } else {
                    utterance.lang = "vi-VN";
                }
                utterance.rate = Math.min(2, Math.max(0.5, playbackRate));
                utterance.onend = function () {
                    if (currentPlaybackToken === token) {
                        activeUtterance = null;
                    }
                    resolve(true);
                };
                utterance.onerror = function (event) {
                    console.warn("browser speech failed:", event);
                    browserTtsAvailable = false;
                    if (currentPlaybackToken === token) {
                        activeUtterance = null;
                    }
                    resolve(false);
                };
                activeUtterance = utterance;
                speechSynthesisApi.speak(utterance);
            } catch (error) {
                console.warn("browser speech init failed:", error);
                browserTtsAvailable = false;
                resolve(false);
            }
        });
    }

    function resetPendingQuestionDraft() {
        pendingQuestionDraft = "";
        pendingQuestionInterim = "";
        clearPendingQuestionCommitTimer();
        syncStableQuestionPreview(true);
        renderQuestionHistory();
    }

    function clearAudioCache() {
        audioUrlCache.forEach(function (url) {
            try {
                URL.revokeObjectURL(url);
            } catch (error) {
                console.warn("revoke audio url failed:", error);
            }
        });
        audioUrlCache.clear();
    }

    async function unlockAudioPlayback() {
        if (audioPlaybackUnlocked) return true;
        try {
            const audio = new Audio(
                "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="
            );
            audio.volume = 0;
            await audio.play();
            audio.pause();
            audio.currentTime = 0;
            audioPlaybackUnlocked = true;
            return true;
        } catch (error) {
            console.warn("unlockAudioPlayback failed:", error);
            return false;
        }
    }

    function splitAnswerIntoSegments(text) {
        const normalized = String(text || "")
            .replace(/\s*;\s*/g, ". ")
            .replace(/\s*:\s*/g, ". ")
            .replace(/\s*\/\s*/g, ". ")
            .replace(/\s*-\s*/g, ", ")
            .replace(/\s{2,}/g, " ")
            .trim();
        if (!normalized) return [];
        const rawParts = normalized
            .split(/(?<=[.!?])\s+/)
            .map(function (part) { return String(part || "").trim(); })
            .filter(Boolean);
        const parts = [];
        rawParts.forEach(function (part) {
            if (part.length <= 140) {
                parts.push(part);
                return;
            }
            part.split(/,\s+/).forEach(function (subPart) {
                const trimmed = String(subPart || "").trim();
                if (trimmed) parts.push(trimmed);
            });
        });
        return parts.length ? parts : [normalized];
    }

    async function fetchServerAudioForText(text, forceRefresh) {
        const normalized = String(text || "").trim();
        if (!normalized) return null;
        if (!forceRefresh && audioUrlCache.has(normalized)) {
            return audioUrlCache.get(normalized);
        }
        if (!forceRefresh && audioPromiseCache.has(normalized)) {
            return audioPromiseCache.get(normalized);
        }
        const controller = new AbortController();
        pendingAudioControllers.add(controller);
        const promise = (async function () {
            const res = await fetch("/api/qa/tts", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: normalized }),
                signal: controller.signal,
            });
            if (!res.ok) {
                throw new Error(t("qa.error.voice"));
            }
            const blob = await res.blob();
            const audioUrl = URL.createObjectURL(blob);
            audioUrlCache.set(normalized, audioUrl);
            return audioUrl;
        })();
        audioPromiseCache.set(normalized, promise);

        try {
            return await promise;
        } catch (error) {
            if (error && error.name === "AbortError") return null;
            console.error("fetchServerAudioForText error:", error);
            return null;
        } finally {
            audioPromiseCache.delete(normalized);
            pendingAudioControllers.delete(controller);
        }
    }

    function waitForAudioEnded(audio, token) {
        return new Promise(function (resolve) {
            if (!audio) {
                resolve();
                return;
            }
            const finish = function () {
                if (currentPlaybackToken === token) {
                    currentAudio = null;
                }
                resolve();
            };
            audio.addEventListener("ended", finish, { once: true });
            audio.addEventListener("error", finish, { once: true });
        });
    }

    function waitMs(ms) {
        return new Promise(function (resolve) {
            window.setTimeout(resolve, Math.max(0, Number(ms) || 0));
        });
    }

    async function playAnswerSegments(forceRefresh) {
        if (!currentAnswer) return;
        resetIdleReturnWindow();
        stopSpeaking();
        speakingActive = true;
        const playbackToken = currentPlaybackToken;
        const segments = splitAnswerIntoSegments(currentAnswer);
        if (!segments.length) {
            speakingActive = false;
            return;
        }
        clearRecognitionRestartTimer();
        if (recognitionActive && recognition) {
            try {
                recognition.stop();
            } catch (error) {
                console.warn("pause recognition for playback failed:", error);
            }
        }
        await unlockAudioPlayback();

        segments.forEach(function (segment) {
            fetchServerAudioForText(segment, forceRefresh);
        });

        for (const segment of segments) {
            if (playbackToken !== currentPlaybackToken) return;
            const audioUrl = await fetchServerAudioForText(segment, forceRefresh);
            if (playbackToken !== currentPlaybackToken) return;
            try {
                if (audioUrl) {
                    currentAudio = new Audio(audioUrl);
                    currentAudio.preload = "auto";
                    currentAudio.playbackRate = playbackRate;
                    currentAudio.defaultPlaybackRate = playbackRate;
                    currentAudio.preservesPitch = false;
                    await currentAudio.play();
                    await waitForAudioEnded(currentAudio, playbackToken);
                } else {
                    const spoken = await speakSegmentWithBrowserTts(segment, playbackToken);
                    if (!spoken) {
                        return;
                    }
                }
                if (segmentPauseMs > 0) {
                    await waitMs(segmentPauseMs);
                }
            } catch (error) {
                console.error("playAnswerSegments error:", error);
                return;
            }
        }
        if (playbackToken === currentPlaybackToken) {
            speakingActive = false;
            scheduleIdleReturnHome();
        }
    }

    async function autoSpeakAnswer() {
        await playAnswerSegments(false);
    }

    function clearRecognitionRestartTimer() {
        if (!recognitionRestartTimer) return;
        window.clearTimeout(recognitionRestartTimer);
        recognitionRestartTimer = null;
    }

    async function listAudioInputs() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
            return [];
        }
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices.filter(function (device) {
                return device && device.kind === "audioinput";
            });
        } catch (error) {
            console.warn("enumerateDevices failed:", error);
            return [];
        }
    }

    function getQuestionCommitDelayMs() {
        const draft = [pendingQuestionDraft, pendingQuestionInterim]
            .map((item) => String(item || "").trim())
            .filter(Boolean)
            .join(" ")
            .trim();
        if (!draft) return QUESTION_COMMIT_BASE_MS;
        if (/[.!?]\s*$/.test(draft)) {
            return QUESTION_COMMIT_PUNCT_MS;
        }
        const wordCount = draft.split(/\s+/).filter(Boolean).length;
        if (wordCount >= 8 && !pendingQuestionInterim) {
            return QUESTION_COMMIT_FAST_MS;
        }
        return QUESTION_COMMIT_BASE_MS;
    }

    async function resolveMicAccessState() {
        if (!RecognitionCtor) {
            return { state: "unsupported", message: t("qa.mic.denied.msg") };
        }
        if (navigator.permissions && navigator.permissions.query) {
            try {
                const permission = await navigator.permissions.query({ name: "microphone" });
                if (permission && permission.state === "denied") {
                    return { state: "denied", message: t("qa.mic.denied.msg") };
                }
            } catch (error) {
                console.warn("permissions.query(microphone) failed:", error);
            }
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            return { state: "granted", message: "" };
        }
        const audioInputs = await listAudioInputs();
        if (audioInputs.length === 0) {
            return { state: "unavailable", message: t("qa.mic.unavailable.msg") };
        }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(function (track) { track.stop(); });
            return { state: "granted", message: "" };
        } catch (error) {
            console.error("resolveMicAccessState getUserMedia failed:", error);
            const errorName = String(error && error.name || "");
            if (errorName === "NotAllowedError" || errorName === "SecurityError" || errorName === "PermissionDeniedError") {
                return { state: "denied", message: t("qa.mic.denied.msg") };
            }
            if (errorName === "NotFoundError" || errorName === "DevicesNotFoundError") {
                return { state: "unavailable", message: t("qa.mic.unavailable.msg") };
            }
            if (errorName === "NotReadableError" || errorName === "TrackStartError" || errorName === "AbortError" || errorName === "OverconstrainedError") {
                return { state: "proceed", message: "" };
            }
            return { state: "proceed", message: "" };
        }
    }

    function applyMicAccessState(stateInfo) {
        const state = String((stateInfo && stateInfo.state) || "unknown");
        const message = String((stateInfo && stateInfo.message) || "").trim();
        if (state === "granted" || state === "proceed") {
            micPermissionGranted = true;
            return true;
        }
        micPermissionGranted = false;
        listeningEnabled = false;
        updateMicButton();
        if (state === "unsupported") {
            setStatusI18n("qa.status.mic.unsupported");
        } else if (state === "denied") {
            setStatusI18n("qa.status.mic.denied");
        } else if (state === "unavailable") {
            setStatusI18n("qa.status.mic.unavailable");
        } else {
            setStatusI18n("qa.status.mic.error");
        }
        if (message) appendSystemAnswer(message);
        return false;
    }

    function scheduleRecognitionRestart(delayMs = 250) {
        if (!listeningEnabled || qaBusy || speakingActive) return;
        clearRecognitionRestartTimer();
        recognitionRestartTimer = window.setTimeout(function () {
            recognitionRestartTimer = null;
            startRecognition();
        }, Math.max(120, Number(delayMs) || 0));
    }

    async function ensureMicPermission() {
        if (micPermissionGranted) return true;
        const stateInfo = await resolveMicAccessState();
        return applyMicAccessState(stateInfo);
    }

    async function primeMicPermissionOnLoad() {
        const stateInfo = await resolveMicAccessState();
        const accessOk = applyMicAccessState(stateInfo);
        if (accessOk) {
            setStatusI18n("qa.status.ready");
        }
    }

    async function askQuestion(question) {
        resetIdleReturnWindow();
        const normalized = String(question || "").trim();
        if (!normalized) {
            if (listeningEnabled) {
                setStatusI18n("qa.status.idle");
                scheduleRecognitionRestart(180);
                scheduleIdleReturnHome();
            }
            return;
        }
        const nowMs = Date.now();
        const normalizedKey = normalizeQuestionKey(normalized);
        if (
            normalizedKey &&
            normalizedKey === lastSubmittedQuestionKey &&
            (nowMs - lastSubmittedAtMs) < 8000
        ) {
            resetPendingQuestionDraft();
            setStatus(listeningEnabled ? t("qa.status.idle") : t("qa.status.paused"));
            if (listeningEnabled && !recognitionActive && !speakingActive) {
                scheduleRecognitionRestart(260);
                scheduleIdleReturnHome();
            }
            return;
        }
        lastSubmittedQuestionKey = normalizedKey;
        lastSubmittedAtMs = nowMs;

        qaBusy = true;
        resetPendingQuestionDraft();
        clearRecognitionRestartTimer();
        if (recognitionActive && recognition) {
            try {
                recognition.stop();
            } catch (error) {
                console.warn("stop recognition before ask failed:", error);
            }
        }
        currentRequestController = new AbortController();
        currentAnswer = "";
        pendingAnswerDraft = "";
        questionHistory.push(normalized);
        renderQuestionHistory();
        renderAnswerHistory();
        setStatusI18n("qa.status.generating");

        try {
            const res = await fetch("/api/qa/ask-stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: normalized,
                    language: window.I18N ? window.I18N.getLang() : "vi",
                    channel: "qa_demo",
                    session_key: qaSessionKey,
                }),
                signal: currentRequestController.signal,
            });
            if (!res.ok || !res.body) {
                throw new Error(t("qa.error.no.answer"));
            }
            const reader = res.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";
            let doneItem = null;

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";
                for (const line of lines) {
                    const trimmed = String(line || "").trim();
                    if (!trimmed) continue;
                    let event;
                    try {
                        event = JSON.parse(trimmed);
                    } catch (parseError) {
                        console.warn("qa stream parse failed:", parseError, trimmed);
                        continue;
                    }
                    if (event.type === "answer_delta") {
                        pendingAnswerDraft = `${pendingAnswerDraft}${String(event.text || "")}`;
                        renderAnswerHistory();
                        setStatusI18n("qa.status.generating");
                        continue;
                    }
                    if (event.type === "replace_answer") {
                        pendingAnswerDraft = String(event.text || "").trim();
                        renderAnswerHistory();
                        setStatusI18n("qa.status.generating");
                        continue;
                    }
                    if (event.type === "done" && event.item) {
                        doneItem = event.item;
                    } else if (event.type === "error") {
                        throw new Error(String(event.error || t("qa.error.no.answer")));
                    }
                }
            }
            if (!doneItem) {
                throw new Error(t("qa.error.stream.end"));
            }
            currentAnswer = String(doneItem.answer || "").trim() || t("qa.fallback");
            pendingAnswerDraft = "";
            clearAudioCache();
            answerHistory.push(currentAnswer);
            renderAnswerHistory();
            setStatusI18n("qa.status.speaking");
            try {
                await autoSpeakAnswer();
            } catch (playbackError) {
                console.error("autoSpeakAnswer failed:", playbackError);
            }
            setStatus(listeningEnabled ? t("qa.status.idle") : t("qa.status.paused"));
        } catch (error) {
            if (error && error.name === "AbortError") return;
            currentAnswer = t("qa.fallback");
            pendingAnswerDraft = "";
            clearAudioCache();
            answerHistory.push(currentAnswer);
            renderAnswerHistory();
            setStatusI18n("qa.status.speaking");
            try {
                await autoSpeakAnswer();
            } catch (playbackError) {
                console.error("autoSpeakAnswer failed after fallback:", playbackError);
            }
            setStatusI18n("qa.status.error");
            console.error("askQuestion error:", error);
        } finally {
            currentRequestController = null;
            qaBusy = false;
            if (listeningEnabled && !recognitionActive && !speakingActive) {
                scheduleRecognitionRestart(260);
                scheduleIdleReturnHome();
            }
        }
    }

    function schedulePendingQuestionCommit() {
        if (!listeningEnabled || qaBusy || speakingActive) return;
        clearPendingQuestionCommitTimer();
        pendingQuestionCommitTimer = window.setTimeout(function () {
            pendingQuestionCommitTimer = null;
            pendingQuestionInterim = "";
            syncStableQuestionPreview();
            renderQuestionHistory();
            const transcript = String(pendingQuestionDraft || "").trim();
            if (!transcript || qaBusy || speakingActive) return;
            askQuestion(transcript);
        }, getQuestionCommitDelayMs());
    }

    function ensureRecognition() {
        if (!RecognitionCtor) return null;
        if (recognition) return recognition;
        recognition = new RecognitionCtor();
        recognition.lang = window.I18N ? (window.I18N.getLang() === "ja" ? "ja-JP" : "vi-VN") : "vi-VN";
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        recognition.addEventListener("start", () => {
            clearRecognitionRestartTimer();
            recognitionActive = true;
            if (speakingActive) {
                setStatusI18n("qa.status.speaking");
                return;
            }
            if (qaBusy) {
                setStatusI18n("qa.status.processing");
                return;
            }
            if (pendingQuestionDraft) {
                setStatus(pendingQuestionInterim ? t("qa.status.recording") : t("qa.status.waiting"));
                return;
            }
            setStatusI18n("qa.status.listening");
            scheduleIdleReturnHome();
        });

        recognition.addEventListener("end", () => {
            recognitionActive = false;
            if (speakingActive) {
                setStatusI18n("qa.status.speaking");
                return;
            }
            if (qaBusy) {
                setStatusI18n("qa.status.processing");
                return;
            }
            if (pendingQuestionDraft) {
                setStatus(pendingQuestionInterim ? t("qa.status.recording") : t("qa.status.waiting"));
                if (listeningEnabled && document.visibilityState === "visible") {
                    scheduleRecognitionRestart(150);
                }
                return;
            }
            if (listeningEnabled && document.visibilityState === "visible") {
                setStatusI18n("qa.status.idle");
                scheduleRecognitionRestart(220);
                scheduleIdleReturnHome();
                return;
            }
            setStatus(listeningEnabled ? t("qa.status.idle") : t("qa.status.paused"));
        });

        recognition.addEventListener("result", (event) => {
            if (speakingActive || qaBusy) return;
            let finalTranscript = "";
            let interimTranscript = "";
            const startIndex = Number(event.resultIndex || 0);
            for (let i = startIndex; i < event.results.length; i += 1) {
                const result = event.results[i];
                if (!result || !result[0]) continue;
                const text = String(result[0].transcript || "").trim();
                if (!text) continue;
                if (result.isFinal) {
                    finalTranscript += `${text} `;
                } else {
                    interimTranscript += `${text} `;
                }
            }
            finalTranscript = finalTranscript.trim();
            interimTranscript = interimTranscript.trim();
            if (finalTranscript || interimTranscript) {
                resetIdleReturnWindow();
            }

            if (finalTranscript) {
                const nowMs = Date.now();
                const transcriptKey = normalizeQuestionKey(finalTranscript);
                const draftKey = normalizeQuestionKey(pendingQuestionDraft);
                if (
                    transcriptKey &&
                    (
                        (transcriptKey === draftKey) ||
                        (transcriptKey === lastResultKey && (nowMs - lastResultAtMs) < 5000)
                    )
                ) {
                    pendingQuestionInterim = interimTranscript;
                    syncStableQuestionPreview();
                    renderQuestionHistory();
                    setStatus(interimTranscript ? t("qa.status.recording") : t("qa.status.waiting"));
                    schedulePendingQuestionCommit();
                    return;
                }
                lastResultKey = transcriptKey;
                lastResultAtMs = nowMs;
                pendingQuestionDraft = pendingQuestionDraft
                    ? `${pendingQuestionDraft} ${finalTranscript}`.trim()
                    : finalTranscript;
            }
            pendingQuestionInterim = interimTranscript;
            syncStableQuestionPreview();
            renderQuestionHistory();
            setStatus((pendingQuestionDraft || pendingQuestionInterim) ? t("qa.status.recording") : t("qa.status.listening"));
            schedulePendingQuestionCommit();
            if (!pendingQuestionDraft && !pendingQuestionInterim) {
                scheduleIdleReturnHome();
            }
        });

        recognition.addEventListener("error", async (event) => {
            recognitionActive = false;
            if (event && (event.error === "no-speech" || event.error === "aborted")) {
                if (listeningEnabled && document.visibilityState === "visible" && !speakingActive && !qaBusy) {
                    if (pendingQuestionDraft) {
                        setStatus(pendingQuestionInterim ? t("qa.status.recording") : t("qa.status.waiting"));
                        scheduleRecognitionRestart(150);
                        return;
                    }
                    setStatusI18n("qa.status.idle");
                    scheduleRecognitionRestart(220);
                    scheduleIdleReturnHome();
                }
                return;
            }
            if (event && (event.error === "not-allowed" || event.error === "service-not-allowed")) {
                const stateInfo = await resolveMicAccessState();
                if (stateInfo.state === "granted") {
                    setStatusI18n("qa.status.error");
                    appendSystemAnswer(t("qa.mic.denied.msg"));
                    listeningEnabled = false;
                    updateMicButton();
                    return;
                }
                applyMicAccessState(stateInfo);
                return;
            }
            if (event && event.error === "audio-capture") {
                setStatusI18n("qa.status.mic.unavailable");
                appendSystemAnswer(t("qa.mic.unavailable.msg"));
                listeningEnabled = false;
                updateMicButton();
                return;
            }
            setStatusI18n("qa.status.mic.error");
            appendSystemAnswer(t("qa.mic.denied.msg"));
            console.error("speech recognition error:", event);
        });

        return recognition;
    }

    async function startRecognition() {
        if (speakingActive || qaBusy) return;
        const permissionOk = await ensureMicPermission();
        if (!permissionOk) {
            listeningEnabled = false;
            updateMicButton();
            return;
        }
        unlockAudioPlayback();
        const instance = ensureRecognition();
        if (!instance) {
            setStatusI18n("qa.status.mic.unsupported");
            appendSystemAnswer(t("qa.mic.denied.msg"));
            listeningEnabled = false;
            updateMicButton();
            return;
        }
        try {
            instance.start();
        } catch (error) {
            console.warn("recognition start failed:", error);
            scheduleRecognitionRestart(500);
        }
    }

    function pauseListening() {
        listeningEnabled = false;
        resetIdleReturnWindow();
        clearRecognitionRestartTimer();
        clearPendingQuestionCommitTimer();
        if (recognitionActive && recognition) {
            try {
                recognition.stop();
            } catch (error) {
                console.warn("pause recognition failed:", error);
            }
        }
        updateMicButton();
        setStatusI18n("qa.status.paused");
    }

    function resumeListening() {
        listeningEnabled = true;
        updateMicButton();
        setStatus(pendingQuestionDraft ? t("qa.status.waiting") : t("qa.status.idle"));
        startRecognition();
        scheduleIdleReturnHome();
    }

    function resetQaDemo() {
        listeningEnabled = false;
        resetIdleReturnWindow();
        clearRecognitionRestartTimer();
        resetPendingQuestionDraft();
        if (recognitionActive && recognition) {
            try {
                recognition.stop();
            } catch (error) {
                console.warn("reset recognition failed:", error);
            }
        }
        if (currentRequestController) {
            currentRequestController.abort();
            currentRequestController = null;
        }
        stopSpeaking();
        clearAudioCache();
        currentAnswer = "";
        pendingAnswerDraft = "";
        qaBusy = false;
        lastResultKey = "";
        lastResultAtMs = 0;
        lastSubmittedQuestionKey = "";
        lastSubmittedAtMs = 0;
        questionHistory.length = 0;
        answerHistory.length = 0;
        qaSessionKey = createQaSessionKey();
        renderQuestionHistory();
        renderAnswerHistory();
        updateMicButton();
        setStatusI18n("qa.status.ready");
    }

    if (micBtn) {
        micBtn.addEventListener("click", () => {
            if (listeningEnabled) {
                pauseListening();
                return;
            }
            resumeListening();
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener("click", resetQaDemo);
    }

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            if (listeningEnabled && !recognitionActive) {
                scheduleRecognitionRestart(220);
                scheduleIdleReturnHome();
            }
            return;
        }
        resetIdleReturnWindow();
        clearRecognitionRestartTimer();
        if (recognitionActive && recognition) {
            try {
                recognition.stop();
            } catch (error) {
                console.warn("recognition stop on hidden failed:", error);
            }
        }
    });

    fetch("/api/qa/tts-status")
        .then(function (res) { return res.json(); })
        .then(function (js) {
            if (!js || !js.ok || !js.item) return;
            segmentPauseMs = Number(js.item.segment_pause_ms || 60);
            playbackRate = Math.max(0.5, Number(js.item.playback_rate || 1.15) || 1.15);
        })
        .catch(function (error) {
            console.warn("load qa tts status failed:", error);
        });

    // Fetch ngôn ngữ từ server, apply i18n, rồi cập nhật recognition lang
    (async function initLang() {
        if (window.I18N) {
            await window.I18N.fetchAndApply();
            if (typeof window.I18N.updateLanguageSwitchers === "function") {
                window.I18N.updateLanguageSwitchers();
            }
            // Cập nhật recognition lang nếu đã tạo
            if (recognition) {
                recognition.lang = window.I18N.getLang() === "ja" ? "ja-JP" : "vi-VN";
            }
        }
        await primeMicPermissionOnLoad();
        if (autoStartQa) {
            resumeListening();
        }
    })();

    window.addEventListener("i18n:languagechange", refreshLanguageSensitiveUi);
    bindLanguageSwitcher();
    updateMicButton();
    qaSessionKey = createQaSessionKey();
    renderQuestionHistory();
    renderAnswerHistory();
})();
