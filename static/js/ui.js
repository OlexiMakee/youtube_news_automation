import { state, DEFAULT_COLORS } from './state.js';
import { translations } from './translations.js';
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
    renderModalViewsChart 
} from './charts.js';
import { initTerminal } from './terminal.js';

// LANGUAGE MANAGER
export function changeLanguage(lang) {
    state.currentLang = lang;
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
    if (state.chartRawData) {
        renderActiveChart();
    }
}

// THEME MANAGER
export function changeTheme(theme) {
    state.currentTheme = theme;
    localStorage.setItem("app_theme", theme);
    document.documentElement.setAttribute("data-theme", theme);
    
    // Redraw charts with theme-specific font colors if necessary
    if (state.chartRawData) {
        renderActiveChart();
    }
}

// SECTION TOGGLER (For real tab switching)
export function switchSection(tabId, element) {
    document.querySelectorAll(".sidebar-menu-item").forEach(item => {
        item.classList.remove("active");
    });
    
    if (element) {
        element.parentElement.classList.add("active");
    } else {
        // Fallback search menu item
        const targetMenuId = tabId === "analytics-tab" ? "menu-item-analytics" : "menu-item-terminal";
        const targetMenu = document.getElementById(targetMenuId);
        if (targetMenu) targetMenu.classList.add("active");
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
    } else if (tabId === "terminal-tab") {
        document.getElementById("section-terminal").classList.add("active");
        initTerminal();
    }
    
    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        document.getElementById("sidebar").classList.remove("open");
    }
}

export function toggleSidebar() {
    if (window.innerWidth <= 768) {
        const sidebar = document.getElementById("sidebar");
        if (sidebar) sidebar.classList.toggle("open");
    } else {
        const isCollapsed = document.body.classList.toggle("sidebar-collapsed");
        localStorage.setItem("sidebar_collapsed", isCollapsed ? "1" : "0");
    }
}

export function toggleChannelsDropdown(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    const menu = document.getElementById("channels-dropdown-menu");
    if (menu) {
        menu.style.display = menu.style.display === "block" ? "none" : "block";
    }
}

export function onChannelCheckboxChange(event) {
    // Keep checkbox state in view, click to apply filters
}

export function onChannelColorChange(channelId, newColor) {
    state.channelColors[channelId] = newColor;
    localStorage.setItem("channel_colors", JSON.stringify(state.channelColors));
    
    renderChannelsMenu();
    if (state.chartRawData) {
        renderActiveChart();
    }
}

export function toggleSelectAllChannels(selectAll) {
    document.querySelectorAll("#dropdown-channels-list input[type='checkbox']").forEach(chk => {
        chk.checked = selectAll;
    });
}

export function getSelectedChannels() {
    const list = [];
    document.querySelectorAll("#dropdown-channels-list input[type='checkbox']").forEach(chk => {
        if (chk.checked) list.push(chk.value);
    });
    return list;
}

export function updateActiveChannelNameLabel() {
    const selected = getSelectedChannels();
    const btnText = document.getElementById("dropdown-selected-text");
    const label = document.getElementById("active-analytics-channel-name");
    
    if (!btnText) return;
    
    if (selected.length === 0) {
        btnText.innerText = translations[state.currentLang].dropdown_choose_channels || "Оберіть канали";
        if (label) label.innerText = "";
    } else if (selected.length === 1) {
        const chId = selected[0];
        const chObj = state.allChannels.find(c => c.channel_id === chId);
        const name = chObj ? chObj.channel_name : chId;
        btnText.innerText = name;
        if (label) label.innerText = `[${name}]`;
    } else if (selected.length === state.allChannels.length) {
        const txt = state.currentLang === "ua" ? "Всі канали" : "All Channels";
        btnText.innerText = txt;
        if (label) label.innerText = `[${txt}]`;
    } else {
        const countText = state.currentLang === "ua" ? `Обрано: ${selected.length} кан.` : `${selected.length} channels`;
        btnText.innerText = countText;
        if (label) label.innerText = `[${countText}]`;
    }
}

