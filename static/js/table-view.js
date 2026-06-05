import { state } from './state.js';
import { formatNumber, escapeHtml } from './utils.js';

export function renderTableView(data, chartDef, rootNode) {
    const root = rootNode || document.getElementById("table-view-root");
    if (!root) return;

    if (!data || data.length === 0) {
        root.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 12px;">No data available for table view.</div>';
        return;
    }

    let metricKey = 'views';
    if (chartDef) {
        if (chartDef.id.includes('liked')) metricKey = 'likes';
        else if (chartDef.id.includes('commented')) metricKey = 'comments';
        else if (chartDef.id.includes('viewed')) metricKey = 'views';
        else metricKey = 'value'; // fallback for promo
    }

    let tableHtml = `
        <table class="workspace-data-table">
            <thead>
                <tr>
                    <th style="width: 60px;">Thumb</th>
                    <th>Title</th>
                    <th>Channel</th>
                    <th>Published Date</th>
                    <th style="text-align: right;">Metric (${metricKey})</th>
                </tr>
            </thead>
            <tbody>
    `;

    data.forEach(item => {
        let value = item.value !== undefined ? item.value : (item[metricKey] || 0);
        let title = item.title || item.label || 'N/A';
        let channel = item.channel || item.channel_name || 'Unknown';
        let thumbUrl = item.thumb_url || item.thumbnail_url || '';
        let dateStr = item.date || item.published_at || '';
        
        let thumbImg = thumbUrl ? `<img src="${escapeHtml(thumbUrl)}" class="table-thumbnail" loading="lazy" />` : '<div class="table-thumbnail" style="background: var(--bg-hover);"></div>';

        tableHtml += `
            <tr>
                <td>${thumbImg}</td>
                <td class="truncate" title="${escapeHtml(title)}">${escapeHtml(title)}</td>
                <td>${escapeHtml(channel)}</td>
                <td>${escapeHtml(dateStr)}</td>
                <td style="text-align: right; font-weight: 600;">${formatNumber(value)}</td>
            </tr>
        `;
    });

    tableHtml += `
            </tbody>
        </table>
    `;

    root.innerHTML = tableHtml;
}
