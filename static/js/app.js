import { state } from './state.js';
import { 
    changeLanguage, 
    changeTheme, 
    switchSection, 
    toggleSidebar, 
    closeSidebar,
    toggleChannelsDropdown, 
    onChannelCheckboxChange, 
    onChannelColorChange, 
    toggleSelectAllChannels, 
    getSelectedChannels, 
    updateActiveChannelNameLabel, 
    renderChannelsMenu, 
    renderTable, 
    toggleSort, 
    debounceFilter, 
    resetFilters, 
    setDateRange, 
    toggleColumnsSelector, 
    updateColumns, 
    changePage, 
    changePerPage, 
    changeChartLimit,
    toggleExportDropdown,
    exportData, 
    openVideoModal, 
    closeVideoModal, 
    downloadVideoFromModal, 
    scrapeDetailsFromModal, 
    getTranscriptFromModal, 
    hideDownloadQualityPanel,
    startVideoDownload, 
    toggleViewsDropdown, 
    runViewsUpdate, 
    openAddChannelModal, 
    closeAddChannelModal, 
    setAddChannelMode, 
    setAddChannelPeriodPreset, 
    setAddChannelLimitPreset, 
    submitAddChannel,
    toggleChatDrawer,
    openChatDrawer,
    closeChatDrawer,
    summarizeCurrentScreen,
    exportCurrentScreenMd,
    exportChatMarkdown,
    clearChatAction,
    handleSendChatMessage,
    selectSingleChannel,
    changeChatProvider,
    switchAgentRole,
    initChatResizer,
    loadProposalInbox,
    updateProposalStatus,
    initProposalInbox,
    loadOperatorRuntimePanel,
    initOperatorRuntimePanel,
    loadWatchers,
    runWatchersNow,
    toggleWatcher,
    runDataMethodReview,
    generateMethodProposals,
    openAddSourceModal,
    closeAddSourceModal,
    submitAddSource,
    deleteSource,
    prepareIngestSource,
    runIngest,
    runIngestionPreview,
    runIngestionPersist,
    approveScrapingProposal,
    applyEntitlementsUI,
    applyRoleVisibility
} from './ui.js';
import {
    loadStats, 
    loadChannelStatsHeader, 
    loadChannels, 
    loadVideos, 
    triggerAction, 
    checkProcessStatus, 
    loadChartsData, 
    applyFilters,
    loadEntitlements
} from './api.js';
import { 
    initChartUI, 
    renderActiveChart, 
    selectChart, 
    selectPromoChart,
    formatChartValue,
    truncateChartTitle,
    renderModalViewsChart 
} from './charts.js';
import { 
    initTerminal, 
    connectTerminalStream, 
    sendTerminalInput, 
    sendTerminalResize, 
    injectCommand, 
    toggleDropdown 
} from './terminal.js';
import { initDashboardWorkspace } from './widgets.js';
import { loadBriefs, loadBriefSources, loadReviewQueue } from './briefs.js';

const DATE_SLIDER_FLOOR = "2022-02-24";
let dateSliderApplyTimer = null;

function dateToDay(value) {
    const parsed = Date.parse(`${value}T00:00:00Z`);
    if (Number.isNaN(parsed)) return null;
    return Math.floor(parsed / 86400000);
}

function dayToDate(day) {
    return new Date(day * 86400000).toISOString().split("T")[0];
}

function clearQuickDateSelection() {
    state.activeQuickDate = null;
    document.querySelectorAll(".quick-date-btn, .quick-date-btn-compact").forEach(btn => {
        btn.classList.remove("active");
    });
}

function updateDateRangeSliderLabels() {
    const startInput = document.getElementById("filter-start-date");
    const endInput = document.getElementById("filter-end-date");
    const startLabel = document.getElementById("date-range-start-label");
    const endLabel = document.getElementById("date-range-end-label");
    if (startLabel) startLabel.textContent = startInput?.value || "-";
    if (endLabel) endLabel.textContent = endInput?.value || "-";
}