export function renderChannelsMenu() {
    const listContainer = document.getElementById("dropdown-channels-list");
    if (!listContainer) return;
    
    listContainer.innerHTML = "";
    
    state.allChannels.forEach(ch => {
        const row = document.createElement("div");
        row.className = "channel-item-row";
        
        const isChecked = state.selectedChannelIds.includes(ch.channel_id) ? "checked" : "";
        const chColor = state.channelColors[ch.channel_id] || "#008abb";
        
        row.innerHTML = `
            <label class="channel-item-label" for="chk-ch-${ch.channel_id}">
                <input type="checkbox" value="${ch.channel_id}" id="chk-ch-${ch.channel_id}" ${isChecked} onchange="onChannelCheckboxChange(event)">
                <span class="channel-name-span" title="${ch.channel_name}" onclick="selectSingleChannel(event, '${ch.channel_id}')">${ch.channel_name}</span>
            </label>
            <div class="channel-color-picker-wrapper">
                <input type="color" value="${chColor}" class="channel-color-input" onchange="onChannelColorChange('${ch.channel_id}', this.value)">
            </div>
        `;
        listContainer.appendChild(row);
    });
    
    updateActiveChannelNameLabel();
}

const SORTABLE_COLS = ["published_at", "view_count", "like_count", "comment_count", "duration", "scraped_at"];

