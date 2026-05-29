import { state } from './state.js';
import { translations } from './translations.js';
import { openVideoModal } from './ui.js';
import { isD3ChartType, renderD3Chart, hideD3Tooltip } from './d3-charts.js';

export const CHART_DEFS = [
    // Group 1: Stats split-buttons (video metrics)
    { id: 'top_viewed',         group: 'stats', pair: 'left',  pairId: 'worst_viewed',    icon: '👁', labelKey: 'chart_top_viewed' },
    { id: 'worst_viewed',       group: 'stats', pair: 'right', pairId: 'top_viewed',      icon: '📉', labelKey: 'chart_worst_sub' },
    
    { id: 'top_liked',          group: 'stats', pair: 'left',  pairId: 'worst_liked',     icon: '👍', labelKey: 'chart_top_liked' },
    { id: 'worst_liked',        group: 'stats', pair: 'right', pairId: 'top_liked',       icon: '📉', labelKey: 'chart_worst_sub' },
    
    { id: 'top_commented',      group: 'stats', pair: 'left',  pairId: 'worst_commented',   icon: '💬', labelKey: 'chart_top_commented' },
    { id: 'worst_commented',    group: 'stats', pair: 'right', pairId: 'top_commented',     icon: '📉', labelKey: 'chart_worst_sub' },
    
    // Group 2: Promo split-buttons (text analytics)
    { id: 'best_promo_title_words', group: 'promo', pair: 'left', pairId: 'worst_promo_title_words', icon: '🚀', labelKey: 'chart_best_promo_title_words' },
    { id: 'worst_promo_title_words', group: 'promo', pair: 'right', pairId: 'best_promo_title_words', icon: '📉', labelKey: 'chart_worst_sub' },

    { id: 'best_promo_words',   group: 'promo', pair: 'left',  pairId: 'worst_promo_words', icon: '🚀', labelKey: 'chart_best_promo_words' },
    { id: 'worst_promo_words',  group: 'promo', pair: 'right', pairId: 'best_promo_words',  icon: '📉', labelKey: 'chart_worst_sub' },
    
    { id: 'best_promo_tags',    group: 'promo', pair: 'left',  pairId: 'worst_promo_tags',  icon: '🚀', labelKey: 'chart_best_promo_tags' },
    { id: 'worst_promo_tags',   group: 'promo', pair: 'right', pairId: 'best_promo_tags',   icon: '📉', labelKey: 'chart_worst_sub' },
    
    // Group 3: Other analytical buttons (formerly in dropdown)
    { id: 'best_day_to_post',   group: 'other', icon: '📅', labelKey: 'chart_best_day_to_post' },
    { id: 'duration_vs_views',  group: 'other', icon: '📈', labelKey: 'chart_duration_vs_views' },
    { id: 'views_distribution', group: 'other', icon: '🍩', labelKey: 'chart_views_distribution' }
];

