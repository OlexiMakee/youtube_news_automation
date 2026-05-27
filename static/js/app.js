// Translations dictionary
const translations = {
    ua: {
        menu_dashboard: "Дані та Аналітика",
        menu_operations: "Операції",
        header_title: "Панель автоматизації новин",
        theme_light: "Світла (Біла)",
        theme_sepia: "Світла (Сепія)",
        theme_dark_black: "Темна (Чорна)",
        theme_dark_blue: "Темна (Синя)",
        card_local_db: "Локальна БД (SQLite)",
        card_sync_status: "Черга синхронізації",
        card_cloud_db: "Хмарна БД (Neon)",
        card_cloud_config: "З'єднання з Neon",
        stat_channels: "Каналів",
        stat_recent: "Нові (Delta)",
        stat_ignored: "Архівні",
        title_database_explorer: "Перегляд бази даних",
        placeholder_search: "Шукати заголовок чи опис...",
        filter_all_channels: "Оберіть канал для аналітики...",
        btn_reset: "Скинути",
        btn_choose_columns: "Вибрати колонки",
        pag_showing: "Сторінка",
        title_process_control: "Операції та процеси",
        status_idle: "Очікування",
        status_scraping: "СКРАПІНГ",
        status_syncing: "СИНХРОНІЗАЦІЯ",
        status_updating: "ОНОВЛЕННЯ",
        status_updating_views: "ОНОВЛЕННЯ ПЕРГЛЯДІВ",
        btn_run_scraper: "Запустити скрапер",
        btn_run_sync: "Запустити синхронізацію",
        btn_update_db: "Оновити БД",
        btn_update_views: "Оновити перегляди",
        console_output: "Лог виконання процесу",
        chart_uploads_month: "Завантаження по місяцях",
        chart_duration_dist: "Розподіл за тривалістю відео",
        chart_top_viewed: "Топ-100 за переглядами",
        chart_worst_viewed: "Найгірші 100 за переглядами",
        chart_top_liked: "Топ-100 за лайками",
        chart_worst_liked: "Найгірші 100 за лайками",
        chart_top_commented: "Топ-100 за коментарями",
        chart_worst_commented: "Найгірші 100 за коментарями",
        chart_top_hashtags: "Топ-100 хештегів за переглядами",
        chart_top_description_words: "Топ-100 слів в описах за переглядами",
        title_visualizations: "Візуалізація каналу",
        lbl_rows_per_page: "Рядків на сторінку:",
        btn_export_csv: "Експорт CSV",
        kpi_total_views: "Всього переглядів",
        kpi_median_views: "Медіана переглядів",
        kpi_like_ratio: "Лайки / Перегляди",
        kpi_comment_ratio: "Коментарі / Перегляди",
        chart_best_day_to_post: "Активність по днях тижня",
        chart_duration_vs_views: "Тривалість vs Перегляди",
        chart_views_distribution: "Розподіл за переглядами",
        chart_best_promo_words: "Найкращі слова для просування",
        chart_worst_promo_words: "Найгірші слова для просування",
        chart_best_promo_tags: "Найкращі теги для просування",
        chart_worst_promo_tags: "Найгірші теги для просування",
        chart_placeholder: "-- Оберіть графік --",
        qd_1d: "1 доба",
        qd_1w: "1 Тиждень",
        qd_1m: "1 Місяць",
        qd_3m: "3 Місяці",
        qd_6m: "6 Місяців",
        qd_1y: "1 Рік",
        qd_2y: "2 Роки",
        qd_3y: "3 Роки",
        qd_4y: "4 Роки",
        qd_5y: "5 Років",
        qd_war: "🇺🇦 З 24.02.2022",
        
        // Modal & Views Update translations (UA)
        modal_watch_yt: "Дивитись на YouTube",
        modal_download_mp4: "Завантажити MP4",
        modal_downloading: "Завантаження...",
        modal_scrape_details: "Зібрати деталі",
        modal_scraping: "Збирання...",
        modal_description: "Опис відео",
        modal_views_trend: "Динаміка росту переглядів",
        chart_worst_sub: "Найгірші",
        chart_best_sub: "Найкращі",
        views_1w: "1 Тиждень (Швидко)",
        views_1m: "1 Місяць (Повільно)",
        views_3m: "3 Місяці (Повільно)",
        views_6m: "6 Місяців (Повільно)",
        views_1y: "1 Рік+ (Дуже повільно)",
        btn_updating_views: "Оновлення...",
        lbl_from: "Від",
        lbl_to: "До",
        
        // Channel Selector dropdown & modals
        dropdown_choose_channels: "Оберіть канали",
        dropdown_select_all: "Всі",
        dropdown_deselect_all: "Очистити",
        dropdown_add_channel: "Додати",
        modal_add_channel_title: "Додати новий канал",
        lbl_channel_url: "Введіть назву або URL каналу",
        lbl_scraping_mode: "Режим збору даних",
        btn_apply: "Застосувати"
    },
    en: {
        menu_dashboard: "Data & Analytics",
        menu_operations: "Operations",
        header_title: "News Research Automation Dashboard",
        theme_light: "Light (White)",
        theme_sepia: "Light (Sepia)",
        theme_dark_black: "Dark (Black)",
        theme_dark_blue: "Dark (Blue)",
        card_local_db: "Local DB (SQLite)",
        card_sync_status: "Sync Queue",
        card_cloud_db: "Cloud DB (Neon)",
        card_cloud_config: "Neon Connection",
        stat_channels: "Channels",
        stat_recent: "Recent (Delta)",
        stat_ignored: "Archived",
        title_database_explorer: "Database Explorer",
        placeholder_search: "Search title or description...",
        filter_all_channels: "Select a channel for analysis...",
        btn_reset: "Reset",
        btn_choose_columns: "Select Columns",
        pag_showing: "Showing page",
        title_process_control: "Operations & Controls",
        status_idle: "IDLE",
        status_scraping: "SCRAPING",
        status_syncing: "SYNCING",
        status_updating: "UPDATING",
        status_updating_views: "UPDATING VIEWS",
        btn_run_scraper: "Run Scraper",
        btn_run_sync: "Run Sync",
        btn_update_db: "Update DB",
        btn_update_views: "Update Views",
        console_output: "Live Process Console",
        chart_uploads_month: "Uploads By Month",
        chart_duration_dist: "Duration Distribution",
        chart_top_viewed: "Top 100 Viewed",
        chart_worst_viewed: "Worst 100 Viewed",
        chart_top_liked: "Top 100 Liked",
        chart_worst_liked: "Worst 100 Liked",
        chart_top_commented: "Top 100 Commented",
        chart_worst_commented: "Worst 100 Commented",
        chart_top_hashtags: "Top 100 Hashtags by Views",
        chart_top_description_words: "Top 100 Words in Descriptions by Views",
        title_visualizations: "Channel Visualizations",
        lbl_rows_per_page: "Rows per page:",
        btn_export_csv: "Export CSV",
        kpi_total_views: "Total Views",
        kpi_median_views: "Median Views",
        kpi_like_ratio: "Avg Like Ratio",
        kpi_comment_ratio: "Avg Comment Ratio",
        chart_best_day_to_post: "Best Day to Post",
        chart_duration_vs_views: "Duration vs Views (Scatter)",
        chart_views_distribution: "Views Distribution",
        chart_best_promo_words: "Best Words for Promotion",
        chart_worst_promo_words: "Worst Words for Promotion",
        chart_best_promo_tags: "Best Tags for Promotion",
        chart_worst_promo_tags: "Worst Tags for Promotion",
        chart_placeholder: "-- Select Chart --",
        qd_1d: "1 Day",
        qd_1w: "1 Week",
        qd_1m: "1 Month",
        qd_3m: "3 Months",
        qd_6m: "6 Months",
        qd_1y: "1 Year",
        qd_2y: "2 Years",
        qd_3y: "3 Years",
        qd_4y: "4 Years",
        qd_5y: "5 Years",
        qd_war: "🇺🇦 Since 24.02.2022",
        
        // Modal & Views Update translations (EN)
        modal_watch_yt: "Watch on YouTube",
        modal_download_mp4: "Download MP4",
        modal_downloading: "Downloading...",
        modal_scrape_details: "Scrape Details",
        modal_scraping: "Scraping...",
        modal_description: "Video Description",
        modal_views_trend: "Views Growth Trend",
        chart_worst_sub: "Worst",
        chart_best_sub: "Best",
        views_1w: "1 Week (Fast)",
        views_1m: "1 Month (Slow)",
        views_3m: "3 Months (Slow)",
        views_6m: "6 Months (Slow)",
        views_1y: "1 Year+ (Very Slow)",
        btn_updating_views: "Updating...",
        lbl_from: "From",
        lbl_to: "To",
        
        // Channel Selector dropdown & modals
        dropdown_choose_channels: "Select Channels",
        dropdown_select_all: "All",
        dropdown_deselect_all: "Clear",
        dropdown_add_channel: "Add",
        modal_add_channel_title: "Add New Channel",
        lbl_channel_url: "Enter channel name or URL",
        lbl_scraping_mode: "Scraping Mode",
        btn_apply: "Apply"
    }
};

