import { state } from './state.js';
import { translations } from './translations.js';
import { CHART_DEFS, initChartUI, renderActiveChart } from './charts.js';

const STORAGE_KEY = 'dashboard_widgets_v1';
const WIDGETS_STATE_ENDPOINT = '/api/widgets/state';

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function readDateRange() {
    return {
        startDate: document.getElementById('filter-start-date')?.value || '',
        endDate: document.getElementById('filter-end-date')?.value || ''
    };
}

function findUatvEnglishChannel() {
    return state.allChannels.find(ch => ch.channel_name && ch.channel_name.toLowerCase().includes('uatv english'));
}

function defaultChannelIds(preferSecondary = false) {
    if (!state.allChannels.length) return [];

    const uatv = findUatvEnglishChannel();
    if (preferSecondary) {
        const secondary = state.allChannels.find(ch => !uatv || ch.channel_id !== uatv.channel_id);
        if (secondary) return [secondary.channel_id];
    }

    return [uatv?.channel_id || state.allChannels[0].channel_id];
}

function chartLabel(chartType) {
    const def = CHART_DEFS.find(item => item.id === chartType);
    if (!def) return chartType || 'chart';
    return translations[state.currentLang]?.[def.labelKey] || def.labelKey || chartType || 'chart';
}

function formatMetricLine(chartType, item, index) {
    const rank = index + 1;
    if (['top_viewed', 'worst_viewed', 'top_liked', 'worst_liked', 'top_commented', 'worst_commented'].includes(chartType)) {
        const channel = state.allChannels.find(ch => ch.channel_id === item.channel_id);
        const metric = chartType.includes('viewed')
            ? `views=${item.view_count || 0}`
            : chartType.includes('liked')
                ? `likes=${item.like_count || 0}`
                : `comments=${item.comment_count || 0}`;
        return `${rank}. "${item.title || 'Untitled'}" | channel=${channel?.channel_name || item.channel_id || '-'} | date=${(item.published_at || '').slice(0, 10) || '-'} | ${metric}`;
    }

    const label = item.word || item.tag || item.phrase || item.day_of_week || item.category || item.title || 'Unknown';
    const lift = item.lift !== undefined ? ` | lift=${Number(item.lift || 0).toFixed(2)}x` : '';
    const count = item.video_count !== undefined ? ` | videos=${item.video_count}` : '';
    const views = item.total_views !== undefined ? ` | views=${item.total_views}` : '';
    return `${rank}. ${label}${lift}${count}${views}`;
}

