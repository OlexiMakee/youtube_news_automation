import { state, DEFAULT_COLORS } from './state.js';
import { translations } from './translations.js';
import { renderTable, updateActiveChannelNameLabel, renderChannelsMenu, openVideoModal } from './ui.js';
import { renderActiveChart, initChartUI } from './charts.js';

// API CALL: FETCH DATABASE STATS
export async function loadStats() {
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
            document.getElementById("neon-status-msg").innerText = translations[state.currentLang].card_cloud_config + " is empty in .env";
        }
        
    } catch (err) {
        console.error("Failed to load statistics:", err);
    }
}

// API CALL: LOAD CHANNEL HEADER
export async function loadChannelStatsHeader() {
    const headerCard = document.getElementById("channel-header-card");
    if (!headerCard) return;
    
    // Helper to get selected channels from checkbox DOM
    const selected = [];
    document.querySelectorAll("#dropdown-channels-list input[type='checkbox']").forEach(chk => {
        if (chk.checked) selected.push(chk.value);
    });
    
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
                                <span class="header-stat-lbl">${state.currentLang === 'ua' ? 'Підписників' : 'Subscribers'}</span>
                            </div>
                            <div class="header-stat-badge">
                                <span class="header-stat-num">${videoCountStr}</span>
                                <span class="header-stat-lbl">${state.currentLang === 'ua' ? 'Відео в БД' : 'Videos in DB'}</span>
                            </div>
                            <div class="header-stat-badge">
                                <span class="header-stat-num">${totalViewsStr}</span>
                                <span class="header-stat-lbl">${state.currentLang === 'ua' ? 'Переглядів' : 'Views'}</span>
                            </div>
                            <div class="header-stat-badge">
                                <span class="header-stat-num">${medianViewsStr}</span>
                                <span class="header-stat-lbl">${state.currentLang === 'ua' ? 'Медіана' : 'Median'}</span>
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
                            <div class="combined-title-main">${state.currentLang === 'ua' ? 'Об\'єднана аналітика бази даних' : 'Consolidated Database Analytics'}</div>
                            <div class="combined-title-sub">${state.currentLang === 'ua' ? `Аналіз вибірки з ${channelCount} каналів` : `Analytics snapshot for ${channelCount} channels`}</div>
                        </div>
                    </div>
                    <div class="combined-banner-stats">
                        <div class="header-stat-badge">
                            <span class="header-stat-num">${channelCount}</span>
                            <span class="header-stat-lbl">${state.currentLang === 'ua' ? 'Каналів' : 'Channels'}</span>
                        </div>
                        <div class="header-stat-badge">
                            <span class="header-stat-num">${videoCountStr}</span>
                            <span class="header-stat-lbl">${state.currentLang === 'ua' ? 'Відео в БД' : 'Videos in DB'}</span>
                        </div>
                        <div class="header-stat-badge">
                            <span class="header-stat-num">${totalViewsStr}</span>
                            <span class="header-stat-lbl">${state.currentLang === 'ua' ? 'Переглядів' : 'Views'}</span>
                        </div>
                        <div class="header-stat-badge">
                            <span class="header-stat-num">${medianViewsStr}</span>
                            <span class="header-stat-lbl">${state.currentLang === 'ua' ? 'Медіана' : 'Median'}</span>
                        </div>
                    </div>
                </div>
            `;
        }
    } catch (err) {
        console.error("Failed to load channel stats header:", err);
    }
}

// API CALL: LOAD CHANNELS FOR SELECT FILTER & ANALYTICS INITIALIZATION
export async function loadChannels() {
    try {
        const res = await fetch("/api/channels");
        state.allChannels = await res.json();
        
        // Initialize default colors for channels if they don't exist
        state.allChannels.forEach((ch, idx) => {
            if (!state.channelColors[ch.channel_id]) {
                state.channelColors[ch.channel_id] = DEFAULT_COLORS[idx % DEFAULT_COLORS.length];
            }
        });
        localStorage.setItem("channel_colors", JSON.stringify(state.channelColors));
        
        // If there's no saved selection, default to selecting all channels
        if (!state.selectedChannelIds || state.selectedChannelIds.length === 0) {
            state.selectedChannelIds = state.allChannels.map(c => c.channel_id);
        } else {
            // Filter out any IDs that no longer exist
            const activeIds = state.allChannels.map(c => c.channel_id);
            state.selectedChannelIds = state.selectedChannelIds.filter(id => activeIds.includes(id));
            if (state.selectedChannelIds.length === 0 && state.allChannels.length > 0) {
                state.selectedChannelIds = state.allChannels.map(c => c.channel_id);
            }
        }
        localStorage.setItem("selected_channels", JSON.stringify(state.selectedChannelIds));
        
        renderChannelsMenu();
        applyFilters();
        
    } catch (err) {
        console.error("Failed to load channels:", err);
    }
}

// API CALL: LOAD VIDEOS TABLE WITH FILTERS
export async function loadVideos() {
    const search = document.getElementById("filter-search").value;
    
    // Helper to get selected channels from checkbox DOM
    const selected = [];
    document.querySelectorAll("#dropdown-channels-list input[type='checkbox']").forEach(chk => {
        if (chk.checked) selected.push(chk.value);
    });
    const channelId = selected.join(',');
    
    const startDate = document.getElementById("filter-start-date").value;
    const endDate = document.getElementById("filter-end-date").value;
    
    const params = new URLSearchParams({
        page: state.pagination.page,
        per_page: state.pagination.per_page,
        search: search,
        channel_id: channelId,
        start_date: startDate,
        end_date: endDate,
        columns: state.activeColumns.join(","),
        sort_by: state.sortCol,
        sort_order: state.sortDir
    });
    
    try {
        const res = await fetch(`/api/videos?${params.toString()}`);
        const data = await res.json();
        
        if (data.error) {
            console.error(data.error);
            return;
        }
        
        state.pagination.total_pages = data.total_pages;
        state.pagination.total_records = data.total_records;
        
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

// BACKGROUND OPERATION TRIGGER
export async function triggerAction(actionName) {
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
export async function checkProcessStatus() {
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
                if (span) span.innerText = state.currentLang === "ua" ? "Оновлення..." : "Updating...";
            } else {
                btnUpdate.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> <span data-i18n="btn_update_db">Update DB</span>`;
                const span = btnUpdate.querySelector("span");
                if (span) span.innerText = state.currentLang === "ua" ? "Оновити БД" : "Update DB";
            }
        }
        
        // Handle Views Update button states & animations
        if (btnViewsUpdate) {
            btnViewsUpdate.disabled = isBusy;
            if (status.status === "updating_views") {
                btnViewsUpdate.innerHTML = `<i class="fa-solid fa-chart-line fa-spin"></i> <span data-i18n="btn_updating_views">Updating...</span>`;
                const span = btnViewsUpdate.querySelector("span");
                if (span) span.innerText = state.currentLang === "ua" ? "Оновлення..." : "Updating...";
            } else {
                btnViewsUpdate.innerHTML = `<i class="fa-solid fa-chart-line"></i> <span data-i18n="btn_update_views">Update Views</span>`;
                const span = btnViewsUpdate.querySelector("span");
                if (span) span.innerText = state.currentLang === "ua" ? "Оновити перегляди" : "Update Views";
            }
        }
        
        // Handle updateBadge next to the button
        if (updateBadge) {
            if (status.status === "updating") {
                updateBadge.innerText = translations[state.currentLang].status_updating;
                updateBadge.className = "task-badge active";
                updateBadge.style.display = "inline-block";
            } else if (status.status === "updating_views") {
                updateBadge.innerText = translations[state.currentLang].status_updating_views;
                updateBadge.className = "task-badge active";
                updateBadge.style.display = "inline-block";
            } else {
                updateBadge.style.display = "none";
            }
        }
        
        // Handle main Operations tab badge
        if (badge) {
            if (status.status === "idle") {
                badge.innerText = translations[state.currentLang].status_idle;
                badge.className = "task-badge idle";
            } else {
                let statusText = "";
                if (status.status === "scraping") statusText = translations[state.currentLang].status_scraping;
                else if (status.status === "syncing") statusText = translations[state.currentLang].status_syncing;
                else if (status.status === "updating") statusText = translations[state.currentLang].status_updating;
                else if (status.status === "updating_views") statusText = translations[state.currentLang].status_updating_views;
                
                badge.innerText = statusText;
                badge.className = "task-badge active";
                
                // Reload stats dynamically while scraping/syncing/updating
                loadStats();
            }
        }
        
        // If status transitioned from "updating" or "updating_views" to "idle", reload table and chart!
        if ((state.lastKnownStatus === "updating" || state.lastKnownStatus === "updating_views") && status.status === "idle") {
            loadStats();
            loadVideos();
            loadChannelStatsHeader();
            const selected = [];
            document.querySelectorAll("#dropdown-channels-list input[type='checkbox']").forEach(chk => {
                if (chk.checked) selected.push(chk.value);
            });
            if (selected.length > 0) {
                loadChartsData(selected.join(','));
            }
        }
        
        // Update the last known status
        state.lastKnownStatus = status.status;
        
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
export async function loadChartsData(channelId) {
    if (!channelId) return;
    try {
        const startDate = document.getElementById("filter-start-date").value;
        const endDate = document.getElementById("filter-end-date").value;
        
        const params = new URLSearchParams({ channel_id: channelId });
        if (startDate) params.append("start_date", startDate);
        if (endDate) params.append("end_date", endDate);
        
        const res = await fetch(`/api/charts?${params.toString()}`);
        state.chartRawData = await res.json();
        
        // Populate KPIs
        if (state.chartRawData.kpis) {
            document.getElementById("kpi-total-views").innerText = state.chartRawData.kpis.total_views.toLocaleString();
            document.getElementById("kpi-median-views").innerText = state.chartRawData.kpis.median_views.toLocaleString();
            document.getElementById("kpi-like-ratio").innerText = state.chartRawData.kpis.like_ratio.toFixed(2) + "%";
            document.getElementById("kpi-comment-ratio").innerText = state.chartRawData.kpis.comment_ratio.toFixed(2) + "%";
        }
        
        renderActiveChart();
    } catch (err) {
        console.error("Failed to load charts data:", err);
    }
}

export function applyFilters() {
    state.pagination.page = 1;
    
    // Helper to get selected channels from checkbox DOM
    const selected = [];
    document.querySelectorAll("#dropdown-channels-list input[type='checkbox']").forEach(chk => {
        if (chk.checked) selected.push(chk.value);
    });
    
    state.selectedChannelIds = selected;
    localStorage.setItem("selected_channels", JSON.stringify(selected));
    
    updateActiveChannelNameLabel();
    
    // Close dropdown
    const menu = document.getElementById("channels-dropdown-menu");
    if (menu) menu.style.display = "none";
    
    loadVideos();
    loadChannelStatsHeader();
    
    if (selected.length > 0) {
        loadChartsData(selected.join(','));
    } else {
        // Clear charts/KPIs if nothing is selected
        state.chartRawData = null;
        document.getElementById("kpi-total-views").innerText = "0";
        document.getElementById("kpi-median-views").innerText = "0";
        document.getElementById("kpi-like-ratio").innerText = "0.00%";
        document.getElementById("kpi-comment-ratio").innerText = "0.00%";
        if (state.activeChartInstance) {
            state.activeChartInstance.destroy();
            state.activeChartInstance = null;
        }
    }
}