// ─────────────────────────────────────────────────────────────────────
// CHART REGISTRY WITH DYNAMIC SPLIT BUTTON GROUPS
// ─────────────────────────────────────────────────────────────────────
const CHART_DEFS = [
    // Group 1: Stats split-buttons (video metrics)
    { id: 'top_viewed',         group: 'stats', pair: 'left',  pairId: 'worst_viewed',    icon: '👁', labelKey: 'chart_top_viewed' },
    { id: 'worst_viewed',       group: 'stats', pair: 'right', pairId: 'top_viewed',      icon: '📉', labelKey: 'chart_worst_sub' },
    
    { id: 'top_liked',          group: 'stats', pair: 'left',  pairId: 'worst_liked',     icon: '👍', labelKey: 'chart_top_liked' },
    { id: 'worst_liked',        group: 'stats', pair: 'right', pairId: 'top_liked',       icon: '📉', labelKey: 'chart_worst_sub' },
    
    { id: 'top_commented',      group: 'stats', pair: 'left',  pairId: 'worst_commented',   icon: '💬', labelKey: 'chart_top_commented' },
    { id: 'worst_commented',    group: 'stats', pair: 'right', pairId: 'top_commented',     icon: '📉', labelKey: 'chart_worst_sub' },
    
    // Group 2: Promo split-buttons (text analytics)
    { id: 'best_promo_words',   group: 'promo', pair: 'left',  pairId: 'worst_promo_words', icon: '🚀', labelKey: 'chart_best_promo_words' },
    { id: 'worst_promo_words',  group: 'promo', pair: 'right', pairId: 'best_promo_words',  icon: '📉', labelKey: 'chart_worst_sub' },
    
    { id: 'best_promo_tags',    group: 'promo', pair: 'left',  pairId: 'worst_promo_tags',  icon: '🚀', labelKey: 'chart_best_promo_tags' },
    { id: 'worst_promo_tags',   group: 'promo', pair: 'right', pairId: 'best_promo_tags',   icon: '📉', labelKey: 'chart_worst_sub' },
    
    // Group 3: Other analytical buttons (formerly in dropdown)
    { id: 'duration_dist',      group: 'other', icon: '📊', labelKey: 'chart_duration_dist' },
    { id: 'best_day_to_post',   group: 'other', icon: '📅', labelKey: 'chart_best_day_to_post' },
    { id: 'duration_vs_views',  group: 'other', icon: '📈', labelKey: 'chart_duration_vs_views' },
    { id: 'views_distribution', group: 'other', icon: '🍩', labelKey: 'chart_views_distribution' }
];

// Global App State
let currentLang = localStorage.getItem("app_lang") || "ua";
let currentTheme = localStorage.getItem("app_theme") || "light";
let currentSection = "analytics-tab";
let activeChartInstance = null;
let chartRawData = null;
let activeChartType = 'top_viewed';   // currently displayed chart — persists across date changes

// Video Details Modal State
let activeModalChartInstance = null;
let activeModalVideoId = null;

// Channels selection & color customization
const DEFAULT_COLORS = ["#008abb", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#3b82f6", "#ef4444", "#14b8a6", "#f97316"];
let channelColors = JSON.parse(localStorage.getItem("channel_colors")) || {};
let selectedChannelIds = JSON.parse(localStorage.getItem("selected_channels")) || [];

// Pagination and Filters State
let pagination = {
    page: 1,
    per_page: 25,
    total_pages: 1,
    total_records: 0
};

// Sorting State
let sortCol = "published_at";
let sortDir = "desc";
let activeQuickDate = null;

let activeColumns = ["video_id", "title", "channel_name", "published_at", "view_count", "like_count", "comment_count"];
let searchDebounceTimer = null;
let statusPollingInterval = null;
let lastKnownStatus = "idle";

// On Page Load
document.addEventListener("DOMContentLoaded", () => {
    // Apply saved configurations
    document.getElementById("lang-selector").value = currentLang;
    document.getElementById("theme-selector").value = currentTheme;
    changeTheme(currentTheme);
    changeLanguage(currentLang);
    
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
    statusPollingInterval = setInterval(checkProcessStatus, 2000);
});

// LANGUAGE MANAGER
function changeLanguage(lang) {
    currentLang = lang;
    localStorage.setItem("app_lang", lang);
    
    // Translate elements with data-i18n attribute
    document.querySelectorAll("[data-i18n]").forEach(elem => {
        const key = elem.getAttribute("data-i18n");
        if (translations[lang] && translations[lang][key]) {
            elem.innerText = translations[lang][key];
        }
    });
    
    // Translate placeholders
    document.querySelectorAll("[data-i18n-placeholder]").forEach(elem => {
        const key = elem.getAttribute("data-i18n-placeholder");
        if (translations[lang] && translations[lang][key]) {
            elem.setAttribute("placeholder", translations[lang][key]);
        }
    });
    
    // Update active labels
    updateActiveChannelNameLabel();
    
    // Rebuild chart buttons/options with new language labels
    initChartUI();
    
    // Re-render active chart with new language labels
    if (chartRawData) {
        renderActiveChart();
    }
}

// THEME MANAGER
function changeTheme(theme) {
    currentTheme = theme;
    localStorage.setItem("app_theme", theme);
    document.documentElement.setAttribute("data-theme", theme);
    
    // Redraw charts with theme-specific font colors if necessary
    if (chartRawData) {
        renderActiveChart();
    }
}

// SECTION TOGGLER (For real tab switching)
function switchSection(tabId, element) {
    document.querySelectorAll(".sidebar-menu-item").forEach(item => {
        item.classList.remove("active");
    });
    
    if (element) {
        element.parentElement.classList.add("active");
    }
    
    // Hide all tab contents
    document.querySelectorAll(".tab-content").forEach(tab => {
        tab.classList.remove("active");
    });
    
    // Toggle filter bar visibility in the sticky header based on section
    const topFilterBar = document.getElementById("top-filter-bar");
    if (topFilterBar) {
        if (tabId === "analytics-tab") {
            topFilterBar.classList.remove("hide-filters");
        } else {
            topFilterBar.classList.add("hide-filters");
        }
    }
    
    // Show active tab content
    if (tabId === "analytics-tab") {
        document.getElementById("section-data-analytics").classList.add("active");
    } else if (tabId === "operations-tab") {
        document.getElementById("section-operations").classList.add("active");
    }
    
    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        document.getElementById("sidebar").classList.remove("open");
    }
}

function toggleSidebar() {
    document.getElementById("sidebar").classList.toggle("open");
}

// API CALL: FETCH DATABASE STATS
async function loadStats() {
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();
        
        // SQLite Stats
        document.getElementById("sqlite-total-videos").innerText = data.sqlite.total_videos.toLocaleString();
        document.getElementById("sqlite-total-channels").innerText = data.sqlite.total_channels;
        document.getElementById("sqlite-unsynced-videos").innerText = data.sqlite.unsynced_videos_count.toLocaleString();
        
        const recentUnsynced = data.sqlite.recent_unsynced || 0;
        const histUnsynced = data.sqlite.historical_unsynced || 0;
        document.getElementById("sqlite-recent-unsynced").innerText = recentUnsynced.toLocaleString();
        document.getElementById("sqlite-historical-unsynced").innerText = histUnsynced.toLocaleString();
        
        // Neon Cloud Stats
        if (data.postgres.is_configured) {
            document.getElementById("neon-connection-status").innerText = data.postgres.connected ? "CONNECTED" : "DISCONNECTED";
            document.getElementById("neon-connection-status").style.color = data.postgres.connected ? "var(--teal-color)" : "var(--danger-color)";
            document.getElementById("neon-total-videos").innerText = data.postgres.connected ? data.postgres.total_videos.toLocaleString() : "N/A";
            document.getElementById("neon-total-channels").innerText = data.postgres.connected ? data.postgres.total_channels : "N/A";
            document.getElementById("neon-status-msg").innerText = data.postgres.status_message;
        } else {
            document.getElementById("neon-connection-status").innerText = "NOT CONFIG";
            document.getElementById("neon-connection-status").style.color = "var(--text-muted)";
            document.getElementById("neon-total-videos").innerText = "N/A";
            document.getElementById("neon-total-channels").innerText = "N/A";
            document.getElementById("neon-status-msg").innerText = translations[currentLang].card_cloud_config + " is empty in .env";
        }
        
    } catch (err) {
        console.error("Failed to load statistics:", err);
    }
}