export function syncDateRangeSliderFromInputs() {
    const startInput = document.getElementById("filter-start-date");
    const endInput = document.getElementById("filter-end-date");
    const startSlider = document.getElementById("date-range-start");
    const endSlider = document.getElementById("date-range-end");
    if (!startInput || !endInput || !startSlider || !endSlider) return;

    const todayDay = dateToDay(new Date().toISOString().split("T")[0]);
    const floorDay = dateToDay(DATE_SLIDER_FLOOR);
    const startDay = dateToDay(startInput.value) ?? floorDay;
    const endDay = dateToDay(endInput.value) ?? todayDay;
    const minDay = Math.min(floorDay, startDay, endDay);
    const maxDay = Math.max(todayDay, startDay, endDay);

    [startSlider, endSlider].forEach(slider => {
        slider.min = String(minDay);
        slider.max = String(maxDay);
        slider.step = "1";
    });
    startSlider.value = String(Math.min(startDay, endDay));
    endSlider.value = String(Math.max(startDay, endDay));
    updateDateRangeSliderLabels();
}

function applyDateRangeFromSlider(source) {
    const startInput = document.getElementById("filter-start-date");
    const endInput = document.getElementById("filter-end-date");
    const startSlider = document.getElementById("date-range-start");
    const endSlider = document.getElementById("date-range-end");
    if (!startInput || !endInput || !startSlider || !endSlider) return;

    let startDay = Number(startSlider.value);
    let endDay = Number(endSlider.value);
    if (startDay > endDay) {
        if (source === "end") {
            startDay = endDay;
            startSlider.value = String(startDay);
        } else {
            endDay = startDay;
            endSlider.value = String(endDay);
        }
    }

    startInput.value = dayToDate(startDay);
    endInput.value = dayToDate(endDay);
    clearQuickDateSelection();
    updateDateRangeSliderLabels();
}

function scheduleDateSliderApply() {
    clearTimeout(dateSliderApplyTimer);
    dateSliderApplyTimer = setTimeout(() => {
        applyFilters();
        window.dashboardWorkspace?.refreshAll();
    }, 250);
}

function initDateRangeSlider() {
    const startInput = document.getElementById("filter-start-date");
    const endInput = document.getElementById("filter-end-date");
    const startSlider = document.getElementById("date-range-start");
    const endSlider = document.getElementById("date-range-end");
    if (!startInput || !endInput || !startSlider || !endSlider) return;

    syncDateRangeSliderFromInputs();
    [startInput, endInput].forEach(input => {
        input.addEventListener("change", () => {
            clearQuickDateSelection();
            syncDateRangeSliderFromInputs();
            window.dashboardWorkspace?.refreshAll();
        });
    });
    startSlider.addEventListener("input", () => {
        applyDateRangeFromSlider("start");
        scheduleDateSliderApply();
    });
    endSlider.addEventListener("input", () => {
        applyDateRangeFromSlider("end");
        scheduleDateSliderApply();
    });
    startSlider.addEventListener("change", scheduleDateSliderApply);
    endSlider.addEventListener("change", scheduleDateSliderApply);
}

