import { state } from './state.js';
import { translations } from './translations.js';
import { CHART_DEFS, initChartUI, renderActiveChart } from './charts.js';
import { adminFetch, adminFetchSilent } from './auth.js';

const STORAGE_KEY = 'dashboard_widgets_v1';
const WIDGETS_STATE_ENDPOINT = '/api/widgets/state';
const MIN_WIDGET_WIDTH = 320;
const MIN_WIDGET_HEIGHT = 180;
const MAX_WIDGET_HEIGHT_RATIO = 0.86;

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

function parsePixelSize(value) {
    if (typeof value !== 'string') return null;
    const match = value.trim().match(/^(\d+(?:\.\d+)?)px$/);
    if (!match) return null;
    const parsed = Number(match[1]);
    return Number.isFinite(parsed) ? parsed : null;
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

function getPresetDateRange(preset) {
    const today = new Date();
    const formatDate = (d) => d.toISOString().split('T')[0];
    
    let start = new Date();
    let end = new Date();
    
    switch (preset) {
        case 'today':
            break;
        case 'yesterday':
            start.setDate(today.getDate() - 1);
            end.setDate(today.getDate() - 1);
            break;
        case 'week':
            start.setDate(today.getDate() - 7);
            break;
        case 'prev-week':
            start.setDate(today.getDate() - 14);
            end.setDate(today.getDate() - 7);
            break;
        case 'month':
            start.setDate(today.getDate() - 30);
            break;
        case 'prev-month':
            start.setDate(today.getDate() - 60);
            end.setDate(today.getDate() - 30);
            break;
    }
    return { start: formatDate(start), end: formatDate(end) };
}

function getPresetDateRangeForDays(days) {
    const today = new Date();
    const start = new Date();
    start.setDate(today.getDate() - days);
    return {
        start: start.toISOString().split('T')[0],
        end: today.toISOString().split('T')[0]
    };
}


class BaseWidget {
    constructor(workspace, config = {}) {
        this.workspace = workspace;
        this.id = config.id || `widget-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        this.type = config.type;
        this.width = config.width || '';
        this.height = config.height || '';
        this.collapsed = !!config.collapsed;
        this.dateStart = config.dateStart || '';
        this.dateEnd = config.dateEnd || '';
        this.linkedWidgetIds = config.linkedWidgetIds || [];
        this.element = null;
    }

    mount(container) {
        this.element = this.renderShell();
        container.appendChild(this.element);
        this.afterMount();
        this.setupResizingAndCollapsing();
        this.clampStoredDimensions();
    }

    renderShell() {
        const el = document.createElement('div');
        el.className = 'card dashboard-column-card dashboard-widget';
        el.dataset.widgetId = this.id;
        el.dataset.widgetType = this.type;
        el.style.position = 'relative';

        if (this.width) el.style.width = this.width;
        if (this.height) el.style.height = this.height;
        if (this.collapsed) {
            el.classList.add('collapsed');
        }
        return el;
    }

    afterMount() {}

    setupResizingAndCollapsing() {
        if (!this.element) return;

        const removeBtn = this.element.querySelector('.widget-remove-btn');
        if (removeBtn) {
            const collapseBtn = document.createElement('button');
            collapseBtn.type = 'button';
            collapseBtn.className = 'widget-collapse-btn';
            collapseBtn.title = 'Collapse/Expand widget';
            collapseBtn.innerHTML = this.collapsed ? '<i class="fa-solid fa-chevron-down"></i>' : '<i class="fa-solid fa-chevron-up"></i>';

            collapseBtn.style.background = 'none';
            collapseBtn.style.border = 'none';
            collapseBtn.style.color = 'var(--text-muted)';
            collapseBtn.style.cursor = 'pointer';
            collapseBtn.style.padding = '0 6px';
            collapseBtn.style.fontSize = '12px';
            collapseBtn.style.display = 'inline-flex';
            collapseBtn.style.alignItems = 'center';
            collapseBtn.style.justifyContent = 'center';
            collapseBtn.style.position = 'absolute';
            collapseBtn.style.top = '12px';
            collapseBtn.style.right = '38px';
            collapseBtn.style.zIndex = '10';

            this.element.appendChild(collapseBtn);

            collapseBtn.addEventListener('click', () => {
                this.toggleCollapse();
            });
        }

        const handle = document.createElement('div');
        handle.className = 'widget-resize-handle';
        handle.innerHTML = '<i class="fa-solid fa-caret-down" aria-hidden="true"></i>';

        this.element.appendChild(handle);

        const initResize = (e) => {
            e.preventDefault();
            const point = e.touches?.[0] || e;
            const startX = point.clientX;
            const startY = point.clientY;
            if (!Number.isFinite(startX) || !Number.isFinite(startY)) return;
            const startWidth = this.element.offsetWidth;
            const startHeight = this.element.offsetHeight;

            const onResize = (moveEvent) => {
                const movePoint = moveEvent.touches?.[0] || moveEvent;
                const currentX = movePoint.clientX;
                const currentY = movePoint.clientY;
                if (!Number.isFinite(currentX) || !Number.isFinite(currentY)) return;

                const { maxWidth, maxHeight } = this.dimensionLimits();
                const newWidth = Math.min(maxWidth, Math.max(MIN_WIDGET_WIDTH, startWidth + (currentX - startX)));
                const newHeight = Math.min(maxHeight, Math.max(MIN_WIDGET_HEIGHT, startHeight + (currentY - startY)));

                this.element.style.width = `${newWidth}px`;
                this.element.style.height = `${newHeight}px`;

                this.width = `${newWidth}px`;
                this.height = `${newHeight}px`;

                window.dispatchEvent(new Event('resize'));
            };

            const stopResize = () => {
                window.removeEventListener('mousemove', onResize);
                window.removeEventListener('mouseup', stopResize);
                window.removeEventListener('touchmove', onResize);
                window.removeEventListener('touchend', stopResize);
                this.workspace.save();
            };

            window.addEventListener('mousemove', onResize);
            window.addEventListener('mouseup', stopResize);
            window.addEventListener('touchmove', onResize, { passive: false });
            window.addEventListener('touchend', stopResize);
        };

        handle.addEventListener('mousedown', initResize);
        handle.addEventListener('touchstart', initResize, { passive: false });
    }

    dimensionLimits() {
        const rootWidth = this.workspace?.root?.clientWidth || window.innerWidth || MIN_WIDGET_WIDTH;
        const maxWidth = Math.max(MIN_WIDGET_WIDTH, rootWidth);
        const maxHeight = Math.max(MIN_WIDGET_HEIGHT, Math.floor((window.innerHeight || 900) * MAX_WIDGET_HEIGHT_RATIO));
        return { maxWidth, maxHeight };
    }

    clampStoredDimensions() {
        if (!this.element || this.collapsed) return;
        const { maxWidth, maxHeight } = this.dimensionLimits();
        const storedWidth = parsePixelSize(this.width);
        const storedHeight = parsePixelSize(this.height);
        if (storedWidth !== null) {
            const nextWidth = Math.min(maxWidth, Math.max(MIN_WIDGET_WIDTH, storedWidth));
            this.width = `${nextWidth}px`;
            this.element.style.width = this.width;
        }
        if (storedHeight !== null) {
            const nextHeight = Math.min(maxHeight, Math.max(MIN_WIDGET_HEIGHT, storedHeight));
            this.height = `${nextHeight}px`;
            this.element.style.height = this.height;
        }
    }

    toggleCollapse() {
        this.collapsed = !this.collapsed;
        if (this.collapsed) {
            this.element.classList.add('collapsed');
        } else {
            this.element.classList.remove('collapsed');
        }

        const collapseBtn = this.element.querySelector('.widget-collapse-btn');
        if (collapseBtn) {
            collapseBtn.innerHTML = this.collapsed ? '<i class="fa-solid fa-chevron-down"></i>' : '<i class="fa-solid fa-chevron-up"></i>';
        }

        window.dispatchEvent(new Event('resize'));
        this.workspace.save();
    }

    renderDateSyncMenu() {
        const container = document.createElement('div');
        container.className = 'top-filter-item widget-date-sync-container';
        container.style.position = 'relative';
        container.style.display = 'inline-block';

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'control-select widget-date-sync-btn';
        btn.title = 'Configure date & sync';
        btn.style.padding = '4px 8px';
        btn.style.fontSize = '11px';
        btn.style.display = 'inline-flex';
        btn.style.alignItems = 'center';
        btn.style.gap = '4px';
        btn.innerHTML = `<i class="fa-solid fa-calendar-days"></i> <span class="widget-date-summary-text">Auto</span>`;
        container.appendChild(btn);

        const menu = document.createElement('div');
        menu.className = 'widget-date-sync-menu';
        menu.style.cssText = 'display:none; position:absolute; right:0; top:30px; z-index:1000; background:var(--card-bg); border:1px solid var(--border-color); border-radius:6px; padding:12px; min-width:280px; box-shadow:0 4px 12px rgba(0,0,0,0.15);';
        
        menu.innerHTML = `
            <div style="font-weight:700; font-size:12px; margin-bottom:8px; color:var(--text-color);">Date Scope</div>
            <div style="display:flex; gap:6px; margin-bottom:8px;">
                <input type="date" class="control-select widget-start-date" style="padding:4px; font-size:11px; flex:1;" />
                <input type="date" class="control-select widget-end-date" style="padding:4px; font-size:11px; flex:1;" />
            </div>
            <div class="widget-date-presets" style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px;">
                <button class="btn-dropdown-action date-preset-btn" data-range="today" type="button">Today</button>
                <button class="btn-dropdown-action date-preset-btn" data-range="yesterday" type="button">Yesterday</button>
                <button class="btn-dropdown-action date-preset-btn" data-range="week" type="button">Week</button>
                <button class="btn-dropdown-action date-preset-btn" data-range="prev-week" type="button">Prev Week</button>
                <button class="btn-dropdown-action date-preset-btn" data-range="month" type="button">Month</button>
                <button class="btn-dropdown-action date-preset-btn" data-range="prev-month" type="button">Prev Month</button>
            </div>
            <div style="margin-bottom:8px;">
                <input type="range" class="widget-date-slider" style="width:100%; cursor:pointer;" min="1" max="180" value="30" />
                <div style="display:flex; justify-content:space-between; font-size:9px; color:var(--text-muted);">
                    <span>1 day</span>
                    <span class="widget-slider-label">30 days</span>
                    <span>180 days</span>
                </div>
            </div>
            <hr style="border:0; border-top:1px solid var(--border-color); margin:8px 0;" />
            <div style="font-weight:700; font-size:12px; margin-bottom:6px; color:var(--text-color);">Link / Sync Widgets</div>
            <div class="widget-sync-list" style="max-height:100px; overflow-y:auto; display:flex; flex-direction:column; gap:4px; margin-bottom:8px; font-size:11px; color:var(--text-color);">
            </div>
            <div style="display:flex; justify-content:space-between; gap:6px;">
                <button class="btn-secondary widget-date-clear-btn" type="button" style="padding:4px 8px; font-size:11px;">Reset</button>
                <button class="btn-primary widget-date-apply-btn" type="button" style="padding:4px 8px; font-size:11px;">Apply</button>
            </div>
        `;
        container.appendChild(menu);

        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
            if (menu.style.display === 'block') {
                this.populateSyncList(menu);
            }
        });

        const startInput = menu.querySelector('.widget-start-date');
        const endInput = menu.querySelector('.widget-end-date');
        startInput.value = this.dateStart || '';
        endInput.value = this.dateEnd || '';

        menu.querySelectorAll('.date-preset-btn').forEach(presetBtn => {
            presetBtn.addEventListener('click', () => {
                const range = getPresetDateRange(presetBtn.dataset.range);
                startInput.value = range.start;
                endInput.value = range.end;
            });
        });

        const slider = menu.querySelector('.widget-date-slider');
        const sliderLabel = menu.querySelector('.widget-slider-label');
        slider.addEventListener('input', () => {
            const days = parseInt(slider.value, 10);
            sliderLabel.textContent = `${days} days`;
            const range = getPresetDateRangeForDays(days);
            startInput.value = range.start;
            endInput.value = range.end;
        });

        menu.querySelector('.widget-date-clear-btn').addEventListener('click', () => {
            startInput.value = '';
            endInput.value = '';
            this.dateStart = '';
            this.dateEnd = '';
            this.updateDateSummary(btn);
            menu.style.display = 'none';
            this.load();
            this.workspace.save();
        });

        menu.querySelector('.widget-date-apply-btn').addEventListener('click', () => {
            this.dateStart = startInput.value;
            this.dateEnd = endInput.value;
            
            this.linkedWidgetIds = Array.from(menu.querySelectorAll('.widget-sync-check:checked')).map(chk => chk.value);

            this.updateDateSummary(btn);
            menu.style.display = 'none';
            this.load();
            this.workspace.save();

            this.propagateDates(this.dateStart, this.dateEnd);
        });

        this.updateDateSummary(btn);

        document.addEventListener('click', (e) => {
            if (!container.contains(e.target)) {
                menu.style.display = 'none';
            }
        });

        return container;
    }

    populateSyncList(menu) {
        const list = menu.querySelector('.widget-sync-list');
        list.innerHTML = '';
        
        let count = 0;
        this.workspace.widgets.forEach(other => {
            if (other.id === this.id) return;
            if (other.type !== 'channel-analytics' && other.type !== 'anomaly-alerts') return;
            
            count++;
            const row = document.createElement('label');
            row.style.display = 'flex';
            row.style.alignItems = 'center';
            row.style.gap = '6px';
            row.style.cursor = 'pointer';
            
            const isChecked = this.linkedWidgetIds.includes(other.id) ? 'checked' : '';
            const typeLabel = other.type === 'channel-analytics' ? 'Channel' : 'Anomalies';
            
            row.innerHTML = `
                <input type="checkbox" class="widget-sync-check" value="${other.id}" ${isChecked}>
                <span>${typeLabel} (${other.id.slice(-5)})</span>
            `;
            list.appendChild(row);
        });

        if (count === 0) {
            list.innerHTML = `<div style="color:var(--text-muted); font-style:italic;">No other widgets open</div>`;
        }
    }

    updateDateSummary(btn) {
        const label = btn.querySelector('.widget-date-summary-text');
        if (this.dateStart && this.dateEnd) {
            label.textContent = `${this.dateStart.slice(5)} / ${this.dateEnd.slice(5)}`;
        } else {
            label.textContent = 'Auto';
        }
    }

    propagateDates(start, end) {
        this.linkedWidgetIds.forEach(targetId => {
            const target = this.workspace.widgets.get(targetId);
            if (target) {
                target.dateStart = start;
                target.dateEnd = end;
                if (!target.linkedWidgetIds.includes(this.id)) {
                    target.linkedWidgetIds.push(this.id);
                }
                const btn = target.element.querySelector('.widget-date-sync-btn');
                if (btn) {
                    target.updateDateSummary(btn);
                    const startInput = target.element.querySelector('.widget-start-date');
                    const endInput = target.element.querySelector('.widget-end-date');
                    if (startInput) startInput.value = start || '';
                    if (endInput) endInput.value = end || '';
                }
                target.load();
            }
        });
    }

    destroy() {
        if (this.element) this.element.remove();
    }

    toJSON() {
        return {
            id: this.id,
            type: this.type,
            width: this.width,
            height: this.height,
            collapsed: this.collapsed,
            dateStart: this.dateStart,
            dateEnd: this.dateEnd,
            linkedWidgetIds: this.linkedWidgetIds
        };
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
            <button class="widget-remove-btn" type="button" title="Remove widget">
                <i class="fa-solid fa-xmark"></i>
            </button>
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
        
        const leftHeader = this.element.querySelector('.card-header-left');
        const limitControl = this.element.querySelector('.widget-limit-control');
        const dateSyncEl = this.renderDateSyncMenu();
        leftHeader.insertBefore(dateSyncEl, limitControl);

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
        const startDate = this.dateStart || document.getElementById('filter-start-date')?.value || '';
        const endDate = this.dateEnd || document.getElementById('filter-end-date')?.value || '';
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
        const startDate = this.dateStart || document.getElementById('filter-start-date')?.value || '';
        const endDate = this.dateEnd || document.getElementById('filter-end-date')?.value || '';
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

window.showAnomalyVideoModal = async function(videoId) {
    try {
        const response = await fetch(`/api/videos/${videoId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const video = await response.json();
        if (window.openVideoModal) {
            window.openVideoModal(video);
        }
    } catch (err) {
        console.error("Failed to load video details for modal:", err);
        alert(`Failed to load video details: ${err.message}`);
    }
};


class AnomalyAlertsWidget extends BaseWidget {
    constructor(workspace, config = {}) {
        super(workspace, { ...config, type: 'anomaly-alerts' });
        this.selectedChannelId = config.selectedChannelId || defaultChannelIds()[0] || '';
        this.anomalyThreshold = config.anomalyThreshold || 2.5;
        this.anomalies = [];
        this.summary = null;
        this.handleDocumentClick = null;
    }

    afterMount() {
        this.element.innerHTML = `
            <button class="widget-remove-btn" type="button" title="Remove widget" style="width:24px; height:24px; border-radius:4px; font-size:11px;">
                <i class="fa-solid fa-xmark"></i>
            </button>
            <div class="card-header dashboard-card-header widget-card-header">
                <div class="card-header-left" style="width: 100%; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid fa-triangle-exclamation" style="color:var(--warning-color); font-size:14px;"></i>
                        <span class="card-title" style="font-size:13px; font-weight:700;">Viral Anomalies</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;" class="header-widget-actions">
                        <div class="top-filter-item custom-dropdown widget-channel-dropdown">
                            <button class="control-select dropdown-trigger widget-channel-btn" type="button" style="padding: 4px 8px; font-size: 11px;">
                                <span class="widget-selected-text">Choose channel</span>
                                <i class="fa-solid fa-chevron-down" style="font-size:9px; margin-left:4px;"></i>
                            </button>
                            <div class="dropdown-menu-channels widget-channel-menu" style="display:none; min-width:180px; position:absolute; z-index:100; background:var(--card-bg); border:1px solid var(--border-color); border-radius:6px; margin-top:4px;">
                                <div class="dropdown-channels-list widget-channels-list" style="max-height: 180px; overflow-y: auto;"></div>
                            </div>
                        </div>
                        <div class="top-filter-item widget-limit-control" style="font-size: 11px; display: flex; align-items: center; gap: 4px;">
                            <span>Min:</span>
                            <select class="control-select widget-anomaly-threshold" style="padding: 4px; font-size: 11px;">
                                <option value="1.5">1.5σ</option>
                                <option value="2.0">2.0σ</option>
                                <option value="2.5">2.5σ</option>
                                <option value="3.0">3.0σ</option>
                                <option value="4.0">4.0σ</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
            <div class="card-body" style="padding-top: 4px;">
                <div class="anomaly-alerts-widget" style="min-height: 100px;">
                    <div class="widget-loading" style="text-align:center; color:var(--text-muted); font-size:11px; padding: 20px 0;">Loading anomalies...</div>
                </div>
            </div>
        `;

        this.bindControls();
        this.renderChannelMenu();
        
        const actionsContainer = this.element.querySelector('.header-widget-actions');
        const limitControl = this.element.querySelector('.widget-limit-control');
        const dateSyncEl = this.renderDateSyncMenu();
        actionsContainer.insertBefore(dateSyncEl, limitControl);

        this.element.querySelector('.widget-anomaly-threshold').value = String(this.anomalyThreshold);
        this.load();
    }

    bindControls() {
        const thresholdSelect = this.element.querySelector('.widget-anomaly-threshold');
        thresholdSelect.addEventListener('change', event => {
            this.anomalyThreshold = parseFloat(event.target.value || 2.5);
            this.load();
            this.workspace.save();
        });

        this.element.querySelector('.widget-channel-btn').addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            const menu = this.element.querySelector('.widget-channel-menu');
            menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
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
            row.style.padding = '6px 12px';
            row.style.cursor = 'pointer';
            row.style.fontSize = '11px';
            if (channel.channel_id === this.selectedChannelId) {
                row.style.background = 'var(--sidebar-hover)';
            }
            row.innerHTML = `<span class="channel-name-span" title="${escapeHtml(channel.channel_name)}">${escapeHtml(channel.channel_name)}</span>`;

            row.addEventListener('click', () => {
                this.selectedChannelId = channel.channel_id;
                this.element.querySelector('.widget-channel-menu').style.display = 'none';
                this.renderChannelMenu();
                this.load();
                this.workspace.save();
            });
            list.appendChild(row);
        });

        this.updateSelectedLabel();
    }

    updateSelectedLabel() {
        const label = this.element.querySelector('.widget-selected-text');
        const channel = state.allChannels.find(ch => ch.channel_id === this.selectedChannelId);
        label.textContent = channel ? channel.channel_name : 'Choose channel';
    }

    async load() {
        const target = this.element.querySelector('.anomaly-alerts-widget');
        if (!this.selectedChannelId) {
            target.innerHTML = `<div class="widget-error" style="font-size:11px; padding:20px 0;">Please select a channel.</div>`;
            return;
        }

        const channel = state.allChannels.find(ch => ch.channel_id === this.selectedChannelId);
        if (!channel) {
            target.innerHTML = `<div class="widget-error" style="font-size:11px; padding:20px 0;">Selected channel not found.</div>`;
            return;
        }

        const params = new URLSearchParams({
            channel: channel.channel_name,
            threshold: String(this.anomalyThreshold),
            output: 'json'
        });

        try {
            const response = await adminFetchSilent(`/api/analytics/anomalies?${params.toString()}`);
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || `HTTP ${response.status}`);
            }
            const data = await response.json();
            this.anomalies = data.anomalies || [];
            this.summary = data.summary || null;
            this.renderBody();
        } catch (error) {
            console.error('Widget load anomalies failed:', error);
            target.innerHTML = `<div class="widget-error" style="font-size:11px; padding:20px 0;">Failed to load anomalies: ${escapeHtml(error.message)}</div>`;
        }
    }

    renderBody() {
        const target = this.element.querySelector('.anomaly-alerts-widget');
        if (!target) return;

        // Apply local/linked date range filtering to anomalies list
        let filteredAnoms = this.anomalies;
        if (this.dateStart || this.dateEnd) {
            const start = this.dateStart ? new Date(this.dateStart) : null;
            const end = this.dateEnd ? new Date(this.dateEnd) : null;
            filteredAnoms = this.anomalies.filter(anom => {
                if (!anom.published_at) return true;
                const pubDate = new Date(anom.published_at.slice(0, 10));
                if (start && pubDate < start) return false;
                if (end && pubDate > end) return false;
                return true;
            });
        }

        if (filteredAnoms.length === 0) {
            target.innerHTML = `<div class="widget-loading" style="text-align:center; padding: 24px 0; color:var(--text-muted); font-size:11px;">No anomalies detected (threshold: ${this.anomalyThreshold}σ).</div>`;
            return;
        }

        target.innerHTML = '';
        filteredAnoms.slice(0, 5).forEach(anom => {
            const row = document.createElement('div');
            row.className = 'anomaly-video-row';
            row.style.marginBottom = '8px';

            let confClass = 'low';
            if (anom.confidence >= 0.7) confClass = 'high';
            else if (anom.confidence >= 0.4) confClass = 'medium';

            const formattedViews = (anom.views_24h || 0).toLocaleString();
            const pct = Math.round(anom.confidence * 100);

            const caveatBadges = (anom.caveat_details || [])
                .map(cav => `<span class="anomaly-caveat-badge" title="${escapeHtml(cav.text)}">${escapeHtml(cav.code)}</span>`)
                .join('');

            row.innerHTML = `
                <div class="anomaly-video-title-wrap">
                    <span class="anomaly-video-title" onclick="window.showAnomalyVideoModal('${escapeHtml(anom.video_id)}')">${escapeHtml(anom.title)}</span>
                    <span class="anomaly-confidence-badge ${confClass}">${pct}% conf</span>
                </div>
                <div class="anomaly-stats-bar">
                    <span class="anomaly-stat-item" title="Views accumulated over the monitored period">Views (24h): <strong>${formattedViews}</strong></span>
                    <span class="anomaly-stat-item" title="Z-Score (Standard Score): Indicates how many standard deviations the views are above the channel's average. &gt;2.0 means exceptionally high performance.">Z-Score: <strong>${anom.z_score >= 0 ? '+' : ''}${anom.z_score.toFixed(2)}σ</strong></span>
                </div>
                <div class="confidence-bar-container">
                    <div class="confidence-bar-outer">
                        <div class="confidence-bar-inner ${confClass}" style="width: ${anom.confidence * 100}%;"></div>
                    </div>
                    <span class="confidence-percent-lbl">${pct}%</span>
                </div>
                <div class="anomaly-caveats-list">${caveatBadges}</div>
            `;
            target.appendChild(row);
        });
    }

    setStatus(text) {}

    destroy() {
        if (this.handleDocumentClick) document.removeEventListener('click', this.handleDocumentClick);
        super.destroy();
    }

    toJSON() {
        return {
            ...super.toJSON(),
            selectedChannelId: this.selectedChannelId,
            anomalyThreshold: this.anomalyThreshold
        };
    }

    serializeForSummary() {
        const channelName = state.allChannels.find(ch => ch.channel_id === this.selectedChannelId)?.channel_name || this.selectedChannelId;
        if (!this.anomalies || this.anomalies.length === 0) {
            return `Widget: Viral Anomalies\nChannel: ${channelName}\nThreshold: ${this.anomalyThreshold}σ\nNo anomalies found.`;
        }

        const body = this.anomalies.map((anom, idx) => {
            const caveats = (anom.caveats || []).join(', ');
            return `${idx + 1}. "${anom.title}" (ID: ${anom.video_id}) | Z=${anom.z_score.toFixed(2)}σ | Confidence=${Math.round(anom.confidence * 100)}% | Caveats: ${caveats || 'None'}`;
        }).join('\n');

        return `Widget: Viral Anomalies\nChannel: ${channelName}\nThreshold: ${this.anomalyThreshold}σ\n\n${body}`;
    }
}