async function loadChannelStatsHeader() {
    const headerCard = document.getElementById("channel-header-card");
    if (!headerCard) return;
    
    const selected = getSelectedChannels();
    const startDate = document.getElementById("filter-start-date").value;
    const endDate = document.getElementById("filter-end-date").value;
    
    const params = new URLSearchParams({
        channel_ids: selected.join(','),
        start_date: startDate,
        end_date: endDate
    });
    
    try {
        const res = await fetch(`/api/channel/stats?${params.toString()}`);
        const data = await res.json();
        
        if (data.error) {
            headerCard.innerHTML = `<div class="card" style="padding:15px; text-align:center; color:var(--danger-color);">${data.error}</div>`;
            return;
        }
        
        if (data.mode === "single") {
            const subscribersStr = data.subscribers !== null ? data.subscribers.toLocaleString() : "-";
            const videoCountStr = data.db_video_count !== null ? data.db_video_count.toLocaleString() : "0";
            const totalViewsStr = data.db_total_views !== null ? data.db_total_views.toLocaleString() : "0";
            const medianViewsStr = data.db_median_views !== null ? data.db_median_views.toLocaleString() : "0";
            
            // Set cover banner
            const bannerStyle = data.banner_url 
                ? `background-image: url('${data.banner_url}');` 
                : `background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);`;
                
            const avatarUrl = data.avatar_url || 'https://www.gstatic.com/youtube/src/web/image/presentation/loading.gif';
            const handleText = data.channel_handle ? `@${data.channel_handle}` : '';
            const desc = data.description || '';
            
            headerCard.innerHTML = `
                <div class="channel-premium-header">
                    <div class="channel-banner-bg" style="${bannerStyle}"></div>
                    <div class="channel-profile-info">
                        <div class="channel-avatar-wrapper">
                            <img src="${avatarUrl}" alt="Avatar" onerror="this.src='https://www.youtube.com/img/desktop/yt_1200_share.png'">
                        </div>
                        <div class="channel-meta-text">
                            <div class="channel-name-title">
                                <span>${data.channel_name}</span>
                            </div>
                            <div class="channel-handle-sub">${handleText}</div>
                            <div class="channel-desc-sub" title="${desc.replace(/"/g, '&quot;')}">${desc}</div>
                        </div>
                        <div class="channel-header-stats">
                            <div class="header-stat-badge">
                                <span class="header-stat-num">${subscribersStr}</span>
                                <span class="header-stat-lbl">${currentLang === 'ua' ? 'Підписників' : 'Subscribers'}</span>
                            </div>
                            <div class="header-stat-badge">
                                <span class="header-stat-num">${videoCountStr}</span>
                                <span class="header-stat-lbl">${currentLang === 'ua' ? 'Відео в БД' : 'Videos in DB'}</span>
                            </div>
                            <div class="header-stat-badge">
                                <span class="header-stat-num">${totalViewsStr}</span>
                                <span class="header-stat-lbl">${currentLang === 'ua' ? 'Переглядів' : 'Views'}</span>
                            </div>
                            <div class="header-stat-badge">
                                <span class="header-stat-num">${medianViewsStr}</span>
                                <span class="header-stat-lbl">${currentLang === 'ua' ? 'Медіана' : 'Median'}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            // mode is combined
            const channelCount = data.channel_count || 0;
            const videoCountStr = data.db_video_count !== null ? data.db_video_count.toLocaleString() : "0";
            const totalViewsStr = data.db_total_views !== null ? data.db_total_views.toLocaleString() : "0";
            const medianViewsStr = data.db_median_views !== null ? data.db_median_views.toLocaleString() : "0";
            
            headerCard.innerHTML = `
                <div class="combined-premium-banner">
                    <div class="combined-banner-title">
                        <i class="fa-solid fa-layer-group"></i>
                        <div class="combined-title-text">
                            <div class="combined-title-main">${currentLang === 'ua' ? 'Об\'єднана аналітика бази даних' : 'Consolidated Database Analytics'}</div>
                            <div class="combined-title-sub">${currentLang === 'ua' ? `Аналіз вибірки з ${channelCount} каналів` : `Analytics snapshot for ${channelCount} channels`}</div>
                        </div>
                    </div>
                    <div class="combined-banner-stats">
                        <div class="header-stat-badge">
                            <span class="header-stat-num">${channelCount}</span>
                            <span class="header-stat-lbl">${currentLang === 'ua' ? 'Каналів' : 'Channels'}</span>
                        </div>
                        <div class="header-stat-badge">
                            <span class="header-stat-num">${videoCountStr}</span>
                            <span class="header-stat-lbl">${currentLang === 'ua' ? 'Відео в БД' : 'Videos in DB'}</span>
                        </div>
                        <div class="header-stat-badge">
                            <span class="header-stat-num">${totalViewsStr}</span>
                            <span class="header-stat-lbl">${currentLang === 'ua' ? 'Переглядів' : 'Views'}</span>
                        </div>
                        <div class="header-stat-badge">
                            <span class="header-stat-num">${medianViewsStr}</span>
                            <span class="header-stat-lbl">${currentLang === 'ua' ? 'Медіана' : 'Median'}</span>
                        </div>
                    </div>
                </div>
            `;
        }
    } catch (err) {
        console.error("Failed to load channel stats header:", err);
    }
}

let allChannels = [];

// API CALL: LOAD CHANNELS FOR SELECT FILTER & ANALYTICS INITIALIZATION
async function loadChannels() {
    try {
        const res = await fetch("/api/channels");
        allChannels = await res.json();
        
        // Initialize default colors for channels if they don't exist
        allChannels.forEach((ch, idx) => {
            if (!channelColors[ch.channel_id]) {
                channelColors[ch.channel_id] = DEFAULT_COLORS[idx % DEFAULT_COLORS.length];
            }
        });
        localStorage.setItem("channel_colors", JSON.stringify(channelColors));
        
        // If there's no saved selection, default to selecting all channels
        if (!selectedChannelIds || selectedChannelIds.length === 0) {
            selectedChannelIds = allChannels.map(c => c.channel_id);
        } else {
            // Filter out any IDs that no longer exist
            const activeIds = allChannels.map(c => c.channel_id);
            selectedChannelIds = selectedChannelIds.filter(id => activeIds.includes(id));
            if (selectedChannelIds.length === 0 && allChannels.length > 0) {
                selectedChannelIds = allChannels.map(c => c.channel_id);
            }
        }
        localStorage.setItem("selected_channels", JSON.stringify(selectedChannelIds));
        
        renderChannelsMenu();
        applyFilters();
        
    } catch (err) {
        console.error("Failed to load channels:", err);
    }
}

function renderChannelsMenu() {
    const listContainer = document.getElementById("dropdown-channels-list");
    if (!listContainer) return;
    
    listContainer.innerHTML = "";
    
    allChannels.forEach(ch => {
        const row = document.createElement("div");
        row.className = "channel-item-row";
        
        const isChecked = selectedChannelIds.includes(ch.channel_id) ? "checked" : "";
        const chColor = channelColors[ch.channel_id] || "#008abb";
        
        row.innerHTML = `
            <label class="channel-item-label" for="chk-ch-${ch.channel_id}">
                <input type="checkbox" value="${ch.channel_id}" id="chk-ch-${ch.channel_id}" ${isChecked} onchange="onChannelCheckboxChange(event)">
                <span class="channel-name-span" title="${ch.channel_name}">${ch.channel_name}</span>
            </label>
            <div class="channel-color-picker-wrapper">
                <input type="color" value="${chColor}" class="channel-color-input" onchange="onChannelColorChange('${ch.channel_id}', this.value)">
            </div>
        `;
        listContainer.appendChild(row);
    });
    
    updateActiveChannelNameLabel();
}

function toggleChannelsDropdown(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    const menu = document.getElementById("channels-dropdown-menu");
    if (menu) {
        menu.style.display = menu.style.display === "block" ? "none" : "block";
    }
}

function onChannelCheckboxChange(event) {
    // Keep internal UI checkbox state
}

function onChannelColorChange(channelId, newColor) {
    channelColors[channelId] = newColor;
    localStorage.setItem("channel_colors", JSON.stringify(channelColors));
    
    renderChannelsMenu();
    if (chartRawData) {
        renderActiveChart();
    }
}

function toggleSelectAllChannels(selectAll) {
    document.querySelectorAll("#dropdown-channels-list input[type='checkbox']").forEach(chk => {
        chk.checked = selectAll;
    });
}

function getSelectedChannels() {
    const list = [];
    document.querySelectorAll("#dropdown-channels-list input[type='checkbox']").forEach(chk => {
        if (chk.checked) list.push(chk.value);
    });
    return list;
}

function updateActiveChannelNameLabel() {
    const selected = getSelectedChannels();
    const btnText = document.getElementById("dropdown-selected-text");
    const label = document.getElementById("active-analytics-channel-name");
    
    if (!btnText || !label) return;
    
    if (selected.length === 0) {
        btnText.innerText = translations[currentLang].dropdown_choose_channels || "Оберіть канали";
        label.innerText = "";
    } else if (selected.length === 1) {
        const chId = selected[0];
        const chObj = allChannels.find(c => c.channel_id === chId);
        const name = chObj ? chObj.channel_name : chId;
        btnText.innerText = name;
        label.innerText = `[${name}]`;
    } else if (selected.length === allChannels.length) {
        const txt = currentLang === "ua" ? "Всі канали" : "All Channels";
        btnText.innerText = txt;
        label.innerText = `[${txt}]`;
    } else {
        const countText = currentLang === "ua" ? `Обрано: ${selected.length} кан.` : `${selected.length} channels`;
        btnText.innerText = countText;
        label.innerText = `[${countText}]`;
    }
}

// API CALL: LOAD VIDEOS TABLE WITH FILTERS
async function loadVideos() {
    const search = document.getElementById("filter-search").value;
    const channelId = getSelectedChannels().join(',');
    const startDate = document.getElementById("filter-start-date").value;
    const endDate = document.getElementById("filter-end-date").value;
    
    const params = new URLSearchParams({
        page: pagination.page,
        per_page: pagination.per_page,
        search: search,
        channel_id: channelId,
        start_date: startDate,
        end_date: endDate,
        columns: activeColumns.join(","),
        sort_by: sortCol,
        sort_order: sortDir
    });
    
    try {
        const res = await fetch(`/api/videos?${params.toString()}`);
        const data = await res.json();
        
        if (data.error) {
            console.error(data.error);
            return;
        }
        
        pagination.total_pages = data.total_pages;
        pagination.total_records = data.total_records;
        
        document.getElementById("explorer-records-count").innerText = `${data.total_records.toLocaleString()} records found`;
        document.getElementById("pag-current").innerText = data.page;
        document.getElementById("pag-total").innerText = data.total_pages || 1;
        
        document.getElementById("btn-pag-prev").disabled = (data.page <= 1);
        document.getElementById("btn-pag-next").disabled = (data.page >= data.total_pages);
        
        renderTable(data.videos);
        
    } catch (err) {
        console.error("Failed to load videos data:", err);
    }
}

// Sortable numeric/date columns
const SORTABLE_COLS = ["published_at", "view_count", "like_count", "comment_count", "duration", "scraped_at"];

// RENDER TABLE HEADERS & ROWS DYNAMICALLY
function renderTable(videos) {
    const headersTr = document.getElementById("table-headers");
    const bodyTbody = document.getElementById("table-body");
    
    headersTr.innerHTML = "";
    bodyTbody.innerHTML = "";
    
    const colLabels = {
        video_id: "ID",
        title: "Title",
        channel_name: "Channel",
        published_at: currentLang === "ua" ? "Дата публікації" : "Published At",
        view_count: currentLang === "ua" ? "Перегляди" : "Views",
        like_count: currentLang === "ua" ? "Лайки" : "Likes",
        comment_count: currentLang === "ua" ? "Коментарі" : "Comments",
        duration: currentLang === "ua" ? "Тривалість (с)" : "Duration (s)",
        scraped_at: currentLang === "ua" ? "Зібрано" : "Scraped At"
    };
    
    activeColumns.forEach(col => {
        const th = document.createElement("th");
        const isSortable = SORTABLE_COLS.includes(col);
        
        if (isSortable) {
            th.classList.add("th-sortable");
            if (col === sortCol) {
                th.classList.add(sortDir === "asc" ? "th-sort-asc" : "th-sort-desc");
            }
            th.onclick = () => toggleSort(col);
            th.innerHTML = `${colLabels[col] || col}<span class="sort-arrow"></span>`;
        } else {
            th.innerText = colLabels[col] || col;
        }
        headersTr.appendChild(th);
    });
    
    if (videos.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = activeColumns.length;
        td.style.textAlign = "center";
        td.style.padding = "24px";
        td.innerText = currentLang === "ua" ? "Жодних записів не знайдено." : "No records match search filters.";
        tr.appendChild(td);
        bodyTbody.appendChild(tr);
        return;
    }
    
    videos.forEach(v => {
        const tr = document.createElement("tr");
        
        activeColumns.forEach(col => {
            const td = document.createElement("td");
            let val = v[col];
            
            if (col === "title") {
                td.className = "td-title";
                td.title = val;
                td.innerText = val;
            } else if (col === "video_id") {
                td.className = "td-id";
                td.innerHTML = `<a href="https://youtube.com/watch?v=${val}" target="_blank" style="color: var(--accent-color); font-weight:600; text-decoration:none;"><i class="fa-brands fa-youtube"></i> ${val}</a>`;
            } else if (["view_count", "like_count", "comment_count"].includes(col)) {
                td.innerText = val !== null ? val.toLocaleString() : "-";
            } else {
                td.innerText = val !== null ? val : "-";
            }
            
            tr.appendChild(td);
        });
        
        bodyTbody.appendChild(tr);
    });
}

// SORT TOGGLE
function toggleSort(col) {
    if (sortCol === col) {
        sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
        sortCol = col;
        sortDir = "asc";
    }
    pagination.page = 1;
    loadVideos();
}

// FILTERS EVENT HANDLERS
function applyFilters() {
    pagination.page = 1;
    
    const selectedIds = getSelectedChannels();
    selectedChannelIds = selectedIds;
    localStorage.setItem("selected_channels", JSON.stringify(selectedIds));
    
    updateActiveChannelNameLabel();
    
    // Close dropdown
    const menu = document.getElementById("channels-dropdown-menu");
    if (menu) menu.style.display = "none";
    
    loadVideos();
    loadChannelStatsHeader();
    
    if (selectedIds.length > 0) {
        loadChartsData(selectedIds.join(','));
    } else {
        // Clear charts/KPIs if nothing is selected
        chartRawData = null;
        document.getElementById("kpi-total-views").innerText = "0";
        document.getElementById("kpi-median-views").innerText = "0";
        document.getElementById("kpi-like-ratio").innerText = "0.00%";
        document.getElementById("kpi-comment-ratio").innerText = "0.00%";
        if (activeChartInstance) {
            activeChartInstance.destroy();
            activeChartInstance = null;
        }
    }
}

function debounceFilter() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        applyFilters();
    }, 400);
}

function resetFilters() {
    document.getElementById("filter-search").value = "";
    
    // Check all channels in checkboxes list
    toggleSelectAllChannels(true);
    
    // Reset date range to today
    const todayStr = new Date().toISOString().split("T")[0];
    document.getElementById("filter-start-date").value = todayStr;
    document.getElementById("filter-end-date").value = todayStr;
    
    // Clear active quick-date button
    activeQuickDate = null;
    document.querySelectorAll(".quick-date-btn, .quick-date-btn-compact").forEach(b => b.classList.remove("active"));
    
    applyFilters();
}

// QUICK DATE RANGE SETTER
function setDateRange(preset) {
    const now = new Date();
    let startDate = new Date(now);
    
    const presets = {
        '1d':  () => { startDate.setDate(now.getDate() - 1); },
        '1w':  () => { startDate.setDate(now.getDate() - 7); },
        '1m':  () => { startDate.setMonth(now.getMonth() - 1); },
        '3m':  () => { startDate.setMonth(now.getMonth() - 3); },
        '6m':  () => { startDate.setMonth(now.getMonth() - 6); },
        '1y':  () => { startDate.setFullYear(now.getFullYear() - 1); },
        '2y':  () => { startDate.setFullYear(now.getFullYear() - 2); },
        '3y':  () => { startDate.setFullYear(now.getFullYear() - 3); },
        '4y':  () => { startDate.setFullYear(now.getFullYear() - 4); },
        '5y':  () => { startDate.setFullYear(now.getFullYear() - 5); },
        'war': () => { startDate = new Date('2022-02-24'); }
    };
    
    if (presets[preset]) {
        presets[preset]();
    } else {
        return;
    }
    
    const fmt = (d) => d.toISOString().split('T')[0];
    document.getElementById("filter-start-date").value = fmt(startDate);
    document.getElementById("filter-end-date").value = fmt(now);
    
    // Highlight active quick-date button
    activeQuickDate = preset;
    document.querySelectorAll(".quick-date-btn, .quick-date-btn-compact").forEach(b => b.classList.remove("active"));
    const activeBtn = document.getElementById(`qd-${preset}`);
    if (activeBtn) activeBtn.classList.add("active");
    
    pagination.page = 1;
    loadVideos();
    
    // Also reload charts for the new date range
    const selectedIds = getSelectedChannels();
    if (selectedIds.length > 0) {
        loadChartsData(selectedIds.join(','));
        loadChannelStatsHeader();
    }
}


function toggleColumnsSelector() {
    const panel = document.getElementById("columns-chooser-panel");
    panel.style.display = panel.style.display === "none" ? "flex" : "none";
}

function updateColumns() {
    const list = ["title"];
    document.querySelectorAll(".column-checkbox input").forEach(cb => {
        if (cb.checked && cb.value !== "title") {
            list.push(cb.value);
        }
    });
    
    const order = ["video_id", "title", "channel_name", "published_at", "view_count", "like_count", "comment_count", "duration", "scraped_at"];
    activeColumns = order.filter(c => list.includes(c));
    loadVideos();
}

// PAGINATION NAVIGATION
function changePage(direction) {
    const newPage = pagination.page + direction;
    if (newPage >= 1 && newPage <= pagination.total_pages) {
        pagination.page = newPage;
        loadVideos();
    }
}

function changePerPage(val) {
    pagination.per_page = parseInt(val);
    pagination.page = 1;
    loadVideos();
}

function exportCSV() {
    const search = document.getElementById("filter-search").value;
    const channelId = getSelectedChannels().join(',');
    const startDate = document.getElementById("filter-start-date").value;
    const endDate = document.getElementById("filter-end-date").value;
    
    const params = new URLSearchParams({
        search: search,
        channel_id: channelId,
        start_date: startDate,
        end_date: endDate,
        columns: activeColumns.join(",")
    });
    
    window.location.href = `/api/videos/export?${params.toString()}`;
}

// BACKGROUND OPERATION TRIGGER
async function triggerAction(actionName) {
    const btnScrape = document.getElementById("btn-run-scrape");
    const btnSync = document.getElementById("btn-run-sync");
    const btnUpdate = document.getElementById("btn-run-update");
    
    if (btnScrape) btnScrape.disabled = true;
    if (btnSync) btnSync.disabled = true;
    if (btnUpdate) btnUpdate.disabled = true;
    
    try {
        const res = await fetch(`/api/action/${actionName}`, { method: "POST" });
        const data = await res.json();
        
        const consoleOut = document.getElementById("console-output");
        
        if (data.error) {
            consoleOut.innerHTML += `<div class="console-line err">[ERROR] ${data.error}</div>`;
        } else {
            consoleOut.innerHTML += `<div class="console-line success">[SUCCESS] ${data.message}</div>`;
            checkProcessStatus();
        }
        
        consoleOut.scrollTop = consoleOut.scrollHeight;
    } catch (err) {
        console.error("Action trigger failed:", err);
    } finally {
        checkProcessStatus();
    }
}

// LIVE LOGS POLLING & TASK STATUS
async function checkProcessStatus() {
    try {
        const res = await fetch("/api/action/status");
        const status = await res.json();
        
        const badge = document.getElementById("task-badge");
        const updateBadge = document.getElementById("update-badge");
        const btnScrape = document.getElementById("btn-run-scrape");
        const btnSync = document.getElementById("btn-run-sync");
        const btnUpdate = document.getElementById("btn-run-update");
        const btnViewsUpdate = document.getElementById("btn-run-views-update");
        
        const isBusy = status.status !== "idle";
        
        if (btnScrape) btnScrape.disabled = isBusy;
        if (btnSync) btnSync.disabled = isBusy;
        
        // Handle Update button states & animations
        if (btnUpdate) {
            btnUpdate.disabled = isBusy;
            if (status.status === "updating") {
                btnUpdate.innerHTML = `<i class="fa-solid fa-arrows-rotate fa-spin"></i> <span data-i18n="btn_updating">Updating...</span>`;
                const span = btnUpdate.querySelector("span");
                if (span) span.innerText = currentLang === "ua" ? "Оновлення..." : "Updating...";
            } else {
                btnUpdate.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> <span data-i18n="btn_update_db">Update DB</span>`;
                const span = btnUpdate.querySelector("span");
                if (span) span.innerText = currentLang === "ua" ? "Оновити БД" : "Update DB";
            }
        }
        
        // Handle Views Update button states & animations
        if (btnViewsUpdate) {
            btnViewsUpdate.disabled = isBusy;
            if (status.status === "updating_views") {
                btnViewsUpdate.innerHTML = `<i class="fa-solid fa-chart-line fa-spin"></i> <span data-i18n="btn_updating_views">Updating...</span>`;
                const span = btnViewsUpdate.querySelector("span");
                if (span) span.innerText = currentLang === "ua" ? "Оновлення..." : "Updating...";
            } else {
                btnViewsUpdate.innerHTML = `<i class="fa-solid fa-chart-line"></i> <span data-i18n="btn_update_views">Update Views</span>`;
                const span = btnViewsUpdate.querySelector("span");
                if (span) span.innerText = currentLang === "ua" ? "Оновити перегляди" : "Update Views";
            }
        }
        
        // Handle updateBadge next to the button
        if (updateBadge) {
            if (status.status === "updating") {
                updateBadge.innerText = translations[currentLang].status_updating;
                updateBadge.className = "task-badge active";
                updateBadge.style.display = "inline-block";
            } else if (status.status === "updating_views") {
                updateBadge.innerText = translations[currentLang].status_updating_views;
                updateBadge.className = "task-badge active";
                updateBadge.style.display = "inline-block";
            } else {
                updateBadge.style.display = "none";
            }
        }
        
        // Handle main Operations tab badge
        if (badge) {
            if (status.status === "idle") {
                badge.innerText = translations[currentLang].status_idle;
                badge.className = "task-badge idle";
            } else {
                let statusText = "";
                if (status.status === "scraping") statusText = translations[currentLang].status_scraping;
                else if (status.status === "syncing") statusText = translations[currentLang].status_syncing;
                else if (status.status === "updating") statusText = translations[currentLang].status_updating;
                else if (status.status === "updating_views") statusText = translations[currentLang].status_updating_views;
                
                badge.innerText = statusText;
                badge.className = "task-badge active";
                
                // Reload stats dynamically while scraping/syncing/updating
                loadStats();
            }
        }
        
        // If status transitioned from "updating" or "updating_views" to "idle", reload table and chart!
        if ((lastKnownStatus === "updating" || lastKnownStatus === "updating_views") && status.status === "idle") {
            loadStats();
            loadVideos();
            loadChannelStatsHeader();
            const selectedIds = getSelectedChannels();
            if (selectedIds.length > 0) {
                loadChartsData(selectedIds.join(','));
            }
        }
        
        // Update the last known status
        lastKnownStatus = status.status;
        
        if (status.logs) {
            const consoleOut = document.getElementById("console-output");
            const formattedLogs = status.logs
                .replace(/\[\*\]/g, '<span style="color:#38bdf8;">[*]</span>')
                .replace(/\[\+\]/g, '<span style="color:#00ff87;">[+]</span>')
                .replace(/\[i\]/g, '<span style="color:#e2e8f0;">[i]</span>')
                .replace(/\[!\]/g, '<span style="color:#f87171;">[!]</span>');
                
            consoleOut.innerHTML = `<div class="console-line">${formattedLogs}</div>`;
            consoleOut.scrollTop = consoleOut.scrollHeight;
        }
    } catch (err) {
        console.error("Failed to query background status:", err);
    }
}

