import { state } from './state.js';
import { translations } from './translations.js';
import { openVideoModal } from './ui.js';

export const CHART_DEFS = [
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

export function initChartUI() {
    const container = document.getElementById('chart-controls-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    const statsElements = [];
    const promoElements = [];
    const otherElements = [];
    
    const processedIds = new Set();
    
    CHART_DEFS.forEach(def => {
        if (processedIds.has(def.id)) return;
        
        const label = (translations[state.currentLang] && translations[state.currentLang][def.labelKey])
            ? translations[state.currentLang][def.labelKey]
            : def.id;
            
        let elementToAdd = null;
        
        if (def.pair === 'left') {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'split-btn-group';
            
            const leftBtn = document.createElement('button');
            leftBtn.className = 'split-btn left';
            leftBtn.id = `chart-btn-${def.id}`;
            leftBtn.setAttribute('data-chart-id', def.id);
            if (state.activeChartType === def.id) leftBtn.classList.add('active');
            leftBtn.onclick = () => selectChart(def.id);
            leftBtn.innerHTML = `${def.icon || ''} ${label}`;
            groupDiv.appendChild(leftBtn);
            processedIds.add(def.id);
            
            const rightDef = CHART_DEFS.find(d => d.id === def.pairId);
            if (rightDef) {
                const rightLabel = (translations[state.currentLang] && translations[state.currentLang][rightDef.labelKey])
                    ? translations[state.currentLang][rightDef.labelKey]
                    : rightDef.id;
                    
                const rightBtn = document.createElement('button');
                rightBtn.className = 'split-btn right';
                rightBtn.id = `chart-btn-${rightDef.id}`;
                rightBtn.setAttribute('data-chart-id', rightDef.id);
                if (state.activeChartType === rightDef.id) rightBtn.classList.add('active');
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
            if (state.activeChartType === def.id) btn.classList.add('active');
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

export function selectChart(chartType) {
    if (!chartType) return;
    state.activeChartType = chartType;
    
    document.querySelectorAll('.split-btn, .promo-tab-btn').forEach(el => el.classList.remove('active'));
    
    const activeEl = document.getElementById(`chart-btn-${chartType}`);
    if (activeEl) activeEl.classList.add('active');
    
    renderActiveChart();
}

export function selectPromoChart(chartType) {
    selectChart(chartType);
}

export function formatChartValue(value, suffix = "") {
    if (value === null || value === undefined || value === "") return "-";
    if (typeof value === "number") return `${value.toLocaleString()}${suffix}`;
    const numericValue = Number(value);
    if (!Number.isNaN(numericValue) && value !== true && value !== false) {
        return `${numericValue.toLocaleString()}${suffix}`;
    }
    return `${value}${suffix}`;
}

export function truncateChartTitle(title, maxLength = 90) {
    const safeTitle = title || (state.currentLang === "ua" ? "Без назви" : "Untitled");
    return safeTitle.length > maxLength ? `${safeTitle.substring(0, maxLength - 1)}...` : safeTitle;
}

export function getChartTextRows(chartType) {
    if (!state.chartRawData) return [];
    
    const videoChartMap = {
        top_viewed: { list: state.chartRawData.top_viewed || [], metric: state.currentLang === "ua" ? "Перегляди" : "Views", field: "view_count" },
        worst_viewed: { list: state.chartRawData.worst_viewed || [], metric: state.currentLang === "ua" ? "Перегляди" : "Views", field: "view_count" },
        top_liked: { list: state.chartRawData.top_liked || [], metric: state.currentLang === "ua" ? "Лайки" : "Likes", field: "like_count" },
        worst_liked: { list: state.chartRawData.worst_liked || [], metric: state.currentLang === "ua" ? "Лайки" : "Likes", field: "like_count" },
        top_commented: { list: state.chartRawData.top_commented || [], metric: state.currentLang === "ua" ? "Коментарі" : "Comments", field: "comment_count" },
        worst_commented: { list: state.chartRawData.worst_commented || [], metric: state.currentLang === "ua" ? "Коментарі" : "Comments", field: "comment_count" }
    };
    
    if (videoChartMap[chartType]) {
        const cfg = videoChartMap[chartType];
        return cfg.list.map((video, index) => ({
            type: "video",
            item: video,
            label: video.title || (state.currentLang === "ua" ? "Без назви" : "Untitled"),
            meta: [
                `${cfg.metric}: ${formatChartValue(video[cfg.field])}`,
                video.published_at ? `${state.currentLang === "ua" ? "Дата" : "Date"}: ${video.published_at}` : null
            ].filter(Boolean).join(" | "),
            index
        }));
    }
    
    const rowsByType = {
        by_month: (state.chartRawData.by_month || []).map((d, index) => ({
            label: d.month,
            meta: `${state.currentLang === "ua" ? "Відео" : "Videos"}: ${formatChartValue(d.video_count)}`,
            index
        })),
        duration_dist: (state.chartRawData.duration_dist || []).map((d, index) => ({
            label: d.category,
            meta: `${state.currentLang === "ua" ? "Відео" : "Videos"}: ${formatChartValue(d.video_count)}`,
            index
        })),
        top_hashtags: (state.chartRawData.top_hashtags || []).map((d, index) => ({
            label: d.tag,
            meta: `${state.currentLang === "ua" ? "Перегляди" : "Views"}: ${formatChartValue(d.count)} | ${state.currentLang === "ua" ? "Відео" : "Videos"}: ${formatChartValue(d.video_count)}`,
            index
        })),
        top_description_words: (state.chartRawData.top_words || []).map((d, index) => ({
            label: d.word,
            meta: `${state.currentLang === "ua" ? "Перегляди" : "Views"}: ${formatChartValue(d.count)} | ${state.currentLang === "ua" ? "Відео" : "Videos"}: ${formatChartValue(d.video_count)}`,
            index
        })),
        best_promo_words: (state.chartRawData.best_promo_words || []).map((d, index) => ({
            label: d.word,
            meta: `Lift: ${formatChartValue(Number(d.lift || 0).toFixed(2), "x")} | ${state.currentLang === "ua" ? "Медіана" : "Median"}: ${formatChartValue(d.median_views)} | ${state.currentLang === "ua" ? "Відео" : "Videos"}: ${formatChartValue(d.video_count)}`,
            index
        })),
        worst_promo_words: (state.chartRawData.worst_promo_words || []).map((d, index) => ({
            label: d.word,
            meta: `Lift: ${formatChartValue(Number(d.lift || 0).toFixed(2), "x")} | ${state.currentLang === "ua" ? "Медіана" : "Median"}: ${formatChartValue(d.median_views)} | ${state.currentLang === "ua" ? "Відео" : "Videos"}: ${formatChartValue(d.video_count)}`,
            index
        })),
        best_promo_tags: (state.chartRawData.best_promo_tags || []).map((d, index) => ({
            label: d.tag,
            meta: `Lift: ${formatChartValue(Number(d.lift || 0).toFixed(2), "x")} | ${state.currentLang === "ua" ? "Медіана" : "Median"}: ${formatChartValue(d.median_views)} | ${state.currentLang === "ua" ? "Відео" : "Videos"}: ${formatChartValue(d.video_count)}`,
            index
        })),
        worst_promo_tags: (state.chartRawData.worst_promo_tags || []).map((d, index) => ({
            label: d.tag,
            meta: `Lift: ${formatChartValue(Number(d.lift || 0).toFixed(2), "x")} | ${state.currentLang === "ua" ? "Медіана" : "Median"}: ${formatChartValue(d.median_views)} | ${state.currentLang === "ua" ? "Відео" : "Videos"}: ${formatChartValue(d.video_count)}`,
            index
        })),
        best_day_to_post: (state.chartRawData.best_day_to_post || []).map((d, index) => ({
            label: d.day_of_week,
            meta: `${state.currentLang === "ua" ? "Відео" : "Videos"}: ${formatChartValue(d.video_count)} | ${state.currentLang === "ua" ? "Перегляди" : "Views"}: ${formatChartValue(d.total_views)}`,
            index
        })),
        duration_vs_views: (state.chartRawData.duration_vs_views || []).map((d, index) => ({
            label: d.title,
            meta: `${state.currentLang === "ua" ? "Тривалість" : "Duration"}: ${formatChartValue(d.duration, "s")} | ${state.currentLang === "ua" ? "Перегляди" : "Views"}: ${formatChartValue(d.view_count)}`,
            index
        })),
        views_distribution: (state.chartRawData.views_distribution || []).map((d, index) => ({
            label: d.category,
            meta: `${state.currentLang === "ua" ? "Відео" : "Videos"}: ${formatChartValue(d.video_count)}`,
            index
        }))
    };
    
    return rowsByType[chartType] || [];
}

export function renderChartCopyLayer(chartType, chartTitle) {
    const layer = document.getElementById("chart-copy-layer");
    if (!layer) return;
    
    layer.innerHTML = "";
    const rows = getChartTextRows(chartType);
    
    if (!rows.length) {
        layer.hidden = true;
        return;
    }
    
    layer.hidden = false;
    
    const heading = document.createElement("div");
    heading.className = "chart-copy-heading";
    heading.textContent = chartTitle || (state.currentLang === "ua" ? "Текстова версія візуалізації" : "Visualization text version");
    layer.appendChild(heading);
    
    const list = document.createElement("ol");
    list.className = "chart-copy-list";
    
    rows.forEach(row => {
        const item = document.createElement("li");
        item.className = row.type === "video" ? "chart-copy-row chart-copy-row-video" : "chart-copy-row";
        
        const label = document.createElement(row.type === "video" ? "button" : "span");
        label.className = row.type === "video" ? "chart-copy-label chart-copy-video-title" : "chart-copy-label";
        label.textContent = truncateChartTitle(row.label);
        label.title = row.label || "";
        
        if (row.type === "video") {
            label.type = "button";
            label.setAttribute("aria-label", `${state.currentLang === "ua" ? "Відкрити деталі відео" : "Open video details"}: ${row.label}`);
            label.addEventListener("click", () => openVideoModal(row.item));
        }
        
        const meta = document.createElement("span");
        meta.className = "chart-copy-meta";
        meta.textContent = row.meta || "";
        
        item.appendChild(label);
        item.appendChild(meta);
        list.appendChild(item);
    });
    
    layer.appendChild(list);
}

export function renderActiveChart() {
    const chartType = state.activeChartType;
    if (!state.chartRawData || !chartType) return;
    
    const isScrollable = ["best_promo_words", "worst_promo_words", "best_promo_tags", "worst_promo_tags", "top_viewed", "top_liked", "top_commented", "worst_viewed", "worst_liked", "worst_commented"].includes(chartType);
    
    // Destroy previous chart first so we can safely resize
    if (state.activeChartInstance) {
        state.activeChartInstance.destroy();
        state.activeChartInstance = null;
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
            if (chartType === "best_promo_words" && state.chartRawData.best_promo_words) itemCount = state.chartRawData.best_promo_words.length;
            else if (chartType === "worst_promo_words" && state.chartRawData.worst_promo_words) itemCount = state.chartRawData.worst_promo_words.length;
            else if (chartType === "best_promo_tags" && state.chartRawData.best_promo_tags) itemCount = state.chartRawData.best_promo_tags.length;
            else if (chartType === "worst_promo_tags" && state.chartRawData.worst_promo_tags) itemCount = state.chartRawData.worst_promo_tags.length;
            else if (chartType === "top_viewed" && state.chartRawData.top_viewed) itemCount = state.chartRawData.top_viewed.length;
            else if (chartType === "top_liked" && state.chartRawData.top_liked) itemCount = state.chartRawData.top_liked.length;
            else if (chartType === "top_commented" && state.chartRawData.top_commented) itemCount = state.chartRawData.top_commented.length;
            else if (chartType === "worst_viewed" && state.chartRawData.worst_viewed) itemCount = state.chartRawData.worst_viewed.length;
            else if (chartType === "worst_liked" && state.chartRawData.worst_liked) itemCount = state.chartRawData.worst_liked.length;
            else if (chartType === "worst_commented" && state.chartRawData.worst_commented) itemCount = state.chartRawData.worst_commented.length;
            
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
    
    const isDark = ["dark-black", "dark-blue"].includes(state.currentTheme);
    const gridColor = isDark ? "#334155" : "#e2e8f0";
    const labelColor = isDark ? "#94a3b8" : "#5f6368";
    const titleColor = isDark ? "#f8fafc" : "#202124";
    
    let chartConfig = {};
    
    if (chartType === "by_month") {
        const labels = state.chartRawData.by_month.map(d => d.month);
        const values = state.chartRawData.by_month.map(d => d.video_count);
        
        chartConfig = {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Завантажено відео" : "Videos Uploaded",
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
                    title: { display: true, text: state.currentLang === "ua" ? "Динаміка завантажень по місяцях" : "Upload Volume By Month", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { color: gridColor }, ticks: { color: labelColor } }
                }
            }
        };
        
    } else if (chartType === "duration_dist") {
        const categoriesMap = {
            "Short (< 1m)": state.currentLang === "ua" ? "Короткі (< 1хв)" : "Short (< 1m)",
            "Medium (1-10m)": state.currentLang === "ua" ? "Середні (1-10хв)" : "Medium (1-10m)",
            "Long (> 10m)": state.currentLang === "ua" ? "Довгі (> 10хв)" : "Long (> 10m)"
        };
        
        const labels = state.chartRawData.duration_dist.map(d => categoriesMap[d.category] || d.category);
        const values = state.chartRawData.duration_dist.map(d => d.video_count);
        
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
                    title: { display: true, text: state.currentLang === "ua" ? "Розподіл за тривалістю відео" : "Videos Duration Share", color: titleColor }
                }
            }
        };
        
    } else if (chartType === "top_viewed") {
        const labels = state.chartRawData.top_viewed.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = state.chartRawData.top_viewed.map(d => d.view_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Перегляди" : "Views",
                    data: values,
                    backgroundColor: state.chartRawData.top_viewed.map(d => state.channelColors[d.channel_id] || "#00e676")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: state.currentLang === "ua" ? "Топ-100 відео за переглядами" : "Top 100 Most Viewed Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
        
    } else if (chartType === "top_liked") {
        const labels = state.chartRawData.top_liked.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = state.chartRawData.top_liked.map(d => d.like_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Лайки" : "Likes",
                    data: values,
                    backgroundColor: state.chartRawData.top_liked.map(d => state.channelColors[d.channel_id] || "#f59e0b")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: state.currentLang === "ua" ? "Топ-100 відео за лайками" : "Top 100 Most Liked Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
        
    } else if (chartType === "top_commented") {
        const labels = state.chartRawData.top_commented.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = state.chartRawData.top_commented.map(d => d.comment_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Коментарі" : "Comments",
                    data: values,
                    backgroundColor: state.chartRawData.top_commented.map(d => state.channelColors[d.channel_id] || "#8b5cf6")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: state.currentLang === "ua" ? "Топ-100 відео за коментарями" : "Top 100 Most Commented Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "worst_viewed") {
        const labels = state.chartRawData.worst_viewed.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = state.chartRawData.worst_viewed.map(d => d.view_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Перегляди" : "Views",
                    data: values,
                    backgroundColor: state.chartRawData.worst_viewed.map(d => state.channelColors[d.channel_id] || "#f43f5e")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: state.currentLang === "ua" ? "Найгірші 100 відео за переглядами" : "Worst 100 Viewed Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "worst_liked") {
        const labels = state.chartRawData.worst_liked.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = state.chartRawData.worst_liked.map(d => d.like_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Лайки" : "Likes",
                    data: values,
                    backgroundColor: state.chartRawData.worst_liked.map(d => state.channelColors[d.channel_id] || "#f43f5e")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: state.currentLang === "ua" ? "Найгірші 100 відео за лайками" : "Worst 100 Liked Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "worst_commented") {
        const labels = state.chartRawData.worst_commented.map(d => d.title.length > 35 ? d.title.substring(0, 32) + "..." : d.title);
        const values = state.chartRawData.worst_commented.map(d => d.comment_count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Коментарі" : "Comments",
                    data: values,
                    backgroundColor: state.chartRawData.worst_commented.map(d => state.channelColors[d.channel_id] || "#f43f5e")
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: state.currentLang === "ua" ? "Найгірші 100 відео за коментарями" : "Worst 100 Commented Videos", color: titleColor }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor, autoSkip: false, font: { size: 11 } } }
                }
            }
        };
    } else if (chartType === "top_hashtags") {
        const labels = state.chartRawData.top_hashtags.map(d => d.tag);
        const values = state.chartRawData.top_hashtags.map(d => d.count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Сумарні перегляди" : "Total Attributed Views",
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
                    title: { display: true, text: state.currentLang === "ua" ? "Топ-10 хештегів за сумарними переглядами" : "Top 10 Hashtags by Attributed Views", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = state.chartRawData.top_hashtags[idx];
                                const avgViews = item.video_count > 0 ? Math.round(item.count / item.video_count) : 0;
                                return [
                                    (state.currentLang === "ua" ? "Перегляди: " : "Views: ") + item.count.toLocaleString(),
                                    (state.currentLang === "ua" ? "Відео: " : "Videos: ") + item.video_count,
                                    (state.currentLang === "ua" ? "Сер. переглядів/відео: " : "Avg views/video: ") + avgViews.toLocaleString()
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
        const labels = state.chartRawData.top_words.map(d => d.word);
        const values = state.chartRawData.top_words.map(d => d.count);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Сумарні перегляди" : "Total Attributed Views",
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
                    title: { display: true, text: state.currentLang === "ua" ? "Топ-10 слів в описах за сумарними переглядами" : "Top 10 Description Words by Attributed Views", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = state.chartRawData.top_words[idx];
                                const avgViews = item.video_count > 0 ? Math.round(item.count / item.video_count) : 0;
                                return [
                                    (state.currentLang === "ua" ? "Перегляди: " : "Views: ") + item.count.toLocaleString(),
                                    (state.currentLang === "ua" ? "Відео: " : "Videos: ") + item.video_count,
                                    (state.currentLang === "ua" ? "Сер. переглядів/відео: " : "Avg views/video: ") + avgViews.toLocaleString()
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
        const labels = state.chartRawData.best_promo_words.map(d => d.word);
        const values = state.chartRawData.best_promo_words.map(d => d.lift);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Приріст (Lift)" : "Performance Lift",
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
                    title: { display: true, text: state.currentLang === "ua" ? "Найкращі слова для просування (Множник медіани)" : "Top Promotion Keywords (Median Lift Factor)", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = state.chartRawData.best_promo_words[idx];
                                const changePct = Math.round((item.lift - 1) * 100);
                                const changeSign = changePct >= 0 ? "+" : "";
                                return [
                                    (state.currentLang === "ua" ? "Ефективність: " : "Performance Lift: ") + item.lift.toFixed(2) + "x (" + changeSign + changePct + "%)",
                                    (state.currentLang === "ua" ? "Медіана переглядів слова: " : "Word Median Views: ") + item.median_views.toLocaleString(),
                                    (state.currentLang === "ua" ? "Кількість відео: " : "Videos count: ") + item.video_count
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
        const labels = state.chartRawData.worst_promo_words.map(d => d.word);
        const values = state.chartRawData.worst_promo_words.map(d => d.lift);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Приріст (Lift)" : "Performance Lift",
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
                    title: { display: true, text: state.currentLang === "ua" ? "Топ-30 найгірших слів для просування (Множник медіани)" : "Worst Promotion Keywords (Median Lift Factor)", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = state.chartRawData.worst_promo_words[idx];
                                const changePct = Math.round((item.lift - 1) * 100);
                                const changeSign = changePct >= 0 ? "+" : "";
                                return [
                                    (state.currentLang === "ua" ? "Ефективність: " : "Performance Lift: ") + item.lift.toFixed(2) + "x (" + changeSign + changePct + "%)",
                                    (state.currentLang === "ua" ? "Медіана переглядів слова: " : "Word Median Views: ") + item.median_views.toLocaleString(),
                                    (state.currentLang === "ua" ? "Кількість відео: " : "Videos count: ") + item.video_count
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
        const labels = state.chartRawData.best_promo_tags.map(d => d.tag);
        const values = state.chartRawData.best_promo_tags.map(d => d.lift);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Приріст (Lift)" : "Performance Lift",
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
                    title: { display: true, text: state.currentLang === "ua" ? "Топ-30 найкращих хештегів для просування (Множник медіани)" : "Top 30 Promotion Hashtags (Median Lift Factor)", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = state.chartRawData.best_promo_tags[idx];
                                const changePct = Math.round((item.lift - 1) * 100);
                                const changeSign = changePct >= 0 ? "+" : "";
                                return [
                                    (state.currentLang === "ua" ? "Ефективність: " : "Performance Lift: ") + item.lift.toFixed(2) + "x (" + changeSign + changePct + "%)",
                                    (state.currentLang === "ua" ? "Медіана переглядів тегу: " : "Tag Median Views: ") + item.median_views.toLocaleString(),
                                    (state.currentLang === "ua" ? "Кількість відео: " : "Videos count: ") + item.video_count
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
        const labels = state.chartRawData.worst_promo_tags.map(d => d.tag);
        const values = state.chartRawData.worst_promo_tags.map(d => d.lift);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: state.currentLang === "ua" ? "Приріст (Lift)" : "Performance Lift",
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
                    title: { display: true, text: state.currentLang === "ua" ? "Топ-30 найгірших хештегів для просування (Множник медіани)" : "Worst Promotion Hashtags (Median Lift Factor)", color: titleColor },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = state.chartRawData.worst_promo_tags[idx];
                                const changePct = Math.round((item.lift - 1) * 100);
                                const changeSign = changePct >= 0 ? "+" : "";
                                return [
                                    (state.currentLang === "ua" ? "Ефективність: " : "Performance Lift: ") + item.lift.toFixed(2) + "x (" + changeSign + changePct + "%)",
                                    (state.currentLang === "ua" ? "Медіана переглядів тегу: " : "Tag Median Views: ") + item.median_views.toLocaleString(),
                                    (state.currentLang === "ua" ? "Кількість відео: " : "Videos count: ") + item.video_count
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
            "Sunday": state.currentLang === "ua" ? "Неділя" : "Sunday",
            "Monday": state.currentLang === "ua" ? "Понеділок" : "Monday",
            "Tuesday": state.currentLang === "ua" ? "Вівторок" : "Tuesday",
            "Wednesday": state.currentLang === "ua" ? "Середа" : "Wednesday",
            "Thursday": state.currentLang === "ua" ? "Четвер" : "Thursday",
            "Friday": state.currentLang === "ua" ? "П'ятниця" : "Friday",
            "Saturday": state.currentLang === "ua" ? "Субота" : "Saturday"
        };
        const labels = state.chartRawData.best_day_to_post.map(d => labelsMap[d.day_of_week] || d.day_of_week);
        const counts = state.chartRawData.best_day_to_post.map(d => d.video_count);
        const views = state.chartRawData.best_day_to_post.map(d => d.total_views);
        
        chartConfig = {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: state.currentLang === "ua" ? "Кількість відео" : "Videos Count",
                        data: counts,
                        backgroundColor: "#38bdf8",
                        yAxisID: "y"
                    },
                    {
                        label: state.currentLang === "ua" ? "Всього переглядів" : "Total Views",
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
                    title: { display: true, text: state.currentLang === "ua" ? "Кращий день для публікації (Кількість vs Перегляди)" : "Best Day to Post (Volume vs Views)", color: titleColor }
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
        const scatterData = state.chartRawData.duration_vs_views.map(d => ({
            x: d.duration,
            y: d.view_count,
            title: d.title,
            channel_id: d.channel_id
        }));
        
        chartConfig = {
            type: "scatter",
            data: {
                datasets: [{
                    label: state.currentLang === "ua" ? "Відео" : "Videos",
                    data: scatterData,
                    backgroundColor: state.chartRawData.duration_vs_views.map(d => state.channelColors[d.channel_id] || "rgba(56, 189, 248, 0.6)"),
                    borderColor: state.chartRawData.duration_vs_views.map(d => state.channelColors[d.channel_id] || "#38bdf8"),
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: state.currentLang === "ua" ? "Кореляція: Тривалість відео (сек) vs Перегляди" : "Correlation: Duration (seconds) vs Views", color: titleColor },
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
                        title: { display: true, text: state.currentLang === "ua" ? "Тривалість (секунди)" : "Duration (seconds)", color: labelColor },
                        grid: { color: gridColor }, 
                        ticks: { color: labelColor } 
                    },
                    y: { 
                        title: { display: true, text: state.currentLang === "ua" ? "Перегляди" : "Views", color: labelColor },
                        grid: { color: gridColor }, 
                        ticks: { color: labelColor } 
                    }
                }
            }
        };
    } else if (chartType === "views_distribution") {
        const labelsMap = {
            "Very Low (< 1k)": state.currentLang === "ua" ? "Дуже низькі (< 1к)" : "Very Low (< 1k)",
            "Low (1k-10k)": state.currentLang === "ua" ? "Низькі (1к-10к)" : "Low (1k-10k)",
            "Medium (10k-50k)": state.currentLang === "ua" ? "Середні (10к-50к)" : "Medium (10k-50k)",
            "High (50k-100k)": state.currentLang === "ua" ? "Високі (50к-100к)" : "High (50k-100k)",
            "Very High (> 100k)": state.currentLang === "ua" ? "Дуже високі (> 100к)" : "Very High (> 100k)"
        };
        const labels = state.chartRawData.views_distribution.map(d => labelsMap[d.category] || d.category);
        const values = state.chartRawData.views_distribution.map(d => d.video_count);
        
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
                    title: { display: true, text: state.currentLang === "ua" ? "Розподіл відео за рівнем переглядів" : "Views Performance Distribution", color: titleColor }
                }
            }
        };
    }
    
    if (["top_viewed", "worst_viewed", "top_liked", "worst_liked", "top_commented", "worst_commented"].includes(chartType)) {
        if (!chartConfig.options) chartConfig.options = {};
        chartConfig.options.onClick = (evt, activeElements) => {
            if (activeElements && activeElements.length > 0) {
                const index = activeElements[0].index;
                const dataList = state.chartRawData[chartType];
                if (dataList && dataList[index]) {
                    openVideoModal(dataList[index]);
                }
            }
        };
    }
    
    state.activeChartInstance = new Chart(ctx, chartConfig);
    
    const chartTitle = chartConfig?.options?.plugins?.title?.text;
    renderChartCopyLayer(chartType, chartTitle);
}

export function renderModalViewsChart(history) {
    if (state.activeModalChartInstance) {
        state.activeModalChartInstance.destroy();
        state.activeModalChartInstance = null;
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
        return date.toLocaleDateString(state.currentLang === 'ua' ? 'uk-UA' : 'en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    });
    
    const data = history.map(item => item[1]);
    
    const isDark = ["dark-black", "dark-blue"].includes(state.currentTheme);
    const gridColor = isDark ? "#334155" : "#e2e8f0";
    const labelColor = isDark ? "#94a3b8" : "#5f6368";
    
    state.activeModalChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: state.currentLang === 'ua' ? 'Перегляди' : 'Views',
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
