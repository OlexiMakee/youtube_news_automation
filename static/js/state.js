// Global App State for Governed Autonomous Intelligence Workspace
export const state = {
    currentLang: localStorage.getItem("app_lang") || "ua",
    currentTheme: localStorage.getItem("app_theme") || "light",
    currentSection: "analytics-tab",
    activeChartInstance: null,
    chartRawData: null,
    activeChartType: 'top_viewed',
    activeWorkspaceView: 'chart', // chart | timeline | table
    chartLimit: parseInt(localStorage.getItem("chart_limit")) || 50,

    // Video Details Modal State
    activeModalChartInstance: null,
    activeModalVideoId: null,

    // Channels selection & color customization
    channelColors: JSON.parse(localStorage.getItem("channel_colors")) || {},
    selectedChannelIds: JSON.parse(localStorage.getItem("selected_channels")) || [],

    // Pagination and Filters State
    pagination: {
        page: 1,
        per_page: 50,
        total_pages: 1,
        total_records: 0
    },

    // Sorting State
    sortCol: "published_at",
    sortDir: "desc",
    activeQuickDate: null,

    activeColumns: ["video_id", "title", "channel_name", "published_at", "view_count", "like_count", "comment_count"],
    searchDebounceTimer: null,
    statusPollingInterval: null,
    lastKnownStatus: "idle",

    // Terminal state
    term: null,
    fitAddon: null,
    termEventSource: null,
    termInitialized: false,

    // Loaded channels list
    allChannels: [],
    
    // AI Chat config
    agentRole: "admin",
    agentProvider: localStorage.getItem("ui_chat_provider") || "gemini",

    // Basic role visibility state. Backend authorization remains authoritative.
    authStatus: null,
    userRole: "reader",

    // Progressive Entitlements state
    entitlements: {
        ready_workspace: true,
        dense_workspace: true,
        linked_intelligence: false,
        operator_runtime: false,
        autonomous_watchers: false
    }
};

export const DEFAULT_COLORS = ["#008abb", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#3b82f6", "#ef4444", "#14b8a6", "#f97316"];