class DailyBriefsWidget extends BaseWidget {
    constructor(workspace, config = {}) {
        super(workspace, { ...config, type: 'daily-brief' });
        this.limit = Number(config.limit || 10);
        this.briefs = [];
    }

    afterMount() {
        this.element.innerHTML = `
            <button class="widget-remove-btn" type="button" title="Remove widget" style="width:24px; height:24px; border-radius:4px; font-size:11px;">
                <i class="fa-solid fa-xmark"></i>
            </button>
            <div class="card-header dashboard-card-header widget-card-header">
                <div class="card-header-left" style="width: 100%; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid fa-file-invoice" style="color:var(--primary-color); font-size:14px;"></i>
                        <span class="card-title" style="font-size:13px; font-weight:700;" data-i18n="widget_title_daily_brief">Daily Briefs</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <input type="date" class="control-select widget-brief-date" style="padding: 4px; font-size: 11px; border-radius: 4px; font-weight: 600; width: 120px;" />
                        <button class="btn-primary widget-generate-btn" type="button" style="padding: 4px 8px; font-size: 11px; font-weight: 600; display: flex; align-items: center; gap: 4px;">
                            <i class="fa-solid fa-magic"></i>
                            <span class="widget-btn-text">Generate</span>
                        </button>
                        <select class="control-select widget-brief-limit" style="padding: 4px; font-size: 11px; border-radius: 4px; font-weight: 600;">
                            <option value="5">5</option>
                            <option value="10">10</option>
                            <option value="20">20</option>
                            <option value="50">50</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="card-body" style="padding-top: 4px;">
                <div class="briefs-widget-list" style="min-height: 100px; display: flex; flex-direction: column; gap: 6px;">
                    <div class="widget-loading" style="text-align:center; color:var(--text-muted); font-size:11px; padding: 20px 0;">Loading briefs...</div>
                </div>
            </div>
        `;

        this.bindControls();
        const dateInput = this.element.querySelector('.widget-brief-date');
        if (dateInput) {
            dateInput.value = new Date().toISOString().split('T')[0];
        }
        this.element.querySelector('.widget-brief-limit').value = String(this.limit);
        this.load();
    }

