/**
 * D3.js Chart Module — Phase 1: Video Bar Charts
 * 
 * Renders interactive horizontal bar charts for video metrics
 * with rich HTML tooltips (thumbnails, full titles, metrics).
 * 
 * Replaces Chart.js for: top_viewed, worst_viewed, top_liked,
 * worst_liked, top_commented, worst_commented.
 */

import { state } from './state.js';
import { translations } from './translations.js';
import { openVideoModal } from './ui.js';

// ─── Constants ───────────────────────────────────────────────

const BAR_HEIGHT = 22;
const BAR_GAP = 3;
const BAR_TOTAL = BAR_HEIGHT + BAR_GAP;
const LABEL_WIDTH_RATIO = 0.42; // 42% of width for labels
const MARGIN = { top: 36, right: 20, bottom: 10, left: 12 };
const ANIMATION_DURATION = 400;
const ANIMATION_STAGGER = 12;

// Chart type → data field mapping
const VIDEO_CHART_CONFIGS = {
    top_viewed:       { dataKey: 'top_viewed',       field: 'view_count',    metricLabel: { ua: 'Перегляди', en: 'Views' },    color: '#00e676', titleKey: { ua: 'Топ відео за переглядами', en: 'Top Videos by Views' } },
    worst_viewed:     { dataKey: 'worst_viewed',     field: 'view_count',    metricLabel: { ua: 'Перегляди', en: 'Views' },    color: '#f43f5e', titleKey: { ua: 'Найгірші відео за переглядами', en: 'Worst Videos by Views' } },
    top_liked:        { dataKey: 'top_liked',        field: 'like_count',    metricLabel: { ua: 'Лайки', en: 'Likes' },        color: '#f59e0b', titleKey: { ua: 'Топ відео за лайками', en: 'Top Videos by Likes' } },
    worst_liked:      { dataKey: 'worst_liked',      field: 'like_count',    metricLabel: { ua: 'Лайки', en: 'Likes' },        color: '#f43f5e', titleKey: { ua: 'Найгірші відео за лайками', en: 'Worst Videos by Likes' } },
    top_commented:    { dataKey: 'top_commented',    field: 'comment_count', metricLabel: { ua: 'Коментарі', en: 'Comments' }, color: '#8b5cf6', titleKey: { ua: 'Топ відео за коментарями', en: 'Top Videos by Comments' } },
    worst_commented:  { dataKey: 'worst_commented',  field: 'comment_count', metricLabel: { ua: 'Коментарі', en: 'Comments' }, color: '#f43f5e', titleKey: { ua: 'Найгірші відео за коментарями', en: 'Worst Videos by Comments' } },
};

export const D3_VIDEO_CHART_TYPES = Object.keys(VIDEO_CHART_CONFIGS);

// Promo Chart type → data field mapping
const PROMO_CHART_CONFIGS = {
    best_promo_words: {
        dataKey: 'best_promo_words',
        labelField: 'word',
        valueField: 'lift',
        color: '#10b981',
        titleKey: { ua: 'Найкращі слова для просування (Множник медіани)', en: 'Top Promotion Keywords (Median Lift Factor)' }
    },
    worst_promo_words: {
        dataKey: 'worst_promo_words',
        labelField: 'word',
        valueField: 'lift',
        color: '#ef4444',
        titleKey: { ua: 'Топ-30 найгірших слів для просування (Множник медіани)', en: 'Worst Promotion Keywords (Median Lift Factor)' }
    },
    best_promo_tags: {
        dataKey: 'best_promo_tags',
        labelField: 'tag',
        valueField: 'lift',
        color: '#10b981',
        titleKey: { ua: 'Топ-30 найкращих хештегів для просування (Множник медіани)', en: 'Top 30 Promotion Hashtags (Median Lift Factor)' }
    },
    worst_promo_tags: {
        dataKey: 'worst_promo_tags',
        labelField: 'tag',
        valueField: 'lift',
        color: '#ef4444',
        titleKey: { ua: 'Топ-30 найгірших хештегів для просування (Множник медіани)', en: 'Worst Promotion Hashtags (Median Lift Factor)' }
    },
    best_promo_title_words: {
        dataKey: 'best_promo_title_words',
        labelField: 'word',
        valueField: 'lift',
        color: '#10b981',
        titleKey: { ua: 'Найкращі слова з заголовків (Множник медіани)', en: 'Top Title Keywords (Median Lift Factor)' }
    },
    worst_promo_title_words: {
        dataKey: 'worst_promo_title_words',
        labelField: 'word',
        valueField: 'lift',
        color: '#ef4444',
        titleKey: { ua: 'Найгірші слова з заголовків (Множник медіани)', en: 'Worst Title Keywords (Median Lift Factor)' }
    },
    best_promo_thumb_words: {
        dataKey: 'best_promo_thumb_words',
        labelField: 'word',
        valueField: 'lift',
        color: '#10b981',
        titleKey: { ua: 'Найкращі слова з тамбнейлів (Множник медіани)', en: 'Top Thumbnail Keywords (Median Lift Factor)' }
    },
    worst_promo_thumb_words: {
        dataKey: 'worst_promo_thumb_words',
        labelField: 'word',
        valueField: 'lift',
        color: '#ef4444',
        titleKey: { ua: 'Найгірші слова з тамбнейлів (Множник медіани)', en: 'Worst Thumbnail Keywords (Median Lift Factor)' }
    }
};