export function initChartUI() {
    const container = document.getElementById('chart-controls-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Setup explicit row wrapper containers to keep them strictly separated in 3 rows
    const row1 = document.createElement('div');
    row1.className = 'chart-controls-row stats-row';
    row1.style.display = 'flex';
    row1.style.gap = '8px';
    row1.style.marginBottom = '8px';
    row1.style.flexWrap = 'wrap';

    const row2 = document.createElement('div');
    row2.className = 'chart-controls-row promo-row';
    row2.style.display = 'flex';
    row2.style.gap = '8px';
    row2.style.marginBottom = '8px';
    row2.style.flexWrap = 'wrap';

    const row3 = document.createElement('div');
    row3.className = 'chart-controls-row other-row';
    row3.style.display = 'flex';
    row3.style.gap = '8px';
    row3.style.flexWrap = 'wrap';
    
    const statsElements = [];
    const promoElements = [];
    const otherElements = [];
    
    const processedIds = new Set();
    
    CHART_DEFS.forEach(def => {
        if (processedIds.has(def.id)) return;
        
        let label = (translations[state.currentLang] && translations[state.currentLang][def.labelKey])
            ? translations[state.currentLang][def.labelKey]
            : def.id;
            
        if (typeof label === 'string') {
            label = label.replace("100", state.chartLimit);
        }
            
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
                let rightLabel = (translations[state.currentLang] && translations[state.currentLang][rightDef.labelKey])
                    ? translations[state.currentLang][rightDef.labelKey]
                    : rightDef.id;
                    
                if (typeof rightLabel === 'string') {
                    rightLabel = rightLabel.replace("100", state.chartLimit);
                }
                    
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
    
    statsElements.forEach(el => row1.appendChild(el));
    promoElements.forEach(el => row2.appendChild(el));
    otherElements.forEach(el => row3.appendChild(el));
    
    if (statsElements.length > 0) container.appendChild(row1);
    if (promoElements.length > 0) container.appendChild(row2);
    if (otherElements.length > 0) container.appendChild(row3);
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

export function renderActiveChart(dashboardCard) {
    const chartType = state.activeChartType;
    if (!state.chartRawData || !chartType) return;
    
    const card = dashboardCard || document.getElementById('card-visualizations-container');
    const d3Root = card ? card.querySelector('.d3-chart-root') : document.getElementById('d3-chart-root');
    const canvasEl = card ? card.querySelector('canvas') : document.getElementById('analytics-chart');
    const container = card ? card.querySelector('.chart-container') : document.querySelector('.chart-container');
    
    // Destroy previous Chart.js instance
    if (state.activeChartInstance) {
        state.activeChartInstance.destroy();
        state.activeChartInstance = null;
    }
    hideD3Tooltip();
    
    // Update button active states inside the card (or globally if card is missing)
    const btnContainer = card ? card.querySelector('.card-header') : document;
    if (btnContainer) {
        btnContainer.querySelectorAll('.split-btn').forEach(el => {
            el.classList.toggle('active', el.id === `chart-btn-${chartType}`);
        });
    }
    
    // ── D3 route: video charts ──────────────────────────────
    if (isD3ChartType(chartType)) {
        // Show D3 root, hide canvas
        if (d3Root) d3Root.style.display = 'block';
        if (canvasEl) canvasEl.style.display = 'none';
        
        // Restore canvas from scroll wrapper if needed
        if (container) {
            const wrapper = container.querySelector('.chart-scroll-inner');
            if (wrapper) {
                container.insertBefore(canvasEl, wrapper);
                container.removeChild(wrapper);
            }
        }
        
        renderD3Chart(chartType, d3Root);
        return;
    }
    
    // ── Chart.js route: everything else ─────────────────────
    // Hide D3 root, show canvas
    if (d3Root) {
        d3Root.style.display = 'none';
        d3Root.innerHTML = '';
    }
    if (canvasEl) canvasEl.style.display = 'block';
    
    const isScrollable = [
        "best_promo_words", "worst_promo_words", 
        "best_promo_tags", "worst_promo_tags",
        "best_promo_title_words", "worst_promo_title_words",
        "best_promo_thumb_words", "worst_promo_thumb_words"
    ].includes(chartType);
    
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
            else if (chartType === "best_promo_title_words" && state.chartRawData.best_promo_title_words) itemCount = state.chartRawData.best_promo_title_words.length;
            else if (chartType === "worst_promo_title_words" && state.chartRawData.worst_promo_title_words) itemCount = state.chartRawData.worst_promo_title_words.length;
            else if (chartType === "best_promo_thumb_words" && state.chartRawData.best_promo_thumb_words) itemCount = state.chartRawData.best_promo_thumb_words.length;
            else if (chartType === "worst_promo_thumb_words" && state.chartRawData.worst_promo_thumb_words) itemCount = state.chartRawData.worst_promo_thumb_words.length;
            
            // 18px per bar + 60px header/footer
            const canvasH = Math.max(300, itemCount * 18 + 60);
            
            // Use an inner wrapper div so Chart.js fills it and container scrolls
            let wrapper = container.querySelector(".chart-scroll-inner");
            if (!wrapper) {
                wrapper = document.createElement("div");
                wrapper.className = "chart-scroll-inner";
                wrapper.style.position = "relative";
                // Move canvas into wrapper
                container.appendChild(wrapper);
                wrapper.appendChild(canvasEl);
            }
            wrapper.style.height = canvasH + "px";
            wrapper.style.minHeight = canvasH + "px";
            
        } else {
            // Restore canvas directly in container if it was inside a wrapper
            const wrapper = container.querySelector(".chart-scroll-inner");
            if (wrapper) {
                container.insertBefore(canvasEl, wrapper);
                container.removeChild(wrapper);
            }
            container.style.height = "280px";
            container.style.overflowY = "visible";
            container.style.overflowX = "visible";
        }
    }

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
    
    
    state.activeChartInstance = new Chart(ctx, chartConfig);
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
    
    // Extract series and detect presence of likes and comments
    const viewsData = [];
    const likesData = [];
    const commentsData = [];
    
    let hasLikes = false;
    let hasComments = false;
    
    history.forEach(item => {
        viewsData.push(item[1]);
        
        if (item.length > 2 && item[2] !== null && item[2] !== undefined) {
            likesData.push(item[2]);
            hasLikes = true;
        } else {
            likesData.push(null);
        }
        
        if (item.length > 3 && item[3] !== null && item[3] !== undefined) {
            commentsData.push(item[3]);
            hasComments = true;
        } else {
            commentsData.push(null);
        }
    });
    
    const datasets = [
        {
            label: state.currentLang === 'ua' ? 'Перегляди' : 'Views',
            data: viewsData,
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.08)',
            borderWidth: 2,
            fill: true,
            tension: 0.15,
            pointRadius: 2.5,
            pointHoverRadius: 4.5,
            yAxisID: 'y'
        }
    ];
    
    if (hasComments) {
        datasets.push({
            label: state.currentLang === 'ua' ? 'Коментарі' : 'Comments',
            data: commentsData,
            borderColor: '#a855f7',
            backgroundColor: 'transparent',
            borderWidth: 2,
            fill: false,
            tension: 0.15,
            pointRadius: 2.5,
            pointHoverRadius: 4.5,
            yAxisID: 'y1'
        });
    }
    
    if (hasLikes) {
        datasets.push({
            label: state.currentLang === 'ua' ? 'Лайки' : 'Likes',
            data: likesData,
            borderColor: '#f43f5e',
            backgroundColor: 'transparent',
            borderWidth: 2,
            fill: false,
            tension: 0.15,
            pointRadius: 2.5,
            pointHoverRadius: 4.5,
            yAxisID: 'y2'
        });
    }
    
    const isDark = ["dark-black", "dark-blue"].includes(state.currentTheme);
    const gridColor = isDark ? "#334155" : "#e2e8f0";
    const labelColor = isDark ? "#94a3b8" : "#5f6368";
    
    const scales = {
        x: {
            grid: { color: gridColor },
            ticks: { color: labelColor, maxRotation: 45, minRotation: 0, font: { size: 9 } }
        },
        y: {
            type: 'linear',
            display: true,
            position: 'left',
            grid: { color: gridColor },
            ticks: { color: '#38bdf8', font: { size: 9 }, callback: value => value.toLocaleString() }
        }
    };
    
    if (hasComments) {
        scales.y1 = {
            type: 'linear',
            display: true,
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: '#a855f7', font: { size: 9 }, callback: value => value.toLocaleString() }
        };
    }
    
    if (hasLikes) {
        scales.y2 = {
            type: 'linear',
            display: true,
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: '#f43f5e', font: { size: 9 }, callback: value => value.toLocaleString() }
        };
    }
    
    state.activeModalChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    display: true,
                    position: 'top',
                    labels: {
                        boxWidth: 8,
                        font: { size: 9 },
                        color: labelColor
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw.toLocaleString()}`;
                        }
                    }
                }
            },
            scales: scales
        }
    });
}