    bindControls() {
        const limitSelect = this.element.querySelector('.widget-brief-limit');
        limitSelect.addEventListener('change', event => {
            this.limit = parseInt(event.target.value || 10, 10);
            this.load();
            this.workspace.save();
        });

        const generateBtn = this.element.querySelector('.widget-generate-btn');
        generateBtn.addEventListener('click', async () => {
            const dateInput = this.element.querySelector('.widget-brief-date');
            if (!dateInput || !dateInput.value) {
                const alertMsg = state.currentLang === "ua" ? "Будь ласка, оберіть дату." : "Please select a date.";
                window.alert(alertMsg);
                return;
            }

            const date = dateInput.value;
            const btnText = generateBtn.querySelector('.widget-btn-text');
            const oldText = btnText.innerText;
            btnText.innerText = state.currentLang === "ua" ? "Генерація..." : "Generating...";
            generateBtn.disabled = true;

            try {
                const res = await adminFetch(`/api/briefs/generate?date=${date}`, {
                    method: "POST"
                });
                const data = await res.json();
                if (!res.ok || data.error) {
                    window.alert(data.error || "Failed to generate brief.");
                    return;
                }

                const successMsg = state.currentLang === "ua" ? "Дайджест успішно згенеровано!" : "Brief generated successfully!";
                window.alert(successMsg);

                this.load();
                if (window.loadBriefs) window.loadBriefs();
            } catch (err) {
                console.error("Failed to generate brief from widget:", err);
                window.alert("Connection error during brief generation.");
            } finally {
                btnText.innerText = oldText;
                generateBtn.disabled = false;
            }
        });

        this.element.querySelector('.widget-remove-btn').addEventListener('click', () => {
            this.workspace.removeWidget(this.id);
        });
    }

