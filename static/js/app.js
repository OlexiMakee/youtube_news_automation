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
    exportCSV, 
    openVideoModal, 
    closeVideoModal, 
    downloadVideoFromModal, 
    scrapeDetailsFromModal, 
    toggleViewsDropdown, 
    runViewsUpdate, 
    openAddChannelModal, 
    closeAddChannelModal, 
    setAddChannelMode, 
    setAddChannelPeriodPreset, 
    setAddChannelLimitPreset, 
    submitAddChannel,
    toggleChatDrawer,
    handleSendChatMessage
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
    getChartTextRows,
    renderChartCopyLayer,
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
window.exportCSV = exportCSV;
window.openVideoModal = openVideoModal;
window.closeVideoModal = closeVideoModal;
window.downloadVideoFromModal = downloadVideoFromModal;
window.scrapeDetailsFromModal = scrapeDetailsFromModal;
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
window.getChartTextRows = getChartTextRows;
window.renderChartCopyLayer = renderChartCopyLayer;
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
    
    // Build chart buttons/dropdown from CHART_DEFS
    initChartUI();
    
    // Switch to initial tab content
    switchSection("analytics-tab", document.getElementById("menu-item-analytics").querySelector("a"));
    
    // Set default date range to today
    const todayStr = new Date().toISOString().split("T")[0];
    document.getElementById("filter-start-date").value = todayStr;
    document.getElementById("filter-end-date").value = todayStr;

    // Load initial data
    loadStats();
    loadChannels();   // will trigger loadChannelStatsHeader, loadChartsData, and loadVideos
    
    // Start polling status
    checkProcessStatus();
    state.statusPollingInterval = setInterval(checkProcessStatus, 2000);
    
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
});