export const D3_PROMO_CHART_TYPES = Object.keys(PROMO_CHART_CONFIGS);

// ─── Theme helpers ───────────────────────────────────────────

function getThemeColors() {
    const root = document.documentElement;
    const cs = getComputedStyle(root);
    const isDark = ['dark-black', 'dark-blue'].includes(state.currentTheme);
    return {
        bg:         cs.getPropertyValue('--bg-color').trim()         || (isDark ? '#0f172a' : '#ffffff'),
        text:       cs.getPropertyValue('--text-color').trim()       || (isDark ? '#e2e8f0' : '#1e293b'),
        muted:      cs.getPropertyValue('--text-muted').trim()       || (isDark ? '#64748b' : '#94a3b8'),
        border:     cs.getPropertyValue('--border-color').trim()     || (isDark ? '#1e293b' : '#e2e8f0'),
        gridLine:   isDark ? '#1e293b' : '#f1f5f9',
        barDefault: isDark ? '#38bdf8' : '#008abb',
        isDark
    };
}

// ─── Tooltip ────────────────────────────────────────────────

let tooltipEl = null;

function ensureTooltip() {
    if (tooltipEl) return tooltipEl;
    tooltipEl = document.createElement('div');
    tooltipEl.className = 'd3-tooltip';
    tooltipEl.style.display = 'none';
    document.body.appendChild(tooltipEl);
    return tooltipEl;
}

/**
 * Show rich tooltip with thumbnail, title, and metrics.
 */
export function showD3Tooltip(event, video, config) {
    const tip = ensureTooltip();
    const lang = state.currentLang === 'ua' ? 'ua' : 'en';
    const metricValue = (video[config.field] || 0).toLocaleString();
    const metricName = config.metricLabel[lang];
    const thumbnailUrl = `https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`;
    const publishDate = video.published_at || '—';
    const title = video.title || (lang === 'ua' ? 'Без назви' : 'Untitled');

    tip.innerHTML = `
        <div class="d3-tip-thumb-wrap">
            <img class="d3-tip-thumb" src="${thumbnailUrl}" alt="" loading="lazy"
                 onerror="this.style.display='none'">
        </div>
        <div class="d3-tip-body">
            <div class="d3-tip-title" title="${title.replace(/"/g, '&quot;')}">${title}</div>
            <div class="d3-tip-meta">
                <span class="d3-tip-metric">${metricName}: <strong>${metricValue}</strong></span>
                <span class="d3-tip-date">${publishDate}</span>
            </div>
        </div>
    `;
    tip.style.display = 'block';

    // Position near cursor
    positionTooltip(event);
}

/**
 * Show rich text-based tooltip for promo words/tags lift metrics.
 */