    async load() {
        const listContainer = this.element.querySelector('.briefs-widget-list');
        if (!listContainer) return;

        try {
            const res = await adminFetchSilent(`/api/briefs?limit=${this.limit}`);
            const data = await res.json();

            if (!res.ok || data.error) {
                listContainer.innerHTML = `<div class="widget-loading" style="text-align:center; color:var(--danger-color); font-size:11px; padding: 20px 0;">Failed to load briefs.</div>`;
                return;
            }

            if (!data.registry_ready) {
                listContainer.innerHTML = `<div class="widget-loading" style="text-align:center; color:var(--text-muted); font-size:11px; padding: 20px 0;">Governance registry pending.</div>`;
                return;
            }

            const briefs = data.briefs || [];
            this.briefs = briefs;
            if (briefs.length === 0) {
                const emptyLabel = state.currentLang === "ua" ? "Дайджести ще не створювалися." : "No briefs generated yet.";
                listContainer.innerHTML = `<div class="widget-loading" style="text-align:center; color:var(--text-muted); font-size:11px; padding: 20px 0;">${emptyLabel}</div>`;
                return;
            }

            listContainer.innerHTML = briefs.map(b => {
                const dateStr = b.created_at ? b.created_at.substring(0, 19).replace('T', ' ') : 'no date';
                return `
                    <div class="operator-source-row" style="cursor: pointer; padding: 8px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-color); display: flex; justify-content: space-between; align-items: center;" onclick="viewBriefDetails(${b.id})">
                        <div style="display: flex; flex-direction: column; gap: 2px;">
                            <strong style="color: var(--text-color); font-size: 12px;">${escapeHtml(b.title || 'Untitled Brief')}</strong>
                            <span style="font-size: 10px; color: var(--text-muted);">${dateStr} | Status: ${escapeHtml(b.status)}</span>
                        </div>
                        <i class="fa-solid fa-chevron-right" style="color: var(--text-muted); font-size: 11px;"></i>
                    </div>
                `;
            }).join("");
        } catch (err) {
            console.error("Failed to load briefs in widget:", err);
            listContainer.innerHTML = `<div class="widget-loading" style="text-align:center; color:var(--danger-color); font-size:11px; padding: 20px 0;">Connection error.</div>`;
        }
    }

    toJSON() {
        return {
            ...super.toJSON(),
            limit: this.limit
        };
    }

    serializeForSummary() {
        if (!this.briefs || this.briefs.length === 0) {
            return `Widget: Daily Briefs\nLimit: ${this.limit}\nNo briefs found.`;
        }
        return `Widget: Daily Briefs\nLimit: ${this.limit}\nBriefs:\n` + this.briefs.map(b => `- ${b.title || 'Untitled'} (${b.created_at})`).join('\n');
    }
}