class BaseWidget {
    constructor(workspace, config = {}) {
        this.workspace = workspace;
        this.id = config.id || `widget-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        this.type = config.type;
        this.element = null;
    }

    mount(container) {
        this.element = this.renderShell();
        container.appendChild(this.element);
        this.afterMount();
    }

    renderShell() {
        const el = document.createElement('div');
        el.className = 'card dashboard-column-card dashboard-widget';
        el.dataset.widgetId = this.id;
        el.dataset.widgetType = this.type;
        return el;
    }

    afterMount() {}

    destroy() {
        if (this.element) this.element.remove();
    }

    toJSON() {
        return { id: this.id, type: this.type };
    }
}

class ChannelAnalyticsWidget extends BaseWidget {
    constructor(workspace, config = {}) {
        super(workspace, { ...config, type: 'channel-analytics' });
        this.chartState = {
            activeChartInstance: null,
            chartRawData: null,
            activeChartType: config.activeChartType || 'top_viewed',
            chartLimit: Number(config.chartLimit || state.chartLimit || 50),
            selectedChannelIds: Array.isArray(config.selectedChannelIds) && config.selectedChannelIds.length
                ? config.selectedChannelIds
                : defaultChannelIds(config.preferSecondary),
            channelColors: state.channelColors
        };
        this.resizeObserver = null;
        this.resizeTimer = null;
        this.handleDocumentClick = null;
    }

    afterMount() {
        this.element.innerHTML = `
            <div class="card-header dashboard-card-header widget-card-header">
                <div class="card-header-left">
                    <div class="top-filter-item custom-dropdown widget-channel-dropdown">
                        <button class="control-select dropdown-trigger widget-channel-btn" type="button">
                            <span class="widget-selected-text">Choose channels</span>
                            <i class="fa-solid fa-chevron-down"></i>
                        </button>
                        <div class="dropdown-menu-channels widget-channel-menu" style="display:none;">
                            <div class="dropdown-actions">
                                <button class="btn-dropdown-action widget-select-all" type="button">All</button>
                                <button class="btn-dropdown-action widget-select-none" type="button">Clear</button>
                            </div>
                            <div class="dropdown-channels-list widget-channels-list"></div>
                            <div class="dropdown-apply-container">
                                <button class="btn-primary widget-apply" type="button" style="width:100%; padding:6px; font-size:11px;">Apply</button>
                            </div>
                        </div>
                    </div>
                    <div class="top-filter-item widget-limit-control">
                        <span>Limit:</span>
                        <select class="control-select widget-chart-limit">
                            <option value="10">10</option>
                            <option value="25">25</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                            <option value="200">200</option>
                        </select>
                    </div>
                    <button class="widget-remove-btn" type="button" title="Remove widget">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                    <span class="task-badge idle widget-status"></span>
                </div>
                <div class="card-header-right widget-chart-controls"></div>
            </div>
            <div class="widget-channel-details"></div>
            <div class="card-body">
                <div class="chart-container" style="height:280px; width:100%;">
                    <div class="d3-chart-root" style="display:none; width:100%; height:100%;"></div>
                    <canvas></canvas>
                </div>
            </div>
        `;

        this.bindControls();
        this.renderChannelMenu();
        initChartUI({
            container: this.element.querySelector('.widget-chart-controls'),
            chartState: this.chartState,
            idPrefix: `chart-btn-${this.id}`,
            onSelect: chartType => this.selectChart(chartType)
        });
        this.element.querySelector('.widget-chart-limit').value = String(this.chartState.chartLimit);
        this.load();
        this.observeResize();
    }

    bindControls() {
        this.element.querySelector('.widget-channel-btn').addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            const menu = this.element.querySelector('.widget-channel-menu');
            menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
        });

        this.element.querySelector('.widget-select-all').addEventListener('click', () => {
            this.element.querySelectorAll('.widget-channel-check').forEach(chk => { chk.checked = true; });
            this.updateSelectedLabel();
        });

        this.element.querySelector('.widget-select-none').addEventListener('click', () => {
            this.element.querySelectorAll('.widget-channel-check').forEach(chk => { chk.checked = false; });
            this.updateSelectedLabel();
        });

        this.element.querySelector('.widget-apply').addEventListener('click', () => {
            this.chartState.selectedChannelIds = this.getCheckedChannelIds();
            this.element.querySelector('.widget-channel-menu').style.display = 'none';
            this.load();
            this.workspace.save();
        });

        this.element.querySelector('.widget-chart-limit').addEventListener('change', event => {
            this.chartState.chartLimit = Number(event.target.value || 50);
            initChartUI({
                container: this.element.querySelector('.widget-chart-controls'),
                chartState: this.chartState,
                idPrefix: `chart-btn-${this.id}`,
                onSelect: chartType => this.selectChart(chartType)
            });
            this.load();
            this.workspace.save();
        });

        this.element.querySelector('.widget-remove-btn').addEventListener('click', () => {
            this.workspace.removeWidget(this.id);
        });

        this.handleDocumentClick = event => {
            if (!this.element || this.element.contains(event.target)) return;
            const menu = this.element.querySelector('.widget-channel-menu');
            if (menu) menu.style.display = 'none';
        };
        document.addEventListener('click', this.handleDocumentClick);
    }

    renderChannelMenu() {
        const list = this.element.querySelector('.widget-channels-list');
        list.innerHTML = '';

        state.allChannels.forEach(channel => {
            const row = document.createElement('div');
            row.className = 'channel-item-row';
            const checked = this.chartState.selectedChannelIds.includes(channel.channel_id) ? 'checked' : '';
            const color = state.channelColors[channel.channel_id] || '#008abb';
            row.innerHTML = `
                <label class="channel-item-label">
                    <input class="widget-channel-check" type="checkbox" value="${escapeHtml(channel.channel_id)}" ${checked}>
                    <span class="channel-name-span" title="${escapeHtml(channel.channel_name)}">${escapeHtml(channel.channel_name)}</span>
                </label>
                <div class="channel-color-picker-wrapper">
                    <input type="color" value="${escapeHtml(color)}" class="channel-color-input widget-channel-color" data-channel-id="${escapeHtml(channel.channel_id)}">
                </div>
            `;
            list.appendChild(row);
        });

        list.querySelectorAll('.widget-channel-check').forEach(chk => {
            chk.addEventListener('change', () => this.updateSelectedLabel());
        });

        list.querySelectorAll('.widget-channel-color').forEach(input => {
            input.addEventListener('change', event => {
                const channelId = event.target.getAttribute('data-channel-id');
                state.channelColors[channelId] = event.target.value;
                localStorage.setItem('channel_colors', JSON.stringify(state.channelColors));
                this.chartState.channelColors = state.channelColors;
                renderActiveChart(this.element, this.chartState);
            });
        });

        this.updateSelectedLabel();
    }

    getCheckedChannelIds() {
        return Array.from(this.element.querySelectorAll('.widget-channel-check:checked')).map(chk => chk.value);
    }

    updateSelectedLabel() {
        const selected = this.getCheckedChannelIds();
        const label = this.element.querySelector('.widget-selected-text');

        if (!selected.length) {
            label.textContent = 'Choose channels';
        } else if (selected.length === 1) {
            const channel = state.allChannels.find(ch => ch.channel_id === selected[0]);
            label.textContent = channel?.channel_name || selected[0];
        } else if (selected.length === state.allChannels.length) {
            label.textContent = 'All Channels';
        } else {
            label.textContent = `${selected.length} channels`;
        }
    }

    selectChart(chartType) {
        this.chartState.activeChartType = chartType;
        renderActiveChart(this.element, this.chartState);
        this.workspace.save();
    }

    async load() {
        const selected = this.chartState.selectedChannelIds.filter(Boolean);
        this.updateSelectedLabel();
        if (!selected.length) {
            this.setStatus('No channel');
            return;
        }

        this.setStatus('Loading...');
        await Promise.all([this.loadHeader(selected), this.loadChartData(selected)]);
        this.setStatus('');
    }

    async loadHeader(selected) {
        const target = this.element.querySelector('.widget-channel-details');
        const { startDate, endDate } = readDateRange();
        const params = new URLSearchParams({
            channel_ids: selected.join(','),
            start_date: startDate,
            end_date: endDate
        });

        try {
            const response = await fetch(`/api/channel/stats?${params.toString()}`);
            const data = await response.json();
            this.renderHeader(data);
        } catch (error) {
            console.error('Widget channel stats failed:', error);
            target.innerHTML = `<div class="widget-error">Failed to load channel stats.</div>`;
        }
    }

    renderHeader(data) {
        const target = this.element.querySelector('.widget-channel-details');
        if (!target) return;

        if (data.error) {
            target.innerHTML = `<div class="widget-error">${escapeHtml(data.error)}</div>`;
            return;
        }

        const totalViews = (data.db_total_views ?? 0).toLocaleString();
        const videos = (data.db_video_count ?? 0).toLocaleString();
        const median = (data.db_median_views ?? 0).toLocaleString();
        const likeRatio = data.db_total_views > 0 ? (((data.db_total_likes || 0) / data.db_total_views) * 100).toFixed(2) + '%' : '0.00%';
        const commentRatio = data.db_total_views > 0 ? (((data.db_total_comments || 0) / data.db_total_views) * 100).toFixed(2) + '%' : '0.00%';

        if (data.mode === 'single') {
            const bannerStyle = data.banner_url
                ? `background-image:url('${escapeHtml(data.banner_url)}');`
                : 'background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);';
            const avatarUrl = data.avatar_url || 'https://www.youtube.com/img/desktop/yt_1200_share.png';

            target.innerHTML = `
                <div class="channel-premium-header widget-premium-header">
                    <div class="channel-banner-bg" style="${bannerStyle}"></div>
                    <div class="channel-profile-info">
                        <div class="channel-avatar-wrapper">
                            <img src="${escapeHtml(avatarUrl)}" alt="" onerror="this.src='https://www.youtube.com/img/desktop/yt_1200_share.png'">
                        </div>
                        <div class="channel-meta-text">
                            <div class="channel-name-title"><span>${escapeHtml(data.channel_name)}</span></div>
                            <div class="channel-handle-sub">${data.channel_handle ? '@' + escapeHtml(data.channel_handle) : ''}</div>
                            <div class="channel-desc-sub" title="${escapeHtml(data.description || '')}">${escapeHtml(data.description || '')}</div>
                        </div>
                        ${this.renderStatBadges(videos, totalViews, median, likeRatio, commentRatio)}
                    </div>
                </div>
            `;
        } else {
            target.innerHTML = `
                <div class="combined-premium-banner widget-combined-banner">
                    <div class="combined-banner-title">
                        <i class="fa-solid fa-layer-group"></i>
                        <div class="combined-title-text">
                            <div class="combined-title-main">Consolidated Database Analytics</div>
                            <div class="combined-title-sub">Analytics snapshot for ${escapeHtml(data.channel_count || 0)} channels</div>
                        </div>
                    </div>
                    ${this.renderStatBadges(videos, totalViews, median, likeRatio, commentRatio)}
                </div>
            `;
        }
    }

    renderStatBadges(videos, totalViews, median, likeRatio, commentRatio) {
        return `
            <div class="channel-header-stats">
                <div class="header-stat-badge"><span class="header-stat-num">${videos}</span><span class="header-stat-lbl">Videos</span></div>
                <div class="header-stat-badge"><span class="header-stat-num">${totalViews}</span><span class="header-stat-lbl">Views</span></div>
                <div class="header-stat-badge"><span class="header-stat-num">${median}</span><span class="header-stat-lbl">Median</span></div>
                <div class="header-stat-badge"><span class="header-stat-num">${likeRatio}</span><span class="header-stat-lbl">Likes/Views</span></div>
                <div class="header-stat-badge"><span class="header-stat-num">${commentRatio}</span><span class="header-stat-lbl">Comments/Views</span></div>
            </div>
        `;
    }

    async loadChartData(selected) {
        const { startDate, endDate } = readDateRange();
        const params = new URLSearchParams({
            channel_id: selected.join(','),
            limit: this.chartState.chartLimit
        });
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);

        try {
            const response = await fetch(`/api/charts?${params.toString()}`);
            this.chartState.chartRawData = await response.json();
            renderActiveChart(this.element, this.chartState);
        } catch (error) {
            console.error('Widget chart load failed:', error);
            this.element.querySelector('.chart-container').innerHTML = `<div class="widget-error">Failed to load chart.</div>`;
        }
    }

    setStatus(text) {
        const badge = this.element.querySelector('.widget-status');
        if (!badge) return;
        badge.textContent = text;
        badge.style.display = text ? 'inline-block' : 'none';
    }

    observeResize() {
        if (!window.ResizeObserver) return;
        this.resizeObserver = new ResizeObserver(() => {
            clearTimeout(this.resizeTimer);
            this.resizeTimer = setTimeout(() => {
                if (this.chartState.chartRawData) renderActiveChart(this.element, this.chartState);
            }, 120);
        });
        this.resizeObserver.observe(this.element);
    }

    destroy() {
        if (this.resizeObserver) this.resizeObserver.disconnect();
        if (this.handleDocumentClick) document.removeEventListener('click', this.handleDocumentClick);
        if (this.chartState.activeChartInstance) this.chartState.activeChartInstance.destroy();
        super.destroy();
    }

    toJSON() {
        return {
            ...super.toJSON(),
            selectedChannelIds: this.chartState.selectedChannelIds,
            activeChartType: this.chartState.activeChartType,
            chartLimit: this.chartState.chartLimit
        };
    }

    serializeForSummary() {
        const chartType = this.chartState.activeChartType;
        const chartRawData = this.chartState.chartRawData;
        const rows = chartRawData && chartType ? chartRawData[chartType] : null;
        const channels = this.chartState.selectedChannelIds
            .map(id => state.allChannels.find(ch => ch.channel_id === id)?.channel_name || id)
            .join(', ');

        if (!Array.isArray(rows) || rows.length === 0) {
            return `Widget: Channel Analytics\nChannels: ${channels || '-'}\nChart: ${chartLabel(chartType)}\nNo data loaded.`;
        }

        const maxRows = Math.min(rows.length, 30);
        const body = rows.slice(0, maxRows).map((item, index) => formatMetricLine(chartType, item, index)).join('\n');
        return `Widget: Channel Analytics\nChannels: ${channels || '-'}\nChart: ${chartLabel(chartType)}\nRows: ${rows.length}\n\n${body}`;
    }
}

export class DashboardWorkspace {
    constructor(root) {
        this.root = root;
        this.widgets = new Map();
        this.palette = document.querySelector('.widget-palette');
    }

    async init() {
        if (!this.root) return;
        this.bindPalette();
        this.bindDropzone();
        await this.restore();
    }

    bindPalette() {
        if (!this.palette) return;
        this.palette.querySelectorAll('.widget-template').forEach(template => {
            template.addEventListener('dragstart', event => {
                event.dataTransfer.setData('application/x-dashboard-widget', template.dataset.widgetType);
                event.dataTransfer.effectAllowed = 'copy';
            });
            template.addEventListener('click', () => {
                this.addWidget(template.dataset.widgetType, { preferSecondary: true });
            });
        });
    }

    bindDropzone() {
        this.root.addEventListener('dragover', event => {
            const types = Array.from(event.dataTransfer?.types || []);
            if (!types.includes('application/x-dashboard-widget')) return;
            event.preventDefault();
            this.root.classList.add('dashboard-workspace-dragover');
        });
        this.root.addEventListener('dragleave', event => {
            if (!this.root.contains(event.relatedTarget)) {
                this.root.classList.remove('dashboard-workspace-dragover');
            }
        });
        this.root.addEventListener('drop', event => {
            const type = event.dataTransfer.getData('application/x-dashboard-widget');
            if (!type) return;
            event.preventDefault();
            this.root.classList.remove('dashboard-workspace-dragover');
            this.addWidget(type, { preferSecondary: true });
        });
    }

    addWidget(type, config = {}) {
        if (type !== 'channel-analytics') return null;
        const widget = new ChannelAnalyticsWidget(this, config);
        this.widgets.set(widget.id, widget);
        widget.mount(this.root);
        this.save();
        return widget;
    }

    removeWidget(id) {
        const widget = this.widgets.get(id);
        if (!widget) return;
        widget.destroy();
        this.widgets.delete(id);
        this.save();
    }

    refreshAll() {
        this.widgets.forEach(widget => widget.load());
    }

    serializeForSummary() {
        return Array.from(this.widgets.values())
            .map(widget => widget.serializeForSummary?.())
            .filter(Boolean);
    }

    save() {
        const data = Array.from(this.widgets.values()).map(widget => widget.toJSON());
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        void this.saveRemote(data);
    }

    async saveRemote(data) {
        try {
            await fetch(WIDGETS_STATE_ENDPOINT, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ widgets: data })
            });
        } catch (error) {
            // LocalStorage remains the source of truth when server persistence is unavailable.
        }
    }

    async loadRemote() {
        try {
            const response = await fetch(WIDGETS_STATE_ENDPOINT);
            if (!response.ok) return null;
            const data = await response.json();
            return Array.isArray(data.widgets) ? data.widgets : null;
        } catch (error) {
            return null;
        }
    }

    readLocal() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        } catch (error) {
            return [];
        }
    }

    async restore() {
        let saved = await this.loadRemote();
        if (!Array.isArray(saved) || !saved.length) saved = this.readLocal();
        saved
            .filter(item => item && item.type === 'channel-analytics')
            .forEach(item => this.addWidget(item.type, item));
    }
}

export function initDashboardWorkspace() {
    const workspace = new DashboardWorkspace(document.getElementById('dashboard-workspace'));
    void workspace.init();
    window.dashboardWorkspace = workspace;
    return workspace;
}