// RENDER TABLE HEADERS & ROWS DYNAMICALLY
export function renderTable(videos) {
    const headersTr = document.getElementById("table-headers");
    const bodyTbody = document.getElementById("table-body");
    
    if (!headersTr || !bodyTbody) return;
    
    headersTr.innerHTML = "";
    bodyTbody.innerHTML = "";
    
    const colLabels = {
        video_id: "ID",
        title: "Title",
        channel_name: "Channel",
        published_at: state.currentLang === "ua" ? "Дата публікації" : "Published At",
        view_count: state.currentLang === "ua" ? "Перегляди" : "Views",
        like_count: state.currentLang === "ua" ? "Лайки" : "Likes",
        comment_count: state.currentLang === "ua" ? "Коментарі" : "Comments",
        duration: state.currentLang === "ua" ? "Тривалість (с)" : "Duration (s)",
        scraped_at: state.currentLang === "ua" ? "Зібрано" : "Scraped At"
    };
    
    state.activeColumns.forEach(col => {
        const th = document.createElement("th");
        const isSortable = SORTABLE_COLS.includes(col);
        
        if (isSortable) {
            th.classList.add("th-sortable");
            if (col === state.sortCol) {
                th.classList.add(state.sortDir === "asc" ? "th-sort-asc" : "th-sort-desc");
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
        td.colSpan = state.activeColumns.length;
        td.style.textAlign = "center";
        td.style.padding = "24px";
        td.innerText = state.currentLang === "ua" ? "Жодних записів не знайдено." : "No records match search filters.";
        tr.appendChild(td);
        bodyTbody.appendChild(tr);
        return;
    }
    
    videos.forEach(v => {
        const tr = document.createElement("tr");
        tr.style.cursor = "pointer";
        tr.onclick = (e) => {
            // Do not open modal if user clicks on the link inside ID cell
            if (e.target.closest("a")) return;
            openVideoModal(v);
        };
        
        state.activeColumns.forEach(col => {
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
export function toggleSort(col) {
    if (state.sortCol === col) {
        state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
    } else {
        state.sortCol = col;
        state.sortDir = "asc";
    }
    state.pagination.page = 1;
    loadVideos();
}

export function debounceFilter() {
    clearTimeout(state.searchDebounceTimer);
    state.searchDebounceTimer = setTimeout(() => {
        applyFilters();
    }, 400);
}

export function resetFilters() {
    document.getElementById("filter-search").value = "";
    
    // Check all channels in checkboxes list
    toggleSelectAllChannels(true);
    
    // Reset date range to 6 months
    const now = new Date();
    const startDate = new Date();
    startDate.setMonth(now.getMonth() - 6);
    const fmt = (d) => d.toISOString().split('T')[0];
    document.getElementById("filter-start-date").value = fmt(startDate);
    document.getElementById("filter-end-date").value = fmt(now);
    
    // Highlight active quick-date button for 6m
    state.activeQuickDate = "6m";
    document.querySelectorAll(".quick-date-btn, .quick-date-btn-compact").forEach(b => b.classList.remove("active"));
    const activeBtn = document.getElementById("qd-6m");
    if (activeBtn) activeBtn.classList.add("active");
    
    // Reset per page limit input and select to 50
    state.pagination.per_page = 50;
    const topInput = document.getElementById("per-page-input-top");
    if (topInput) topInput.value = 50;
    const bottomSelect = document.getElementById("per-page-selector");
    if (bottomSelect) bottomSelect.value = 50;
    
    applyFilters();
}

// QUICK DATE RANGE SETTER
export function setDateRange(preset) {
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
    state.activeQuickDate = preset;
    document.querySelectorAll(".quick-date-btn, .quick-date-btn-compact").forEach(b => b.classList.remove("active"));
    const activeBtn = document.getElementById(`qd-${preset}`);
    if (activeBtn) activeBtn.classList.add("active");
    
    state.pagination.page = 1;
    loadVideos();
    
    // Also reload charts for the new date range
    const selectedIds = getSelectedChannels();
    if (selectedIds.length > 0) {
        loadChartsData(selectedIds.join(','));
        loadChannelStatsHeader();
    }
}

export function toggleColumnsSelector() {
    const panel = document.getElementById("columns-chooser-panel");
    panel.style.display = panel.style.display === "none" ? "flex" : "none";
}

export function updateColumns() {
    const list = ["title"];
    document.querySelectorAll(".column-checkbox input").forEach(cb => {
        if (cb.checked && cb.value !== "title") {
            list.push(cb.value);
        }
    });
    
    const order = ["video_id", "title", "channel_name", "published_at", "view_count", "like_count", "comment_count", "duration", "scraped_at"];
    state.activeColumns = order.filter(c => list.includes(c));
    loadVideos();
}

// PAGINATION NAVIGATION
export function changePage(direction) {
    const newPage = state.pagination.page + direction;
    if (newPage >= 1 && newPage <= state.pagination.total_pages) {
        state.pagination.page = newPage;
        loadVideos();
    }
}

export function changePerPage(val) {
    const numericVal = parseInt(val) || 25;
    state.pagination.per_page = numericVal;
    
    // Sync top-bar numeric input
    const topInput = document.getElementById("per-page-input-top");
    if (topInput) {
        topInput.value = numericVal;
    }
    
    // Sync bottom select
    const bottomSelect = document.getElementById("per-page-selector");
    if (bottomSelect) {
        if (!Array.from(bottomSelect.options).some(opt => opt.value == numericVal)) {
            const opt = document.createElement("option");
            opt.value = numericVal;
            opt.innerText = numericVal;
            bottomSelect.appendChild(opt);
        }
        bottomSelect.value = numericVal;
    }
    
    state.pagination.page = 1;
    loadVideos();
}

export function changeChartLimit(val) {
    const numericVal = parseInt(val) || 25;
    state.chartLimit = numericVal;
    localStorage.setItem("chart_limit", numericVal);
    
    // Refresh button labels on chart limit change
    initChartUI();
    
    const selected = getSelectedChannels();
    if (selected.length > 0) {
        loadChartsData(selected.join(','));
    }
}

export function selectSingleChannel(event, channelId) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    // Set only the target channel checkbox checked
    document.querySelectorAll("#dropdown-channels-list input[type='checkbox']").forEach(chk => {
        chk.checked = (chk.value === channelId);
    });
    
    applyFilters();
}

export function toggleExportDropdown(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    const menu = document.getElementById("export-menu");
    if (!menu) return;
    const isShowing = menu.style.display === "block";
    
    // Close other dropdowns
    const channelsMenu = document.getElementById("channels-dropdown-menu");
    if (channelsMenu) channelsMenu.style.display = "none";
    const viewsMenu = document.getElementById("views-update-menu");
    if (viewsMenu) viewsMenu.style.display = "none";
    
    menu.style.display = isShowing ? "none" : "block";
}

export function exportData(format, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    const menu = document.getElementById("export-menu");
    if (menu) menu.style.display = "none";
    
    const search = document.getElementById("filter-search").value;
    const channelId = getSelectedChannels().join(',');
    const startDate = document.getElementById("filter-start-date").value;
    const endDate = document.getElementById("filter-end-date").value;
    
    const params = new URLSearchParams({
        search: search,
        channel_id: channelId,
        start_date: startDate,
        end_date: endDate,
        columns: state.activeColumns.join(","),
        format: format
    });
    
    window.location.href = `/api/videos/export?${params.toString()}`;
}

// VIDEO DETAILS MODAL WINDOW & API
export function openVideoModal(video) {
    if (!video) return;
    state.activeModalVideoId = video.video_id;
    
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
    descBox.innerText = video.full_description || video.description || (state.currentLang === "ua" ? "Опис відсутній. Натисніть 'Зібрати деталі' для завантаження." : "No description available. Click 'Scrape Details' to fetch.");
    descBox.style.whiteSpace = "pre-wrap";
    
    // Reset buttons
    const downloadBtn = document.getElementById("mv-modal-download-btn");
    const downloadText = document.getElementById("mv-modal-download-text");
    downloadBtn.disabled = false;
    downloadText.innerText = translations[state.currentLang].modal_download_mp4 || "Download MP4";
    
    const scrapeBtn = document.getElementById("mv-modal-scrape-btn");
    const scrapeText = document.getElementById("mv-modal-scrape-text");
    scrapeBtn.disabled = false;
    scrapeText.innerText = translations[state.currentLang].modal_scrape_details || "Scrape Details";
    
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

export function closeVideoModal() {
    const modal = document.getElementById("video-details-modal");
    if (modal) {
        modal.style.display = "none";
        document.body.classList.remove("modal-open");
    }
    
    if (state.activeModalChartInstance) {
        state.activeModalChartInstance.destroy();
        state.activeModalChartInstance = null;
    }
    
    state.activeModalVideoId = null;
    
    // Reset download quality panel to default actions view
    hideDownloadQualityPanel();
}

export function hideDownloadQualityPanel() {
    const defaultPanel = document.getElementById("mv-modal-actions-default");
    const qualityPanel = document.getElementById("mv-download-quality-panel");
    const progressPanel = document.getElementById("mv-download-progress-panel");
    
    if (defaultPanel) defaultPanel.style.display = "flex";
    if (qualityPanel) qualityPanel.style.display = "none";
    if (progressPanel) progressPanel.style.display = "none";
}

export async function downloadVideoFromModal() {
    if (!state.activeModalVideoId) return;
    
    const defaultPanel = document.getElementById("mv-modal-actions-default");
    const qualityPanel = document.getElementById("mv-download-quality-panel");
    const progressPanel = document.getElementById("mv-download-progress-panel");
    const statusText = document.getElementById("mv-dl-progress-status");
    const progressPercent = document.getElementById("mv-dl-progress-percent");
    const progressBar = document.getElementById("mv-dl-progress-bar");
    
    // Switch to progress panel in "checking formats" state
    if (defaultPanel) defaultPanel.style.display = "none";
    if (qualityPanel) qualityPanel.style.display = "none";
    if (progressPanel) progressPanel.style.display = "flex";
    
    if (statusText) statusText.innerText = translations[state.currentLang].modal_dl_checking_formats || "Checking available formats...";
    if (progressPercent) progressPercent.innerText = "0%";
    if (progressBar) progressBar.style.width = "0%";
    
    try {
        const res = await fetch(`/api/videos/${state.activeModalVideoId}/formats`);
        if (!res.ok) {
            throw new Error("Failed to load formats");
        }
        const data = await res.json();
        const formats = data.formats || ["720", "audio"]; // fallback
        
        // Dynamically build formats options inside mv-download-quality-options
        const optionsContainer = document.getElementById("mv-download-quality-options");
        if (optionsContainer) {
            optionsContainer.innerHTML = "";
            
            formats.forEach((fmt, index) => {
                const label = document.createElement("label");
                label.className = "quality-option";
                label.style.cssText = "display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-color); cursor: pointer; padding: 6px; border-radius: 4px; transition: background 0.2s;";
                
                // Add hover style
                label.onmouseover = () => label.style.background = "var(--bg-hover)";
                label.onmouseout = () => label.style.background = "transparent";
                
                const radio = document.createElement("input");
                radio.type = "radio";
                radio.name = "video-quality";
                radio.value = fmt;
                if (index === 0) {
                    radio.checked = true;
                }
                
                const span = document.createElement("span");
                if (fmt === "audio") {
                    span.innerText = translations[state.currentLang].modal_dl_audio_only || "Audio Only (M4A)";
                } else {
                    span.innerText = `${fmt}p`;
                }
                
                label.appendChild(radio);
                label.appendChild(span);
                optionsContainer.appendChild(label);
            });
        }
        
        // Switch to quality selector panel
        if (progressPanel) progressPanel.style.display = "none";
        if (qualityPanel) qualityPanel.style.display = "flex";
        
    } catch (err) {
        alert(state.currentLang === 'ua' ? `Не вдалося отримати формати: ${err.message}` : `Failed to get formats: ${err.message}`);
        // Go back to default buttons
        if (progressPanel) progressPanel.style.display = "none";
        if (defaultPanel) defaultPanel.style.display = "flex";
    }
}

export async function startVideoDownload() {
    const videoId = state.activeModalVideoId;
    if (!videoId) return;
    
    // Get selected quality
    const selectedRadio = document.querySelector('input[name="video-quality"]:checked');
    const quality = selectedRadio ? selectedRadio.value : "720";
    
    const qualityPanel = document.getElementById("mv-download-quality-panel");
    const progressPanel = document.getElementById("mv-download-progress-panel");
    const statusText = document.getElementById("mv-dl-progress-status");
    const progressPercent = document.getElementById("mv-dl-progress-percent");
    const progressBar = document.getElementById("mv-dl-progress-bar");
    
    // Suggest clean name based on title
    const titleText = document.getElementById("mv-modal-title").innerText || videoId;
    const cleanTitle = titleText.replace(/[^a-zA-Z0-9\sа-яА-ЯіІєЄїЇґҐ]/g, "").trim().replace(/\s+/g, "_");
    const ext = quality === "audio" ? "m4a" : "mp4";
    const filename = `${cleanTitle}.${ext}`;
    
    let fileWritable = null;
    let useFilePicker = false;
    
    // Prompt where to save using showSaveFilePicker if available
    if (window.showSaveFilePicker) {
        try {
            const handle = await window.showSaveFilePicker({
                suggestedName: filename,
                types: [{
                    description: quality === "audio" ? 'Audio File' : 'Video File',
                    accept: quality === "audio" ? { 'audio/mp4': ['.m4a'] } : { 'video/mp4': ['.mp4'] }
                }]
            });
            fileWritable = await handle.createWritable();
            useFilePicker = true;
        } catch (err) {
            if (err.name === 'AbortError') {
                // User cancelled the file dialog
                return;
            }
            console.warn("showSaveFilePicker failed or was rejected, falling back to legacy download", err);
        }
    }
    
    // Switch to progress panel
    if (qualityPanel) qualityPanel.style.display = "none";
    if (progressPanel) progressPanel.style.display = "flex";
    
    if (statusText) statusText.innerText = translations[state.currentLang].modal_dl_yt_status || "Fetching from YouTube...";
    if (progressPercent) progressPercent.innerText = "0%";
    if (progressBar) progressBar.style.width = "0%";
    
    try {
        const downloadUrl = `/api/videos/${videoId}/download?quality=${quality}`;
        const response = await fetch(downloadUrl);
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error || "Failed to download");
        }
        
        if (statusText) statusText.innerText = translations[state.currentLang].modal_dl_saving_status || "Saving to disk...";
        
        if (useFilePicker && fileWritable) {
            const reader = response.body.getReader();
            const contentLength = +response.headers.get('Content-Length');
            let receivedLength = 0;
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                await fileWritable.write(value);
                receivedLength += value.length;
                
                if (contentLength) {
                    const percent = Math.round((receivedLength / contentLength) * 100);
                    if (progressPercent) progressPercent.innerText = `${percent}%`;
                    if (progressBar) progressBar.style.width = `${percent}%`;
                }
            }
            await fileWritable.close();
            
            alert(translations[state.currentLang].modal_dl_save_success || "Video downloaded successfully!");
            hideDownloadQualityPanel();
        } else {
            // Legacy fallback using blob/objectURL
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            hideDownloadQualityPanel();
        }
        
    } catch (err) {
        alert(state.currentLang === 'ua' ? `Помилка завантаження: ${err.message}` : `Download failed: ${err.message}`);
        hideDownloadQualityPanel();
    }
}

export async function scrapeDetailsFromModal() {
    const btn = document.getElementById("mv-modal-scrape-btn");
    const txt = document.getElementById("mv-modal-scrape-text");
    if (!state.activeModalVideoId || btn.disabled) return;
    
    const oldText = txt.innerText;
    txt.innerText = translations[state.currentLang].modal_scraping || "Scraping...";
    btn.disabled = true;
    
    try {
        const res = await fetch(`/api/videos/${state.activeModalVideoId}/scrape_details`, {
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
        
        if (state.chartRawData) {
            ["top_viewed", "worst_viewed", "top_liked", "worst_liked", "top_commented", "worst_commented"].forEach(listKey => {
                updateVideoFields(state.chartRawData[listKey], state.activeModalVideoId, data);
            });
        }
        
        loadVideos();
        loadStats();
        alert(state.currentLang === 'ua' ? "Дані успішно оновлено!" : "Video statistics successfully updated!");
    } catch (err) {
        alert(state.currentLang === 'ua' ? `Не вдалося отримати деталі: ${err.message}` : `Scrape failed: ${err.message}`);
    } finally {
        btn.disabled = false;
        txt.innerText = oldText;
    }
}

// VIEWS UPDATE ACTIONS IN DATABASE EXPLORER
export function toggleViewsDropdown(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const menu = document.getElementById("views-update-menu");
    if (menu) {
        menu.style.display = menu.style.display === "block" ? "none" : "block";
    }
}

export async function runViewsUpdate(period, event) {
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

// --- ADD CHANNEL MODAL FUNCTIONS ---
export let activeAddChannelMode = "period"; // "period" or "limit"

export function openAddChannelModal(event) {
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

export function closeAddChannelModal() {
    const addModal = document.getElementById("add-channel-modal");
    if (addModal) {
        addModal.style.display = "none";
        document.body.classList.remove("modal-open");
    }
}

export function setAddChannelMode(mode) {
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

export function setAddChannelPeriodPreset(preset) {
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

export function setAddChannelLimitPreset(limit) {
    document.getElementById("ac-limit-val").value = limit;
}

export async function submitAddChannel(event) {
    if (event) event.preventDefault();
    
    const channelUrl = document.getElementById("ac-channel-url").value.trim();
    if (!channelUrl) return;
    
    let modeArg = "";
    let valArg = "";
    
    if (activeAddChannelMode === "period") {
        modeArg = "2";
        const startRaw = document.getElementById("ac-start-date").value;
        if (!startRaw) {
            alert(state.currentLang === 'ua' ? "Оберіть дату початку!" : "Please select a start date!");
            return;
        }
        valArg = startRaw.replace(/-/g, ""); // Strip hyphens
    } else {
        modeArg = "1";
        const limitVal = document.getElementById("ac-limit-val").value;
        if (!limitVal || parseInt(limitVal) <= 0) {
            alert(state.currentLang === 'ua' ? "Введіть коректний ліміт відео!" : "Please enter a valid video limit!");
            return;
        }
        valArg = parseInt(limitVal).toString();
    }
    
    closeAddChannelModal();
    
    // Switch to Terminal tab so user can see logs
    switchSection("terminal-tab", document.getElementById("menu-item-terminal").querySelector("a"));
    
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

// AI CHAT UI METHODS
export function toggleChatDrawer() {
    const drawer = document.getElementById("chat-drawer");
    if (drawer) {
        const isOpen = drawer.classList.toggle("open");
        if (window.innerWidth > 768) {
            document.body.classList.toggle("chat-drawer-open", isOpen);
        }
    }
}

export async function handleSendChatMessage(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    const inputEl = document.getElementById("chat-input");
    const containerEl = document.getElementById("chat-messages");
    if (!inputEl || !containerEl) return;
    
    const message = inputEl.value.trim();
    if (!message) return;
    
    // Clear input
    inputEl.value = "";
    
    // Append User Bubble
    const userDiv = document.createElement("div");
    userDiv.className = "chat-bubble user";
    userDiv.innerText = message;
    containerEl.appendChild(userDiv);
    
    // Auto-scroll
    containerEl.scrollTop = containerEl.scrollHeight;
    
    // Add Bot Typing placeholder
    const botTypingDiv = document.createElement("div");
    botTypingDiv.className = "chat-bubble bot typing";
    botTypingDiv.innerHTML = `<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>`;
    containerEl.appendChild(botTypingDiv);
    containerEl.scrollTop = containerEl.scrollHeight;
    
    try {
        const res = await fetch("/api/agent/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: message })
        });
        const data = await res.json();
        
        // Remove typing indicator
        if (botTypingDiv.parentNode) {
            botTypingDiv.parentNode.removeChild(botTypingDiv);
        }
        
        // Append Bot Response
        const botDiv = document.createElement("div");
        botDiv.className = "chat-bubble bot";
        if (data.error) {
            botDiv.classList.add("error");
            botDiv.innerText = `Error: ${data.error}`;
        } else {
            botDiv.innerText = data.response;
        }
        containerEl.appendChild(botDiv);
        containerEl.scrollTop = containerEl.scrollHeight;
        
    } catch (err) {
        if (botTypingDiv.parentNode) {
            botTypingDiv.parentNode.removeChild(botTypingDiv);
        }
        const errorDiv = document.createElement("div");
        errorDiv.className = "chat-bubble bot error";
        errorDiv.innerText = `Network error: ${err.message}`;
        containerEl.appendChild(errorDiv);
        containerEl.scrollTop = containerEl.scrollHeight;
    }
}