export function showD3PromoTooltip(event, item, config) {
    const tip = ensureTooltip();
    const lang = state.currentLang === 'ua' ? 'ua' : 'en';
    const lift = item.lift || 0;
    const changePct = Math.round((lift - 1) * 100);
    const changeSign = changePct >= 0 ? "+" : "";
    const medianViews = (item.median_views || 0).toLocaleString();
    const videoCount = item.video_count || 0;
    const label = item[config.labelField] || "";

    const labelTitle = config.dataKey.includes("tag")
        ? (lang === 'ua' ? 'Хештег' : 'Hashtag')
        : (lang === 'ua' ? 'Слово' : 'Word');

    tip.innerHTML = `
        <div class="d3-tip-body">
            <div class="d3-tip-title">${labelTitle}: "${label}"</div>
            <div class="d3-tip-meta">
                <span class="d3-tip-metric">
                    ${lang === 'ua' ? 'Ефективність' : 'Performance Lift'}: 
                    <strong>${lift.toFixed(2)}x (${changeSign}${changePct}%)</strong>
                </span>
                <span class="d3-tip-metric">
                    ${lang === 'ua' ? 'Медіана переглядів' : 'Median Views'}: 
                    <strong>${medianViews}</strong>
                </span>
                <span class="d3-tip-metric">
                    ${lang === 'ua' ? 'Кількість відео' : 'Videos count'}: 
                    <strong>${videoCount}</strong>
                </span>
            </div>
        </div>
    `;
    tip.style.display = 'block';

    // Position near cursor
    positionTooltip(event);
}

function positionTooltip(event) {
    if (!tooltipEl) return;
    const tipW = tooltipEl.offsetWidth;
    const tipH = tooltipEl.offsetHeight;
    const pad = 16;
    let x = event.pageX + pad;
    let y = event.pageY - tipH / 2;

    // Keep within viewport
    if (x + tipW > window.innerWidth + window.scrollX - pad) {
        x = event.pageX - tipW - pad;
    }
    if (y < window.scrollY + pad) {
        y = window.scrollY + pad;
    }
    if (y + tipH > window.innerHeight + window.scrollY - pad) {
        y = window.innerHeight + window.scrollY - tipH - pad;
    }

    tooltipEl.style.left = `${x}px`;
    tooltipEl.style.top = `${y}px`;
}

export function hideD3Tooltip() {
    if (tooltipEl) {
        tooltipEl.style.display = 'none';
    }
}

// ─── Main Renderer ──────────────────────────────────────────

/**
 * Render a D3 horizontal bar chart for video metrics.
 * 
 * @param {string} chartType — one of D3_VIDEO_CHART_TYPES
 */