// Bind all functions to window to satisfy HTML inline event handlers
window.changeLanguage = changeLanguage;
window.changeTheme = changeTheme;
window.switchSection = switchSection;
window.toggleSidebar = toggleSidebar;
window.closeSidebar = closeSidebar;
window.toggleChannelsDropdown = toggleChannelsDropdown;
window.onChannelCheckboxChange = onChannelCheckboxChange;
window.onChannelColorChange = onChannelColorChange;
window.toggleSelectAllChannels = toggleSelectAllChannels;
window.getSelectedChannels = getSelectedChannels;
window.updateActiveChannelNameLabel = updateActiveChannelNameLabel;
window.renderChannelsMenu = renderChannelsMenu;
window.renderTable = renderTable;
window.toggleSort = toggleSort;
window.debounceFilter = debounceFilter;
window.resetFilters = resetFilters;
window.setDateRange = setDateRange;
window.toggleColumnsSelector = toggleColumnsSelector;
window.updateColumns = updateColumns;
window.changePage = changePage;
window.changePerPage = changePerPage;
window.changeChartLimit = changeChartLimit;
window.toggleExportDropdown = toggleExportDropdown;
window.exportData = exportData;
window.openVideoModal = openVideoModal;
window.closeVideoModal = closeVideoModal;
window.downloadVideoFromModal = downloadVideoFromModal;
window.scrapeDetailsFromModal = scrapeDetailsFromModal;
window.getTranscriptFromModal = getTranscriptFromModal;
window.hideDownloadQualityPanel = hideDownloadQualityPanel;
window.startVideoDownload = startVideoDownload;
window.toggleViewsDropdown = toggleViewsDropdown;
window.runViewsUpdate = runViewsUpdate;
window.openAddChannelModal = openAddChannelModal;
window.closeAddChannelModal = closeAddChannelModal;
window.setAddChannelMode = setAddChannelMode;
window.setAddChannelPeriodPreset = setAddChannelPeriodPreset;
window.setAddChannelLimitPreset = setAddChannelLimitPreset;
window.submitAddChannel = submitAddChannel;
window.toggleChatDrawer = toggleChatDrawer;
window.openChatDrawer = openChatDrawer;
window.closeChatDrawer = closeChatDrawer;
window.summarizeCurrentScreen = summarizeCurrentScreen;
window.exportCurrentScreenMd = exportCurrentScreenMd;
window.exportChatMarkdown = exportChatMarkdown;
window.clearChatAction = clearChatAction;
window.handleSendChatMessage = handleSendChatMessage;
window.selectSingleChannel = selectSingleChannel;
window.changeChatProvider = changeChatProvider;
window.switchAgentRole = switchAgentRole;
window.initChatResizer = initChatResizer;
window.loadProposalInbox = loadProposalInbox;
window.updateProposalStatus = updateProposalStatus;
window.initProposalInbox = initProposalInbox;
window.loadOperatorRuntimePanel = loadOperatorRuntimePanel;
window.initOperatorRuntimePanel = initOperatorRuntimePanel;
window.loadWatchers = loadWatchers;
window.runWatchersNow = runWatchersNow;
window.toggleWatcher = toggleWatcher;
window.loadReviewQueue = loadReviewQueue;
window.runDataMethodReview = runDataMethodReview;
window.generateMethodProposals = generateMethodProposals;
window.openAddSourceModal = openAddSourceModal;
window.closeAddSourceModal = closeAddSourceModal;
window.submitAddSource = submitAddSource;
window.deleteSource = deleteSource;
window.prepareIngestSource = prepareIngestSource;
window.runIngest = runIngest;
window.runIngestionPreview = runIngestionPreview;
window.runIngestionPersist = runIngestionPersist;
window.approveScrapingProposal = approveScrapingProposal;
window.applyRoleVisibility = applyRoleVisibility;
window.syncDateRangeSliderFromInputs = syncDateRangeSliderFromInputs;

window.loadStats = loadStats;
window.loadChannelStatsHeader = loadChannelStatsHeader;
window.loadChannels = loadChannels;
window.loadVideos = loadVideos;
window.triggerAction = triggerAction;
window.checkProcessStatus = checkProcessStatus;
window.loadChartsData = loadChartsData;
window.applyFilters = applyFilters;

window.initChartUI = initChartUI;
window.renderActiveChart = renderActiveChart;
window.selectChart = selectChart;
window.selectPromoChart = selectPromoChart;
window.formatChartValue = formatChartValue;
window.truncateChartTitle = truncateChartTitle;
window.renderModalViewsChart = renderModalViewsChart;

window.initTerminal = initTerminal;
window.connectTerminalStream = connectTerminalStream;
window.sendTerminalInput = sendTerminalInput;
window.sendTerminalResize = sendTerminalResize;
window.injectCommand = injectCommand;
window.toggleDropdown = toggleDropdown;

function syncTopBarHeight() {
    const topBar = document.querySelector(".top-bar");
    if (!topBar) return;

    const updateHeight = () => {
        document.documentElement.style.setProperty("--top-bar-height", `${topBar.offsetHeight}px`);
    };

    updateHeight();
    window.addEventListener("resize", updateHeight);
    if (window.ResizeObserver) {
        const observer = new ResizeObserver(updateHeight);
        observer.observe(topBar);
        window.topBarResizeObserver = observer;
    }
}

