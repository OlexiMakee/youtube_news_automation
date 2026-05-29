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
    state.currentSection = tabId;
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
        
        // Hover video preview tooltip
        tr.onmouseenter = (e) => {
            showTableTooltip(e, v);
        };
        tr.onmousemove = (e) => {
            positionTableTooltip(e);
        };
        tr.onmouseleave = () => {
            hideTableTooltip();
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

    // Trigger background OCR for top 20 most viewed visible thumbnails without text
    const ocrQueue = [...videos]
        .sort((a, b) => (b.view_count || 0) - (a.view_count || 0))
        .filter(v => !v.thumbnail_text || v.thumbnail_text.trim() === "")
        .slice(0, 20)
        .map(v => v.video_id);
        
    if (ocrQueue.length > 0) {
        fetch("/api/videos/ocr_thumbnails", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_ids: ocrQueue })
        }).catch(err => console.error("[OCR Auto] Failed to queue background OCR:", err));
    }
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
    renderModalComments(video.top_comments);
    
    // Hide table hover tooltip if visible
    hideTableTooltip();
    
    // Show Modal overlay
    const modal = document.getElementById("video-details-modal");
    if (modal) {
        modal.style.display = "flex";
        document.body.classList.add("modal-open");
    }
    
    // Automatically trigger detailed scraping if the database record is missing details
    if (!isVideoFullyScraped(video)) {
        setTimeout(() => {
            scrapeDetailsFromModal(true);
        }, 100);
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

export async function scrapeDetailsFromModal(isAuto = false) {
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
        renderModalComments(data.top_comments);
        
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
                found.top_comments = scrapedData.top_comments;
            }
        };
        
        if (state.chartRawData) {
            ["top_viewed", "worst_viewed", "top_liked", "worst_liked", "top_commented", "worst_commented"].forEach(listKey => {
                updateVideoFields(state.chartRawData[listKey], state.activeModalVideoId, data);
            });
        }
        
        loadVideos();
        loadStats();
        if (!isAuto) {
            alert(state.currentLang === 'ua' ? "Дані успішно оновлено!" : "Video statistics successfully updated!");
        }
    } catch (err) {
        if (!isAuto) {
            alert(state.currentLang === 'ua' ? `Не вдалося отримати деталі: ${err.message}` : `Scrape failed: ${err.message}`);
        } else {
            console.error("Auto scrape failed:", err);
        }
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


/** Scrapes all text information from the currently active visualization */
function _scrapeActiveChartText() {
    const chartType = state.activeChartType || "top_viewed";
    const chartData = state.chartRawData ? state.chartRawData[chartType] : null;
    
    const chartTitleKey = 'chart_' + chartType;
    const chartTitle = (translations[state.currentLang] && translations[state.currentLang][chartTitleKey]) || chartType;
    
    if (!chartData || !Array.isArray(chartData) || chartData.length === 0) {
        return `Немає даних для поточної візуалізації "${chartTitle}".`;
    }

    let text = `Дані з вікна візуалізації "${chartTitle}":\n\n`;

    const isVideoChart = [
        "top_viewed", "worst_viewed", "top_liked", "worst_liked", "top_commented", "worst_commented"
    ].includes(chartType);

    if (isVideoChart) {
        chartData.forEach((v, index) => {
            const num = index + 1;
            const title = v.title || (state.currentLang === "ua" ? "Без назви" : "Untitled");
            const published = v.published_at ? v.published_at.substring(0, 10) : "-";
            const channel = (state.allChannels || []).find(c => c.channel_id === v.channel_id);
            const channelName = channel ? channel.channel_name : "Unknown";
            
            let metricText = "";
            if (chartType.includes("viewed")) {
                metricText = `${state.currentLang === 'ua' ? 'Перегляди' : 'Views'}: ${v.view_count || 0}`;
            } else if (chartType.includes("liked")) {
                metricText = `${state.currentLang === 'ua' ? 'Лайки' : 'Likes'}: ${v.like_count || 0}`;
            } else if (chartType.includes("commented")) {
                metricText = `${state.currentLang === 'ua' ? 'Коментарі' : 'Comments'}: ${v.comment_count || 0}`;
            }
            
            text += `${num}. "${title}" | ${state.currentLang === 'ua' ? 'Канал' : 'Channel'}: ${channelName} | ${state.currentLang === 'ua' ? 'Дата' : 'Date'}: ${published} | ${metricText}\n`;
        });
    } else {
        // Words, tags, etc.
        chartData.forEach((item, index) => {
            const num = index + 1;
            const label = item.word || item.tag || item.phrase || "Unknown";
            const lift = item.lift ? item.lift.toFixed(2) : "0.00";
            const count = item.video_count || item.count || 0;
            const views = item.total_views || item.sum_views || item.views || 0;
            
            if (state.currentLang === 'ua') {
                text += `${num}. Слово/Тег: "${label}" | Множник Lift: ${lift}x | Кількість відео: ${count} | Сума переглядів: ${views}\n`;
            } else {
                text += `${num}. Word/Tag: "${label}" | Lift Factor: ${lift}x | Videos: ${count} | Total Views: ${views}\n`;
            }
        });
    }

    return text;
}

/** Returns {channelIds, startDate, endDate} from current UI state */
function _getChatContext() {
    const startEl = document.getElementById("filter-start-date");
    const endEl   = document.getElementById("filter-end-date");
    return {
        channel_ids: state.selectedChannelIds || [],
        start_date:  startEl ? startEl.value : "",
        end_date:    endEl   ? endEl.value   : ""
    };
}

/** Selected model id from the dropdown (empty = server default) */
function _getSelectedModel() {
    const sel = document.getElementById("chat-model-select");
    return sel ? sel.value : "";
}

export async function changeChatProvider(provider) {
    state.agentProvider = provider;
    await _loadModels();
}

export function switchAgentRole(role) {
    state.agentRole = role;
    const adminBtn = document.getElementById("chat-tab-admin");
    const userBtn = document.getElementById("chat-tab-user");
    if (adminBtn && userBtn) {
        if (role === 'admin') {
            adminBtn.classList.add("active");
            adminBtn.style.borderBottom = "2px solid var(--accent-color)";
            adminBtn.style.color = "var(--text-color)";
            userBtn.classList.remove("active");
            userBtn.style.borderBottom = "2px solid transparent";
            userBtn.style.color = "var(--text-muted)";
        } else {
            userBtn.classList.add("active");
            userBtn.style.borderBottom = "2px solid var(--accent-color)";
            userBtn.style.color = "var(--text-color)";
            adminBtn.classList.remove("active");
            adminBtn.style.borderBottom = "2px solid transparent";
            adminBtn.style.color = "var(--text-muted)";
        }
    }
}

/** Loads model list from backend and populates the selector */
async function _loadModels() {
    const sel = document.getElementById("chat-model-select");
    if (!sel) return;
    try {
        const res  = await fetch(`/api/agent/models?provider=${state.agentProvider}`);
        const data = await res.json();
        const models = data.models || [];
        sel.innerHTML = "";
        if (models.length === 0) {
            sel.innerHTML = '<option value="">Авто (за замовчуванням)</option>';
        } else {
            const def = document.createElement("option");
            def.value = ""; def.textContent = "Авто (за замовчуванням)";
            sel.appendChild(def);
            models.forEach(m => {
                const opt = document.createElement("option");
                opt.value = m.id;
                opt.textContent = m.id;
                sel.appendChild(opt);
            });
        }
    } catch (e) {
        sel.innerHTML = '<option value="">Авто (за замовчуванням)</option>';
        console.warn("[chat] loadModels error:", e);
    }
}

/** Collects prior assistant/user messages from chat history */
function _getChatHistory() {
    const containerEl = document.getElementById("chat-messages");
    if (!containerEl) return [];
    
    const bubbles = containerEl.querySelectorAll(".chat-bubble");
    const history = [];
    bubbles.forEach(bubble => {
        if (bubble.classList.contains("typing") || bubble.classList.contains("streaming")) {
            return;
        }
        
        let role = null;
        if (bubble.classList.contains("user")) {
            role = "user";
        } else if (bubble.classList.contains("bot")) {
            role = "assistant";
        }
        
        if (role) {
            const content = bubble.dataset.raw || bubble.innerText || "";
            if (content.trim()) {
                history.push({ role, content });
            }
        }
    });
    return history;
}

/** Streams a response from /api/agent/chat/stream, appending tokens to botDiv */
async function _streamBotMessage(message, containerEl, contextOverride = null, history = []) {
    const ctx = _getChatContext();
    const modelId = _getSelectedModel();

    // Create bubble immediately
    const botDiv = document.createElement("div");
    botDiv.className = "chat-bubble bot streaming";
    botDiv.innerText = "";
    containerEl.appendChild(botDiv);
    containerEl.scrollTop = containerEl.scrollHeight;

    let hasError = false;
    let accumulatedText = "";
    try {
        const payload = {
            message,
            channel_ids: ctx.channel_ids,
            start_date:  ctx.start_date,
            end_date:    ctx.end_date,
            provider:    state.agentProvider,
            model_id:    modelId || null,
            role:        state.agentRole,
            history:     history
        };
        if (contextOverride) {
            payload.context_override = contextOverride;
        }

        const res = await fetch("/api/agent/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split("\n");
            buffer = lines.pop(); // keep incomplete line in buffer

            for (const line of lines) {
                if (!line.startsWith("data:")) continue;
                const payload = line.slice(5).trim();
                if (payload === "[DONE]") {
                    botDiv.classList.remove("streaming");
                    if (window.marked) {
                        botDiv.innerHTML = window.marked.parse ? window.marked.parse(accumulatedText) : window.marked(accumulatedText);
                    } else {
                        botDiv.innerText = accumulatedText;
                    }
                    botDiv.dataset.raw = accumulatedText;
                    return;
                }
                try {
                    const obj = JSON.parse(payload);
                    if (obj.error) {
                        hasError = true;
                        botDiv.classList.add("error");
                        botDiv.innerText = `Помилка: ${obj.error}`;
                        botDiv.classList.remove("streaming");
                        return;
                    }
                    if (obj.text) {
                        accumulatedText += obj.text;
                        botDiv.dataset.raw = accumulatedText;
                        if (window.marked) {
                            botDiv.innerHTML = window.marked.parse ? window.marked.parse(accumulatedText) : window.marked(accumulatedText);
                        } else {
                            botDiv.innerText = accumulatedText;
                        }
                        containerEl.scrollTop = containerEl.scrollHeight;
                    }
                } catch (_) { /* skip malformed */ }
            }
        }
    } catch (err) {
        if (!hasError) {
            botDiv.classList.add("error");
            botDiv.innerText = `Помилка з'єднання: ${err.message}`;
        }
    } finally {
        botDiv.classList.remove("streaming");
    }
}

export function toggleChatDrawer(forceClose = false) {
    const drawer = document.getElementById("chat-drawer");
    if (!drawer) return;

    const isCurrentlyOpen = drawer.classList.contains("open");

    if (isCurrentlyOpen && !forceClose) {
        // Chat is open, and we clicked the global "Summarize" button again -> request another summary from the current screen!
        _requestAddScreenSummary();
        return;
    }

    let newOpenState = !isCurrentlyOpen;
    if (forceClose) {
        newOpenState = false;
    }

    if (newOpenState) {
        drawer.classList.add("open");
    } else {
        drawer.classList.remove("open");
    }

    if (window.innerWidth > 768) {
        document.body.classList.toggle("chat-drawer-open", newOpenState);
    }

    if (newOpenState) {
        _loadModels();
        _requestAutoSummary();
    }
}

async function _requestAutoSummary() {
    const containerEl = document.getElementById("chat-messages");
    if (!containerEl) return;
    containerEl.innerHTML = "";

    // Show typing indicator while context builds
    const typingDiv = document.createElement("div");
    typingDiv.className = "chat-bubble bot typing";
    typingDiv.innerHTML = `<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>`;
    containerEl.appendChild(typingDiv);
    containerEl.scrollTop = containerEl.scrollHeight;

    // Brief delay so model selector starts loading first
    await new Promise(r => setTimeout(r, 400));
    if (typingDiv.parentNode) typingDiv.parentNode.removeChild(typingDiv);

    const screenText = _scrapeCurrentScreenText();
    await _streamBotMessage(
        "Зроби висновки",
        containerEl,
        screenText,
        []
    );
}

export async function handleSendChatMessage(event) {
    if (event) { event.preventDefault(); event.stopPropagation(); }

    const inputEl     = document.getElementById("chat-input");
    const containerEl = document.getElementById("chat-messages");
    if (!inputEl || !containerEl) return;

    const message = inputEl.value.trim();
    if (!message) return;
    inputEl.value = "";

    // Collect history before appending new user bubble
    const history = _getChatHistory();

    // User bubble
    const userDiv = document.createElement("div");
    userDiv.className = "chat-bubble user";
    userDiv.innerText = message;
    userDiv.dataset.raw = message;
    containerEl.appendChild(userDiv);
    containerEl.scrollTop = containerEl.scrollHeight;

    // Stream bot reply with context of current screen
    const screenText = _scrapeCurrentScreenText();
    await _streamBotMessage(message, containerEl, screenText, history);
}


export function renderModalComments(topComments) {
    const commentsTitle = document.getElementById("mv-modal-comments-title");
    const commentsList = document.getElementById("mv-modal-comments-list");
    
    if (!commentsTitle || !commentsList) return;
    
    let parsedComments = [];
    if (topComments) {
        try {
            parsedComments = typeof topComments === "string" ? JSON.parse(topComments) : topComments;
        } catch (err) {
            console.error("Failed to parse top_comments:", err);
            parsedComments = [];
        }
    }
    
    if (parsedComments && parsedComments.length > 0) {
        commentsList.innerHTML = "";
        parsedComments.forEach(c => {
            const commentDiv = document.createElement("div");
            commentDiv.style.borderBottom = "1px solid var(--border-color)";
            commentDiv.style.paddingBottom = "6px";
            commentDiv.style.marginBottom = "6px";
            
            commentDiv.innerHTML = `
                <div style="font-weight: 600; color: var(--accent-color); margin-bottom: 2px; display: flex; justify-content: space-between;">
                    <span>${c.author}</span>
                    <span style="font-weight: normal; font-size: 10px; color: var(--text-color); opacity: 0.8;"><i class="fa-solid fa-thumbs-up"></i> ${c.likes}</span>
                </div>
                <div style="color: var(--text-color); line-height: 1.3;">${c.text}</div>
            `;
            commentsList.appendChild(commentDiv);
        });
        if (commentsList.lastChild) {
            commentsList.lastChild.style.borderBottom = "none";
            commentsList.lastChild.style.paddingBottom = "0";
            commentsList.lastChild.style.marginBottom = "0";
        }
        commentsTitle.style.display = "block";
        commentsList.style.display = "flex";
    } else {
        commentsTitle.style.display = "none";
        commentsList.style.display = "none";
    }
}

// ─── Table Hover Tooltip & Auto-Scrape Helpers ───────────────────────

let tableTooltipEl = null;

function ensureTableTooltip() {
    if (tableTooltipEl) return tableTooltipEl;
    tableTooltipEl = document.createElement("div");
    tableTooltipEl.className = "d3-tooltip";
    tableTooltipEl.style.display = "none";
    document.body.appendChild(tableTooltipEl);
    return tableTooltipEl;
}

function showTableTooltip(event, video) {
    if (state.activeModalVideoId) return; // Don't show hover preview if modal is open
    const tip = ensureTableTooltip();
    const lang = state.currentLang === 'ua' ? 'ua' : 'en';
    const title = video.title || (lang === 'ua' ? 'Без назви' : 'Untitled');
    const channel = video.channel_name || '—';
    const date = video.published_at || '—';
    const views = video.view_count ? parseInt(video.view_count).toLocaleString() : '0';
    const likes = video.like_count ? parseInt(video.like_count).toLocaleString() : '0';
    const comments = video.comment_count ? parseInt(video.comment_count).toLocaleString() : '0';
    const thumbnailUrl = `https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`;
    
    const viewsLabel = lang === 'ua' ? 'Перегляди' : 'Views';
    const likesLabel = lang === 'ua' ? 'Лайки' : 'Likes';
    const commentsLabel = lang === 'ua' ? 'Коментарі' : 'Comments';

    tip.innerHTML = `
        <div class="d3-tip-thumb-wrap">
            <img class="d3-tip-thumb" src="${thumbnailUrl}" alt="" loading="lazy" onerror="this.style.display='none'">
        </div>
        <div class="d3-tip-body" style="padding: 10px 14px 12px;">
            <div class="d3-tip-title" style="margin-bottom: 8px;">${title}</div>
            <div style="font-size: 11px; color: var(--text-color); opacity: 0.8; margin-bottom: 6px;">
                <i class="fa-solid fa-tv" style="margin-right: 4px;"></i>${channel}
            </div>
            <div class="d3-tip-meta" style="display: flex; flex-direction: column; align-items: flex-start; gap: 4px;">
                <div style="display: flex; justify-content: space-between; width: 100%; font-size: 11px;">
                    <span class="d3-tip-metric">${viewsLabel}: <strong>${views}</strong></span>
                    <span class="d3-tip-metric">${likesLabel}: <strong>${likes}</strong></span>
                </div>
                <div style="display: flex; justify-content: space-between; width: 100%; font-size: 11px;">
                    <span class="d3-tip-metric">${commentsLabel}: <strong>${comments}</strong></span>
                    <span class="d3-tip-date">${date}</span>
                </div>
            </div>
        </div>
    `;
    tip.style.display = 'block';
    positionTableTooltip(event);
}

function positionTableTooltip(event) {
    if (!tableTooltipEl) return;
    const tipW = tableTooltipEl.offsetWidth;
    const tipH = tableTooltipEl.offsetHeight;
    const pad = 16;
    let x = event.pageX + pad;
    let y = event.pageY - tipH / 2;

    if (x + tipW > window.innerWidth + window.scrollX - pad) {
        x = event.pageX - tipW - pad;
    }
    if (y < window.scrollY + pad) {
        y = window.scrollY + pad;
    }
    if (y + tipH > window.innerHeight + window.scrollY - pad) {
        y = window.innerHeight + window.scrollY - tipH - pad;
    }

    tableTooltipEl.style.left = `${x}px`;
    tableTooltipEl.style.top = `${y}px`;
}

function hideTableTooltip() {
    if (tableTooltipEl) {
        tableTooltipEl.style.display = 'none';
    }
}

function isVideoFullyScraped(video) {
    if (!video) return true;
    const hasFullDesc = video.full_description !== null && video.full_description !== undefined && video.full_description !== "";
    const hasTopComments = video.top_comments !== null && video.top_comments !== undefined && video.top_comments !== "" && video.top_comments !== "[]";
    const hasViewsUpdate = video.views_update !== null && video.views_update !== undefined && video.views_update !== "" && video.views_update !== "[]";
    const hasLikes = video.like_count !== null && video.like_count !== undefined;
    const hasComments = video.comment_count !== null && video.comment_count !== undefined;
    return hasFullDesc && hasTopComments && hasViewsUpdate && hasLikes && hasComments;
}

// ─── AI Screen Summarization Parsers ─────────────────────────────────

async function _requestAddScreenSummary() {
    const containerEl = document.getElementById("chat-messages");
    if (!containerEl) return;

    // Collect history before appending new user bubble
    const history = _getChatHistory();

    const userText = state.currentLang === "ua" ? "Зроби висновки з поточного екрану" : "Make conclusions from the current screen";

    // User bubble
    const userDiv = document.createElement("div");
    userDiv.className = "chat-bubble user";
    userDiv.innerText = userText;
    userDiv.dataset.raw = userText;
    containerEl.appendChild(userDiv);
    containerEl.scrollTop = containerEl.scrollHeight;

    // Stream bot reply with context of current screen
    const screenText = _scrapeCurrentScreenText();
    await _streamBotMessage(
        "Зроби висновки",
        containerEl,
        screenText,
        history
    );
}

function _scrapeCurrentScreenText() {
    if (state.activeModalVideoId) {
        const modal = document.getElementById("video-details-modal");
        if (modal && modal.style.display === "flex") {
            return _scrapeVideoModalText();
        }
    }
    if (state.currentSection === "terminal-tab") {
        return _scrapeTerminalAndTableText();
    }
    return _scrapeActiveChartText();
}

function _scrapeVideoModalText() {
    const title = document.getElementById("mv-modal-title")?.innerText || "";
    const views = document.getElementById("mv-modal-views")?.innerText || "";
    const likes = document.getElementById("mv-modal-likes")?.innerText || "";
    const commentsCount = document.getElementById("mv-modal-comments")?.innerText || "";
    const date = document.getElementById("mv-modal-date")?.innerText || "";
    const description = document.getElementById("mv-modal-description")?.innerText || "";
    
    let text = `Дані з відкритого вікна відео:\n`;
    text += `Назва: "${title}"\n`;
    text += `Дата публікації: ${date}\n`;
    text += `Перегляди: ${views} | Лайки: ${likes} | Коментарі: ${commentsCount}\n\n`;
    text += `Опис:\n${description}\n\n`;
    
    const commentsList = document.getElementById("mv-modal-comments-list");
    if (commentsList && commentsList.style.display !== "none") {
        text += `Коментарі глядачів:\n`;
        Array.from(commentsList.children).forEach(div => {
            text += `- ${div.innerText.replace(/\n/g, ' | ')}\n`;
        });
    }
    return text;
}

function _scrapeTerminalAndTableText() {
    let text = "Дані з вікна терміналу та таблиці відео:\n\n";
    
    text += "--- Останні рядки терміналу ---\n";
    let termText = "";
    if (state.term) {
        const buffer = state.term.buffer.active;
        const startLine = Math.max(0, buffer.length - 60);
        for (let i = startLine; i < buffer.length; i++) {
            const line = buffer.getLine(i);
            if (line) {
                termText += line.translateToString(true) + "\n";
            }
        }
    }
    text += (termText.trim() || "[Термінал порожній або не ініціалізований]") + "\n\n";
    
    text += "--- Дані таблиці відео (Database Explorer) ---\n";
    text += _scrapeTableText();
    
    return text;
}

function _scrapeTableText() {
    let text = "";
    const recordsCount = document.getElementById("explorer-records-count")?.innerText || "";
    text += `Статус таблиці: ${recordsCount}\n\n`;
    
    const table = document.getElementById("data-table");
    if (table) {
        const headers = Array.from(table.querySelectorAll("thead th")).map(th => th.innerText.trim());
        text += `Колонки: ${headers.join(" | ")}\n`;
        
        const rows = table.querySelectorAll("tbody tr");
        if (rows.length > 0) {
            text += `Записи в таблиці:\n`;
            rows.forEach((tr, idx) => {
                if (tr.innerText.includes("Жодних записів") || tr.innerText.includes("No records match")) {
                    return;
                }
                const cells = Array.from(tr.querySelectorAll("td")).map(td => td.innerText.trim());
                text += `${idx + 1}. ${cells.join(" | ")}\n`;
            });
        }
    }
    return text;
}

export function initChatResizer() {
    const resizer = document.getElementById("chat-resizer");
    const drawer = document.getElementById("chat-drawer");
    if (!resizer || !drawer) return;

    let isResizing = false;

    // Mouse events
    resizer.addEventListener("mousedown", function(e) {
        e.preventDefault();
        isResizing = true;
        resizer.classList.add("active");
        document.body.style.cursor = "ew-resize";
        document.body.style.userSelect = "none";
    });

    window.addEventListener("mousemove", function(e) {
        if (!isResizing) return;

        let newWidth = window.innerWidth - e.clientX;
        const minWidth = 380;
        const maxWidth = Math.floor(window.innerWidth / 2);

        if (newWidth < minWidth) {
            newWidth = minWidth;
        } else if (newWidth > maxWidth) {
            newWidth = maxWidth;
        }

        document.documentElement.style.setProperty("--chat-width", newWidth + "px");
    });

    window.addEventListener("mouseup", function() {
        if (isResizing) {
            isResizing = false;
            resizer.classList.remove("active");
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
            window.dispatchEvent(new Event('resize'));
        }
    });

    // Touch events
    resizer.addEventListener("touchstart", function(e) {
        isResizing = true;
        resizer.classList.add("active");
        document.body.style.userSelect = "none";
    });

    window.addEventListener("touchmove", function(e) {
        if (!isResizing) return;
        if (e.touches.length === 0) return;
        let newWidth = window.innerWidth - e.touches[0].clientX;
        const minWidth = 380;
        const maxWidth = Math.floor(window.innerWidth / 2);
        if (newWidth < minWidth) newWidth = minWidth;
        if (newWidth > maxWidth) newWidth = maxWidth;
        document.documentElement.style.setProperty("--chat-width", newWidth + "px");
    });

    window.addEventListener("touchend", function() {
        if (isResizing) {
            isResizing = false;
            resizer.classList.remove("active");
            document.body.style.userSelect = "";
            window.dispatchEvent(new Event('resize'));
        }
    });
}