export function renderD3VideoChart(chartType, d3RootNode, chartState = state) {
    const config = VIDEO_CHART_CONFIGS[chartType];
    const chartRawData = chartState.chartRawData;
    if (!config || !chartRawData) return;

    const data = chartRawData[config.dataKey] || [];
    if (!data.length) return;

    const root = d3RootNode || document.getElementById('d3-chart-root');
    if (!root) return;

    // Clear previous
    root.innerHTML = '';

    const theme = getThemeColors();
    const lang = state.currentLang === 'ua' ? 'ua' : 'en';
    let chartTitle = config.titleKey[lang];
    if (lang === 'ua') {
        chartTitle = chartTitle
            .replace('Топ ', `Топ-${chartState.chartLimit || state.chartLimit} `)
            .replace('Найгірші ', `Найгірші ${chartState.chartLimit || state.chartLimit} `);
    } else {
        chartTitle = chartTitle
            .replace('Top ', `Top ${chartState.chartLimit || state.chartLimit} `)
            .replace('Worst ', `Worst ${chartState.chartLimit || state.chartLimit} `);
    }

    // Dimensions
    const containerWidth = root.clientWidth || 800;
    const labelAreaWidth = Math.floor(containerWidth * LABEL_WIDTH_RATIO);
    const chartAreaWidth = containerWidth - labelAreaWidth - MARGIN.left - MARGIN.right;
    const contentHeight = data.length * BAR_TOTAL;
    const totalHeight = contentHeight + MARGIN.top + MARGIN.bottom;

    // Scrollable wrapper setup
    const outerContainer = root.parentElement;
    if (outerContainer) {
        outerContainer.style.height = '420px';
        outerContainer.style.overflowY = 'auto';
        outerContainer.style.overflowX = 'hidden';
    }

    // Create SVG
    const svg = d3.select(root)
        .append('svg')
        .attr('width', containerWidth)
        .attr('height', totalHeight)
        .attr('class', 'd3-chart-svg');

    // Title
    svg.append('text')
        .attr('x', containerWidth / 2)
        .attr('y', 22)
        .attr('text-anchor', 'middle')
        .attr('class', 'd3-chart-title')
        .style('fill', theme.text)
        .style('font-size', '13px')
        .style('font-weight', '600')
        .text(chartTitle);

    // Scale
    const maxVal = d3.max(data, d => d[config.field] || 0) || 1;
    const xScale = d3.scaleLinear()
        .domain([0, maxVal])
        .range([0, chartAreaWidth]);

    // Chart group
    const g = svg.append('g')
        .attr('transform', `translate(${MARGIN.left}, ${MARGIN.top})`);

    // Row groups
    const rows = g.selectAll('.d3-bar-row')
        .data(data)
        .enter()
        .append('g')
        .attr('class', 'd3-bar-row')
        .attr('transform', (d, i) => `translate(0, ${i * BAR_TOTAL})`)
        .style('cursor', 'pointer')
        .on('click', (event, d) => {
            hideD3Tooltip();
            openVideoModal(d);
        })
        .on('mouseenter', (event, d) => {
            showD3Tooltip(event, d, config);
        })
        .on('mousemove', (event) => {
            positionTooltip(event);
        })
        .on('mouseleave', () => {
            hideD3Tooltip();
        });

    // Rank number
    rows.append('text')
        .attr('x', 0)
        .attr('y', BAR_HEIGHT / 2)
        .attr('dy', '0.35em')
        .attr('class', 'd3-bar-rank')
        .style('fill', theme.muted)
        .style('font-size', '10px')
        .style('text-anchor', 'start')
        .text((d, i) => `${i + 1}`);

    // Label (title text — truncated with ellipsis via foreignObject)
    const rankOffset = 28;
    const labelMaxW = labelAreaWidth - rankOffset - 8;

    rows.append('foreignObject')
        .attr('x', rankOffset)
        .attr('y', 0)
        .attr('width', labelMaxW)
        .attr('height', BAR_HEIGHT)
        .append('xhtml:div')
        .attr('class', 'd3-bar-label')
        .style('color', theme.text)
        .style('width', `${labelMaxW}px`)
        .style('height', `${BAR_HEIGHT}px`)
        .style('line-height', `${BAR_HEIGHT}px`)
        .style('overflow', 'hidden')
        .style('text-overflow', 'ellipsis')
        .style('white-space', 'nowrap')
        .style('font-size', '11px')
        .attr('title', d => d.title || '')
        .text(d => d.title || (lang === 'ua' ? 'Без назви' : 'Untitled'));

    // Bars
    const barX = labelAreaWidth;

    rows.append('rect')
        .attr('class', 'd3-bar-rect')
        .attr('x', barX)
        .attr('y', 1)
        .attr('height', BAR_HEIGHT - 2)
        .attr('rx', 3)
        .attr('ry', 3)
        .style('fill', d => (chartState.channelColors || state.channelColors)[d.channel_id] || config.color)
        .style('opacity', 0.85)
        // Animate from 0 width
        .attr('width', 0)
        .transition()
        .duration(ANIMATION_DURATION)
        .delay((d, i) => i * ANIMATION_STAGGER)
        .ease(d3.easeCubicOut)
        .attr('width', d => Math.max(2, xScale(d[config.field] || 0)));

    // Value labels on bars
    rows.append('text')
        .attr('x', d => barX + Math.max(2, xScale(d[config.field] || 0)) + 6)
        .attr('y', BAR_HEIGHT / 2)
        .attr('dy', '0.35em')
        .attr('class', 'd3-bar-value')
        .style('fill', theme.muted)
        .style('font-size', '10px')
        .style('opacity', 0)
        .text(d => (d[config.field] || 0).toLocaleString())
        .transition()
        .duration(ANIMATION_DURATION)
        .delay((d, i) => i * ANIMATION_STAGGER + ANIMATION_DURATION * 0.5)
        .style('opacity', 1);

    // Light gridlines on x axis
    const tickCount = 5;
    const ticks = xScale.ticks(tickCount);
    
    g.selectAll('.d3-grid-line')
        .data(ticks.slice(1)) // skip 0
        .enter()
        .append('line')
        .attr('class', 'd3-grid-line')
        .attr('x1', d => barX + xScale(d))
        .attr('x2', d => barX + xScale(d))
        .attr('y1', -4)
        .attr('y2', contentHeight)
        .style('stroke', theme.gridLine)
        .style('stroke-width', 1)
        .style('stroke-dasharray', '3,3');

    // Axis labels at top
    g.selectAll('.d3-axis-label')
        .data(ticks.filter((t, i) => i % 2 === 0 || i === ticks.length - 1))
        .enter()
        .append('text')
        .attr('class', 'd3-axis-label')
        .attr('x', d => barX + xScale(d))
        .attr('y', -8)
        .attr('text-anchor', 'middle')
        .style('fill', theme.muted)
        .style('font-size', '9px')
        .text(d => formatCompact(d));
}

