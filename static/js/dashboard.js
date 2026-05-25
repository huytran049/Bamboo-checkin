window.addEventListener("load", function () {
  const loader = document.getElementById("loader");
  if (!loader) return;
  setTimeout(function () {
    loader.classList.add("fadeOut");
  }, 300);
});

// Helper function for i18n
function t(key, replacements) {
  if (!window.I18N) return key;
  let text = window.I18N.t(key);
  if (replacements) {
    Object.keys(replacements).forEach(k => {
      text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), replacements[k]);
    });
  }
  return text;
}

window.addEventListener("DOMContentLoaded", function () {
  const BREAKPOINT = 1280;
  const body = document.body;
  const toggleButtons = document.querySelectorAll(".sidebar-toggle");
  const screenLinks = document.querySelectorAll("[data-screen-target]");
  const screens = document.querySelectorAll("[data-screen]");

  const globalSearchInput = document.getElementById("globalSearchInput");
  const tableSearchInput = document.getElementById("tableSearchInput");
  const databaseTableBody = document.getElementById("databaseTableBody");
  const databaseEmptyRow = document.getElementById("databaseEmptyRow");
  const recentActivityBody = document.getElementById("recentActivityBody");
  const recentEmptyRow = document.getElementById("recentEmptyRow");
  const exportExcelBtn = document.getElementById("exportExcelBtn");
  const exportJsonlBtn = document.getElementById("exportJsonlBtn");
  const bulkDeleteBtn = document.getElementById("bulkDeleteBtn");
  const databaseSelectAll = document.getElementById("databaseSelectAll");
  const notifCounter = document.getElementById("notifCounter");
  const notificationList = document.getElementById("notificationList");
  const notificationEmpty = document.getElementById("notificationEmpty");
  const notificationMeta = document.getElementById("notificationMeta");
  const logoutBtn = document.getElementById("logoutBtn");
  const editModal = document.getElementById("editModal");
  const confirmModal = document.getElementById("confirmModal");
  const exportModal = document.getElementById("exportModal");
  const editFullName = document.getElementById("editFullName");
  const editCompany = document.getElementById("editCompany");
  const editEmail = document.getElementById("editEmail");
  const editPhone = document.getElementById("editPhone");
  const editTitle = document.getElementById("editTitle");
  const editConfirmBtn = document.getElementById("editConfirmBtn");
  const editCancelBtn = document.getElementById("editCancelBtn");
  const editCloseBtn = document.getElementById("editCloseBtn");
  const exportConfirmBtn = document.getElementById("exportConfirmBtn");
  const exportCancelBtn = document.getElementById("exportCancelBtn");
  const exportCloseBtn = document.getElementById("exportCloseBtn");
  const exportDateFrom = document.getElementById("exportDateFrom");
  const exportDateTo = document.getElementById("exportDateTo");
  const confirmYesBtn = document.getElementById("confirmYesBtn");
  const confirmNoBtn = document.getElementById("confirmNoBtn");
  const confirmModalMessage = document.getElementById("confirmModalMessage");

  const statTotal = document.getElementById("statTotal");
  const statToday = document.getElementById("statToday");
  const statWithEmail = document.getElementById("statWithEmail");
  const statWithPhone = document.getElementById("statWithPhone");
  const recentPrevBtn = document.getElementById("recentPrevBtn");
  const recentNextBtn = document.getElementById("recentNextBtn");
  const recentPageInfo = document.getElementById("recentPageInfo");
  const databasePrevBtn = document.getElementById("databasePrevBtn");
  const databaseNextBtn = document.getElementById("databaseNextBtn");
  const databasePageInfo = document.getElementById("databasePageInfo");
  const databaseMissingOnlyToggle = document.getElementById("databaseMissingOnlyToggle");
  const cccdTableBody = document.getElementById("cccdTableBody");
  const cccdEmptyRow = document.getElementById("cccdEmptyRow");
  const cccdExportExcelBtn = document.getElementById("cccdExportExcelBtn");
  const cccdExportJsonBtn = document.getElementById("cccdExportJsonBtn");
  const cccdBulkDeleteBtn = document.getElementById("cccdBulkDeleteBtn");
  const cccdSelectAll = document.getElementById("cccdSelectAll");
  const cccdPrevBtn = document.getElementById("cccdPrevBtn");
  const cccdNextBtn = document.getElementById("cccdNextBtn");
  const cccdPageInfo = document.getElementById("cccdPageInfo");
  const cccdStatTotal = document.getElementById("cccdStatTotal");
  const cccdStatToday = document.getElementById("cccdStatToday");
  const cccdEditModal = document.getElementById("cccdEditModal");
  const cccdEditFullName = document.getElementById("cccdEditFullName");
  const cccdEditIdNumber = document.getElementById("cccdEditIdNumber");
  const cccdEditGender = document.getElementById("cccdEditGender");
  const cccdEditDob = document.getElementById("cccdEditDob");
  const cccdEditAddress = document.getElementById("cccdEditAddress");
  const cccdEditIssued = document.getElementById("cccdEditIssued");
  const cccdEditExpiry = document.getElementById("cccdEditExpiry");
  const cccdEditOldId = document.getElementById("cccdEditOldId");
  const cccdEditConfirmBtn = document.getElementById("cccdEditConfirmBtn");
  const cccdEditCancelBtn = document.getElementById("cccdEditCancelBtn");
  const cccdEditCloseBtn = document.getElementById("cccdEditCloseBtn");
  const settingsStatusMessage = document.getElementById("settingsStatusMessage");
  const qrPrintEnabledToggle = document.getElementById("qrPrintEnabledToggle");
  const faceRecognitionToggle = document.getElementById("faceRecognitionToggle");
  const appointmentOverlayToggle = document.getElementById("appointmentOverlayToggle");
  const languageSwitchButtons = Array.from(document.querySelectorAll("[data-lang-value]"));
  const qrPrintEnvValue = document.getElementById("qrPrintEnvValue");
  const faceRecognitionEnvValue = document.getElementById("faceRecognitionEnvValue");
  const appointmentOverlayEnvValue = document.getElementById("appointmentOverlayEnvValue");
  const appointmentPrevMonthBtn = document.getElementById("appointmentPrevMonthBtn");
  const appointmentTodayBtn = document.getElementById("appointmentTodayBtn");
  const appointmentNextMonthBtn = document.getElementById("appointmentNextMonthBtn");
  const appointmentsCalendarGrid = document.getElementById("appointmentsCalendarGrid");
  const appointmentMonthLabel = document.getElementById("appointmentMonthLabel");
  const appointmentMonthMeta = document.getElementById("appointmentMonthMeta");
  const appointmentSelectedDateLabel = document.getElementById("appointmentSelectedDateLabel");
  const appointmentStatusMessage = document.getElementById("appointmentStatusMessage");
  const appointmentEmptyState = document.getElementById("appointmentEmptyState");
  const appointmentDayList = document.getElementById("appointmentDayList");
  const appointmentFilterModal = document.getElementById("appointmentFilterModal");
  const appointmentFilterCloseBtn = document.getElementById("appointmentFilterCloseBtn");
  const appointmentFilterMonthHint = document.getElementById("appointmentFilterMonthHint");
  const appointmentFilterList = document.getElementById("appointmentFilterList");
  const appointmentStatusFilter = document.getElementById("appointmentStatusFilter");
  const appointmentAssigneeFilter = document.getElementById("appointmentAssigneeFilter");
  const appointmentFilterApplyBtn = document.getElementById("appointmentFilterApplyBtn");
  const appointmentFilterModalSubmitBtn = document.getElementById("appointmentFilterModalSubmitBtn");
  const appointmentDetailModal = document.getElementById("appointmentDetailModal");
  const appointmentDetailCloseBtn = document.getElementById("appointmentDetailCloseBtn");
  const appointmentDetailDismissBtn = document.getElementById("appointmentDetailDismissBtn");
  const appointmentDetailDate = document.getElementById("appointmentDetailDate");
  const appointmentDetailTime = document.getElementById("appointmentDetailTime");
  const appointmentDetailContact = document.getElementById("appointmentDetailContact");
  const appointmentDetailStatus = document.getElementById("appointmentDetailStatus");
  const appointmentDetailAssignee = document.getElementById("appointmentDetailAssignee");
  const appointmentDetailReason = document.getElementById("appointmentDetailReason");
  const appointmentDetailDescription = document.getElementById("appointmentDetailDescription");
  const appointmentEditModal = document.getElementById("appointmentEditModal");
  const appointmentEditDate = document.getElementById("appointmentEditDate");
  const appointmentEditDateShell = document.getElementById("appointmentEditDateShell");
  const appointmentEditDateError = document.getElementById("appointmentEditDateError");
  const appointmentEditStart = document.getElementById("appointmentEditStart");
  const appointmentEditStartShell = document.getElementById("appointmentEditStartShell");
  const appointmentEditStartError = document.getElementById("appointmentEditStartError");
  const appointmentEditStartHour = document.getElementById("appointmentEditStartHour");
  const appointmentEditStartMinute = document.getElementById("appointmentEditStartMinute");
  const appointmentEditEnd = document.getElementById("appointmentEditEnd");
  const appointmentEditEndShell = document.getElementById("appointmentEditEndShell");
  const appointmentEditEndError = document.getElementById("appointmentEditEndError");
  const appointmentEditEndHour = document.getElementById("appointmentEditEndHour");
  const appointmentEditEndMinute = document.getElementById("appointmentEditEndMinute");
  const appointmentEditContact = document.getElementById("appointmentEditContact");
  const appointmentEditPurpose = document.getElementById("appointmentEditPurpose");
  const appointmentEditDescription = document.getElementById("appointmentEditDescription");
  const appointmentEditAssignee = document.getElementById("appointmentEditAssignee");
  const appointmentEditStatus = document.getElementById("appointmentEditStatus");
  const appointmentEditConfirmBtn = document.getElementById("appointmentEditConfirmBtn");
  const appointmentEditCancelBtn = document.getElementById("appointmentEditCancelBtn");
  const appointmentEditCloseBtn = document.getElementById("appointmentEditCloseBtn");
  const qaHistoryCountLabel = document.getElementById("qaHistoryCountLabel");
  const qaHistoryStatusMessage = document.getElementById("qaHistoryStatusMessage");
  const qaHistoryEmptyState = document.getElementById("qaHistoryEmptyState");
  const qaHistoryList = document.getElementById("qaHistoryList");
  const qaDetailDot = document.getElementById("qaDetailDot");
  const qaDetailTitle = document.getElementById("qaDetailTitle");
  const qaDetailMeta = document.getElementById("qaDetailMeta");
  const qaDetailQuestion = document.getElementById("qaDetailQuestion");
  const qaDetailAnswer = document.getElementById("qaDetailAnswer");
  const qaDetailSources = document.getElementById("qaDetailSources");
  const qaHistoryDeleteAllBtn = document.getElementById("qaHistoryDeleteAllBtn");
  const qaDetailDeleteBtn = document.getElementById("qaDetailDeleteBtn");

  let manualOverride = false;
  let syncingSearch = false;
  let selectedRegistrationId = null;
  let currentSearchKeyword = "";
  let imageLightboxEl = null;
  let imageLightboxTargetEl = null;
  let currentEditItem = null;
  let currentCccdEditItem = null;
  let confirmCallback = null;
  let confirmCancelCallback = null;
  let showMissingOnly = false;
  let currentExportFormat = "xlsx";
  let activeScreen = "database";
  const selectedRegistrationIds = new Set();
  const selectedCccdIds = new Set();
  const LIGHTBOX_ZOOM_SCALE = {
    face: 1,
    bcard: 1,
    cccd: 1,
    default: 1,
  };
  const PAGE_SIZE = 10;
  const MAX_NOTIFICATION_ROWS = 5;
  const databasePagination = { page: 1, totalPages: 1, total: 0 };
  const cccdPagination = { page: 1, totalPages: 1, total: 0 };
  const recentPagination = { page: 1, totalPages: 1, total: 0 };
  let notificationItems = [];
  let selectedCccdRegistrationId = null;
  const searchKeywords = { database: "", cccd: "", qa: "" };
  let dashboardSettings = null;
  let currentAppointmentMonth = new Date();
  currentAppointmentMonth.setDate(1);
  currentAppointmentMonth.setHours(0, 0, 0, 0);
  let selectedAppointmentDate = "";
  let appointmentItems = [];
  let currentAppointmentEditItem = null;
  const appointmentFilters = { status: "", assignee: "" };
  let qaHistoryItems = [];
  let selectedQaHistoryId = null;
  let dashboardPollBusy = false;
  const SCREEN_REFRESH_TTL_MS = 5000;
  const DASHBOARD_POLL_INTERVAL_MS = 5000;
  const dashboardScreenLoadState = {
    database: false,
    cccd: false,
    appointments: false,
    qa: false,
    settings: false,
  };
  const dashboardScreenLoadPromises = {
    database: null,
    cccd: null,
    appointments: null,
    qa: null,
    settings: null,
  };
  const dashboardScreenLastLoadedAt = {
    database: 0,
    cccd: 0,
    appointments: 0,
    qa: 0,
    settings: 0,
  };

  function syncSidebarState() {
    if (window.innerWidth <= BREAKPOINT) {
      body.classList.add("sidebar-collapsed");
      return;
    }
    if (!manualOverride) {
      body.classList.remove("sidebar-collapsed");
    }
  }

  function normalizeText(value) {
    return (value || "").trim().toLowerCase();
  }

  function setActiveScreen(screenName) {
    activeScreen = screenName || "database";
    screens.forEach(function (screen) {
      screen.classList.toggle("is-active", screen.dataset.screen === activeScreen);
    });

    screenLinks.forEach(function (link) {
      link.classList.toggle(
        "active",
        link.getAttribute("data-screen-target") === activeScreen
      );
    });

    updateSearchUiForScreen();
    syncDetailPanelHeight();
  }

  function updateSearchUiForScreen() {
    if (!globalSearchInput) return;
    if (activeScreen === "appointments") {
      globalSearchInput.placeholder = t("dash.search.appointments.disabled");
      globalSearchInput.value = "";
      globalSearchInput.disabled = true;
      return;
    }
    globalSearchInput.disabled = false;
    if (activeScreen === "cccd") {
      globalSearchInput.placeholder = t("dash.search.cccd.placeholder");
      globalSearchInput.value = searchKeywords.cccd || "";
      return;
    }
    if (activeScreen === "qa") {
      globalSearchInput.placeholder = t("dash.search.qa.placeholder");
      globalSearchInput.value = searchKeywords.qa || "";
      return;
    }
    globalSearchInput.placeholder = t("dash.search.placeholder");
    globalSearchInput.value = searchKeywords.database || "";
  }

  function markDashboardScreenLoaded(screenName) {
    if (!Object.prototype.hasOwnProperty.call(dashboardScreenLoadState, screenName)) return;
    dashboardScreenLoadState[screenName] = true;
    dashboardScreenLastLoadedAt[screenName] = Date.now();
  }

  function isDashboardScreenFresh(screenName) {
    const loadedAt = Number(dashboardScreenLastLoadedAt[screenName] || 0);
    return loadedAt > 0 && Date.now() - loadedAt < SCREEN_REFRESH_TTL_MS;
  }

  async function loadScreenData(screenName, options) {
    const screen = String(screenName || "database");
    const opts = options || {};
    if (screen === "settings") {
      await loadSettings();
      return;
    }
    if (screen === "appointments") {
      await loadAppointmentsForCurrentMonth(opts.resetMessage !== false);
      return;
    }
    if (screen === "cccd") {
      await loadCccdDatabase(searchKeywords.cccd || "", cccdPagination.page || 1);
      return;
    }
    if (screen === "qa") {
      await loadQaHistory(searchKeywords.qa || "");
      return;
    }
    currentSearchKeyword = searchKeywords.database || "";
    await Promise.all([
      loadDatabase(currentSearchKeyword, databasePagination.page || 1),
      loadRecentActivity(recentPagination.page || 1),
    ]);
  }

  async function ensureScreenLoaded(screenName, options) {
    const screen = String(screenName || "database");
    if (!Object.prototype.hasOwnProperty.call(dashboardScreenLoadState, screen)) return;
    const force = !!(options && options.force);
    const shouldReuse = !force && dashboardScreenLoadState[screen] && isDashboardScreenFresh(screen);
    if (shouldReuse) return;
    if (dashboardScreenLoadPromises[screen]) {
      await dashboardScreenLoadPromises[screen];
      return;
    }
    const task = Promise.resolve(loadScreenData(screen, options)).finally(function () {
      dashboardScreenLoadPromises[screen] = null;
      markDashboardScreenLoaded(screen);
    });
    dashboardScreenLoadPromises[screen] = task;
    await task;
  }

  async function refreshActiveScreen() {
    await ensureScreenLoaded(activeScreen, { force: true, resetMessage: false });
  }

  function formatCell(value) {
    return value === null || value === undefined || value === "" ? "-" : String(value);
  }

  function getMissingFields(item) {
    return Array.isArray(item && item.missing_fields) ? item.missing_fields : [];
  }

  function hasMissingFields(item) {
    if (!item || typeof item !== "object") return false;
    if (typeof item.has_missing_fields === "boolean") return item.has_missing_fields;
    return getMissingFields(item).length > 0;
  }

  function formatMissingFieldLabel(fieldName) {
    const labels = {
      full_name: "Họ tên",
      company: "Công ty",
      email: "Email",
      phone: "Phone",
    };
    return labels[fieldName] || fieldName;
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatRelativeTime(value) {
    if (!value) return t("dash.time.just.now");
    const parsed = Date.parse(String(value).replace(" ", "T"));
    if (Number.isNaN(parsed)) return String(value);
    const diffSec = Math.max(0, Math.floor((Date.now() - parsed) / 1000));
    if (diffSec < 60) return t("dash.time.seconds.ago", { count: diffSec });
    if (diffSec < 3600) return t("dash.time.minutes.ago", { count: Math.floor(diffSec / 60) });
    if (diffSec < 86400) return t("dash.time.hours.ago", { count: Math.floor(diffSec / 3600) });
    return t("dash.time.days.ago", { count: Math.floor(diffSec / 86400) });
  }

  async function fetchJsonWithAuth(url, options) {
    const res = await fetch(url, options);
    if (res.status === 401) {
      window.location.href = "/login";
      return null;
    }
    return res.json();
  }

  function showSettingsStatus(message, isError) {
    if (!settingsStatusMessage) return;
    settingsStatusMessage.hidden = !message;
    settingsStatusMessage.textContent = message || "";
    settingsStatusMessage.style.borderColor = isError ? "#fecaca" : "#bfdbfe";
    settingsStatusMessage.style.background = isError ? "#fef2f2" : "#eff6ff";
    settingsStatusMessage.style.color = isError ? "#b91c1c" : "#1d4ed8";
  }

  function setSettingsBusy(busy) {
    if (qrPrintEnabledToggle) qrPrintEnabledToggle.disabled = !!busy;
    if (faceRecognitionToggle) faceRecognitionToggle.disabled = !!busy;
    if (appointmentOverlayToggle) appointmentOverlayToggle.disabled = !!busy;
  }

  function renderSettings(settings) {
    dashboardSettings = settings || null;
    if (!dashboardSettings) return;
    if (qrPrintEnabledToggle) qrPrintEnabledToggle.checked = !!dashboardSettings.qr_print_enabled;
    if (faceRecognitionToggle) faceRecognitionToggle.checked = !!dashboardSettings.face_recognition_enabled;
    if (appointmentOverlayToggle) appointmentOverlayToggle.checked = !!dashboardSettings.appointment_overlay_enabled;
    if (qrPrintEnvValue) qrPrintEnvValue.textContent = "QR_PRINT_ENABLED=" + (dashboardSettings.qr_print_enabled_raw || "false");
    if (faceRecognitionEnvValue) faceRecognitionEnvValue.textContent = "FACE_USE_REDIS=" + (dashboardSettings.face_use_redis || "0");
    if (appointmentOverlayEnvValue) {
      appointmentOverlayEnvValue.textContent = "APPOINTMENT_OVERLAY_ENABLED=" + (dashboardSettings.appointment_overlay_enabled_raw || "false");
    }
  }

  async function loadSettings() {
    const js = await fetchJsonWithAuth("/api/dashboard/settings");
    if (!js || !js.ok) {
      showSettingsStatus((js && js.error) || t("dash.settings.error.load"), true);
      return;
    }
    renderSettings(js.settings || {});
  }

  async function updateSetting(payload) {
    setSettingsBusy(true);
    showSettingsStatus(t("dash.settings.saving"), false);
    const js = await fetchJsonWithAuth("/api/dashboard/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    setSettingsBusy(false);
    if (!js || !js.ok) {
      showSettingsStatus((js && js.error) || t("dash.settings.error.save"), true);
      renderSettings(dashboardSettings || {});
      return false;
    }
    renderSettings(js.settings || {});
    showSettingsStatus("", false);
    return true;
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

  function toDateInputValue(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return year + "-" + month + "-" + day;
  }

  function getTodayKey() {
    return toDateInputValue(new Date());
  }

  function getAppointmentItemsForDate(dateKey) {
    return appointmentItems.filter(function (item) {
      return String(item.appointment_date || "") === String(dateKey || "");
    });
  }

  function showAppointmentStatus(message, isError) {
    if (!appointmentStatusMessage) return;
    appointmentStatusMessage.hidden = !message;
    appointmentStatusMessage.textContent = message || "";
    appointmentStatusMessage.style.borderColor = isError ? "#fecaca" : "#bfdbfe";
    appointmentStatusMessage.style.background = isError ? "#fef2f2" : "#eff6ff";
    appointmentStatusMessage.style.color = isError ? "#b91c1c" : "#1d4ed8";
  }

  function formatAppointmentMonthLabel(date) {
    return t("dash.appt.month.label", { month: date.getMonth() + 1, year: date.getFullYear() });
  }

  function formatAppointmentDateLabel(dateKey) {
    if (!dateKey) return t("dash.appt.select.date");
    const parts = String(dateKey).split("-");
    if (parts.length !== 3) return dateKey;
    return parts[2] + "/" + parts[1] + "/" + parts[0];
  }

  function formatAppointmentListDateLabel(dateKey) {
    if (!dateKey) return "-";
    const parts = String(dateKey).split("-");
    if (parts.length !== 3) return dateKey;
    return parts[2] + "/" + parts[1] + "/" + parts[0];
  }

  function formatAppointmentTimeRange(item) {
    const start = String(item && item.start_time ? item.start_time : "").trim();
    const end = String(item && item.end_time ? item.end_time : "").trim();
    if (start && end) return start + " - " + end;
    if (start) return start;
    if (end) return end;
    return t("dash.appt.all.day");
  }

  function formatAppointmentReasonLine(item) {
    const type = String(item && item.appointment_type ? item.appointment_type : "").trim();
    const reason = String(item && item.appointment_reason ? item.appointment_reason : "").trim();
    if (reason) return t("dash.appt.reason.prefix", { reason: reason });
    if (type) return t("dash.appt.reason.prefix", { reason: type });
    return t("dash.appt.reason.empty");
  }

  function formatAppointmentStatusLabel(status) {
    const key = String(status || "pending").trim().toLowerCase();
    const labels = {
      pending: t("dash.appt.status.pending"),
      confirmed: t("dash.appt.status.confirmed"),
      done: t("dash.appt.status.done"),
      cancelled: t("dash.appt.status.cancelled"),
      no_show: t("dash.appt.status.no_show"),
    };
    return labels[key] || t("dash.appt.status.pending");
  }

  function formatAppointmentDescription(item) {
    const raw = String(item && item.description ? item.description : "").trim();
    if (!raw) return t("dash.appt.notes.empty");
    const reason = String(item && item.appointment_reason ? item.appointment_reason : "").trim().toLowerCase();
    const type = String(item && item.appointment_type ? item.appointment_type : "").trim().toLowerCase();
    const seen = new Set();
    const kept = [];
    raw.split(/\r?\n/).forEach(function (line) {
      const text = String(line || "").trim();
      if (!text) return;
      const key = text.toLowerCase();
      if (reason && key === reason) return;
      if (type && key === type) return;
      if (seen.has(key)) return;
      seen.add(key);
      kept.push(text);
    });
    return kept.length ? kept.join("\n") : t("dash.appt.notes.empty");
  }

  function getSortedAppointmentItems(items) {
    return (Array.isArray(items) ? items.slice() : []).sort(function (left, right) {
      const leftKey = String(left && left.appointment_date ? left.appointment_date : "") + " " + String(left && left.start_time ? left.start_time : "");
      const rightKey = String(right && right.appointment_date ? right.appointment_date : "") + " " + String(right && right.start_time ? right.start_time : "");
      return leftKey.localeCompare(rightKey);
    });
  }

  function renderAppointmentFilterList() {
    if (!appointmentFilterList) return;
    if (appointmentFilterMonthHint) {
      appointmentFilterMonthHint.textContent = t("dash.appt.filter.month.hint", {
        month: formatAppointmentMonthLabel(currentAppointmentMonth),
        count: appointmentItems.length,
      });
    }
    const sortedItems = getSortedAppointmentItems(appointmentItems);
    if (!sortedItems.length) {
      appointmentFilterList.innerHTML = "<div class='appointment-filter-list-empty'>" + escapeHtml(t("dash.appt.filter.empty")) + "</div>";
      return;
    }
    appointmentFilterList.innerHTML = "";
    sortedItems.forEach(function (item) {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "appointment-filter-list-item";
      const contactName = String(item && (item.contact_name || item.title) ? (item.contact_name || item.title) : t("dash.appt.item.guest")).trim();
      card.innerHTML =
        "<strong>" +
        escapeHtml(formatAppointmentListDateLabel(item.appointment_date) + " - " + contactName) +
        "</strong>" +
        "<p>" + escapeHtml(formatAppointmentTimeRange(item)) + "</p>";
      card.addEventListener("click", function () {
        openAppointmentDetailModal(item);
      });
      appointmentFilterList.appendChild(card);
    });
  }

  function renderAppointmentDayList(dateKey) {
    if (!appointmentSelectedDateLabel || !appointmentDayList || !appointmentEmptyState) return;
    appointmentSelectedDateLabel.textContent = formatAppointmentDateLabel(dateKey);
    appointmentDayList.innerHTML = "";
    const items = getAppointmentItemsForDate(dateKey);
    if (!items.length) {
      appointmentEmptyState.style.display = "block";
      return;
    }

    appointmentEmptyState.style.display = "none";
    items.forEach(function (item) {
      const card = document.createElement("article");
      card.className = "appointment-item";
      const primaryName = String(item.contact_name || item.title || t("dash.appt.item.default")).trim();
      const statusKey = String(item.status || "pending").trim().toLowerCase() || "pending";
      const assignee = String(item.assignee || "").trim();
      card.innerHTML =
        "<div class='appointment-item-head'>" +
        "  <strong>" + escapeHtml(primaryName + " - " + formatAppointmentTimeRange(item)) + "</strong>" +
        "  <div class='appointment-actions-inline'>" +
        "    <button type='button' class='action-btn appointment-edit-btn'>" + escapeHtml(t("dash.appt.item.edit")) + "</button>" +
        "    <button type='button' class='action-btn action-delete appointment-delete-btn'>" + escapeHtml(t("dash.appt.item.delete")) + "</button>" +
        "  </div>" +
        "</div>" +
        "<p class='appointment-item-meta'>" + escapeHtml(assignee
          ? t("dash.appt.item.status.assignee", { status: formatAppointmentStatusLabel(statusKey), assignee: assignee })
          : t("dash.appt.item.status", { status: formatAppointmentStatusLabel(statusKey) })) + "</p>" +
        "<p class='appointment-item-meta'>" + escapeHtml(formatAppointmentReasonLine(item)) + "</p>" +
        "<p class='appointment-item-desc'>" + escapeHtml(formatAppointmentDescription(item)) + "</p>";
      const editBtn = card.querySelector(".appointment-edit-btn");
      if (editBtn) {
        editBtn.addEventListener("click", function () {
          openAppointmentEditModal(item);
        });
      }
      const deleteBtn = card.querySelector(".appointment-delete-btn");
      if (deleteBtn) {
        deleteBtn.addEventListener("click", function () {
          openConfirm(t("dash.appt.confirm.delete"), async function () {
            const js = await fetchJsonWithAuth("/api/dashboard/appointments/" + encodeURIComponent(String(item.id || "")), {
              method: "DELETE",
            });
            if (!js || !js.ok) {
              showAppointmentStatus((js && js.error) || t("dash.appt.error.delete"), true);
              return;
            }
            showAppointmentStatus(t("dash.appt.success.delete"), false);
            await loadAppointmentsForCurrentMonth(false);
          });
        });
      }
      appointmentDayList.appendChild(card);
    });
  }

  function selectAppointmentDate(dateKey) {
    selectedAppointmentDate = dateKey;
    renderAppointmentCalendar();
    renderAppointmentDayList(dateKey);
  }

  function renderAppointmentCalendar() {
    if (!appointmentsCalendarGrid) return;
    const year = currentAppointmentMonth.getFullYear();
    const month = currentAppointmentMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const startOffset = (firstDay.getDay() + 6) % 7;
    const gridStart = new Date(year, month, 1 - startOffset);
    const monthKey = year + "-" + String(month + 1).padStart(2, "0");
    const todayKey = getTodayKey();

    if (appointmentMonthLabel) appointmentMonthLabel.textContent = formatAppointmentMonthLabel(currentAppointmentMonth);
    if (appointmentMonthMeta) {
      appointmentMonthMeta.textContent = t("dash.appt.count.month", { count: appointmentItems.length });
    }

    appointmentsCalendarGrid.innerHTML = "";
    for (let index = 0; index < 42; index += 1) {
      const date = new Date(gridStart);
      date.setDate(gridStart.getDate() + index);
      const dateKey = toDateInputValue(date);
      const items = getAppointmentItemsForDate(dateKey);
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "appointment-day-cell";
      if (!dateKey.startsWith(monthKey)) cell.classList.add("is-outside");
      if (dateKey === todayKey) cell.classList.add("is-today");
      if (dateKey === selectedAppointmentDate) cell.classList.add("is-selected");
      if (items.length) cell.classList.add("has-appointments");
      cell.innerHTML =
        "<span class='appointment-day-number'>" + date.getDate() + "</span>" +
        "<span class='appointment-day-count'>" +
        (items.length ? escapeHtml(t("dash.appt.item.count", { count: items.length })) : "&nbsp;") +
        "</span>";
      cell.addEventListener("click", function () {
        selectAppointmentDate(dateKey);
      });
      appointmentsCalendarGrid.appendChild(cell);
    }
  }

  async function loadAppointmentsForCurrentMonth(resetMessage) {
    const params = new URLSearchParams({
      year: String(currentAppointmentMonth.getFullYear()),
      month: String(currentAppointmentMonth.getMonth() + 1),
    });
    if (appointmentFilters.status) params.set("status", appointmentFilters.status);
    if (appointmentFilters.assignee) params.set("assignee", appointmentFilters.assignee);
    const js = await fetchJsonWithAuth("/api/dashboard/appointments/month?" + params.toString());
    if (!js || !js.ok) {
      appointmentItems = [];
      renderAppointmentCalendar();
      renderAppointmentDayList(selectedAppointmentDate);
      showAppointmentStatus((js && js.error) || t("dash.appt.error.load"), true);
      return;
    }
    appointmentItems = Array.isArray(js.items) ? js.items : [];
    if (!selectedAppointmentDate || !selectedAppointmentDate.startsWith(params.get("year") + "-" + String(params.get("month")).padStart(2, "0"))) {
      selectAppointmentDate(toDateInputValue(new Date(currentAppointmentMonth.getFullYear(), currentAppointmentMonth.getMonth(), 1)));
      renderAppointmentFilterList();
      return;
    }
    renderAppointmentCalendar();
    renderAppointmentDayList(selectedAppointmentDate);
    renderAppointmentFilterList();
    if (resetMessage !== false) showAppointmentStatus("", false);
  }

  function openAppointmentFilterModal() {
    if (appointmentStatusFilter) appointmentStatusFilter.value = appointmentFilters.status;
    if (appointmentAssigneeFilter) appointmentAssigneeFilter.value = appointmentFilters.assignee;
    renderAppointmentFilterList();
    openModal(appointmentFilterModal);
  }

  function closeAppointmentFilterModal() {
    closeModal(appointmentFilterModal);
  }

  function openAppointmentDetailModal(item) {
    if (!item) return;
    if (appointmentDetailDate) appointmentDetailDate.textContent = formatAppointmentListDateLabel(item.appointment_date);
    if (appointmentDetailTime) appointmentDetailTime.textContent = formatAppointmentTimeRange(item);
    if (appointmentDetailContact) appointmentDetailContact.textContent = String(item.contact_name || item.title || "-").trim() || "-";
    if (appointmentDetailStatus) appointmentDetailStatus.textContent = formatAppointmentStatusLabel(item.status);
    if (appointmentDetailAssignee) appointmentDetailAssignee.textContent = String(item.assignee || "").trim() || t("dash.appt.detail.unassigned");
    if (appointmentDetailReason) appointmentDetailReason.textContent = formatAppointmentReasonLine(item).replace(/^Lí do hẹn:\s*/i, "").replace(/^予約理由:\s*/i, "") || t("dash.appt.detail.none");
    if (appointmentDetailDescription) appointmentDetailDescription.textContent = formatAppointmentDescription(item);
    openModal(appointmentDetailModal);
  }

  function closeAppointmentDetailModal() {
    closeModal(appointmentDetailModal);
  }

  async function applyAppointmentFilters() {
    appointmentFilters.status = String(appointmentStatusFilter ? appointmentStatusFilter.value : "").trim();
    appointmentFilters.assignee = String(appointmentAssigneeFilter ? appointmentAssigneeFilter.value : "").trim();
    await loadAppointmentsForCurrentMonth(true);
  }

  async function shiftAppointmentMonth(offset) {
    currentAppointmentMonth = new Date(currentAppointmentMonth.getFullYear(), currentAppointmentMonth.getMonth() + offset, 1);
    selectAppointmentDate(toDateInputValue(new Date(currentAppointmentMonth.getFullYear(), currentAppointmentMonth.getMonth(), 1)));
    await loadAppointmentsForCurrentMonth(true);
  }

  async function jumpAppointmentMonthToToday() {
    const today = new Date();
    currentAppointmentMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    selectAppointmentDate(toDateInputValue(today));
    await loadAppointmentsForCurrentMonth(true);
  }

  function showQaHistoryStatus(message, isError) {
    if (!qaHistoryStatusMessage) return;
    qaHistoryStatusMessage.hidden = !message;
    qaHistoryStatusMessage.textContent = message || "";
    qaHistoryStatusMessage.style.borderColor = isError ? "#fecaca" : "#bfdbfe";
    qaHistoryStatusMessage.style.background = isError ? "#fef2f2" : "#eff6ff";
    qaHistoryStatusMessage.style.color = isError ? "#b91c1c" : "#1d4ed8";
  }

  function renderQaDetailPanel(item) {
    if (!qaDetailTitle || !qaDetailMeta || !qaDetailQuestion || !qaDetailAnswer || !qaDetailSources || !qaDetailDot) return;
    if (!item) {
      qaDetailTitle.textContent = t("dash.qa.select");
      qaDetailMeta.textContent = t("dash.qa.detail.info.empty");
      qaDetailQuestion.textContent = "-";
      qaDetailAnswer.textContent = "-";
      qaDetailSources.textContent = "-";
      qaDetailDot.classList.remove("active");
      if (qaDetailDeleteBtn) qaDetailDeleteBtn.disabled = true;
      return;
    }

    const turns = Array.isArray(item.conversation_json) ? item.conversation_json : [];
    const createdAtText = formatCell(item.created_at);
    const updatedAtText = formatCell(item.updated_at || item.created_at);
    qaDetailTitle.textContent = t("dash.qa.session.title", {
      channel: String(item.channel || "q&a").toUpperCase(),
      time: createdAtText,
    });
    qaDetailMeta.textContent = [
      t("dash.qa.turn.count", { count: formatCell(item.turn_count) }),
      t("dash.qa.updated", { time: updatedAtText }),
      t("dash.qa.answer.mode", { mode: formatCell(item.answer_mode) }),
      t("dash.qa.language", { language: formatCell(item.language) }),
      t("dash.qa.response.ms", { ms: formatCell(item.response_ms) }),
    ].join("\n");
    qaDetailQuestion.textContent = turns.length
      ? turns.map(function (turn, index) {
          return (index + 1) + ". " + formatCell(turn.question);
        }).join("\n\n")
      : formatCell(item.question);
    qaDetailAnswer.textContent = turns.length
      ? turns.map(function (turn, index) {
          return (index + 1) + ". " + formatCell(turn.answer);
        }).join("\n\n")
      : formatCell(item.answer);
    qaDetailDot.classList.add("active");
    if (qaDetailDeleteBtn) qaDetailDeleteBtn.disabled = false;

    const sources = Array.isArray(item.matched_sources) ? item.matched_sources : [];
    if (!sources.length) {
      qaDetailSources.textContent = t("dash.qa.sources.empty");
      return;
    }
    qaDetailSources.innerHTML = "";
    sources.forEach(function (sourceName) {
      const card = document.createElement("article");
      card.className = "qa-detail-source-card";
      const heading = document.createElement("strong");
      heading.textContent = String(sourceName || t("dash.qa.source.unknown"));
      const body = document.createElement("p");
      body.textContent = t("dash.qa.source.used");
      card.appendChild(heading);
      card.appendChild(body);
      qaDetailSources.appendChild(card);
    });
  }

  function renderQaHistory(items) {
    if (!qaHistoryList || !qaHistoryEmptyState || !qaHistoryCountLabel) return;
    qaHistoryItems = Array.isArray(items) ? items.slice() : [];
    qaHistoryCountLabel.textContent = t("dash.qa.count", { count: qaHistoryItems.length });
    if (qaHistoryDeleteAllBtn) qaHistoryDeleteAllBtn.disabled = qaHistoryItems.length === 0;
    qaHistoryList.innerHTML = "";
    if (!qaHistoryItems.length) {
      qaHistoryEmptyState.style.display = "block";
      selectedQaHistoryId = null;
      renderQaDetailPanel(null);
      return;
    }

    qaHistoryEmptyState.style.display = "none";
    qaHistoryItems.forEach(function (item) {
      const turns = Array.isArray(item.conversation_json) ? item.conversation_json : [];
      const firstQuestion = String((turns[0] && turns[0].question) || item.question || "").trim();
      const lastAnswer = String((turns[turns.length - 1] && turns[turns.length - 1].answer) || item.answer || "").trim();
      const button = document.createElement("button");
      button.type = "button";
      button.className = "qa-history-item";
      button.dataset.id = String(item.id || "");
      if (selectedQaHistoryId === item.id) {
        button.classList.add("is-selected");
      }
      button.innerHTML =
        "<h6>" + escapeHtml(firstQuestion || t("dash.qa.session.default")) + "</h6>" +
        "<p>" + escapeHtml(lastAnswer || "-") + "</p>" +
        "<div class='qa-history-meta'>" +
        "  <span class='qa-history-badge'>" + escapeHtml(String(item.channel || "kiosk")) + "</span>" +
        "  <span class='qa-history-badge'>" + escapeHtml(t("dash.qa.turns", { count: String(item.turn_count || 1) })) + "</span>" +
        "  <span class='qa-history-badge'>" + escapeHtml(String(item.answer_mode || "fallback")) + "</span>" +
        "  <span class='qa-history-badge" + (item.used_fallback ? " is-fallback" : "") + "'>" +
        escapeHtml(item.used_fallback ? "Fallback" : t("dash.qa.enough.context")) +
        "</span>" +
        "</div>";
      button.addEventListener("click", function () {
        selectedQaHistoryId = item.id;
        renderQaHistory(qaHistoryItems);
        renderQaDetailPanel(item);
      });
      qaHistoryList.appendChild(button);
    });

    const selected = qaHistoryItems.find(function (item) {
      return item.id === selectedQaHistoryId;
    }) || qaHistoryItems[0];
    selectedQaHistoryId = selected ? selected.id : null;
    renderQaDetailPanel(selected || null);
    Array.from(qaHistoryList.children).forEach(function (child) {
      child.classList.toggle("is-selected", Number(child.dataset.id) === Number(selectedQaHistoryId));
    });
  }

  async function loadQaHistory(searchKeyword) {
    if (!qaHistoryList) return;
    try {
      const params = new URLSearchParams({
        limit: "150",
        search: searchKeyword || "",
      });
      const js = await fetchJsonWithAuth("/api/dashboard/qa/history?" + params.toString());
      if (!js || !js.ok) {
        qaHistoryItems = [];
        renderQaHistory([]);
        showQaHistoryStatus((js && js.error) || t("dash.qa.error.load"), true);
        return;
      }
      renderQaHistory(Array.isArray(js.items) ? js.items : []);
      showQaHistoryStatus("", false);
    } catch (error) {
      console.error("loadQaHistory error:", error);
      qaHistoryItems = [];
      renderQaHistory([]);
      showQaHistoryStatus(t("dash.qa.error.load"), true);
    }
  }

  async function deleteQaHistoryEntry(historyId) {
    const recordId = Number(historyId || 0);
    if (!recordId) return;
    const js = await fetchJsonWithAuth("/api/dashboard/qa/history/" + encodeURIComponent(String(recordId)), {
      method: "DELETE",
    });
    if (!js || !js.ok) {
      showQaHistoryStatus((js && js.error) || t("dash.qa.error.delete"), true);
      return;
    }
    if (selectedQaHistoryId === recordId) {
      selectedQaHistoryId = null;
    }
    showQaHistoryStatus(t("dash.qa.success.delete"), false);
    await loadQaHistory(searchKeywords.qa || "");
  }

  async function deleteAllQaHistory() {
    const js = await fetchJsonWithAuth("/api/dashboard/qa/history", {
      method: "DELETE",
    });
    if (!js || !js.ok) {
      showQaHistoryStatus((js && js.error) || t("dash.qa.error.delete.all"), true);
      return;
    }
    selectedQaHistoryId = null;
    showQaHistoryStatus(t("dash.qa.success.delete.all"), false);
    await loadQaHistory(searchKeywords.qa || "");
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = formatCell(value);
  }

  function setDetailSelected(active) {
    const dot = document.getElementById("detailDot");
    if (!dot) return;
    dot.classList.toggle("active", !!active);
  }

  function openModal(modal) {
    if (!modal) return;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
  }

  function openConfirm(message, onConfirm, onCancel) {
    if (confirmModalMessage) {
      confirmModalMessage.textContent = message || t("dash.modal.confirm.msg");
    }
    confirmCallback = typeof onConfirm === "function" ? onConfirm : null;
    confirmCancelCallback = typeof onCancel === "function" ? onCancel : null;
    openModal(confirmModal);
  }

  function closeConfirm() {
    confirmCallback = null;
    confirmCancelCallback = null;
    closeModal(confirmModal);
  }

  function openEditModal(item) {
    currentEditItem = item || null;
    if (editFullName) editFullName.value = item && item.full_name ? item.full_name : "";
    if (editCompany) editCompany.value = item && item.company ? item.company : "";
    if (editEmail) editEmail.value = item && item.email ? item.email : "";
    if (editPhone) editPhone.value = item && item.phone ? item.phone : "";
    if (editTitle) editTitle.value = item && item.title ? item.title : "";
    openModal(editModal);
  }

  function closeEditModal() {
    currentEditItem = null;
    closeModal(editModal);
  }

  function openCccdEditModal(item) {
    currentCccdEditItem = item || null;
    if (cccdEditFullName) cccdEditFullName.value = item && item.full_name ? item.full_name : "";
    if (cccdEditIdNumber) cccdEditIdNumber.value = item && item.id_number ? item.id_number : "";
    if (cccdEditGender) cccdEditGender.value = item && item.gender ? item.gender : "";
    if (cccdEditDob) cccdEditDob.value = item && item.dob ? item.dob : "";
    if (cccdEditAddress) cccdEditAddress.value = item && item.address ? item.address : "";
    if (cccdEditIssued) cccdEditIssued.value = item && item.issued ? item.issued : "";
    if (cccdEditExpiry) cccdEditExpiry.value = item && item.expiry ? item.expiry : "";
    if (cccdEditOldId) cccdEditOldId.value = item && item.old_id ? item.old_id : "";
    openModal(cccdEditModal);
  }

  function closeCccdEditModal() {
    currentCccdEditItem = null;
    closeModal(cccdEditModal);
  }

  function openExportModal() {
    openModal(exportModal);
  }

  function closeExportModal() {
    closeModal(exportModal);
  }

  function openAppointmentEditModal(item) {
    currentAppointmentEditItem = item || null;
    const seedDate = String((item && item.appointment_date) || selectedAppointmentDate || toDateInputValue(new Date())).trim();
    if (appointmentEditDate) appointmentEditDate.value = seedDate;
    if (appointmentEditDate) appointmentEditDate.min = toDateInputValue(new Date());
    setAppointmentTimeControl(appointmentEditStart, appointmentEditStartHour, appointmentEditStartMinute, String((item && item.start_time) || "08:00").trim());
    setAppointmentTimeControl(appointmentEditEnd, appointmentEditEndHour, appointmentEditEndMinute, String((item && item.end_time) || "08:10").trim());
    if (appointmentEditContact) appointmentEditContact.value = String((item && (item.contact_name || item.title)) || "").trim();
    if (appointmentEditPurpose) appointmentEditPurpose.value = String((item && item.appointment_reason) || "").trim();
    if (appointmentEditDescription) appointmentEditDescription.value = String((item && item.description) || "").trim();
    if (appointmentEditAssignee) appointmentEditAssignee.value = String((item && item.assignee) || "").trim();
    if (appointmentEditStatus) appointmentEditStatus.value = String((item && item.status) || "pending").trim() || "pending";
    clearAppointmentEditInlineErrors();
    refreshAppointmentEditInlineErrors();
    openModal(appointmentEditModal);
  }

  function closeAppointmentEditModal() {
    currentAppointmentEditItem = null;
    closeModal(appointmentEditModal);
  }

  function showInputPicker(inputEl) {
    if (!inputEl) return;
    try {
      if (typeof inputEl.showPicker === "function") {
        inputEl.showPicker();
        return;
      }
    } catch (_err) {
      // Fallback to focus when showPicker is unsupported or blocked.
    }
    inputEl.focus();
    inputEl.click();
  }

  function setAppointmentEditInlineError(fieldName, message) {
    const maps = {
      date: { label: appointmentEditDateError, shell: appointmentEditDateShell },
      start: { label: appointmentEditStartError, shell: appointmentEditStartShell },
      end: { label: appointmentEditEndError, shell: appointmentEditEndShell },
    };
    const target = maps[fieldName];
    if (!target) return;
    const text = String(message || "").trim();
    if (target.label) {
      target.label.hidden = !text;
      target.label.textContent = text;
    }
    if (target.shell) {
      target.shell.classList.toggle("is-invalid", !!text);
    }
  }

  function clearAppointmentEditInlineErrors() {
    setAppointmentEditInlineError("date", "");
    setAppointmentEditInlineError("start", "");
    setAppointmentEditInlineError("end", "");
  }

  function syncAppointmentTimeInput(hiddenInput, hourSelect, minuteSelect) {
    if (!hiddenInput || !hourSelect || !minuteSelect) return;
    hiddenInput.value = String(hourSelect.value || "08").padStart(2, "0") + ":" + String(minuteSelect.value || "00").padStart(2, "0");
  }

  function setAppointmentTimeControl(hiddenInput, hourSelect, minuteSelect, value) {
    const text = String(value || "").trim();
    const match = /^(\d{2}):(\d{2})$/.exec(text);
    const hour = match ? match[1] : "08";
    const minute = match ? match[2] : "00";
    if (hourSelect) hourSelect.value = hour;
    if (minuteSelect) minuteSelect.value = minute;
    syncAppointmentTimeInput(hiddenInput, hourSelect, minuteSelect);
  }

  function appointmentTimeToMinutes(value) {
    const text = String(value || "").trim();
    if (!/^\d{2}:\d{2}$/.test(text)) return NaN;
    const parts = text.split(":");
    return Number(parts[0]) * 60 + Number(parts[1]);
  }

  function getAppointmentEditInlineErrors(payload) {
    const errors = { date: "", start: "", end: "" };
    const dateValue = String(payload.appointment_date || "").trim();
    const startValue = String(payload.start_time || "").trim();
    const endValue = String(payload.end_time || "").trim();
    const originalDate = String((currentAppointmentEditItem && currentAppointmentEditItem.appointment_date) || "").trim();
    const originalStart = String((currentAppointmentEditItem && currentAppointmentEditItem.start_time) || "").trim();
    const originalEnd = String((currentAppointmentEditItem && currentAppointmentEditItem.end_time) || "").trim();
    const timeChanged = dateValue !== originalDate || startValue !== originalStart || endValue !== originalEnd;
    const today = new Date();
    const todayKey = toDateInputValue(today);
    const nowMinutes = today.getHours() * 60 + today.getMinutes();
    const startMinutes = appointmentTimeToMinutes(startValue);
    const endMinutes = appointmentTimeToMinutes(endValue);

    if (timeChanged && dateValue && dateValue < todayKey) {
      errors.date = t("dash.appt.validation.date.past");
    }
    if (!startValue) {
      errors.start = t("dash.appt.validation.start.required");
    } else if (Number.isNaN(startMinutes)) {
      errors.start = t("dash.appt.validation.time.invalid");
    } else if (startMinutes < 8 * 60 || startMinutes > 17 * 60) {
      errors.start = t("dash.appt.validation.time.range");
    } else if ((startMinutes % 10) !== 0) {
      errors.start = t("dash.appt.validation.time.step");
    } else if (timeChanged && dateValue === todayKey && startMinutes <= nowMinutes) {
      errors.start = t("dash.appt.validation.time.past");
    }
    if (!endValue) {
      errors.end = t("dash.appt.validation.end.required");
    } else if (Number.isNaN(endMinutes)) {
      errors.end = t("dash.appt.validation.time.invalid");
    } else if (endMinutes < 8 * 60 || endMinutes > 17 * 60) {
      errors.end = t("dash.appt.validation.time.range");
    } else if ((endMinutes % 10) !== 0) {
      errors.end = t("dash.appt.validation.time.step");
    } else if (!Number.isNaN(startMinutes) && endMinutes <= startMinutes) {
      errors.end = t("dash.appt.validation.end.after.start");
    }
    return errors;
  }

  function refreshAppointmentEditInlineErrors() {
    const payload = {
      appointment_date: appointmentEditDate ? appointmentEditDate.value : "",
      start_time: appointmentEditStart ? appointmentEditStart.value : "",
      end_time: appointmentEditEnd ? appointmentEditEnd.value : "",
    };
    const errors = getAppointmentEditInlineErrors(payload);
    setAppointmentEditInlineError("date", errors.date);
    setAppointmentEditInlineError("start", errors.start);
    setAppointmentEditInlineError("end", errors.end);
    return errors;
  }

  function validateAppointmentEditPayload(payload) {
    if (!currentAppointmentEditItem || !currentAppointmentEditItem.id) {
      return t("dash.appt.validation.update.only");
    }
    const dateValue = String(payload.appointment_date || "").trim();
    const startValue = String(payload.start_time || "").trim();
    const endValue = String(payload.end_time || "").trim();
    const reasonValue = String(payload.appointment_reason || "").trim();
    const descriptionValue = String(payload.description || "").trim();
    const titleValue = String(payload.title || "").trim();
    const contactValue = String(payload.contact_name || "").trim();
    const assigneeValue = String(payload.assignee || "").trim();
    if (!dateValue) return t("dash.appt.validation.date.required");
    if (!startValue || !endValue) return t("dash.appt.validation.time.required");
    const inlineErrors = getAppointmentEditInlineErrors(payload);
    if (inlineErrors.date || inlineErrors.start || inlineErrors.end) {
      setAppointmentEditInlineError("date", inlineErrors.date);
      setAppointmentEditInlineError("start", inlineErrors.start);
      setAppointmentEditInlineError("end", inlineErrors.end);
      return inlineErrors.date || inlineErrors.start || inlineErrors.end;
    }

    const startMinutes = appointmentTimeToMinutes(startValue);
    const endMinutes = appointmentTimeToMinutes(endValue);
    const durationMinutes = endMinutes - startMinutes;
    if (durationMinutes < 10) return t("dash.appt.validation.duration.min");
    if (durationMinutes > 180) return t("dash.appt.validation.duration.max");
    if (!reasonValue && !descriptionValue) {
      return t("dash.appt.validation.reason");
    }
    if (titleValue.length > 200) return t("dash.appt.validation.title.long");
    if (contactValue.length > 120) return t("dash.appt.validation.contact.long");
    if (reasonValue.length > 500) return t("dash.appt.validation.reason.long");
    if (descriptionValue.length > 2000) return t("dash.appt.validation.desc.long");
    if (assigneeValue.length > 120) return t("dash.appt.validation.assignee.long");

    const conflict = appointmentItems.some(function (item) {
      if (!item || String(item.id || "") === String(currentAppointmentEditItem.id || "")) return false;
      if (String(item.appointment_date || "") !== dateValue) return false;
      const itemStart = appointmentTimeToMinutes(item.start_time);
      const itemEnd = appointmentTimeToMinutes(item.end_time);
      if (Number.isNaN(itemStart) || Number.isNaN(itemEnd)) return false;
      return itemStart < endMinutes && itemEnd > startMinutes;
    });
    if (conflict) return t("dash.appt.validation.conflict");
    return "";
  }

  async function updateRegistration(regId, payload) {
    const js = await fetchJsonWithAuth(
      "/api/dashboard/registrations/" + encodeURIComponent(regId),
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload || {}),
      }
    );
    return js && js.ok;
  }

  async function upsertAppointment(appointmentId, payload) {
    const path = "/api/dashboard/appointments/" + encodeURIComponent(String(appointmentId));
    return fetchJsonWithAuth(path, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
  }

  async function deleteRegistration(regId) {
    const js = await fetchJsonWithAuth(
      "/api/dashboard/registrations/" + encodeURIComponent(regId),
      { method: "DELETE" }
    );
    return js && js.ok;
  }

  async function bulkDeleteRegistrations(regIds) {
    const js = await fetchJsonWithAuth("/api/dashboard/registrations/bulk-delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ registration_ids: Array.from(regIds || []) }),
    });
    return js && js.ok ? Number(js.deleted_count) || 0 : -1;
  }

  async function updateCccd(regId, payload) {
    const js = await fetchJsonWithAuth(
      "/api/dashboard/cccd/" + encodeURIComponent(regId),
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload || {}),
      }
    );
    return js && js.ok;
  }

  async function deleteCccd(regId) {
    const js = await fetchJsonWithAuth(
      "/api/dashboard/cccd/" + encodeURIComponent(regId),
      { method: "DELETE" }
    );
    return js && js.ok;
  }

  async function bulkDeleteCccds(regIds) {
    const js = await fetchJsonWithAuth("/api/dashboard/cccd/bulk-delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ registration_ids: Array.from(regIds || []) }),
    });
    return js && js.ok ? Number(js.deleted_count) || 0 : -1;
  }

  function updateBulkSelectionUi() {
    const checkedCount = selectedRegistrationIds.size;
    if (bulkDeleteBtn) {
      bulkDeleteBtn.hidden = checkedCount === 0;
      bulkDeleteBtn.disabled = checkedCount === 0;
      bulkDeleteBtn.textContent = checkedCount > 0 ? t("dash.bulk.delete.count", { count: checkedCount }) : t("dash.btn.delete");
    }
    if (!databaseSelectAll) return;
    const pageCheckboxes = Array.from(databaseTableBody.querySelectorAll(".row-selector"));
    const selectable = pageCheckboxes.length;
    const checkedOnPage = pageCheckboxes.filter(function (checkbox) { return checkbox.checked; }).length;
    databaseSelectAll.checked = selectable > 0 && checkedOnPage === selectable;
    databaseSelectAll.indeterminate = checkedOnPage > 0 && checkedOnPage < selectable;
  }

  function updateCccdBulkSelectionUi() {
    const checkedCount = selectedCccdIds.size;
    if (cccdBulkDeleteBtn) {
      cccdBulkDeleteBtn.hidden = checkedCount === 0;
      cccdBulkDeleteBtn.disabled = checkedCount === 0;
      cccdBulkDeleteBtn.textContent = checkedCount > 0 ? t("dash.bulk.delete.count", { count: checkedCount }) : t("dash.btn.delete");
    }
    if (!cccdSelectAll || !cccdTableBody) return;
    const pageCheckboxes = Array.from(cccdTableBody.querySelectorAll(".row-selector"));
    const selectable = pageCheckboxes.length;
    const checkedOnPage = pageCheckboxes.filter(function (checkbox) { return checkbox.checked; }).length;
    cccdSelectAll.checked = selectable > 0 && checkedOnPage === selectable;
    cccdSelectAll.indeterminate = checkedOnPage > 0 && checkedOnPage < selectable;
  }

  function ensureDetailImageCard() {
    const panel = document.querySelector(".guest-detail-panel");
    if (!panel) return null;
    let card = document.getElementById("detailImageCard");
    if (!card) {
      card = document.createElement("div");
      card.id = "detailImageCard";
      card.className = "guest-detail-card";
      card.innerHTML =
        "<h6 data-i18n='dash.detail.images'>" + t("dash.detail.images") + "</h6>" +
        "<div id='detailImageGrid' style='display:grid;grid-template-columns:1fr 1fr;gap:10px;'>" +
        "  <figure style='margin:0;'>" +
        "    <figcaption style='font-size:12px;color:#475569;margin-bottom:6px;' data-i18n='dash.detail.face'>" + t("dash.detail.face") + "</figcaption>" +
        "    <img id='detailFaceImg' alt='" + t("preview.face.alt") + "' data-i18n='preview.face.alt' data-i18n-attr='alt' style='width:100%;height:120px;object-fit:contain;border:1px solid #e2e8f0;display:none;background:#f8fafc;cursor:zoom-in;' />" +
        "  </figure>" +
        "  <figure style='margin:0;'>" +
        "    <figcaption style='font-size:12px;color:#475569;margin-bottom:6px;' data-i18n='dash.detail.card'>" + t("dash.detail.card") + "</figcaption>" +
        "    <img id='detailBcardImg' alt='" + t("preview.card.alt") + "' data-i18n='preview.card.alt' data-i18n-attr='alt' style='width:100%;height:120px;object-fit:contain;border:1px solid #e2e8f0;display:none;background:#f8fafc;cursor:zoom-in;' />" +
        "  </figure>" +
        "</div>" +
        "<p id='detailImageEmpty' style='margin-top:8px;' data-i18n='dash.detail.images.empty'>" + t("dash.detail.images.empty") + "</p>";
      panel.appendChild(card);
    }
    return {
      faceImg: document.getElementById("detailFaceImg"),
      bcardImg: document.getElementById("detailBcardImg"),
      emptyText: document.getElementById("detailImageEmpty"),
    };
  }

  function ensureDetailRawTextCard() {
    const panel = document.querySelector(".guest-detail-panel");
    if (!panel) return null;
    let card = document.getElementById("detailRawTextCard");
    if (!card) {
      card = document.createElement("div");
      card.id = "detailRawTextCard";
      card.className = "guest-detail-card";
      card.innerHTML =
        "<h6 data-i18n='dash.detail.raw.text'>" + t("dash.detail.raw.text") + "</h6>" +
        "<pre id='detailRawText' style='margin:0;white-space:pre-wrap;word-break:break-word;'>-</pre>";
      panel.appendChild(card);
    }
    return {
      rawText: document.getElementById("detailRawText"),
    };
  }

  function buildRegistrationAssetUrl(detail, key, registrationId) {
    const raw = detail && detail[key] ? String(detail[key]).trim() : "";
    if (!raw || !registrationId) return "";
    if (/^https?:\/\//i.test(raw) || raw.startsWith("/registrations/")) return raw;
    const normalized = raw.replaceAll("\\", "/");
    const fileName = normalized.split("/").pop();
    if (!fileName) return "";
    return "/registrations/" + encodeURIComponent(registrationId) + "/" + encodeURIComponent(fileName);
  }

  function applyDetailImage(imgEl, src) {
    if (!imgEl) return false;
    if (!src) {
      imgEl.removeAttribute("src");
      imgEl.style.display = "none";
      return false;
    }
    imgEl.onerror = function () {
      imgEl.style.display = "none";
    };
    imgEl.src = src;
    imgEl.style.display = "block";
    return true;
  }

  function closeImageLightbox() {
    if (!imageLightboxEl) return;
    imageLightboxEl.classList.remove("open");
    imageLightboxEl.setAttribute("aria-hidden", "true");
    if (imageLightboxTargetEl) {
      imageLightboxTargetEl.classList.remove("is-zoomed");
      imageLightboxTargetEl.style.removeProperty("--lightbox-zoom-scale");
      imageLightboxTargetEl.removeAttribute("src");
      imageLightboxTargetEl.alt = t("dash.detail.lightbox.alt");
    }
  }

  function ensureImageLightbox() {
    if (imageLightboxEl) return imageLightboxEl;
    const lightbox = document.createElement("div");
    lightbox.id = "dashboardImageLightbox";
    lightbox.className = "image-lightbox";
    lightbox.setAttribute("aria-hidden", "true");
    lightbox.innerHTML =
      "<button type='button' class='image-lightbox-close' aria-label='" + escapeHtml(t("dash.detail.lightbox.close")) + "'>&times;</button>" +
      "<img id='dashboardImageLightboxTarget' alt='" + escapeHtml(t("dash.detail.lightbox.alt")) + "' class='image-lightbox-image' />";
    document.body.appendChild(lightbox);
    imageLightboxEl = lightbox;
    imageLightboxTargetEl = document.getElementById("dashboardImageLightboxTarget");

    lightbox.addEventListener("click", function (event) {
      if (
        event.target === lightbox ||
        event.target.classList.contains("image-lightbox-close")
      ) {
        closeImageLightbox();
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeImageLightbox();
    });
    return lightbox;
  }

  function openImageLightbox(src, alt, imageType) {
    if (!src) return;
    ensureImageLightbox();
    if (!imageLightboxEl || !imageLightboxTargetEl) return;
    const zoomScale =
      LIGHTBOX_ZOOM_SCALE[imageType] || LIGHTBOX_ZOOM_SCALE.default;
    imageLightboxTargetEl.src = src;
    imageLightboxTargetEl.alt = alt || t("dash.detail.lightbox.alt");
    imageLightboxTargetEl.style.setProperty("--lightbox-zoom-scale", String(zoomScale));
    imageLightboxTargetEl.classList.add("is-zoomed");
    imageLightboxEl.classList.add("open");
    imageLightboxEl.setAttribute("aria-hidden", "false");
  }

  function bindDetailImageZoom(imgEl, altText, imageType) {
    if (!imgEl || imgEl.dataset.zoomBound === "1") return;
    imgEl.dataset.zoomBound = "1";
    imgEl.addEventListener("click", function () {
      if (!imgEl.src || imgEl.style.display === "none") return;
      openImageLightbox(imgEl.src, altText, imageType);
    });
  }

  function renderDetailImages(item, detailItem) {
    const refs = ensureDetailImageCard();
    if (!refs) return;
    bindDetailImageZoom(refs.faceImg, t("dash.detail.lightbox.face"), "face");
    bindDetailImageZoom(refs.bcardImg, t("dash.detail.lightbox.card"), "bcard");
    if (!item) {
      applyDetailImage(refs.faceImg, "");
      applyDetailImage(refs.bcardImg, "");
      if (refs.emptyText) refs.emptyText.style.display = "block";
      return;
    }
    const detail = detailItem || item || {};
    const regId = detail.registration_id || item.registration_id || "";
    const faceSrc = buildRegistrationAssetUrl(detail, "face_link", regId);
    const bcardSrc = buildRegistrationAssetUrl(detail, "bcard_link", regId);
    const hasFace = applyDetailImage(refs.faceImg, faceSrc);
    const hasBcard = applyDetailImage(refs.bcardImg, bcardSrc);
    if (refs.emptyText) refs.emptyText.style.display = hasFace || hasBcard ? "none" : "block";
  }

  function renderDetailRawText(item, detailItem) {
    const refs = ensureDetailRawTextCard();
    if (!refs || !refs.rawText) return;
    if (!item) {
      refs.rawText.textContent = "-";
      return;
    }
    const detail = detailItem || item || {};
    refs.rawText.textContent = formatCell(detail.last_bcard_text);
  }

  function renderDetailPanel(item, detailItem) {
    if (!item) {
      setText("detailName", t("dash.detail.select"));
      setText("detailInfo", t("dash.detail.info.empty"));
      setText("detailCompany", "-");
      setText("detailActivity", "-");
      setDetailSelected(false);
      renderDetailImages(null, null);
      renderDetailRawText(null, null);
      return;
    }

    const detail = detailItem || item;
    setText("detailName", item.full_name || item.registration_id || t("dash.detail.unknown"));
    setText(
      "detailInfo",
      [
        t("dash.detail.field.id", { value: formatCell(item.registration_id) }),
        t("dash.detail.field.name", { value: formatCell(item.full_name) }),
        t("dash.detail.field.company", { value: formatCell(item.company) }),
        t("dash.detail.field.email", { value: formatCell(item.email) }),
        t("dash.detail.field.phone", { value: formatCell(item.phone) }),
      ].join("\n")
    );
    setText("detailCompany", "-"); // Keep for safety if element still exists in DOM briefly
    setText(
      "detailActivity",
      [
        t("dash.detail.field.registered.at", { value: formatCell(item.created_at) }),
        t("dash.detail.field.registration.id", { value: formatCell(item.registration_id) }),
      ].join("\n")
    );
    setDetailSelected(true);
    renderDetailImages(item, detail);
    renderDetailRawText(item, detail);
  }

  function renderCccdDetailPanel(item, detailItem) {
    const detailName = document.getElementById("cccdDetailName");
    const detailInfo = document.getElementById("cccdDetailInfo");
    const detailActivity = document.getElementById("cccdDetailActivity");
    const detailDot = document.getElementById("cccdDetailDot");
    const faceImg = document.getElementById("cccdDetailFaceImg");
    const frontImg = document.getElementById("cccdDetailFrontImg");
    const emptyText = document.getElementById("cccdDetailImageEmpty");
    const rawText = document.getElementById("cccdDetailRawText");

    if (!detailName || !detailInfo || !detailActivity || !detailDot || !rawText) return;

    if (!item) {
      detailName.textContent = t("dash.detail.select");
      detailInfo.textContent = t("dash.cccd.info.empty");
      detailActivity.textContent = "-";
      rawText.textContent = "-";
      detailDot.classList.remove("active");
      applyDetailImage(faceImg, "");
      applyDetailImage(frontImg, "");
      if (emptyText) emptyText.style.display = "block";
      return;
    }

    const detail = detailItem || item || {};
    const regId = detail.registration_id || item.registration_id || "";
    detailName.textContent = item.full_name || regId || t("dash.detail.unknown");
    detailInfo.textContent = [
      t("dash.detail.field.id", { value: formatCell(regId) }),
      t("dash.detail.field.name", { value: formatCell(detail.full_name) }),
      t("dash.cccd.field.id.number", { value: formatCell(detail.id_number) }),
      t("dash.cccd.field.gender", { value: formatCell(detail.gender) }),
      t("dash.cccd.field.dob", { value: formatCell(detail.dob) }),
      t("dash.cccd.field.address", { value: formatCell(detail.address) }),
      t("dash.cccd.field.issued", { value: formatCell(detail.issued) }),
      t("dash.cccd.field.expiry", { value: formatCell(detail.expiry) }),
      t("dash.cccd.field.old.id", { value: formatCell(detail.old_id) }),
    ].join("\n");
    detailActivity.textContent = [
      t("dash.cccd.field.created", { value: formatCell(detail.created_at) }),
      t("dash.cccd.field.updated", { value: formatCell(detail.updated_at) }),
      t("dash.detail.field.registration.id", { value: formatCell(regId) }),
    ].join("\n");
    rawText.textContent = formatCell(detail.cccd_ocr_text);
    detailDot.classList.add("active");

    bindDetailImageZoom(faceImg, t("dash.detail.lightbox.cccd.face"), "face");
    bindDetailImageZoom(frontImg, t("dash.detail.lightbox.cccd"), "cccd");
    const hasFace = applyDetailImage(faceImg, buildRegistrationAssetUrl(detail, "face_link", regId));
    const hasFront = applyDetailImage(frontImg, buildRegistrationAssetUrl(detail, "cccd_front_link", regId));
    if (emptyText) emptyText.style.display = hasFace || hasFront ? "none" : "block";
  }

  async function loadRegistrationDetail(registrationId) {
    try {
      const js = await fetchJsonWithAuth("/api/dashboard/registrations/" + encodeURIComponent(registrationId));
      if (!js || !js.ok) return null;
      return js.item || null;
    } catch (e) {
      console.error("loadRegistrationDetail error:", e);
      return null;
    }
  }

  async function loadCccdDetail(registrationId) {
    try {
      const js = await fetchJsonWithAuth("/api/dashboard/cccd/" + encodeURIComponent(registrationId));
      if (!js || !js.ok) return null;
      return js.item || null;
    } catch (e) {
      console.error("loadCccdDetail error:", e);
      return null;
    }
  }

  function clearSelectedRows() {
    Array.from(databaseTableBody.querySelectorAll("tr.clickable-row.selected")).forEach(function (row) {
      row.classList.remove("selected");
    });
    if (cccdTableBody) {
      Array.from(cccdTableBody.querySelectorAll("tr.clickable-row.selected")).forEach(function (row) {
        row.classList.remove("selected");
      });
    }
  }

  function toggleRowSelection(row, item, checked) {
    const regId = item && item.registration_id ? String(item.registration_id) : "";
    if (!regId) return;
    if (checked) selectedRegistrationIds.add(regId);
    else selectedRegistrationIds.delete(regId);
    row.classList.toggle("multi-selected", checked);
    updateBulkSelectionUi();
  }

  function toggleCccdRowSelection(row, item, checked) {
    const regId = item && item.registration_id ? String(item.registration_id) : "";
    if (!regId) return;
    if (checked) selectedCccdIds.add(regId);
    else selectedCccdIds.delete(regId);
    row.classList.toggle("multi-selected", checked);
    updateCccdBulkSelectionUi();
  }

  async function selectRow(row, item) {
    clearSelectedRows();
    row.classList.add("selected");
    selectedRegistrationId = item.registration_id || null;
    renderDetailPanel(item, null);
    if (!selectedRegistrationId) return;

    const detail = await loadRegistrationDetail(selectedRegistrationId);
    if (selectedRegistrationId !== (item.registration_id || null)) return;
    renderDetailPanel(item, detail);
  }

  async function selectCccdRow(row, item) {
    clearSelectedRows();
    row.classList.add("selected");
    selectedCccdRegistrationId = item.registration_id || null;
    renderCccdDetailPanel(item, null);
    if (!selectedCccdRegistrationId) return;

    const detail = await loadCccdDetail(selectedCccdRegistrationId);
    if (selectedCccdRegistrationId !== (item.registration_id || null)) return;
    renderCccdDetailPanel(item, detail);
  }

  function cloneRowFromItem(item) {
    const row = document.createElement("tr");
    row.setAttribute("data-registration-id", item && item.registration_id ? String(item.registration_id) : "");
    const missingFields = getMissingFields(item);
    if (hasMissingFields(item)) {
      row.classList.add("missing-data-row");
      row.title = "Missing: " + missingFields.map(formatMissingFieldLabel).join(", ");
    }
    const selectorTd = document.createElement("td");
    selectorTd.className = "row-selector-cell";
    const selector = document.createElement("input");
    selector.type = "checkbox";
    selector.className = "row-selector";
    selector.checked = selectedRegistrationIds.has(item.registration_id || "");
    selector.addEventListener("click", function (event) {
      event.stopPropagation();
    });
    selector.addEventListener("change", function (event) {
      event.stopPropagation();
      toggleRowSelection(row, item, selector.checked);
    });
    selectorTd.appendChild(selector);
    row.appendChild(selectorTd);

    const cells = [
      item.full_name,
      item.company,
      item.email,
      item.phone,
      item.created_at,
    ];

    cells.forEach(function (value) {
      const td = document.createElement("td");
      td.textContent = formatCell(value);
      row.appendChild(td);
    });

    const actionTd = document.createElement("td");
    actionTd.className = "table-actions";
    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "action-btn action-edit";
    editBtn.textContent = t("dash.appt.item.edit");
    editBtn.addEventListener("click", function (event) {
      event.stopPropagation();
      openEditModal(item);
    });
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "action-btn action-delete";
    deleteBtn.textContent = t("dash.appt.item.delete");
    deleteBtn.addEventListener("click", function (event) {
      event.stopPropagation();
      openConfirm(t("dash.confirm.delete.reg"), async function () {
        const regId = item.registration_id || "";
        if (!regId) return;
        const ok = await deleteRegistration(regId);
        if (!ok) {
          alert(t("dash.error.delete"));
          return;
        }
        if (selectedRegistrationId === regId) {
          selectedRegistrationId = null;
        }
        selectedRegistrationIds.delete(regId);
        await loadDatabase(currentSearchKeyword, databasePagination.page);
        if (!selectedRegistrationId) {
          renderDetailPanel(null, null);
        }
      });
    });
    actionTd.appendChild(editBtn);
    actionTd.appendChild(deleteBtn);
    row.appendChild(actionTd);
    row.classList.toggle("multi-selected", selector.checked);
    return row;
  }

  function cloneCccdRowFromItem(item) {
    const row = document.createElement("tr");
    row.setAttribute("data-registration-id", item && item.registration_id ? String(item.registration_id) : "");

    const selectorTd = document.createElement("td");
    selectorTd.className = "row-selector-cell";
    const selector = document.createElement("input");
    selector.type = "checkbox";
    selector.className = "row-selector";
    selector.checked = selectedCccdIds.has(item.registration_id || "");
    selector.addEventListener("click", function (event) { event.stopPropagation(); });
    selector.addEventListener("change", function (event) {
      event.stopPropagation();
      toggleCccdRowSelection(row, item, selector.checked);
    });
    selectorTd.appendChild(selector);
    row.appendChild(selectorTd);

    [
      item.full_name,
      item.id_number,
      item.gender,
      item.dob,
      item.address,
      item.created_at,
    ].forEach(function (value) {
      const td = document.createElement("td");
      td.textContent = formatCell(value);
      row.appendChild(td);
    });

    const actionTd = document.createElement("td");
    actionTd.className = "table-actions";
    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "action-btn action-edit";
    editBtn.textContent = t("dash.appt.item.edit");
    editBtn.addEventListener("click", function (event) {
      event.stopPropagation();
      openCccdEditModal(item);
    });
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "action-btn action-delete";
    deleteBtn.textContent = t("dash.appt.item.delete");
    deleteBtn.addEventListener("click", function (event) {
      event.stopPropagation();
      openConfirm(t("dash.confirm.delete.cccd"), async function () {
        const regId = item.registration_id || "";
        if (!regId) return;
        const ok = await deleteCccd(regId);
        if (!ok) {
          alert(t("dash.error.delete"));
          return;
        }
        if (selectedCccdRegistrationId === regId) {
          selectedCccdRegistrationId = null;
          renderCccdDetailPanel(null, null);
        }
        selectedCccdIds.delete(regId);
        await loadCccdDatabase(searchKeywords.cccd || "", cccdPagination.page);
      });
    });
    actionTd.appendChild(editBtn);
    actionTd.appendChild(deleteBtn);
    row.appendChild(actionTd);
    row.classList.toggle("multi-selected", selector.checked);
    return row;
  }

  function clearGeneratedRows(root) {
    Array.from(root.querySelectorAll("tr.generated-row")).forEach(function (row) {
      row.remove();
    });
  }

  function renderDatabaseTable(items) {
    clearGeneratedRows(databaseTableBody);
    if (!items.length) {
      if (databaseEmptyRow && databaseEmptyRow.firstElementChild) {
        databaseEmptyRow.firstElementChild.textContent = showMissingOnly
          ? t("dash.table.empty.missing")
          : t("dash.table.empty");
      }
      databaseEmptyRow.style.display = "table-row";
      exportExcelBtn.disabled = true;
      updateBulkSelectionUi();
      if (!selectedRegistrationId) {
        renderDetailPanel(null, null);
      }
      return;
    }

    items.forEach(function (item) {
      const row = cloneRowFromItem(item);
      row.classList.add("generated-row", "clickable-row");
      row.addEventListener("click", function () {
        selectRow(row, item);
      });
      databaseTableBody.insertBefore(row, databaseEmptyRow);
    });

    databaseEmptyRow.style.display = "none";
    exportExcelBtn.disabled = false;
    updateBulkSelectionUi();

    const selectedRow = Array.from(databaseTableBody.querySelectorAll("tr.clickable-row")).find(function (row) {
      return String(row.getAttribute("data-registration-id") || "") === String(selectedRegistrationId || "");
    });
    if (selectedRow) {
      selectedRow.classList.add("selected");
    } else if (!selectedRegistrationId) {
      renderDetailPanel(null, null);
    }
  }

  function renderRecentActivity(items) {
    clearGeneratedRows(recentActivityBody);
    if (!items.length) {
      recentEmptyRow.style.display = "table-row";
      return;
    }

    items.forEach(function (item) {
      const row = cloneRowFromItem(item);
      row.classList.add("generated-row");
      recentActivityBody.insertBefore(row, recentEmptyRow);
    });

    recentEmptyRow.style.display = "none";
  }

  async function loadStats() {
    try {
      const js = await fetchJsonWithAuth("/api/dashboard/stats");
      if (!js || !js.ok) return;
      const stats = js.stats || {};
      if (statTotal) statTotal.textContent = formatCell(stats.total);
      if (statToday) statToday.textContent = formatCell(stats.today);
      if (statWithEmail) statWithEmail.textContent = formatCell(stats.with_email);
      if (statWithPhone) statWithPhone.textContent = formatCell(stats.with_phone);
    } catch (e) {
      console.error("loadStats error:", e);
    }
  }

  async function fetchRegistrations(searchKeyword, page, pageSize, missingOnly) {
    const params = new URLSearchParams({
      page: String(page || 1),
      page_size: String(pageSize),
      sort_by: "created_at",
      sort_dir: "desc",
      search: searchKeyword || "",
      missing_only: missingOnly ? "1" : "0",
    });
    const js = await fetchJsonWithAuth("/api/dashboard/registrations?" + params.toString());
    if (!js || !js.ok) {
      return { items: [], page: 1, total_pages: 1, total: 0 };
    }
    return {
      items: Array.isArray(js.items) ? js.items : [],
      page: Number(js.page) || 1,
      total_pages: Math.max(1, Number(js.total_pages) || 1),
      total: Number(js.total) || 0,
    };
  }

  async function fetchCccdRegistrations(searchKeyword, page, pageSize) {
    const params = new URLSearchParams({
      page: String(page || 1),
      page_size: String(pageSize),
      sort_by: "created_at",
      sort_dir: "desc",
      search: searchKeyword || "",
    });
    const js = await fetchJsonWithAuth("/api/dashboard/cccd?" + params.toString());
    if (!js || !js.ok) {
      return { items: [], page: 1, total_pages: 1, total: 0 };
    }
    return {
      items: Array.isArray(js.items) ? js.items : [],
      page: Number(js.page) || 1,
      total_pages: Math.max(1, Number(js.total_pages) || 1),
      total: Number(js.total) || 0,
    };
  }

  function renderCccdTable(items) {
    clearGeneratedRows(cccdTableBody);
    if (!items.length) {
      if (cccdEmptyRow && cccdEmptyRow.firstElementChild) {
        cccdEmptyRow.firstElementChild.textContent = t("dash.cccd.empty");
      }
      if (cccdEmptyRow) cccdEmptyRow.style.display = "table-row";
      if (cccdExportExcelBtn) cccdExportExcelBtn.disabled = true;
      if (cccdExportJsonBtn) cccdExportJsonBtn.disabled = true;
      updateCccdBulkSelectionUi();
      if (!selectedCccdRegistrationId) renderCccdDetailPanel(null, null);
      return;
    }

    items.forEach(function (item) {
      const row = cloneCccdRowFromItem(item);
      row.classList.add("generated-row", "clickable-row");
      row.addEventListener("click", function () {
        selectCccdRow(row, item);
      });
      cccdTableBody.insertBefore(row, cccdEmptyRow);
    });

    if (cccdEmptyRow) cccdEmptyRow.style.display = "none";
    if (cccdExportExcelBtn) cccdExportExcelBtn.disabled = false;
    if (cccdExportJsonBtn) cccdExportJsonBtn.disabled = false;
    updateCccdBulkSelectionUi();

    const selectedRow = Array.from(cccdTableBody.querySelectorAll("tr.clickable-row")).find(function (row) {
      return String(row.getAttribute("data-registration-id") || "") === String(selectedCccdRegistrationId || "");
    });
    if (selectedRow) {
      selectedRow.classList.add("selected");
    } else if (!selectedCccdRegistrationId) {
      renderCccdDetailPanel(null, null);
    }
  }

  async function loadCccdStats(searchKeyword) {
    try {
      const payload = await fetchCccdRegistrations(searchKeyword || "", 1, 10000);
      const todayToken = new Date().toISOString().slice(0, 10);
      const todayCount = payload.items.filter(function (item) {
        const createdAt = String(item.created_at || "").replace(" ", "T");
        return createdAt.startsWith(todayToken);
      }).length;
      if (cccdStatTotal) cccdStatTotal.textContent = formatCell(payload.total);
      if (cccdStatToday) cccdStatToday.textContent = formatCell(todayCount);
    } catch (e) {
      console.error("loadCccdStats error:", e);
    }
  }

  async function loadCccdDatabase(searchKeyword, page) {
    try {
      const payload = await fetchCccdRegistrations(searchKeyword, page || 1, PAGE_SIZE);
      cccdPagination.page = payload.page;
      cccdPagination.totalPages = payload.total_pages;
      cccdPagination.total = payload.total;
      updatePaginationControls("cccd");
      renderCccdTable(payload.items);
      await loadCccdStats(searchKeyword || "");
    } catch (e) {
      console.error("loadCccdDatabase error:", e);
      cccdPagination.page = 1;
      cccdPagination.totalPages = 1;
      cccdPagination.total = 0;
      updatePaginationControls("cccd");
      renderCccdTable([]);
    }
  }

  function updatePaginationControls(type) {
    if (type === "database") {
      if (databasePageInfo) {
        databasePageInfo.textContent =
          t("dash.page.info", { current: databasePagination.page, total: databasePagination.totalPages });
      }
      if (databasePrevBtn) {
        databasePrevBtn.disabled = databasePagination.page <= 1;
      }
      if (databaseNextBtn) {
        databaseNextBtn.disabled = databasePagination.page >= databasePagination.totalPages;
      }
      return;
    }

    if (type === "cccd") {
      if (cccdPageInfo) {
        cccdPageInfo.textContent =
          t("dash.page.info", { current: cccdPagination.page, total: cccdPagination.totalPages });
      }
      if (cccdPrevBtn) {
        cccdPrevBtn.disabled = cccdPagination.page <= 1;
      }
      if (cccdNextBtn) {
        cccdNextBtn.disabled = cccdPagination.page >= cccdPagination.totalPages;
      }
      return;
    }

    if (recentPageInfo) {
      recentPageInfo.textContent =
        t("dash.page.info", { current: recentPagination.page, total: recentPagination.totalPages });
    }
    if (recentPrevBtn) {
      recentPrevBtn.disabled = recentPagination.page <= 1;
    }
    if (recentNextBtn) {
      recentNextBtn.disabled = recentPagination.page >= recentPagination.totalPages;
    }
  }

  function clearNotificationRows() {
    if (!notificationList) return;
    Array.from(notificationList.querySelectorAll("li.generated-row")).forEach(function (row) {
      row.remove();
    });
  }

  function formatNotificationCounter(total) {
    if (!Number.isFinite(total) || total <= 0) return "0";
    return total > 99 ? "99+" : String(total);
  }

  function groupNotifications(items) {
    const grouped = new Map();
    (Array.isArray(items) ? items : []).forEach(function (item) {
      const name = item.full_name || item.registration_id || t("dash.notification.unknown.guest");
      const company = item.company || "";
      const key = name + "||" + company;
      if (!grouped.has(key)) {
        grouped.set(key, {
          name: name,
          company: company,
          created_at: item.created_at,
          count: 1,
        });
        return;
      }
      grouped.get(key).count += 1;
    });
    return Array.from(grouped.values());
  }

  function renderNotifications(items) {
    if (!notificationList || !notifCounter) return;
    clearNotificationRows();
    const list = Array.isArray(items) ? items : [];
    notifCounter.textContent = formatNotificationCounter(list.length);
    if (!list.length) {
      if (notificationEmpty) notificationEmpty.style.display = "block";
      if (notificationMeta) notificationMeta.style.display = "none";
      return;
    }
    if (notificationEmpty) notificationEmpty.style.display = "none";
    const grouped = groupNotifications(list);
    const visible = grouped.slice(0, MAX_NOTIFICATION_ROWS);

    visible.forEach(function (item) {
      const name = item.name;
      const company = item.company || "";
      const time = formatRelativeTime(item.created_at);
      const countChip = item.count > 1
        ? "<span class='notification-count'>x" + item.count + "</span>"
        : "";
      const li = document.createElement("li");
      li.className = "generated-row";
      li.innerHTML =
        "<a href='javascript:void(0);' class='td-n bdB c-grey-800 cH-blue bgcH-grey-100'>" +
        "  <div class='notification-item-head'>" +
        "    <span class='notification-name'>" + escapeHtml(name) + "</span>" +
        countChip +
        "  </div>" +
        "  <div class='notification-sub'>" + escapeHtml(t("dash.notification.completed")) +
        (company ? " (" + escapeHtml(company) + ")" : "") +
        "</div>" +
        "  <div class='notification-time'>" + escapeHtml(time) + "</div>" +
        "</a>";
      notificationList.insertBefore(li, notificationEmpty || null);
    });

    if (notificationMeta) {
      notificationMeta.style.display = "block";
      notificationMeta.textContent = t("dash.notification.meta", { visible: visible.length, total: grouped.length });
    }
  }

  async function loadNotifications() {
    try {
      const js = await fetchJsonWithAuth("/api/dashboard/notifications?limit=30");
      if (!js || !js.ok) return;
      notificationItems = Array.isArray(js.items) ? js.items : [];
      renderNotifications(notificationItems);
    } catch (e) {
      console.error("loadNotifications error:", e);
    }
  }

  async function loadDatabase(searchKeyword, page) {
    try {
      const payload = await fetchRegistrations(searchKeyword, page || 1, PAGE_SIZE, showMissingOnly);
      databasePagination.page = payload.page;
      databasePagination.totalPages = payload.total_pages;
      databasePagination.total = payload.total;
      updatePaginationControls("database");
      renderDatabaseTable(payload.items);
    } catch (e) {
      console.error("loadDatabase error:", e);
      databasePagination.page = 1;
      databasePagination.totalPages = 1;
      databasePagination.total = 0;
      updatePaginationControls("database");
      renderDatabaseTable([]);
    }
  }

  async function loadRecentActivity(page) {
    try {
      const payload = await fetchRegistrations("", page || 1, PAGE_SIZE, false);
      recentPagination.page = payload.page;
      recentPagination.totalPages = payload.total_pages;
      recentPagination.total = payload.total;
      updatePaginationControls("recent");
      renderRecentActivity(payload.items);
    } catch (e) {
      console.error("loadRecentActivity error:", e);
      recentPagination.page = 1;
      recentPagination.totalPages = 1;
      recentPagination.total = 0;
      updatePaginationControls("recent");
      renderRecentActivity([]);
    }
  }

  function syncInputs(sourceInput, targetInput) {
    if (!sourceInput || !targetInput) return;
    syncingSearch = true;
    targetInput.value = sourceInput.value;
    syncingSearch = false;
  }

  function bindSearchInput(input, mirrorInput, shouldOpenDatabase) {
    if (!input) return;
    input.addEventListener("input", async function () {
      if (syncingSearch) return;
      if (activeScreen === "appointments") return;

      syncInputs(input, mirrorInput);
      const keyword = normalizeText(input.value);
      searchKeywords[activeScreen] = input.value;
      currentSearchKeyword = searchKeywords.database;
      if (shouldOpenDatabase && keyword !== "" && activeScreen !== "cccd" && activeScreen !== "qa") {
        setActiveScreen("database");
      }
      if (activeScreen === "cccd") {
        cccdPagination.page = 1;
        selectedCccdIds.clear();
        updateCccdBulkSelectionUi();
        await loadCccdDatabase(searchKeywords.cccd, 1);
        return;
      }
      if (activeScreen === "qa") {
        await loadQaHistory(searchKeywords.qa);
        return;
      }
      databasePagination.page = 1;
      selectedRegistrationIds.clear();
      updateBulkSelectionUi();
      await loadDatabase(searchKeywords.database, 1);
    });
  }

  function syncDetailPanelHeight() {
    const activeRoot = document.querySelector(".app-screen.is-active");
    const panel = activeRoot ? activeRoot.querySelector(".guest-detail-panel") : null;
    const tableWrap = activeRoot ? activeRoot.querySelector(".table-responsive") : null;
    if (!panel || !tableWrap) return;
    if (window.innerWidth <= 640) {
      panel.style.height = "";
      panel.style.maxHeight = "";
      return;
    }
    const targetHeight = tableWrap.offsetHeight;
    if (!targetHeight) return;
    panel.style.height = targetHeight + "px";
    panel.style.maxHeight = targetHeight + "px";
  }

  function exportVisibleRows(format, dateFrom, dateTo) {
    const keyword = searchKeywords[activeScreen] || "";
    if (activeScreen === "cccd") {
      const params = new URLSearchParams({
        search: keyword,
        sort_by: "created_at",
        sort_dir: "desc",
      });
      const path = format === "jsonl"
        ? "/api/dashboard/cccd/export.json?"
        : "/api/dashboard/cccd/export.xlsx?";
      window.location.href = path + params.toString();
      return;
    }
    const params = new URLSearchParams({
      search: keyword,
      sort_by: "created_at",
      sort_dir: "desc",
      missing_only: showMissingOnly ? "1" : "0",
    });
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    const path = format === "jsonl"
      ? "/api/dashboard/export.jsonl?"
      : "/api/dashboard/export.xlsx?";
    window.location.href = path + params.toString();
  }

  toggleButtons.forEach(function (button) {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      manualOverride = true;
      body.classList.toggle("sidebar-collapsed");
    });
  });

  window.addEventListener("resize", syncSidebarState);
  syncSidebarState();
  window.addEventListener("resize", syncDetailPanelHeight);
  setTimeout(syncDetailPanelHeight, 0);

  screenLinks.forEach(function (link) {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      const target = link.getAttribute("data-screen-target");
      setActiveScreen(target || "dashboard");
      ensureScreenLoaded(activeScreen);
    });
  });

  bindSearchInput(globalSearchInput, tableSearchInput, true);
  bindSearchInput(tableSearchInput, globalSearchInput, false);

  if (exportExcelBtn) {
    exportExcelBtn.addEventListener("click", function () {
      currentExportFormat = "xlsx";
      openExportModal();
    });
  }

  if (exportJsonlBtn) {
    exportJsonlBtn.addEventListener("click", function () {
      currentExportFormat = "jsonl";
      openExportModal();
    });
  }

  if (cccdExportExcelBtn) {
    cccdExportExcelBtn.addEventListener("click", function () {
      currentExportFormat = "xlsx";
      setActiveScreen("cccd");
      openExportModal();
    });
  }

  if (cccdExportJsonBtn) {
    cccdExportJsonBtn.addEventListener("click", function () {
      currentExportFormat = "jsonl";
      setActiveScreen("cccd");
      openExportModal();
    });
  }

  if (databaseMissingOnlyToggle) {
    databaseMissingOnlyToggle.addEventListener("change", async function () {
      showMissingOnly = !!databaseMissingOnlyToggle.checked;
      databasePagination.page = 1;
      selectedRegistrationIds.clear();
      updateBulkSelectionUi();
      await loadDatabase(currentSearchKeyword, 1);
    });
  }

  if (qrPrintEnabledToggle) {
    qrPrintEnabledToggle.addEventListener("change", async function () {
      await updateSetting({ qr_print_enabled: !!qrPrintEnabledToggle.checked });
    });
  }

  if (faceRecognitionToggle) {
    faceRecognitionToggle.addEventListener("change", async function () {
      await updateSetting({ face_recognition_enabled: !!faceRecognitionToggle.checked });
    });
  }

  if (appointmentOverlayToggle) {
    appointmentOverlayToggle.addEventListener("change", async function () {
      await updateSetting({ appointment_overlay_enabled: !!appointmentOverlayToggle.checked });
    });
  }

  if (appointmentPrevMonthBtn) {
    appointmentPrevMonthBtn.addEventListener("click", async function () {
      await shiftAppointmentMonth(-1);
    });
  }

  if (appointmentTodayBtn) {
    appointmentTodayBtn.addEventListener("click", async function () {
      await jumpAppointmentMonthToToday();
    });
  }

  if (appointmentNextMonthBtn) {
    appointmentNextMonthBtn.addEventListener("click", async function () {
      await shiftAppointmentMonth(1);
    });
  }

  if (appointmentFilterApplyBtn) {
    appointmentFilterApplyBtn.addEventListener("click", function () {
      openAppointmentFilterModal();
    });
  }

  if (qaHistoryDeleteAllBtn) {
    qaHistoryDeleteAllBtn.addEventListener("click", function () {
      if (!qaHistoryItems.length) return;
      openConfirm(t("dash.qa.confirm.delete.all"), async function () {
        await deleteAllQaHistory();
      });
    });
  }

  if (qaDetailDeleteBtn) {
    qaDetailDeleteBtn.addEventListener("click", function () {
      if (!selectedQaHistoryId) return;
      openConfirm(t("dash.qa.confirm.delete"), async function () {
        await deleteQaHistoryEntry(selectedQaHistoryId);
      });
    });
  }

  if (appointmentFilterModalSubmitBtn) {
    appointmentFilterModalSubmitBtn.addEventListener("click", async function () {
      await applyAppointmentFilters();
    });
  }

  [
    [appointmentEditDateShell, appointmentEditDate],
  ].forEach(function (pair) {
    const shell = pair[0];
    const input = pair[1];
    if (!shell || !input) return;
    shell.addEventListener("click", function (event) {
      showInputPicker(input);
    });
  });

  [
    [appointmentEditStartShell, appointmentEditStartHour],
    [appointmentEditEndShell, appointmentEditEndHour],
  ].forEach(function (pair) {
    const shell = pair[0];
    const hourSelect = pair[1];
    if (!shell || !hourSelect) return;
    shell.addEventListener("click", function (event) {
      const target = event.target;
      if (target && (target.tagName === "SELECT" || target.tagName === "OPTION")) return;
      hourSelect.focus();
    });
  });

  [appointmentEditDate].forEach(function (input) {
    if (!input) return;
    input.addEventListener("change", function () {
      refreshAppointmentEditInlineErrors();
    });
    input.addEventListener("input", function () {
      refreshAppointmentEditInlineErrors();
    });
  });

  [
    [appointmentEditStart, appointmentEditStartHour, appointmentEditStartMinute],
    [appointmentEditEnd, appointmentEditEndHour, appointmentEditEndMinute],
  ].forEach(function (config) {
    const hiddenInput = config[0];
    const hourSelect = config[1];
    const minuteSelect = config[2];
    [hourSelect, minuteSelect].forEach(function (selectEl) {
      if (!selectEl) return;
      selectEl.addEventListener("change", function () {
        syncAppointmentTimeInput(hiddenInput, hourSelect, minuteSelect);
        refreshAppointmentEditInlineErrors();
      });
      selectEl.addEventListener("input", function () {
        syncAppointmentTimeInput(hiddenInput, hourSelect, minuteSelect);
        refreshAppointmentEditInlineErrors();
      });
    });
  });

  if (appointmentAssigneeFilter) {
    appointmentAssigneeFilter.addEventListener("keydown", async function (event) {
      if (event.key !== "Enter") return;
      event.preventDefault();
      await applyAppointmentFilters();
    });
  }

  if (databaseSelectAll) {
    databaseSelectAll.addEventListener("change", function () {
      const checked = !!databaseSelectAll.checked;
      Array.from(databaseTableBody.querySelectorAll("tr.clickable-row")).forEach(function (row) {
        const checkbox = row.querySelector(".row-selector");
        if (!checkbox) return;
        checkbox.checked = checked;
        const regId = String(row.getAttribute("data-registration-id") || "");
        if (checked) selectedRegistrationIds.add(regId);
        else selectedRegistrationIds.delete(regId);
        row.classList.toggle("multi-selected", checked);
      });
      updateBulkSelectionUi();
    });
  }

  if (cccdSelectAll) {
    cccdSelectAll.addEventListener("change", function () {
      const checked = !!cccdSelectAll.checked;
      Array.from(cccdTableBody.querySelectorAll("tr.clickable-row")).forEach(function (row) {
        const checkbox = row.querySelector(".row-selector");
        if (!checkbox) return;
        checkbox.checked = checked;
        const regId = String(row.getAttribute("data-registration-id") || "");
        if (checked) selectedCccdIds.add(regId);
        else selectedCccdIds.delete(regId);
        row.classList.toggle("multi-selected", checked);
      });
      updateCccdBulkSelectionUi();
    });
  }

  if (bulkDeleteBtn) {
    bulkDeleteBtn.addEventListener("click", function () {
      if (!selectedRegistrationIds.size) return;
      openConfirm(t("dash.confirm.delete.bulk.reg"), async function () {
        const deletedCount = await bulkDeleteRegistrations(selectedRegistrationIds);
        if (deletedCount < 0) {
          alert(t("dash.error.bulk.delete"));
          return;
        }
        if (selectedRegistrationId && selectedRegistrationIds.has(selectedRegistrationId)) {
          selectedRegistrationId = null;
          renderDetailPanel(null, null);
        }
        selectedRegistrationIds.clear();
        await loadDatabase(currentSearchKeyword, databasePagination.page);
      });
    });
  }

  if (cccdBulkDeleteBtn) {
    cccdBulkDeleteBtn.addEventListener("click", function () {
      if (!selectedCccdIds.size) return;
      openConfirm(t("dash.confirm.delete.bulk.cccd"), async function () {
        const deletedCount = await bulkDeleteCccds(selectedCccdIds);
        if (deletedCount < 0) {
          alert(t("dash.error.bulk.delete"));
          return;
        }
        if (selectedCccdRegistrationId && selectedCccdIds.has(selectedCccdRegistrationId)) {
          selectedCccdRegistrationId = null;
          renderCccdDetailPanel(null, null);
        }
        selectedCccdIds.clear();
        await loadCccdDatabase(searchKeywords.cccd || "", cccdPagination.page);
      });
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", async function () {
      try {
        await fetch("/api/auth/logout", { method: "POST" });
      } catch (e) {
        console.error("logout error:", e);
      } finally {
        window.location.href = "/login";
      }
    });
  }

  if (editConfirmBtn) {
    editConfirmBtn.addEventListener("click", function () {
      if (!currentEditItem || !currentEditItem.registration_id) return;
      openConfirm(t("dash.confirm.update.reg"), async function () {
        const regId = currentEditItem.registration_id;
        const payload = {
          full_name: editFullName ? editFullName.value : "",
          company: editCompany ? editCompany.value : "",
          email: editEmail ? editEmail.value : "",
          phone: editPhone ? editPhone.value : "",
          title: editTitle ? editTitle.value : "",
        };
        const ok = await updateRegistration(regId, payload);
        if (!ok) {
          alert(t("dash.error.update"));
          return;
        }
        closeEditModal();
        await loadDatabase(currentSearchKeyword, databasePagination.page);
        const detail = await loadRegistrationDetail(regId);
        if (detail) {
          renderDetailPanel(detail, detail);
        }
      });
    });
  }

  if (appointmentEditConfirmBtn) {
    appointmentEditConfirmBtn.addEventListener("click", function () {
      if (!currentAppointmentEditItem || !currentAppointmentEditItem.id) {
        showAppointmentStatus(t("dash.appt.error.not.found"), true);
        return;
      }
      const payload = {
        appointment_date: appointmentEditDate ? appointmentEditDate.value : "",
        start_time: appointmentEditStart ? appointmentEditStart.value : "",
        end_time: appointmentEditEnd ? appointmentEditEnd.value : "",
        contact_name: appointmentEditContact ? appointmentEditContact.value : "",
        title: appointmentEditContact ? appointmentEditContact.value : "",
        appointment_reason: appointmentEditPurpose ? appointmentEditPurpose.value : "",
        description: appointmentEditDescription ? appointmentEditDescription.value : "",
        assignee: appointmentEditAssignee ? appointmentEditAssignee.value : "",
        status: appointmentEditStatus ? appointmentEditStatus.value : "pending",
        source: "dashboard",
      };
      const validationError = validateAppointmentEditPayload(payload);
      if (validationError) {
        showAppointmentStatus(validationError, true);
        return;
      }
      openConfirm(t("dash.appt.confirm.save"), async function () {
        const js = await upsertAppointment(currentAppointmentEditItem.id, payload);
        if (!js || !js.ok) {
          showAppointmentStatus((js && js.error) || t("dash.appt.error.save"), true);
          return;
        }
        closeAppointmentEditModal();
        showAppointmentStatus(t("dash.appt.success.save"), false);
        await loadAppointmentsForCurrentMonth(false);
      });
    });
  }

  if (appointmentEditCancelBtn) {
    appointmentEditCancelBtn.addEventListener("click", function () {
      closeAppointmentEditModal();
    });
  }

  if (appointmentEditCloseBtn) {
    appointmentEditCloseBtn.addEventListener("click", function () {
      closeAppointmentEditModal();
    });
  }

  if (editCancelBtn) {
    editCancelBtn.addEventListener("click", function () {
      openConfirm(t("dash.confirm.cancel.edit"), function () {
        closeEditModal();
      });
    });
  }

  if (editCloseBtn) {
    editCloseBtn.addEventListener("click", function () {
      openConfirm(t("dash.confirm.cancel.edit"), function () {
        closeEditModal();
      });
    });
  }

  if (cccdEditConfirmBtn) {
    cccdEditConfirmBtn.addEventListener("click", function () {
      if (!currentCccdEditItem || !currentCccdEditItem.registration_id) return;
      openConfirm(t("dash.confirm.update.cccd"), async function () {
        const regId = currentCccdEditItem.registration_id;
        const payload = {
          full_name: cccdEditFullName ? cccdEditFullName.value : "",
          id_number: cccdEditIdNumber ? cccdEditIdNumber.value : "",
          gender: cccdEditGender ? cccdEditGender.value : "",
          dob: cccdEditDob ? cccdEditDob.value : "",
          address: cccdEditAddress ? cccdEditAddress.value : "",
          issued: cccdEditIssued ? cccdEditIssued.value : "",
          expiry: cccdEditExpiry ? cccdEditExpiry.value : "",
          old_id: cccdEditOldId ? cccdEditOldId.value : "",
        };
        const ok = await updateCccd(regId, payload);
        if (!ok) {
          alert(t("dash.error.update"));
          return;
        }
        closeCccdEditModal();
        await loadCccdDatabase(searchKeywords.cccd || "", cccdPagination.page);
        const detail = await loadCccdDetail(regId);
        if (detail) {
          renderCccdDetailPanel(detail, detail);
        }
      });
    });
  }

  if (cccdEditCancelBtn) {
    cccdEditCancelBtn.addEventListener("click", function () {
      openConfirm(t("dash.confirm.cancel.edit"), function () {
        closeCccdEditModal();
      });
    });
  }

  if (cccdEditCloseBtn) {
    cccdEditCloseBtn.addEventListener("click", function () {
      openConfirm(t("dash.confirm.cancel.edit"), function () {
        closeCccdEditModal();
      });
    });
  }

  if (exportConfirmBtn) {
    exportConfirmBtn.addEventListener("click", function () {
      const dateFrom = exportDateFrom ? exportDateFrom.value : "";
      const dateTo = exportDateTo ? exportDateTo.value : "";
      closeExportModal();
      openConfirm(
        t("dash.confirm.export"),
        function () {
          exportVisibleRows(currentExportFormat, dateFrom, dateTo);
        },
        function () {
          if (exportDateFrom) exportDateFrom.value = dateFrom;
          if (exportDateTo) exportDateTo.value = dateTo;
          openExportModal();
        }
      );
    });
  }

  if (exportCancelBtn) {
    exportCancelBtn.addEventListener("click", function () {
      const dateFrom = exportDateFrom ? exportDateFrom.value : "";
      const dateTo = exportDateTo ? exportDateTo.value : "";
      closeExportModal();
      openConfirm(
        t("dash.confirm.cancel.export"),
        function () {
          closeExportModal();
        },
        function () {
          if (exportDateFrom) exportDateFrom.value = dateFrom;
          if (exportDateTo) exportDateTo.value = dateTo;
          openExportModal();
        }
      );
    });
  }

  if (exportCloseBtn) {
    exportCloseBtn.addEventListener("click", function () {
      const dateFrom = exportDateFrom ? exportDateFrom.value : "";
      const dateTo = exportDateTo ? exportDateTo.value : "";
      closeExportModal();
      openConfirm(
        t("dash.confirm.cancel.export"),
        function () {
          closeExportModal();
        },
        function () {
          if (exportDateFrom) exportDateFrom.value = dateFrom;
          if (exportDateTo) exportDateTo.value = dateTo;
          openExportModal();
        }
      );
    });
  }

  if (confirmYesBtn) {
    confirmYesBtn.addEventListener("click", async function () {
      const cb = confirmCallback;
      closeConfirm();
      if (cb) await cb();
    });
  }

  if (confirmNoBtn) {
    confirmNoBtn.addEventListener("click", function () {
      const cb = confirmCancelCallback;
      closeConfirm();
      if (cb) cb();
    });
  }

  document.querySelectorAll("[data-modal-close]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      closeConfirm();
    });
  });

  if (editModal) {
    editModal.addEventListener("click", function (event) {
      if (event.target === editModal) {
        openConfirm(t("dash.confirm.cancel.edit"), function () {
          closeEditModal();
        });
      }
    });
  }

  if (cccdEditModal) {
    cccdEditModal.addEventListener("click", function (event) {
      if (event.target === cccdEditModal) {
        openConfirm(t("dash.confirm.cancel.edit"), function () {
          closeCccdEditModal();
        });
      }
    });
  }

  if (appointmentEditModal) {
    appointmentEditModal.addEventListener("click", function (event) {
      if (event.target === appointmentEditModal) {
        closeAppointmentEditModal();
      }
    });
  }

  if (appointmentFilterCloseBtn) {
    appointmentFilterCloseBtn.addEventListener("click", function () {
      closeAppointmentFilterModal();
    });
  }

  if (appointmentFilterModal) {
    appointmentFilterModal.addEventListener("click", function (event) {
      if (event.target === appointmentFilterModal) {
        closeAppointmentFilterModal();
      }
    });
  }

  if (appointmentDetailCloseBtn) {
    appointmentDetailCloseBtn.addEventListener("click", function () {
      closeAppointmentDetailModal();
    });
  }

  if (appointmentDetailDismissBtn) {
    appointmentDetailDismissBtn.addEventListener("click", function () {
      closeAppointmentDetailModal();
    });
  }

  if (appointmentDetailModal) {
    appointmentDetailModal.addEventListener("click", function (event) {
      if (event.target === appointmentDetailModal) {
        closeAppointmentDetailModal();
      }
    });
  }

  if (confirmModal) {
    confirmModal.addEventListener("click", function (event) {
      if (event.target === confirmModal) closeConfirm();
    });
  }

  if (exportModal) {
    exportModal.addEventListener("click", function (event) {
      if (event.target === exportModal) {
        const dateFrom = exportDateFrom ? exportDateFrom.value : "";
        const dateTo = exportDateTo ? exportDateTo.value : "";
        closeExportModal();
        openConfirm(
          t("dash.confirm.cancel.export"),
          function () {
            closeExportModal();
          },
          function () {
            if (exportDateFrom) exportDateFrom.value = dateFrom;
            if (exportDateTo) exportDateTo.value = dateTo;
            openExportModal();
          }
        );
      }
    });
  }

  if (databasePrevBtn) {
    databasePrevBtn.addEventListener("click", async function () {
      if (databasePagination.page <= 1) return;
      databasePagination.page -= 1;
      selectedRegistrationIds.clear();
      updateBulkSelectionUi();
      await loadDatabase(currentSearchKeyword, databasePagination.page);
    });
  }

  if (databaseNextBtn) {
    databaseNextBtn.addEventListener("click", async function () {
      if (databasePagination.page >= databasePagination.totalPages) return;
      databasePagination.page += 1;
      selectedRegistrationIds.clear();
      updateBulkSelectionUi();
      await loadDatabase(currentSearchKeyword, databasePagination.page);
    });
  }

  if (cccdPrevBtn) {
    cccdPrevBtn.addEventListener("click", async function () {
      if (cccdPagination.page <= 1) return;
      cccdPagination.page -= 1;
      selectedCccdIds.clear();
      updateCccdBulkSelectionUi();
      await loadCccdDatabase(searchKeywords.cccd || "", cccdPagination.page);
    });
  }

  if (cccdNextBtn) {
    cccdNextBtn.addEventListener("click", async function () {
      if (cccdPagination.page >= cccdPagination.totalPages) return;
      cccdPagination.page += 1;
      selectedCccdIds.clear();
      updateCccdBulkSelectionUi();
      await loadCccdDatabase(searchKeywords.cccd || "", cccdPagination.page);
    });
  }

  if (recentPrevBtn) {
    recentPrevBtn.addEventListener("click", async function () {
      if (recentPagination.page <= 1) return;
      recentPagination.page -= 1;
      await loadRecentActivity(recentPagination.page);
    });
  }

  if (recentNextBtn) {
    recentNextBtn.addEventListener("click", async function () {
      if (recentPagination.page >= recentPagination.totalPages) return;
      recentPagination.page += 1;
      await loadRecentActivity(recentPagination.page);
    });
  }

  setActiveScreen("database");
  bindLanguageSwitcher();
  currentSearchKeyword = searchKeywords.database || "";
  selectedAppointmentDate = getTodayKey();
  loadStats();
  loadNotifications();
  ensureScreenLoaded("database", { force: true });
  setTimeout(syncDetailPanelHeight, 100);
  setInterval(async () => {
    if (dashboardPollBusy) return;
    dashboardPollBusy = true;
    try {
      await Promise.all([
        loadStats(),
        loadNotifications(),
        refreshActiveScreen(),
      ]);
    } finally {
      dashboardPollBusy = false;
    }
  }, DASHBOARD_POLL_INTERVAL_MS);

  setInterval(function () {
    if (notificationItems.length) {
      renderNotifications(notificationItems);
    }
  }, 30000);
});