class MinifiedStatCardsWidget extends BaseWidget {
    constructor(workspace, config = {}) {
        super(workspace, { ...config, type: 'minified-stats' });
        this.stats = {};
    }

    afterMount() {
        this.element.innerHTML = `
            <button class="widget-remove-btn" type="button" title="Remove widget" style="width:24px; height:24px; border-radius:4px; font-size:11px;">
                <i class="fa-solid fa-xmark"></i>
            </button>
            <div class="card-header dashboard-card-header widget-card-header">
                <div class="card-header-left" style="width: 100%; display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid fa-table-cells-large" style="color:var(--accent-color); font-size:14px;"></i>
                        <span class="card-title" style="font-size:13px; font-weight:700;" data-i18n="widget_title_minified_stats">Mini Stats</span>
                    </div>
                </div>
            </div>
            <div class="card-body" style="padding-top: 4px;">
                <div class="mini-stats-grid">
                    <div class="mini-stat-card">
                        <div class="mini-stat-label"><i class="fa-solid fa-video"></i> Videos</div>
                        <div class="mini-stat-val class-mini-stat-videos">-</div>
                        <div class="mini-stat-delta neutral"><i class="fa-solid fa-minus"></i> Stable</div>
                    </div>
                    <div class="mini-stat-card">
                        <div class="mini-stat-label"><i class="fa-solid fa-fingerprint"></i> Entities</div>
                        <div class="mini-stat-val class-mini-stat-entities">-</div>
                        <div class="mini-stat-delta positive"><i class="fa-solid fa-arrow-trend-up"></i> +12%</div>
                    </div>
                    <div class="mini-stat-card">
                        <div class="mini-stat-label"><i class="fa-solid fa-quote-left"></i> Mentions</div>
                        <div class="mini-stat-val class-mini-stat-mentions">-</div>
                        <div class="mini-stat-delta positive"><i class="fa-solid fa-arrow-trend-up"></i> Dynamic</div>
                    </div>
                    <div class="mini-stat-card">
                        <div class="mini-stat-label"><i class="fa-solid fa-database"></i> PG Sync</div>
                        <div class="mini-stat-val class-mini-stat-sync">-</div>
                        <div class="mini-stat-delta neutral class-mini-stat-sync-lbl">Offline</div>
                    </div>
                </div>
            </div>
        `;
        this.element.querySelector('.widget-remove-btn').addEventListener('click', () => {
            this.workspace.removeWidget(this.id);
        });
        this.load();
    }

    async load() {
        try {
            const [resStats, resEntities] = await Promise.all([
                adminFetchSilent('/api/stats'),
                adminFetchSilent('/api/entities/stats')
            ]);
            
            const dataStats = resStats.ok ? await resStats.json() : null;
            const dataEntities = resEntities.ok ? await resEntities.json() : null;

            if (dataStats) {
                const sqlite = dataStats.sqlite || {};
                const pg = dataStats.postgres || {};
                const vidEl = this.element.querySelector('.class-mini-stat-videos');
                if (vidEl) vidEl.textContent = (sqlite.total_videos || 0).toLocaleString();
                const syncEl = this.element.querySelector('.class-mini-stat-sync');
                if (syncEl) syncEl.textContent = pg.connected ? 'Online' : 'Offline';
                const syncLbl = this.element.querySelector('.class-mini-stat-sync-lbl');
                if (syncLbl) {
                    if (pg.connected) {
                        syncLbl.className = 'mini-stat-delta positive class-mini-stat-sync-lbl';
                        syncLbl.innerHTML = '<i class="fa-solid fa-check"></i> Synced';
                    } else {
                        syncLbl.className = 'mini-stat-delta neutral class-mini-stat-sync-lbl';
                        syncLbl.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> Local only';
                    }
                }
            }

            if (dataEntities && dataEntities.entities) {
                const totalEntities = dataEntities.entities.length;
                let totalMentions = 0;
                dataEntities.entities.forEach(ent => {
                    totalMentions += (ent.total_mentions || 0);
                });

                const entEl = this.element.querySelector('.class-mini-stat-entities');
                if (entEl) entEl.textContent = totalEntities.toLocaleString();
                const mentEl = this.element.querySelector('.class-mini-stat-mentions');
                if (mentEl) mentEl.textContent = totalMentions.toLocaleString();
            }
        } catch (error) {
            console.error('Failed to load mini stats:', error);
        }
    }

    serializeForSummary() {
        return `Widget: Mini Stats\nStatus: Loaded`;
    }
}

class EntityTimelineTracksWidget extends BaseWidget {
    constructor(workspace, config = {}) {
        super(workspace, { ...config, type: 'entity-timeline' });
        this.timelineData = [];
    }

    afterMount() {
        this.element.innerHTML = `
            <button class="widget-remove-btn" type="button" title="Remove widget" style="width:24px; height:24px; border-radius:4px; font-size:11px;">
                <i class="fa-solid fa-xmark"></i>
            </button>
            <div class="card-header dashboard-card-header widget-card-header">
                <div class="card-header-left" style="width: 100%; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid fa-timeline" style="color:var(--accent-color); font-size:14px;"></i>
                        <span class="card-title" style="font-size:13px; font-weight:700;" data-i18n="widget_title_entity_timeline">Entity Timeline</span>
                    </div>
                </div>
            </div>
            <div class="card-body" style="padding-top: 4px; overflow-y: auto;">
                <div class="entity-timeline-container class-entity-timeline-container">
                    <div style="text-align:center; color:var(--text-muted); font-size:11px; padding: 20px 0;">Loading timeline swimlanes...</div>
                </div>
            </div>
        `;
        
        const headerLeft = this.element.querySelector('.card-header-left');
        const syncEl = this.renderDateSyncMenu();
        headerLeft.appendChild(syncEl);

        this.element.querySelector('.widget-remove-btn').addEventListener('click', () => {
            this.workspace.removeWidget(this.id);
        });
        
        this.load();
    }

    async load() {
        const container = this.element.querySelector('.class-entity-timeline-container');
        if (!container) return;

        const startDate = this.dateStart || document.getElementById('filter-start-date')?.value || '';
        const endDate = this.dateEnd || document.getElementById('filter-end-date')?.value || '';
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);

        try {
            const res = await adminFetchSilent(`/api/entities/timeline?${params.toString()}`);
            if (!res.ok) throw new Error('API failure');
            const data = await res.json();
            this.timelineData = data.timeline || [];
            this.renderTimeline();
        } catch (error) {
            console.error('Failed to load entity timeline:', error);
            container.innerHTML = `<div style="color:var(--danger-color); text-align:center; padding: 20px 0; font-size:11px;">Failed to load timeline.</div>`;
        }
    }

    renderTimeline() {
        const container = this.element.querySelector('.class-entity-timeline-container');
        if (!container) return;

        if (this.timelineData.length === 0) {
            container.innerHTML = `<div style="text-align:center; color:var(--text-muted); padding: 20px 0; font-size:11px;">No entity data for selected range.</div>`;
            return;
        }

        const entitiesMap = new Map();
        const datesSet = new Set();

        this.timelineData.forEach(item => {
            const key = item.name;
            datesSet.add(item.date);
            if (!entitiesMap.has(key)) {
                entitiesMap.set(key, {
                    name: item.name,
                    id: item.entity_id,
                    type: item.type || 'person',
                    history: {}
                });
            }
            entitiesMap.get(key).history[item.date] = item.count;
        });

        const datesList = Array.from(datesSet).sort();
        const displayDates = datesList.slice(-12);

        container.innerHTML = '';
        entitiesMap.forEach(ent => {
            const track = document.createElement('div');
            track.className = 'entity-timeline-track';
            
            const info = document.createElement('div');
            info.className = 'entity-track-name';
            info.innerHTML = `
                <span>${escapeHtml(ent.name)}</span>
                <span class="entity-track-type">${ent.type}</span>
            `;
            track.appendChild(info);

            const cellsContainer = document.createElement('div');
            cellsContainer.className = 'entity-track-cells';

            displayDates.forEach(date => {
                const count = ent.history[date] || 0;
                const cell = document.createElement('div');
                cell.className = 'entity-track-cell';
                cell.title = `${ent.name}: ${count} mentions on ${date}`;
                
                let level = 0;
                if (count > 5) level = 3;
                else if (count >= 3) level = 2;
                else if (count > 0) level = 1;
                cell.classList.add(`level-${level}`);
                
                cellsContainer.appendChild(cell);
            });
            track.appendChild(cellsContainer);
            container.appendChild(track);
        });
    }

    serializeForSummary() {
        return `Widget: Entity Timeline\nRecords: ${this.timelineData.length}`;
    }
}

