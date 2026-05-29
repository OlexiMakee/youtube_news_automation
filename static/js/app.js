import { state } from './state.js';
import { 
    changeLanguage, 
    changeTheme, 
    switchSection, 
    toggleSidebar, 
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
    handleSendChatMessage,
    selectSingleChannel,
    changeChatProvider,
    switchAgentRole,
    initChatResizer
} from './ui.js';
import { 
    loadStats, 
    loadChannelStatsHeader, 
    loadChannels, 
    loadVideos, 
    triggerAction, 
    checkProcessStatus, 
    loadChartsData, 
    applyFilters 
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

// Bind all functions to window to satisfy HTML inline event handlers
window.changeLanguage = changeLanguage;
window.changeTheme = changeTheme;
window.switchSection = switchSection;
window.toggleSidebar = toggleSidebar;
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
window.handleSendChatMessage = handleSendChatMessage;
window.selectSingleChannel = selectSingleChannel;
window.changeChatProvider = changeChatProvider;
window.switchAgentRole = switchAgentRole;
window.initChatResizer = initChatResizer;

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

// Initial Startup
document.addEventListener("DOMContentLoaded", () => {
    // Apply saved configurations
    document.getElementById("lang-selector").value = state.currentLang;
    document.getElementById("theme-selector").value = state.currentTheme;
    changeTheme(state.currentTheme);
    changeLanguage(state.currentLang);
    
    // Sidebar is always collapsed by default — user must manually expand
    document.body.classList.add("sidebar-collapsed");
    localStorage.removeItem("sidebar_collapsed");
    
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
    switchSection("analytics-tab", document.getElementById("menu-item-analytics").querySelector("a"));
    
    // Set default date range to 6 months
    const now = new Date();
    const startDate = new Date();
    startDate.setMonth(now.getMonth() - 6);
    const fmt = (d) => d.toISOString().split('T')[0];
    document.getElementById("filter-start-date").value = fmt(startDate);
    document.getElementById("filter-end-date").value = fmt(now);
    
    // Highlight active quick-date button for 6m
    state.activeQuickDate = "6m";
    const activeBtn = document.getElementById("qd-6m");
    if (activeBtn) activeBtn.classList.add("active");

    // Load initial data
    loadStats();
    loadChannels();   // will trigger loadChannelStatsHeader, loadChartsData, and loadVideos
    
    // Start polling status
    checkProcessStatus();
    state.statusPollingInterval = setInterval(checkProcessStatus, 2000);
    
    // Initialize chat resizer
    initChatResizer();

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
    
    // Click outside to close custom dropdowns
    document.addEventListener("click", (e) => {
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