// API CALL: FETCH CHARTS DATA FOR SELECTED CHANNEL
async function loadChartsData(channelId) {
    if (!channelId) return;
    try {
        // Read current date filter from table inputs
        const startDate = document.getElementById("filter-start-date").value;
        const endDate = document.getElementById("filter-end-date").value;
        
        const params = new URLSearchParams({ channel_id: channelId });
        if (startDate) params.append("start_date", startDate);
        if (endDate) params.append("end_date", endDate);
        
        const res = await fetch(`/api/charts?${params.toString()}`);
        chartRawData = await res.json();
        
        // Populate KPIs
        if (chartRawData.kpis) {
            document.getElementById("kpi-total-views").innerText = chartRawData.kpis.total_views.toLocaleString();
            document.getElementById("kpi-median-views").innerText = chartRawData.kpis.median_views.toLocaleString();
            document.getElementById("kpi-like-ratio").innerText = chartRawData.kpis.like_ratio.toFixed(2) + "%";
            document.getElementById("kpi-comment-ratio").innerText = chartRawData.kpis.comment_ratio.toFixed(2) + "%";
        }
        
        // Render the currently active chart type (preserves selection across date changes)
        renderActiveChart();
    } catch (err) {
        console.error("Failed to load charts data:", err);
    }
}