class SystemStatusIndicatorWidget extends BaseWidget {
    constructor(workspace, config = {}) {
        super(workspace, { ...config, type: 'system-status' });
    }

    afterMount() {
        this.element.innerHTML = `
            <button class="widget-remove-btn" type="button" title="Remove widget" style="width:24px; height:24px; border-radius:4px; font-size:11px;">
                <i class="fa-solid fa-xmark"></i>
            </button>
            <div class="card-header dashboard-card-header widget-card-header">
                <div class="card-header-left" style="width: 100%; display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid fa-server" style="color:var(--accent-color); font-size:14px;"></i>
                        <span class="card-title" style="font-size:13px; font-weight:700;" data-i18n="widget_title_system_status">System Status</span>
                    </div>
                </div>
            </div>
            <div class="card-body" style="padding-top: 4px;">
                <div class="system-status-container">
                    <div class="status-item-row">
                        <div class="status-item-label"><i class="fa-solid fa-database"></i> SQLite Database</div>
                        <div class="status-indicator-wrap">
                            <span class="status-dot green class-status-db-dot"></span>
                            <span class="status-text class-status-db-text">Healthy</span>
                        </div>
                    </div>
                    <div class="status-item-row">
                        <div class="status-item-label"><i class="fa-solid fa-gears"></i> Scraper Daemon</div>
                        <div class="status-indicator-wrap">
                            <span class="status-dot green class-status-daemon-dot"></span>
                            <span class="status-text class-status-daemon-text">Idle</span>
                        </div>
                    </div>
                    <div class="status-item-row">
                        <div class="status-item-label"><i class="fa-solid fa-cloud-arrow-up"></i> API Quota Health</div>
                        <div class="status-indicator-wrap">
                            <span class="status-dot green class-status-quota-dot"></span>
                            <span class="status-text class-status-quota-text">Good</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        this.element.querySelector('.widget-remove-btn').addEventListener('click', () => {
            this.workspace.removeWidget(this.id);
        });
        this.load();
    }

    async load() {
        try {
            const res = await adminFetchSilent('/api/admin/health');
            if (!res.ok) throw new Error('API failure');
            const health = await res.json();
            
            const dbDot = this.element.querySelector('.class-status-db-dot');
            const dbText = this.element.querySelector('.class-status-db-text');
            if (health.database && health.database.exists) {
                if (dbDot) dbDot.className = 'status-dot green class-status-db-dot';
                if (dbText) dbText.textContent = `${health.database.size_mb || 0} MB`;
            } else {
                if (dbDot) dbDot.className = 'status-dot red class-status-db-dot';
                if (dbText) dbText.textContent = 'Missing';
            }

            const daemonDot = this.element.querySelector('.class-status-daemon-dot');
            const daemonText = this.element.querySelector('.class-status-daemon-text');
            if (health.background) {
                if (health.background.active_task) {
                    if (daemonDot) daemonDot.className = 'status-dot yellow class-status-daemon-dot';
                    if (daemonText) daemonText.textContent = 'Active';
                } else if (health.background.error) {
                    if (daemonDot) daemonDot.className = 'status-dot red class-status-daemon-dot';
                    if (daemonText) daemonText.textContent = 'Error';
                } else {
                    if (daemonDot) daemonDot.className = 'status-dot green class-status-daemon-dot';
                    if (daemonText) daemonText.textContent = 'Idle';
                }
            }

            const quotaDot = this.element.querySelector('.class-status-quota-dot');
            const quotaText = this.element.querySelector('.class-status-quota-text');
            if (health.providers && health.providers.rotation_initialized) {
                const providers = health.providers.providers || [];
                const activeCount = providers.filter(p => p.healthy).length;
                if (activeCount === 0 && providers.length > 0) {
                    if (quotaDot) quotaDot.className = 'status-dot red class-status-quota-dot';
                    if (quotaText) quotaText.textContent = 'Exhausted';
                } else if (activeCount < providers.length) {
                    if (quotaDot) quotaDot.className = 'status-dot yellow class-status-quota-dot';
                    if (quotaText) quotaText.textContent = `${activeCount}/${providers.length} OK`;
                } else {
                    if (quotaDot) quotaDot.className = 'status-dot green class-status-quota-dot';
                    if (quotaText) quotaText.textContent = 'Healthy';
                }
            } else {
                if (quotaDot) quotaDot.className = 'status-dot green class-status-quota-dot';
                if (quotaText) quotaText.textContent = 'Mock Mode';
            }
        } catch (error) {
            console.error('Failed to load system health status:', error);
            const dbDot = this.element.querySelector('.class-status-db-dot');
            const dbText = this.element.querySelector('.class-status-db-text');
            if (dbDot) dbDot.className = 'status-dot red class-status-db-dot';
            if (dbText) dbText.textContent = 'Offline';
        }
    }

    serializeForSummary() {
        return `Widget: System Status\nStatus: Checked`;
    }
}

class CostQuotaDashboardWidget extends BaseWidget {
    constructor(workspace, config = {}) {
        super(workspace, { ...config, type: 'cost-quota' });
        this.timeRange = config.timeRange || '24h';
        this.activeTab = 'llm'; // 'llm' or 'system'
        this.quotaChart = null;
        this.systemChart = null;
    }

    afterMount() {
        this.element.innerHTML = `
            <button class="widget-remove-btn" type="button" title="Remove widget" style="width:24px; height:24px; border-radius:4px; font-size:11px;">
                <i class="fa-solid fa-xmark"></i>
            </button>
            <div class="card-header dashboard-card-header widget-card-header" style="flex-wrap: wrap; gap: 8px;">
                <div class="card-header-left" style="display: flex; align-items: center; gap: 8px;">
                    <i class="fa-solid fa-coins" style="color:var(--accent-color); font-size:14px;"></i>
                    <span class="card-title" style="font-size:13px; font-weight:700;" data-i18n="widget_title_cost_quota">Cost & Quotas</span>
                </div>
                <div class="card-header-right" style="display: flex; align-items: center; gap: 8px; margin-left: auto;">
                    <span style="font-size: 11px; font-weight: 500;" data-i18n="lbl_time_range">Range</span>
                    <select class="control-select class-time-range-select" style="padding: 4px 8px; font-size: 11px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-color); color: var(--text-color); font-weight: 600;">
                        <option value="24h">24h</option>
                        <option value="7d">7d</option>
                        <option value="30d">30d</option>
                        <option value="all">All</option>
                    </select>
                </div>
            </div>
            <div class="card-body" style="padding: 8px 12px; display: flex; flex-direction: column; gap: 8px; height: calc(100% - 45px); min-height: 250px;">
                <!-- Tab headers -->
                <div class="widget-tabs" style="display: flex; border-bottom: 1px solid var(--border-color); padding-bottom: 4px; gap: 12px;">
                    <button type="button" class="widget-tab-btn class-tab-llm active" style="background: none; border: none; font-size: 11px; font-weight: 700; color: var(--accent-color); cursor: pointer; padding: 2px 4px; border-bottom: 2px solid var(--accent-color);" data-i18n="lbl_tab_llm_costs">LLM Costs</button>
                    <button type="button" class="widget-tab-btn class-tab-system" style="background: none; border: none; font-size: 11px; font-weight: 700; color: var(--text-muted); cursor: pointer; padding: 2px 4px;" data-i18n="lbl_tab_system_load">System Load</button>
                </div>

                <!-- Tab 1: LLM Content -->
                <div class="class-panel-llm" style="display: flex; flex-direction: column; gap: 8px; flex: 1;">
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px;">
                        <div style="background: var(--bg-secondary-color); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border-color);">
                            <div style="font-size: 10px; color: var(--text-muted);" data-i18n="lbl_total_cost">Total Cost</div>
                            <div class="class-total-cost" style="font-size: 14px; font-weight: 800; color: var(--accent-color);">$0.0000</div>
                        </div>
                        <div style="background: var(--bg-secondary-color); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border-color);">
                            <div style="font-size: 10px; color: var(--text-muted);" data-i18n="lbl_total_tokens">Total Tokens</div>
                            <div class="class-total-tokens" style="font-size: 14px; font-weight: 800; color: var(--text-color);">0</div>
                        </div>
                        <div style="background: var(--bg-secondary-color); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border-color);">
                            <div style="font-size: 10px; color: var(--text-muted);" data-i18n="lbl_total_runs">Total Queries</div>
                            <div class="class-total-runs" style="font-size: 14px; font-weight: 800; color: var(--text-color);">0</div>
                        </div>
                        <div style="background: var(--bg-secondary-color); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border-color);">
                            <div style="font-size: 10px; color: var(--text-muted);" data-i18n="lbl_success_rate">Success Rate</div>
                            <div class="class-success-rate" style="font-size: 14px; font-weight: 800; color: var(--green-color);">0%</div>
                        </div>
                    </div>
                    <div style="position: relative; flex: 1; min-height: 120px; width: 100%;">
                        <canvas class="class-quota-chart" style="width: 100%; height: 100%; max-height: 140px;"></canvas>
                    </div>
                </div>

                <!-- Tab 2: System Content -->
                <div class="class-panel-system" style="display: none; flex-direction: column; gap: 8px; flex: 1;">
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px;">
                        <div style="background: var(--bg-secondary-color); padding: 4px 8px; border-radius: 6px; border: 1px solid var(--border-color); text-align: center;">
                            <div style="font-size: 9px; color: var(--text-muted);">CPU</div>
                            <div class="class-system-cpu" style="font-size: 12px; font-weight: 800; color: var(--accent-color);">0%</div>
                        </div>
                        <div style="background: var(--bg-secondary-color); padding: 4px 8px; border-radius: 6px; border: 1px solid var(--border-color); text-align: center;">
                            <div style="font-size: 9px; color: var(--text-muted);">RAM</div>
                            <div class="class-system-ram" style="font-size: 12px; font-weight: 800; color: var(--text-color);">0 MB</div>
                        </div>
                        <div style="background: var(--bg-secondary-color); padding: 4px 8px; border-radius: 6px; border: 1px solid var(--border-color); text-align: center;">
                            <div style="font-size: 9px; color: var(--text-muted);">Sessions</div>
                            <div class="class-system-sessions" style="font-size: 12px; font-weight: 800; color: var(--text-color);">0</div>
                        </div>
                    </div>
                    <div style="position: relative; flex: 1; min-height: 120px; width: 100%;">
                        <canvas class="class-system-chart" style="width: 100%; height: 100%; max-height: 140px;"></canvas>
                    </div>
                </div>
            </div>
        `;

        // Bind events
        this.element.querySelector('.widget-remove-btn').addEventListener('click', () => {
            this.workspace.removeWidget(this.id);
        });

        const rangeSelect = this.element.querySelector('.class-time-range-select');
        rangeSelect.value = this.timeRange;
        rangeSelect.addEventListener('change', () => {
            this.timeRange = rangeSelect.value;
            this.load();
            this.workspace.save();
        });

        // Tab Switching
        const btnLlm = this.element.querySelector('.class-tab-llm');
        const btnSys = this.element.querySelector('.class-tab-system');
        const panelLlm = this.element.querySelector('.class-panel-llm');
        const panelSys = this.element.querySelector('.class-panel-system');

        btnLlm.addEventListener('click', () => {
            this.activeTab = 'llm';
            btnLlm.style.color = 'var(--accent-color)';
            btnLlm.style.borderBottom = '2px solid var(--accent-color)';
            btnSys.style.color = 'var(--text-muted)';
            btnSys.style.borderBottom = 'none';
            panelLlm.style.display = 'flex';
            panelSys.style.display = 'none';
            this.load();
        });

        btnSys.addEventListener('click', () => {
            this.activeTab = 'system';
            btnSys.style.color = 'var(--accent-color)';
            btnSys.style.borderBottom = '2px solid var(--accent-color)';
            btnLlm.style.color = 'var(--text-muted)';
            btnLlm.style.borderBottom = 'none';
            panelSys.style.display = 'flex';
            panelLlm.style.display = 'none';
            this.load();
        });

        // Localize initial titles/attributes
        if (window.localizeHtml) {
            window.localizeHtml(this.element);
        }

        this.load();
    }

    async load() {
        if (this.activeTab === 'llm') {
            await this.loadLlmMetrics();
        } else {
            await this.loadSystemMetrics();
        }
    }

    async loadLlmMetrics() {
        try {
            const res = await adminFetchSilent(`/api/admin/quota-metrics?time_range=${this.timeRange}`);
            if (!res.ok) throw new Error('API failure');
            const data = await res.json();
            
            const summary = data.summary || {};
            const breakdown = data.model_breakdown || [];

            // Update DOM text
            const totalCost = summary.total_cost !== undefined ? Number(summary.total_cost) : 0;
            const totalTokens = (summary.total_input_tokens || 0) + (summary.total_output_tokens || 0);
            const totalRuns = summary.total_runs || 0;
            const successCount = summary.success_count || 0;
            const errorCount = summary.error_count || 0;
            
            let successRate = 100;
            if (totalRuns > 0) {
                successRate = Math.round((successCount / totalRuns) * 100);
            }

            const costEl = this.element.querySelector('.class-total-cost');
            const tokensEl = this.element.querySelector('.class-total-tokens');
            const runsEl = this.element.querySelector('.class-total-runs');
            const successEl = this.element.querySelector('.class-success-rate');

            if (costEl) costEl.textContent = `$${totalCost.toFixed(4)}`;
            if (tokensEl) tokensEl.textContent = totalTokens.toLocaleString();
            if (runsEl) runsEl.textContent = totalRuns.toLocaleString();
            if (successEl) {
                successEl.textContent = `${successRate}%`;
                if (errorCount > 0) {
                    successEl.style.color = 'var(--red-color)';
                } else {
                    successEl.style.color = 'var(--green-color)';
                }
            }

            // Draw Chart.js horizontal bar chart
            const canvas = this.element.querySelector('.class-quota-chart');
            if (!canvas) return;

            if (this.quotaChart) {
                this.quotaChart.destroy();
                this.quotaChart = null;
            }

            // Prepare chart data
            const labels = breakdown.map(item => item.model_id.replace(/^openrouter\/(?:free\/)?/, ''));
            const costs = breakdown.map(item => item.cost);

            const isDark = ["dark-black", "dark-blue"].includes(state.currentTheme);
            const gridColor = isDark ? "#334155" : "#e2e8f0";
            const labelColor = isDark ? "#94a3b8" : "#5f6368";

            const ctx = canvas.getContext('2d');
            this.quotaChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: state.currentLang === 'ua' ? 'Вартість ($)' : 'Cost ($)',
                        data: costs,
                        backgroundColor: '#38bdf8',
                        borderRadius: 4
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    const item = breakdown[context.dataIndex];
                                    return [
                                        `Cost: $${item.cost.toFixed(4)}`,
                                        `Runs: ${item.run_count}`,
                                        `In/Out Tokens: ${item.input_tokens}/${item.output_tokens}`
                                    ];
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: gridColor },
                            ticks: { color: labelColor, font: { size: 9 } }
                        },
                        y: {
                            grid: { display: false },
                            ticks: { color: labelColor, font: { size: 9 }, autoSkip: false }
                        }
                    }
                }
            });

        } catch (error) {
            console.error('Failed to load LLM quota metrics:', error);
        }
    }

    async loadSystemMetrics() {
        try {
            const res = await adminFetchSilent(`/api/admin/system-metrics?limit=30`);
            if (!res.ok) throw new Error('API failure');
            const data = await res.json();
            const metrics = data.metrics || [];

            // Update stats from the last sample
            if (metrics.length > 0) {
                const last = metrics[metrics.length - 1];
                const cpuEl = this.element.querySelector('.class-system-cpu');
                const ramEl = this.element.querySelector('.class-system-ram');
                const sesEl = this.element.querySelector('.class-system-sessions');

                if (cpuEl) cpuEl.textContent = `${last.cpu_percent.toFixed(1)}%`;
                if (ramEl) ramEl.textContent = `${Math.round(last.ram_mb_used)} MB`;
                if (sesEl) sesEl.textContent = last.http_sessions_active || 0;
            }

            // Draw line chart for CPU and RAM
            const canvas = this.element.querySelector('.class-system-chart');
            if (!canvas) return;

            if (this.systemChart) {
                this.systemChart.destroy();
                this.systemChart = null;
            }

            // Labels are timestamps formatted (e.g. HH:MM:SS)
            const labels = metrics.map(m => {
                const parts = m.timestamp.split('T');
                if (parts.length > 1) {
                    return parts[1].substring(0, 8);
                }
                return m.timestamp;
            });
            const cpuData = metrics.map(m => m.cpu_percent);
            const ramData = metrics.map(m => m.ram_mb_used);

            const isDark = ["dark-black", "dark-blue"].includes(state.currentTheme);
            const gridColor = isDark ? "#334155" : "#e2e8f0";
            const labelColor = isDark ? "#94a3b8" : "#5f6368";

            const ctx = canvas.getContext('2d');
            this.systemChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'CPU (%)',
                            data: cpuData,
                            borderColor: '#38bdf8',
                            backgroundColor: 'transparent',
                            borderWidth: 1.5,
                            pointRadius: 0,
                            tension: 0.2,
                            yAxisID: 'y'
                        },
                        {
                            label: 'RAM (MB)',
                            data: ramData,
                            borderColor: '#a855f7',
                            backgroundColor: 'transparent',
                            borderWidth: 1.5,
                            pointRadius: 0,
                            tension: 0.2,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: { boxWidth: 8, font: { size: 9 }, color: labelColor }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: gridColor },
                            ticks: { display: false } // Hide labels to keep clean
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            grid: { color: gridColor },
                            ticks: { color: '#38bdf8', font: { size: 9 } }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            ticks: { color: '#a855f7', font: { size: 9 } }
                        }
                    }
                }
            });

        } catch (error) {
            console.error('Failed to load system metrics:', error);
        }
    }

    toJSON() {
        return {
            id: this.id,
            type: this.type,
            width: this.width,
            height: this.height,
            collapsed: this.collapsed,
            timeRange: this.timeRange
        };
    }

    destroy() {
        if (this.quotaChart) {
            this.quotaChart.destroy();
            this.quotaChart = null;
        }
        if (this.systemChart) {
            this.systemChart.destroy();
            this.systemChart = null;
        }
        super.destroy();
    }

    serializeForSummary() {
        return `Widget: Cost & Quotas\nRange: ${this.timeRange}`;
    }
}

export class DashboardWorkspace {
    constructor(root) {
        this.root = root;
        this.widgets = new Map();
        this.palette = document.querySelector('.widget-palette');
        this.isRestoring = false;
    }

    async init() {
        if (!this.root) return;
        this.bindPalette();
        this.bindDropzone();
        this.bindLayoutsToolbar();
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

    async bindLayoutsToolbar() {
        const selector = document.getElementById('layout-preset-selector');
        const saveBtn = document.getElementById('btn-save-layout');
        const newBtn = document.getElementById('btn-new-layout');
        const deleteBtn = document.getElementById('btn-delete-layout');
        
        if (!selector) return;

        await this.refreshLayoutsDropdown();

        selector.addEventListener('change', async () => {
            const layoutId = selector.value;
            if (!layoutId) return;
            try {
                const res = await adminFetch(`/api/widgets/layouts/activate/${layoutId}`, { method: 'POST' });
                if (res.ok) {
                    this.clearWorkspace();
                    await this.restore();
                }
            } catch (error) {
                console.error('Failed to activate layout:', error);
            }
        });

        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.save();
                window.alert(state.currentLang === 'ua' ? 'Макет збережено!' : 'Layout saved!');
            });
        }

        if (newBtn) {
            newBtn.addEventListener('click', async () => {
                const name = window.prompt(state.currentLang === 'ua' ? 'Введіть назву нового макету:' : 'Enter new layout name:');
                if (!name || !name.trim()) return;
                try {
                    const res = await adminFetch('/api/widgets/layouts', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: name.trim() })
                    });
                    const data = await res.json();
                    if (!res.ok) {
                        window.alert(data.error || 'Failed to create layout');
                        return;
                    }
                    await this.refreshLayoutsDropdown(data.layout.id);
                    this.clearWorkspace();
                    this.save();
                } catch (error) {
                    console.error('Failed to create layout:', error);
                }
            });
        }

        if (deleteBtn) {
            deleteBtn.addEventListener('click', async () => {
                const layoutId = selector.value;
                if (!layoutId) return;
                const confirmMsg = state.currentLang === 'ua' ? 'Ви впевнені, що хочете видалити цей макет?' : 'Are you sure you want to delete this layout preset?';
                if (!window.confirm(confirmMsg)) return;
                try {
                    const res = await adminFetch(`/api/widgets/layouts/${layoutId}`, { method: 'DELETE' });
                    const data = await res.json();
                    if (!res.ok) {
                        window.alert(data.error || 'Failed to delete layout');
                        return;
                    }
                    await this.refreshLayoutsDropdown();
                    this.clearWorkspace();
                    await this.restore();
                } catch (error) {
                    console.error('Failed to delete layout:', error);
                }
            });
        }
    }

    async refreshLayoutsDropdown(selectId = null) {
        const selector = document.getElementById('layout-preset-selector');
        if (!selector) return;
        try {
            const res = await adminFetchSilent('/api/widgets/layouts');
            if (!res.ok) return;
            const data = await res.json();
            selector.innerHTML = '';
            let activeId = null;
            (data.layouts || []).forEach(layout => {
                const opt = document.createElement('option');
                opt.value = layout.id;
                opt.textContent = layout.name;
                if (layout.is_default) {
                    opt.selected = true;
                    activeId = layout.id;
                }
                selector.appendChild(opt);
            });
            if (selectId) {
                selector.value = selectId;
                await adminFetchSilent(`/api/widgets/layouts/activate/${selectId}`, { method: 'POST' });
            }
        } catch (error) {
            console.error('Failed to fetch layouts:', error);
        }
    }

    clearWorkspace() {
        this.widgets.forEach(w => w.destroy());
        this.widgets.clear();
        this.root.innerHTML = '';
    }

    addWidget(type, config = {}, options = {}) {
        let widget = null;
        if (type === 'channel-analytics') {
            widget = new ChannelAnalyticsWidget(this, config);
        } else if (type === 'anomaly-alerts') {
            widget = new AnomalyAlertsWidget(this, config);
        } else if (type === 'daily-brief') {
            widget = new DailyBriefsWidget(this, config);
        } else if (type === 'minified-stats') {
            widget = new MinifiedStatCardsWidget(this, config);
        } else if (type === 'entity-timeline') {
            widget = new EntityTimelineTracksWidget(this, config);
        } else if (type === 'system-status') {
            widget = new SystemStatusIndicatorWidget(this, config);
        } else if (type === 'cost-quota') {
            widget = new CostQuotaDashboardWidget(this, config);
        } else {
            return null;
        }
        this.widgets.set(widget.id, widget);
        widget.mount(this.root);
        if (!options.skipSave && !this.isRestoring) {
            this.save();
        }
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
            await adminFetchSilent(WIDGETS_STATE_ENDPOINT, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ widgets: data })
            });
        } catch (error) {
            // LocalStorage remains fallback
        }
    }

    async loadRemote() {
        try {
            const response = await adminFetchSilent(WIDGETS_STATE_ENDPOINT);
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
        this.isRestoring = true;
        saved
            .filter(item => item && (
                item.type === 'channel-analytics' || 
                item.type === 'anomaly-alerts' || 
                item.type === 'daily-brief' ||
                item.type === 'minified-stats' ||
                item.type === 'entity-timeline' ||
                item.type === 'system-status' ||
                item.type === 'cost-quota'
            ))
            .forEach(item => this.addWidget(item.type, item, { skipSave: true }));
        this.isRestoring = false;
    }
}

export function initDashboardWorkspace() {
    const workspace = new DashboardWorkspace(document.getElementById('dashboard-workspace'));
    void workspace.init();
    window.dashboardWorkspace = workspace;
    return workspace;
}