/**
 * Render a D3 horizontal bar chart for keyword/tag lift coefficients.
 * 
 * @param {string} chartType — one of D3_PROMO_CHART_TYPES
 */
export function renderD3PromoChart(chartType, d3RootNode, chartState = state) {
    const config = PROMO_CHART_CONFIGS[chartType];
    const chartRawData = chartState.chartRawData;
    if (!config || !chartRawData) return;

    const data = chartRawData[config.dataKey] || [];
    if (!data.length) return;

    const root = d3RootNode || document.getElementById('d3-chart-root');
    if (!root) return;

    // Clear previous
    root.innerHTML = '';

    const theme = getThemeColors();
    const lang = state.currentLang === 'ua' ? 'ua' : 'en';
    const chartTitle = config.titleKey[lang];

    // Dimensions
    const containerWidth = root.clientWidth || 800;
    const labelAreaWidth = Math.floor(containerWidth * LABEL_WIDTH_RATIO);
    const chartAreaWidth = containerWidth - labelAreaWidth - MARGIN.left - MARGIN.right;
    const contentHeight = data.length * BAR_TOTAL;
    const totalHeight = contentHeight + MARGIN.top + MARGIN.bottom;

    // Scrollable wrapper setup
    const outerContainer = root.parentElement;
    if (outerContainer) {
        outerContainer.style.height = '420px';
        outerContainer.style.overflowY = 'auto';
        outerContainer.style.overflowX = 'hidden';
    }

    // Create SVG
    const svg = d3.select(root)
        .append('svg')
        .attr('width', containerWidth)
        .attr('height', totalHeight)
        .attr('class', 'd3-chart-svg');

    // Title
    svg.append('text')
        .attr('x', containerWidth / 2)
        .attr('y', 22)
        .attr('text-anchor', 'middle')
        .attr('class', 'd3-chart-title')
        .style('fill', theme.text)
        .style('font-size', '13px')
        .style('font-weight', '600')
        .text(chartTitle);

    // Scale
    const maxVal = d3.max(data, d => d[config.valueField] || 0) || 1;
    const xScale = d3.scaleLinear()
        .domain([0, maxVal])
        .range([0, chartAreaWidth]);

    // Chart group
    const g = svg.append('g')
        .attr('transform', `translate(${MARGIN.left}, ${MARGIN.top})`);

    // Row groups
    const rows = g.selectAll('.d3-bar-row')
        .data(data)
        .enter()
        .append('g')
        .attr('class', 'd3-bar-row')
        .attr('transform', (d, i) => `translate(0, ${i * BAR_TOTAL})`)
        .on('mouseenter', (event, d) => {
            showD3PromoTooltip(event, d, config);
        })
        .on('mousemove', (event) => {
            positionTooltip(event);
        })
        .on('mouseleave', () => {
            hideD3Tooltip();
        });

    // Rank number
    rows.append('text')
        .attr('x', 0)
        .attr('y', BAR_HEIGHT / 2)
        .attr('dy', '0.35em')
        .attr('class', 'd3-bar-rank')
        .style('fill', theme.muted)
        .style('font-size', '10px')
        .style('text-anchor', 'start')
        .text((d, i) => `${i + 1}`);

    // Label (word or tag text)
    const rankOffset = 28;
    const labelMaxW = labelAreaWidth - rankOffset - 8;

    rows.append('foreignObject')
        .attr('x', rankOffset)
        .attr('y', 0)
        .attr('width', labelMaxW)
        .attr('height', BAR_HEIGHT)
        .append('xhtml:div')
        .attr('class', 'd3-bar-label')
        .style('color', theme.text)
        .style('width', `${labelMaxW}px`)
        .style('height', `${BAR_HEIGHT}px`)
        .style('line-height', `${BAR_HEIGHT}px`)
        .style('overflow', 'hidden')
        .style('text-overflow', 'ellipsis')
        .style('white-space', 'nowrap')
        .style('font-size', '11px')
        .style('font-weight', '500')
        .attr('title', d => d[config.labelField] || '')
        .text(d => d[config.labelField] || "");

    // Bars
    const barX = labelAreaWidth;

    rows.append('rect')
        .attr('class', 'd3-bar-rect')
        .attr('x', barX)
        .attr('y', 1)
        .attr('height', BAR_HEIGHT - 2)
        .attr('rx', 3)
        .attr('ry', 3)
        .style('fill', config.color)
        .style('opacity', 0.85)
        // Animate from 0 width
        .attr('width', 0)
        .transition()
        .duration(ANIMATION_DURATION)
        .delay((d, i) => i * ANIMATION_STAGGER)
        .ease(d3.easeCubicOut)
        .attr('width', d => Math.max(2, xScale(d[config.valueField] || 0)));

    // Value labels on bars
    rows.append('text')
        .attr('x', d => barX + Math.max(2, xScale(d[config.valueField] || 0)) + 6)
        .attr('y', BAR_HEIGHT / 2)
        .attr('dy', '0.35em')
        .attr('class', 'd3-bar-value')
        .style('fill', theme.muted)
        .style('font-size', '10px')
        .style('opacity', 0)
        .text(d => `${(d[config.valueField] || 0).toFixed(2)}x`)
        .transition()
        .duration(ANIMATION_DURATION)
        .delay((d, i) => i * ANIMATION_STAGGER + ANIMATION_DURATION * 0.5)
        .style('opacity', 1);

    // Light gridlines on x axis
    const tickCount = 5;
    const ticks = xScale.ticks(tickCount);
    
    g.selectAll('.d3-grid-line')
        .data(ticks.slice(1)) // skip 0
        .enter()
        .append('line')
        .attr('class', 'd3-grid-line')
        .attr('x1', d => barX + xScale(d))
        .attr('x2', d => barX + xScale(d))
        .attr('y1', -4)
        .attr('y2', contentHeight)
        .style('stroke', theme.gridLine)
        .style('stroke-width', 1)
        .style('stroke-dasharray', '3,3');

    // Axis labels at top
    g.selectAll('.d3-axis-label')
        .data(ticks.filter((t, i) => i % 2 === 0 || i === ticks.length - 1))
        .enter()
        .append('text')
        .attr('class', 'd3-axis-label')
        .attr('x', d => barX + xScale(d))
        .attr('y', -8)
        .attr('text-anchor', 'middle')
        .style('fill', theme.muted)
        .style('font-size', '9px')
        .text(d => `${d}x`);
}

/**
 * Unified entry point to render D3 charts (both video metric and keywords lift).
 */
export function renderD3Chart(chartType, d3RootNode, chartState = state) {
    if (D3_VIDEO_CHART_TYPES.includes(chartType)) {
        renderD3VideoChart(chartType, d3RootNode, chartState);
    } else if (D3_PROMO_CHART_TYPES.includes(chartType)) {
        renderD3PromoChart(chartType, d3RootNode, chartState);
    }
}

// ─── Helpers ────────────────────────────────────────────────

function formatCompact(value) {
    if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + 'M';
    if (value >= 1_000) return (value / 1_000).toFixed(0) + 'K';
    return value.toString();
}

/**
 * Check if a chart type should be rendered by D3 (Phase 1 video + Phase 2 promo charts).
 */
export function isD3ChartType(chartType) {
    return D3_VIDEO_CHART_TYPES.includes(chartType) || D3_PROMO_CHART_TYPES.includes(chartType);
}