// ─────────────────────────────────────────────────────────────────────
// CHART UI BUILDER — builds buttons + dropdown from CHART_DEFS
// Call this on page load and language change
// ─────────────────────────────────────────────────────────────────────
function initChartUI() {
    const container = document.getElementById('chart-controls-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    const statsElements = [];
    const promoElements = [];
    const otherElements = [];
    
    const processedIds = new Set();
    
    CHART_DEFS.forEach(def => {
        if (processedIds.has(def.id)) return;
        
        const label = (translations[currentLang] && translations[currentLang][def.labelKey])
            ? translations[currentLang][def.labelKey]
            : def.id;
            
        let elementToAdd = null;
        
        if (def.pair === 'left') {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'split-btn-group';
            
            const leftBtn = document.createElement('button');
            leftBtn.className = 'split-btn left';
            leftBtn.id = `chart-btn-${def.id}`;
            leftBtn.setAttribute('data-chart-id', def.id);
            if (activeChartType === def.id) leftBtn.classList.add('active');
            leftBtn.onclick = () => selectChart(def.id);
            leftBtn.innerHTML = `${def.icon || ''} ${label}`;
            groupDiv.appendChild(leftBtn);
            processedIds.add(def.id);
            
            const rightDef = CHART_DEFS.find(d => d.id === def.pairId);
            if (rightDef) {
                const rightLabel = (translations[currentLang] && translations[currentLang][rightDef.labelKey])
                    ? translations[currentLang][rightDef.labelKey]
                    : rightDef.id;
                    
                const rightBtn = document.createElement('button');
                rightBtn.className = 'split-btn right';
                rightBtn.id = `chart-btn-${rightDef.id}`;
                rightBtn.setAttribute('data-chart-id', rightDef.id);
                if (activeChartType === rightDef.id) rightBtn.classList.add('active');
                rightBtn.onclick = () => selectChart(rightDef.id);
                rightBtn.innerHTML = `${rightDef.icon || ''} ${rightLabel}`;
                groupDiv.appendChild(rightBtn);
                processedIds.add(rightDef.id);
            }
            
            elementToAdd = groupDiv;
        } else if (!def.pair) {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'split-btn-group';
            
            const btn = document.createElement('button');
            btn.className = 'split-btn';
            btn.style.borderRadius = '4px';
            btn.id = `chart-btn-${def.id}`;
            btn.setAttribute('data-chart-id', def.id);
            if (activeChartType === def.id) btn.classList.add('active');
            btn.onclick = () => selectChart(def.id);
            btn.innerHTML = `${def.icon || ''} ${label}`;
            groupDiv.appendChild(btn);
            
            elementToAdd = groupDiv;
            processedIds.add(def.id);
        }
        
        if (elementToAdd) {
            if (def.group === 'stats') {
                statsElements.push(elementToAdd);
            } else if (def.group === 'promo') {
                promoElements.push(elementToAdd);
            } else if (def.group === 'other') {
                otherElements.push(elementToAdd);
            }
        }
    });
    
    statsElements.forEach(el => container.appendChild(el));
    
    if (statsElements.length > 0 && promoElements.length > 0) {
        const divider = document.createElement('div');
        divider.className = 'chart-group-divider';
        container.appendChild(divider);
    }
    
    promoElements.forEach(el => container.appendChild(el));
    
    if ((statsElements.length > 0 || promoElements.length > 0) && otherElements.length > 0) {
        const divider = document.createElement('div');
        divider.className = 'chart-group-divider';
        container.appendChild(divider);
    }
    
    otherElements.forEach(el => container.appendChild(el));
}

function selectChart(chartType) {
    if (!chartType) return;
    activeChartType = chartType;
    
    document.querySelectorAll('.split-btn, .promo-tab-btn').forEach(el => el.classList.remove('active'));
    
    const activeEl = document.getElementById(`chart-btn-${chartType}`);
    if (activeEl) activeEl.classList.add('active');
    
    renderActiveChart();
}

function selectPromoChart(chartType) {
    selectChart(chartType);
}

// ─────────────────────────────────────────────────────────────────────
// RENDER ACTIVE CHART — always uses activeChartType (persists across reloads)
// ─────────────────────────────────────────────────────────────────────
function renderActiveChart() {
    const chartType = activeChartType;
    if (!chartRawData || !chartType) return;
    
    const isScrollable = ["best_promo_words", "worst_promo_words", "best_promo_tags", "worst_promo_tags", "top_viewed", "top_liked", "top_commented", "worst_viewed", "worst_liked", "worst_commented"].includes(chartType);
    
    // Destroy previous chart first so we can safely resize
    if (activeChartInstance) {
        activeChartInstance.destroy();
        activeChartInstance = null;
    }
    
    const container = document.querySelector(".chart-container");
    
    if (container) {
        if (isScrollable) {
            // Scrollable outer window
            container.style.height = "420px";
            container.style.overflowY = "auto";
            container.style.overflowX = "hidden";
            
            // Calculate how many items to display
            let itemCount = 30;
            if (chartType === "best_promo_words" && chartRawData.best_promo_words) itemCount = chartRawData.best_promo_words.length;
            else if (chartType === "worst_promo_words" && chartRawData.worst_promo_words) itemCount = chartRawData.worst_promo_words.length;
            else if (chartType === "best_promo_tags" && chartRawData.best_promo_tags) itemCount = chartRawData.best_promo_tags.length;
            else if (chartType === "worst_promo_tags" && chartRawData.worst_promo_tags) itemCount = chartRawData.worst_promo_tags.length;
            else if (chartType === "top_viewed" && chartRawData.top_viewed) itemCount = chartRawData.top_viewed.length;
            else if (chartType === "top_liked" && chartRawData.top_liked) itemCount = chartRawData.top_liked.length;
            else if (chartType === "top_commented" && chartRawData.top_commented) itemCount = chartRawData.top_commented.length;
            else if (chartType === "worst_viewed" && chartRawData.worst_viewed) itemCount = chartRawData.worst_viewed.length;
            else if (chartType === "worst_liked" && chartRawData.worst_liked) itemCount = chartRawData.worst_liked.length;
            else if (chartType === "worst_commented" && chartRawData.worst_commented) itemCount = chartRawData.worst_commented.length;
            
            // 18px per bar + 60px header/footer
            const canvasH = Math.max(300, itemCount * 18 + 60);
            
            // Use an inner wrapper div so Chart.js fills it and container scrolls
            let wrapper = container.querySelector(".chart-scroll-inner");
            if (!wrapper) {
                wrapper = document.createElement("div");
                wrapper.className = "chart-scroll-inner";
                wrapper.style.position = "relative";
                // Move canvas into wrapper
                const existingCanvas = document.getElementById("analytics-chart");
                container.appendChild(wrapper);
                wrapper.appendChild(existingCanvas);
            }
            wrapper.style.height = canvasH + "px";
            wrapper.style.minHeight = canvasH + "px";
            
        } else {
            // Restore canvas directly in container if it was inside a wrapper
            const wrapper = container.querySelector(".chart-scroll-inner");
            if (wrapper) {
                const canvas = document.getElementById("analytics-chart");
                container.insertBefore(canvas, wrapper);
                container.removeChild(wrapper);
            }
            container.style.height = "280px";
            container.style.overflowY = "visible";
            container.style.overflowX = "visible";
        }
    }
    
    // Update button active states
    document.querySelectorAll('.split-btn').forEach(el => {
        el.classList.toggle('active', el.id === `chart-btn-${chartType}`);
    });

    const canvasEl = document.getElementById("analytics-chart");
    const ctx = canvasEl.getContext("2d");
    
    const isDark = ["dark-black", "dark-blue"].includes(currentTheme);
    const gridColor = isDark ? "#334155" : "#e2e8f0";
    const labelColor = isDark ? "#94a3b8" : "#5f6368";
    const titleColor = isDark ? "#f8fafc" : "#202124";
    
    let chartConfig = {};
    
    if (chartType === "by_month") {
        const labels = chartRawData.by_month.map(d => d.month);
        const values = chartRawData.by_month.map(d => d.video_count);
        
        chartConfig = {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Завантажено відео" : "Videos Uploaded",
                    data: values,
                    borderColor: "#008abb",
                    backgroundColor: "rgba(0, 138, 187, 0.1)",
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Динаміка завантажень по місяцях" : "Upload Volume By Month", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { color: gridColor }, ticks: { color: labelColor } }
                }
            }
        };
        
    } else if (chartType === "duration_dist") {
        const categoriesMap = {
            "Short (< 1m)": currentLang === "ua" ? "Короткі (< 1хв)" : "Short (< 1m)",
            "Medium (1-10m)": currentLang === "ua" ? "Середні (1-10хв)" : "Medium (1-10m)",
            "Long (> 10m)": currentLang === "ua" ? "Довгі (> 10хв)" : "Long (> 10m)"
        };
        
        const labels = chartRawData.duration_dist.map(d => categoriesMap[d.category] || d.category);
        const values = chartRawData.duration_dist.map(d => d.video_count);
        
        chartConfig = {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: ["#38bdf8", "#34d399", "#f59e0b"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        position: "right",
                        labels: { color: labelColor, boxWidth: 12 }
                    },
                    title: { display: true, text: currentLang === "ua" ? "Розподіл за тривалістю відео" : "Videos Duration Share", color: titleColor }
                }
            }
        };
        
    } else if (chartType === "top_viewed") {
        const labels = chartRawData.top_viewed.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = chartRawData.top_viewed.map(d => d.view_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Перегляди" : "Views",
                    data: values,
                    backgroundColor: chartRawData.top_viewed.map(d => channelColors[d.channel_id] || "#00e676")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Топ-100 відео за переглядами" : "Top 100 Most Viewed Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
        
    } else if (chartType === "top_liked") {
        const labels = chartRawData.top_liked.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = chartRawData.top_liked.map(d => d.like_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Лайки" : "Likes",
                    data: values,
                    backgroundColor: chartRawData.top_liked.map(d => channelColors[d.channel_id] || "#f59e0b")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Топ-100 відео за лайками" : "Top 100 Most Liked Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
        
    } else if (chartType === "top_commented") {
        const labels = chartRawData.top_commented.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = chartRawData.top_commented.map(d => d.comment_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Коментарі" : "Comments",
                    data: values,
                    backgroundColor: chartRawData.top_commented.map(d => channelColors[d.channel_id] || "#8b5cf6")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Топ-100 відео за коментарями" : "Top 100 Most Commented Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "worst_viewed") {
        const labels = chartRawData.worst_viewed.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = chartRawData.worst_viewed.map(d => d.view_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Перегляди" : "Views",
                    data: values,
                    backgroundColor: chartRawData.worst_viewed.map(d => channelColors[d.channel_id] || "#f43f5e")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Найгірші 100 відео за переглядами" : "Worst 100 Viewed Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "worst_liked") {
        const labels = chartRawData.worst_liked.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = chartRawData.worst_liked.map(d => d.like_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Лайки" : "Likes",
                    data: values,
                    backgroundColor: chartRawData.worst_liked.map(d => channelColors[d.channel_id] || "#f43f5e")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Найгірші 100 відео за лайками" : "Worst 100 Liked Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "worst_commented") {
        const labels = chartRawData.worst_commented.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = chartRawData.worst_commented.map(d => d.comment_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Коментарі" : "Comments",
                    data: values,
                    backgroundColor: chartRawData.worst_commented.map(d => channelColors[d.channel_id] || "#f43f5e")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Найгірші 100 відео за коментарями" : "Worst 100 Commented Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "top_hashtags") {
        const labels = chartRawData.top_hashtags.map(d => d.tag);
        const values = chartRawData.top_hashtags.map(d => d.count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Сумарні перегляди" : "Total Attributed Views",
                    data: values,
                    backgroundColor: "#0ea5e9"
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Топ-10 хештегів за сумарними переглядами" : "Top 10 Hashtags by Attributed Views", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = chartRawData.top_hashtags[idx];
                                const avgViews = item.video_count > 0 ? Math.round(item.count / item.video_count) : 0;
                                return [
                                    (currentLang === "ua" ? "Перегляди: " : "Views: ") + item.count.toLocaleString(),
                                    (currentLang === "ua" ? "Відео: " : "Videos: ") + item.video_count,
                                    (currentLang === "ua" ? "Сер. переглядів/відео: " : "Avg views/video: ") + avgViews.toLocaleString()
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "top_description_words") {
        const labels = chartRawData.top_words.map(d => d.word);
        const values = chartRawData.top_words.map(d => d.count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Сумарні перегляди" : "Total Attributed Views",
                    data: values,
                    backgroundColor: "#ec4899"
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Топ-10 слів в описах за сумарними переглядами" : "Top 10 Description Words by Attributed Views", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = chartRawData.top_words[idx];
                                const avgViews = item.video_count > 0 ? Math.round(item.count / item.video_count) : 0;
                                return [
                                    (currentLang === "ua" ? "Перегляди: " : "Views: ") + item.count.toLocaleString(),
                                    (currentLang === "ua" ? "Відео: " : "Videos: ") + item.video_count,
                                    (currentLang === "ua" ? "Сер. переглядів/відео: " : "Avg views/video: ") + avgViews.toLocaleString()
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "best_promo_words") {
        const labels = chartRawData.best_promo_words.map(d => d.word);
        const values = chartRawData.best_promo_words.map(d => d.lift);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Приріст (Lift)" : "Performance Lift",
                    data: values,
                    backgroundColor: "#10b981"
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Найкращі слова для просування (Множник медіани)" : "Top Promotion Keywords (Median Lift Factor)", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = chartRawData.best_promo_words[idx];
                                const changePct = Math.round((item.lift - 1) * 100);
                                const changeSign = changePct >= 0 ? "+" : "";
                                return [
                                    (currentLang === "ua" ? "Ефективність: " : "Performance Lift: ") + item.lift.toFixed(2) + "x (" + changeSign + changePct + "%)",
                                    (currentLang === "ua" ? "Медіана переглядів слова: " : "Word Median Views: ") + item.median_views.toLocaleString(),
                                    (currentLang === "ua" ? "Кількість відео: " : "Videos count: ") + item.video_count
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "worst_promo_words") {
        const labels = chartRawData.worst_promo_words.map(d => d.word);
        const values = chartRawData.worst_promo_words.map(d => d.lift);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Приріст (Lift)" : "Performance Lift",
                    data: values,
                    backgroundColor: "#ef4444"
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Топ-30 найгірших слів для просування (Множник медіани)" : "Worst Promotion Keywords (Median Lift Factor)", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = chartRawData.worst_promo_words[idx];
                                const changePct = Math.round((item.lift - 1) * 100);
                                const changeSign = changePct >= 0 ? "+" : "";
                                return [
                                    (currentLang === "ua" ? "Ефективність: " : "Performance Lift: ") + item.lift.toFixed(2) + "x (" + changeSign + changePct + "%)",
                                    (currentLang === "ua" ? "Медіана переглядів слова: " : "Word Median Views: ") + item.median_views.toLocaleString(),
                                    (currentLang === "ua" ? "Кількість відео: " : "Videos count: ") + item.video_count
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "best_promo_tags") {
        const labels = chartRawData.best_promo_tags.map(d => d.tag);
        const values = chartRawData.best_promo_tags.map(d => d.lift);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Приріст (Lift)" : "Performance Lift",
                    data: values,
                    backgroundColor: "#10b981"
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Топ-30 найкращих хештегів для просування (Множник медіани)" : "Top 30 Promotion Hashtags (Median Lift Factor)", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = chartRawData.best_promo_tags[idx];
                                const changePct = Math.round((item.lift - 1) * 100);
                                const changeSign = changePct >= 0 ? "+" : "";
                                return [
                                    (currentLang === "ua" ? "Ефективність: " : "Performance Lift: ") + item.lift.toFixed(2) + "x (" + changeSign + changePct + "%)",
                                    (currentLang === "ua" ? "Медіана переглядів тегу: " : "Tag Median Views: ") + item.median_views.toLocaleString(),
                                    (currentLang === "ua" ? "Кількість відео: " : "Videos count: ") + item.video_count
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "worst_promo_tags") {
        const labels = chartRawData.worst_promo_tags.map(d => d.tag);
        const values = chartRawData.worst_promo_tags.map(d => d.lift);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: currentLang === "ua" ? "Приріст (Lift)" : "Performance Lift",
                    data: values,
                    backgroundColor: "#ef4444"
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Топ-30 найгірших хештегів для просування (Множник медіани)" : "Worst Promotion Hashtags (Median Lift Factor)", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = chartRawData.worst_promo_tags[idx];
                                const changePct = Math.round((item.lift - 1) * 100);
                                const changeSign = changePct >= 0 ? "+" : "";
                                return [
                                    (currentLang === "ua" ? "Ефективність: " : "Performance Lift: ") + item.lift.toFixed(2) + "x (" + changeSign + changePct + "%)",
                                    (currentLang === "ua" ? "Медіана переглядів тегу: " : "Tag Median Views: ") + item.median_views.toLocaleString(),
                                    (currentLang === "ua" ? "Кількість відео: " : "Videos count: ") + item.video_count
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "best_day_to_post") {
        const labelsMap = {
            "Sunday": currentLang === "ua" ? "Неділя" : "Sunday",
            "Monday": currentLang === "ua" ? "Понеділок" : "Monday",
            "Tuesday": currentLang === "ua" ? "Вівторок" : "Tuesday",
            "Wednesday": currentLang === "ua" ? "Середа" : "Wednesday",
            "Thursday": currentLang === "ua" ? "Четвер" : "Thursday",
            "Friday": currentLang === "ua" ? "П'ятниця" : "Friday",
            "Saturday": currentLang === "ua" ? "Субота" : "Saturday"
        };
        const labels = chartRawData.best_day_to_post.map(d => labelsMap[d.day_of_week] || d.day_of_week);
        const counts = chartRawData.best_day_to_post.map(d => d.video_count);
        const views = chartRawData.best_day_to_post.map(d => d.total_views);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: currentLang === "ua" ? "Кількість відео" : "Videos Count",
                        data: counts,
                        backgroundColor: "#38bdf8",
                        yAxisID: "y"
                    },
                    {
                        label: currentLang === "ua" ? "Всього переглядів" : "Total Views",
                        data: views,
                        backgroundColor: "#a855f7",
                        yAxisID: "y1"
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: labelColor } },
                    title: { display: true, text: currentLang === "ua" ? "Кращий день для публікації (Кількість vs Перегляди)" : "Best Day to Post (Volume vs Views)", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { 
                        type: "linear",
                        display: true,
                        position: "left",
                        grid: { color: gridColor },
                        ticks: { color: labelColor }
                    },
                    y1: {
                        type: "linear",
                        display: true,
                        position: "right",
                        grid: { drawOnChartArea: false },
                        ticks: { color: labelColor }
                    }
                }
            }
        };
    } else if (chartType === "duration_vs_views") {
        const scatterData = chartRawData.duration_vs_views.map(d => ({
            x: d.duration,
            y: d.view_count,
            title: d.title,
            channel_id: d.channel_id
        }));
        
        chartConfig = {
            type: "scatter",
            data: {
                datasets: [{
                    label: currentLang === "ua" ? "Відео" : "Videos",
                    data: scatterData,
                    backgroundColor: chartRawData.duration_vs_views.map(d => channelColors[d.channel_id] || "rgba(56, 189, 248, 0.6)"),
                    borderColor: chartRawData.duration_vs_views.map(d => channelColors[d.channel_id] || "#38bdf8"),
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: currentLang === "ua" ? "Кореляція: Тривалість відео (сек) vs Перегляди" : "Correlation: Duration (seconds) vs Views", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const pt = context.raw;
                                const title = pt.title.length > 40 ? pt.title.substring(0, 37) + "..." : pt.title;
                                return `${title} (${pt.x}s, ${pt.y.toLocaleString()} views)`;
                            }
                        }
                    }
                },
                scales: {
                    x: { 
                        title: { display: true, text: currentLang === "ua" ? "Тривалість (секунди)" : "Duration (seconds)", color: labelColor },
                        grid: { color: gridColor }, 
                        ticks: { color: labelColor } 
                    },
                    y: { 
                        title: { display: true, text: currentLang === "ua" ? "Перегляди" : "Views", color: labelColor },
                        grid: { color: gridColor }, 
                        ticks: { color: labelColor } 
                    }
                }
            }
        };
    } else if (chartType === "views_distribution") {
        const labelsMap = {
            "Very Low (< 1k)": currentLang === "ua" ? "Дуже низькі (< 1к)" : "Very Low (< 1k)",
            "Low (1k-10k)": currentLang === "ua" ? "Низькі (1к-10к)" : "Low (1k-10k)",
            "Medium (10k-50k)": currentLang === "ua" ? "Середні (10к-50к)" : "Medium (10k-50k)",
            "High (50k-100k)": currentLang === "ua" ? "Високі (50к-100к)" : "High (50k-100k)",
            "Very High (> 100k)": currentLang === "ua" ? "Дуже високі (> 100к)" : "Very High (> 100k)"
        };
        const labels = chartRawData.views_distribution.map(d => labelsMap[d.category] || d.category);
        const values = chartRawData.views_distribution.map(d => d.video_count);
        
        chartConfig = {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: ["#94a3b8", "#60a5fa", "#34d399", "#fb7185", "#f59e0b"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        position: "right",
                        labels: { color: labelColor, boxWidth: 12 }
                    },
                    title: { display: true, text: currentLang === "ua" ? "Розподіл відео за рівнем переглядів" : "Views Performance Distribution", color: titleColor }
                }
            }
        };
    }
    
    if (["top_viewed", "worst_viewed", "top_liked", "worst_liked", "top_commented", "worst_commented"].includes(chartType)) {
        if (!chartConfig.options) chartConfig.options = {};
        chartConfig.options.onClick = (evt, activeElements) => {
            if (activeElements && activeElements.length > 0) {
                const index = activeElements[0].index;
                const dataList = chartRawData[chartType];
                if (dataList && dataList[index]) {
                    openVideoModal(dataList[index]);
                }
            }
        };
    }
    
    activeChartInstance = new Chart(ctx, chartConfig);

}

// ─────────────────────────────────────────────────────────────────────
// VIDEO DETAILS MODAL WINDOW & API
// ─────────────────────────────────────────────────────────────────────
function openVideoModal(video) {
    if (!video) return;
    activeModalVideoId = video.video_id;
    
    // Set text elements
    document.getElementById("mv-modal-title").innerText = video.title || "Video Details";
    
    // Format stats
    document.getElementById("mv-modal-views").innerText = video.view_count ? parseInt(video.view_count).toLocaleString() : "0";
    document.getElementById("mv-modal-likes").innerText = video.like_count ? parseInt(video.like_count).toLocaleString() : "0";
    document.getElementById("mv-modal-comments").innerText = video.comment_count ? parseInt(video.comment_count).toLocaleString() : "0";
    document.getElementById("mv-modal-date").innerText = video.published_at || "-";
    
    // Thumbnail from img.youtube.com
    document.getElementById("mv-modal-thumbnail").src = `https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`;
    
    // YouTube link
    document.getElementById("mv-modal-yt-link").href = `https://www.youtube.com/watch?v=${video.video_id}`;
    
    // Description formatting
    const descBox = document.getElementById("mv-modal-description");
    descBox.innerText = video.full_description || video.description || (currentLang === "ua" ? "Опис відсутній. Натисніть 'Зібрати деталі' для завантаження." : "No description available. Click 'Scrape Details' to fetch.");
    descBox.style.whiteSpace = "pre-wrap";
    
    // Reset buttons
    const downloadBtn = document.getElementById("mv-modal-download-btn");
    const downloadText = document.getElementById("mv-modal-download-text");
    downloadBtn.disabled = false;
    downloadText.innerText = translations[currentLang].modal_download_mp4 || "Download MP4";
    
    const scrapeBtn = document.getElementById("mv-modal-scrape-btn");
    const scrapeText = document.getElementById("mv-modal-scrape-text");
    scrapeBtn.disabled = false;
    scrapeText.innerText = translations[currentLang].modal_scrape_details || "Scrape Details";
    
    // Render views growth chart if database history is available
    let history = [];
    if (video.views_update) {
        try {
            history = typeof video.views_update === "string" ? JSON.parse(video.views_update) : video.views_update;
        } catch (err) {
            console.error("Failed to parse views_update:", err);
            history = [];
        }
    }
    
    renderModalViewsChart(history);
    
    // Show Modal overlay
    const modal = document.getElementById("video-details-modal");
    if (modal) {
        modal.style.display = "flex";
        document.body.classList.add("modal-open");
    }
}

function closeVideoModal() {
    const modal = document.getElementById("video-details-modal");
    if (modal) {
        modal.style.display = "none";
        document.body.classList.remove("modal-open");
    }
    
    if (activeModalChartInstance) {
        activeModalChartInstance.destroy();
        activeModalChartInstance = null;
    }
    
    activeModalVideoId = null;
}

function renderModalViewsChart(history) {
    if (activeModalChartInstance) {
        activeModalChartInstance.destroy();
        activeModalChartInstance = null;
    }
    
    const titleEl = document.getElementById("mv-modal-chart-title");
    const containerEl = document.getElementById("mv-modal-chart-container");
    
    if (!history || history.length < 2) {
        if (titleEl) titleEl.style.display = "none";
        if (containerEl) containerEl.style.display = "none";
        return;
    }
    
    if (titleEl) titleEl.style.display = "block";
    if (containerEl) containerEl.style.display = "block";
    
    const canvas = document.getElementById("modal-views-chart");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    
    // Sort chronological order
    history.sort((a, b) => a[0] - b[0]);
    
    const labels = history.map(item => {
        const date = new Date(item[0] * 1000);
        return date.toLocaleDateString(currentLang === 'ua' ? 'uk-UA' : 'en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    });
    
    const data = history.map(item => item[1]);
    
    const isDark = ["dark-black", "dark-blue"].includes(currentTheme);
    const gridColor = isDark ? "#334155" : "#e2e8f0";
    const labelColor = isDark ? "#94a3b8" : "#5f6368";
    
    activeModalChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: currentLang === 'ua' ? 'Перегляди' : 'Views',
                data: data,
                borderColor: '#38bdf8',
                backgroundColor: 'rgba(56, 189, 248, 0.08)',
                borderWidth: 2,
                fill: true,
                tension: 0.15,
                pointRadius: 2.5,
                pointHoverRadius: 4.5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.raw.toLocaleString();
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: labelColor, maxRotation: 45, minRotation: 0, font: { size: 9 } }
                },
                y: {
                    grid: { color: gridColor },
                    ticks: { color: labelColor, font: { size: 9 }, callback: value => value.toLocaleString() }
                }
            }
        }
    });
}

async function downloadVideoFromModal() {
    const btn = document.getElementById("mv-modal-download-btn");
    const txt = document.getElementById("mv-modal-download-text");
    if (!activeModalVideoId || btn.disabled) return;
    
    const oldText = txt.innerText;
    txt.innerText = translations[currentLang].modal_downloading || "Downloading...";
    btn.disabled = true;
    
    try {
        const res = await fetch(`/api/videos/${activeModalVideoId}/download`);
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.error || "Failed to download");
        }
        
        const disposition = res.headers.get('Content-Disposition');
        let filename = `${activeModalVideoId}.mp4`;
        if (disposition && disposition.indexOf('attachment') !== -1) {
            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }
        
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        alert(currentLang === 'ua' ? `Помилка завантаження: ${err.message}` : `Download failed: ${err.message}`);
    } finally {
        btn.disabled = false;
        txt.innerText = oldText;
    }
}