// Initial Startup
document.addEventListener("DOMContentLoaded", async () => {
    syncTopBarHeight();

    // Apply saved configurations
    document.getElementById("lang-selector").value = state.currentLang;
    document.getElementById("theme-selector").value = state.currentTheme;
    changeTheme(state.currentTheme);
    changeLanguage(state.currentLang);
    
    // Force sidebar collapsed by default on startup so the workspace never shifts or starts covered.
    closeSidebar();
    
    // Build chart buttons/dropdown from CHART_DEFS
    initChartUI();
    
    // Synchronize chart limit dropdown value
    const chartLimitSelector = document.getElementById("chart-limit-selector");
    if (chartLimitSelector) {
        chartLimitSelector.value = state.chartLimit;
    }
    
    // Synchronize per-page selector dropdown value
    const perPageSelector = document.getElementById("per-page-selector");
    if (perPageSelector) {
        perPageSelector.value = state.pagination.per_page;
    }
    
    // Switch to initial tab content
    switchSection("analytics-tab", document.getElementById("menu-item-analytics")?.querySelector("a"));
    
    // Set default date range to 6 months
    const now = new Date();
    const startDate = new Date();
    startDate.setMonth(now.getMonth() - 6);
    const fmt = (d) => d.toISOString().split('T')[0];
    document.getElementById("filter-start-date").value = fmt(startDate);
    document.getElementById("filter-end-date").value = fmt(now);
    initDateRangeSlider();
    
    // Highlight active quick-date button for 6m
    state.activeQuickDate = "6m";
    const activeBtn = document.getElementById("qd-6m");
    if (activeBtn) activeBtn.classList.add("active");

    // Load initial data
    loadStats();
    await loadEntitlements();
    applyEntitlementsUI();
    applyRoleVisibility();
    await loadChannels();   // will trigger loadChannelStatsHeader, loadChartsData, and loadVideos
    initDashboardWorkspace();
    loadBriefs();
    loadBriefSources();
    loadReviewQueue();
    
    // Start polling status
    checkProcessStatus();
    state.statusPollingInterval = setInterval(checkProcessStatus, 2000);
    
    // Initialize chat resizer
    initChatResizer();
    initProposalInbox();

    // Register chat input key listener
    const chatInput = document.getElementById("chat-input");
    if (chatInput) {
        chatInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSendChatMessage();
            }
        });
    }
    
    // Click outside to close custom elements
    document.addEventListener("click", (e) => {
        // Close sidebar on click outside
        if (!document.body.classList.contains("sidebar-collapsed")) {
            const sidebar = document.getElementById("sidebar");
            const isClickInsideSidebar = sidebar && sidebar.contains(e.target);
            const isClickOnToggle = e.target.closest('.sidebar-brand-toggle') || e.target.closest('.top-bar-menu-toggle');
            if (!isClickInsideSidebar && !isClickOnToggle) {
                closeSidebar();
            }
        }

        // channels dropdown
        const channelsBtn = document.getElementById("channels-dropdown-btn");
        const channelsMenu = document.getElementById("channels-dropdown-menu");
        if (channelsMenu && channelsBtn && !channelsBtn.contains(e.target) && !channelsMenu.contains(e.target)) {
            channelsMenu.style.display = "none";
        }
        
        // views dropdown
        const viewsBtn = document.getElementById("btn-run-views-update");
        const viewsMenu = document.getElementById("views-update-menu");
        if (viewsMenu && viewsBtn && !viewsBtn.contains(e.target) && !viewsMenu.contains(e.target)) {
            viewsMenu.style.display = "none";
        }
        
        // export dropdown
        const exportBtn = document.getElementById("btn-run-export");
        const exportMenu = document.getElementById("export-menu");
        if (exportMenu && exportBtn && !exportBtn.contains(e.target) && !exportMenu.contains(e.target)) {
            exportMenu.style.display = "none";
        }
    });
});