async function scrapeDetailsFromModal() {
    const btn = document.getElementById("mv-modal-scrape-btn");
    const txt = document.getElementById("mv-modal-scrape-text");
    if (!activeModalVideoId || btn.disabled) return;
    
    const oldText = txt.innerText;
    txt.innerText = translations[currentLang].modal_scraping || "Scraping...";
    btn.disabled = true;
    
    try {
        const res = await fetch(`/api/videos/${activeModalVideoId}/scrape_details`, {
            method: 'POST'
        });
        const data = await res.json();
        
        if (!res.ok) {
            throw new Error(data.error || "Scraping failed");
        }
        
        // Update texts in modal UI
        document.getElementById("mv-modal-views").innerText = data.view_count.toLocaleString();
        document.getElementById("mv-modal-likes").innerText = data.like_count.toLocaleString();
        document.getElementById("mv-modal-comments").innerText = data.comment_count.toLocaleString();
        
        const descBox = document.getElementById("mv-modal-description");
        descBox.innerText = data.description || "";
        
        // Redraw Views Trend line chart
        renderModalViewsChart(data.views_update || []);
        
        // Synchronize this updated object inside the locally cached chartRawData!
        const updateVideoFields = (list, videoId, scrapedData) => {
            if (!list) return;
            const found = list.find(v => v.video_id === videoId);
            if (found) {
                found.full_description = scrapedData.description;
                found.view_count = scrapedData.view_count;
                found.like_count = scrapedData.like_count;
                found.comment_count = scrapedData.comment_count;
                found.tags = scrapedData.tags;
                found.views_update = scrapedData.views_update;
            }
        };
        
        if (chartRawData) {
            ["top_viewed", "worst_viewed", "top_liked", "worst_liked", "top_commented", "worst_commented"].forEach(listKey => {
                updateVideoFields(chartRawData[listKey], activeModalVideoId, data);
            });
        }
        
        loadVideos();
        loadStats();
        alert(currentLang === 'ua' ? "Дані успішно оновлено!" : "Video statistics successfully updated!");
    } catch (err) {
        alert(currentLang === 'ua' ? `Не вдалося отримати деталі: ${err.message}` : `Scrape failed: ${err.message}`);
    } finally {
        btn.disabled = false;
        txt.innerText = oldText;
    }
}

// ─────────────────────────────────────────────────────────────────────
// VIEWS UPDATE ACTIONS IN DATABASE EXPLORER
// ─────────────────────────────────────────────────────────────────────
function toggleViewsDropdown(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const menu = document.getElementById("views-update-menu");
    if (menu) {
        menu.style.display = menu.style.display === "block" ? "none" : "block";
    }
}

async function runViewsUpdate(period, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    // Hide menu
    const menu = document.getElementById("views-update-menu");
    if (menu) menu.style.display = "none";
    
    try {
        const res = await fetch("/api/action/update_views", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ period: period })
        });
        const data = await res.json();
        
        if (res.ok) {
            // Trigger status check immediately
            checkProcessStatus();
            alert(data.message || "Views update successfully triggered.");
        } else {
            alert(data.error || "Failed to trigger views update");
        }
    } catch (err) {
        alert("Error launching views update: " + err.message);
    }
}

// Close dropdowns and modals click handlers
document.addEventListener("click", (e) => {
    // Close views update dropdown
    const menu = document.getElementById("views-update-menu");
    const btn = document.getElementById("btn-run-views-update");
    if (menu && menu.style.display === "block") {
        if (!menu.contains(e.target) && (!btn || !btn.contains(e.target))) {
            menu.style.display = "none";
        }
    }
    
    // Close channels selector dropdown
    const chMenu = document.getElementById("channels-dropdown-menu");
    const chBtn = document.getElementById("channels-dropdown-btn");
    if (chMenu && chMenu.style.display === "block") {
        if (!chMenu.contains(e.target) && (!chBtn || !chBtn.contains(e.target))) {
            chMenu.style.display = "none";
        }
    }
});

// ESC key listener to close modals
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        const modal = document.getElementById("video-details-modal");
        if (modal && modal.style.display === "flex") {
            closeVideoModal();
        }
        const addModal = document.getElementById("add-channel-modal");
        if (addModal && addModal.style.display === "flex") {
            closeAddChannelModal();
        }
    }
});

// --- ADD CHANNEL MODAL FUNCTIONS ---
let activeAddChannelMode = "period"; // "period" or "limit"

function openAddChannelModal(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    // Close channels selector dropdown
    const menu = document.getElementById("channels-dropdown-menu");
    if (menu) menu.style.display = "none";
    
    // Reset modal form fields
    document.getElementById("ac-channel-url").value = "";
    
    const todayStr = new Date().toISOString().split("T")[0];
    document.getElementById("ac-start-date").value = todayStr;
    document.getElementById("ac-end-date").value = todayStr;
    document.getElementById("ac-limit-val").value = "50";
    
    setAddChannelMode("period");
    
    // Show Modal
    const addModal = document.getElementById("add-channel-modal");
    if (addModal) {
        addModal.style.display = "flex";
        document.body.classList.add("modal-open");
    }
}

function closeAddChannelModal() {
    const addModal = document.getElementById("add-channel-modal");
    if (addModal) {
        addModal.style.display = "none";
        document.body.classList.remove("modal-open");
    }
}

function setAddChannelMode(mode) {
    activeAddChannelMode = mode;
    
    const btnPeriod = document.getElementById("btn-ac-mode-period");
    const btnLimit = document.getElementById("btn-ac-mode-limit");
    const groupPeriod = document.getElementById("ac-group-period");
    const groupLimit = document.getElementById("ac-group-limit");
    
    if (mode === "period") {
        btnPeriod.classList.add("active");
        btnLimit.classList.remove("active");
        groupPeriod.style.display = "block";
        groupLimit.style.display = "none";
    } else {
        btnPeriod.classList.remove("active");
        btnLimit.classList.add("active");
        groupPeriod.style.display = "none";
        groupLimit.style.display = "block";
    }
}

function setAddChannelPeriodPreset(preset) {
    const now = new Date();
    let startDate = new Date(now);
    
    if (preset === "1d") {
        startDate.setDate(now.getDate() - 1);
    } else if (preset === "1w") {
        startDate.setDate(now.getDate() - 7);
    } else if (preset === "1m") {
        startDate.setMonth(now.getMonth() - 1);
    }
    
    const fmt = (d) => d.toISOString().split('T')[0];
    document.getElementById("ac-start-date").value = fmt(startDate);
    document.getElementById("ac-end-date").value = fmt(now);
}

function setAddChannelLimitPreset(limit) {
    document.getElementById("ac-limit-val").value = limit;
}

async function submitAddChannel(event) {
    if (event) event.preventDefault();
    
    const channelUrl = document.getElementById("ac-channel-url").value.trim();
    if (!channelUrl) return;
    
    let modeArg = "";
    let valArg = "";
    
    if (activeAddChannelMode === "period") {
        modeArg = "2";
        const startRaw = document.getElementById("ac-start-date").value;
        if (!startRaw) {
            alert(currentLang === 'ua' ? "Оберіть дату початку!" : "Please select a start date!");
            return;
        }
        valArg = startRaw.replace(/-/g, ""); // Strip hyphens
    } else {
        modeArg = "1";
        const limitVal = document.getElementById("ac-limit-val").value;
        if (!limitVal || parseInt(limitVal) <= 0) {
            alert(currentLang === 'ua' ? "Введіть коректний ліміт відео!" : "Please enter a valid video limit!");
            return;
        }
        valArg = parseInt(limitVal).toString();
    }
    
    closeAddChannelModal();
    
    // Switch to Operations tab so user can see logs
    switchSection("operations-tab", document.getElementById("menu-item-operations").querySelector("a"));
    
    try {
        const res = await fetch("/api/action/add_channel", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                channel_url: channelUrl,
                mode: modeArg,
                value: valArg
            })
        });
        
        const data = await res.json();
        const consoleOut = document.getElementById("console-output");
        
        if (res.ok) {
            if (consoleOut) {
                consoleOut.innerHTML += `<div class="console-line success">[SUCCESS] ${data.message}</div>`;
                consoleOut.scrollTop = consoleOut.scrollHeight;
            }
            checkProcessStatus();
        } else {
            if (consoleOut) {
                consoleOut.innerHTML += `<div class="console-line err">[ERROR] ${data.error}</div>`;
                consoleOut.scrollTop = consoleOut.scrollHeight;
            }
            alert(data.error || "Failed to trigger channel scraper.");
        }
    } catch (err) {
        alert("Error launching channel scraper: " + err.message);
    }
}
