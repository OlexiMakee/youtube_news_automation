/**
 * Entity Co-occurrence Graph View — Phase 3 Tri-View
 *
 * Renders a D3 force-directed graph where:
 *   nodes = entities (size ∝ mentions, color by type)
 *   edges = co-occurrence in the same video (thickness ∝ shared_videos)
 *
 * Data is fetched from /api/entities/graph with the current dashboard filters.
 */

import { state } from './state.js';

const TYPE_COLORS = {
    person:       '#38bdf8',
    organization: '#f59e0b',
    location:     '#34d399',
};

const TYPE_LABELS = {
    person:       { ua: 'Персона',       en: 'Person' },
    organization: { ua: 'Організація',   en: 'Organization' },
    location:     { ua: 'Локація',       en: 'Location' },
};

export async function renderGraphView(rootNode, filters = {}) {
    const root = rootNode || document.getElementById('graph-view-root');
    if (!root) return;

    if (root.cleanup) { root.cleanup(); root.cleanup = null; }

    root.innerHTML = '<div class="graph-loading">Loading entity graph…</div>';

    if (typeof d3 === 'undefined') {
        root.innerHTML = '<div class="graph-empty">D3.js is not loaded.</div>';
        return;
    }

    const params = new URLSearchParams({ limit: '30', min_edge: '1' });
    if (filters.start_date) params.set('start_date', filters.start_date);
    if (filters.end_date)   params.set('end_date',   filters.end_date);
    if (filters.channels && filters.channels.length) params.set('channels', filters.channels.join(','));

    let nodes, edges;
    try {
        const resp = await fetch(`/api/entities/graph?${params}`);
        const json = await resp.json();
        if (!json.ok) throw new Error(json.error || 'Server error');
        nodes = json.nodes;
        edges = json.edges;
    } catch (err) {
        root.innerHTML = `<div class="graph-empty" style="color:var(--danger-color);">Failed to load: ${err.message}</div>`;
        return;
    }

    if (!nodes.length) {
        const lang = state.currentLang === 'ua' ? 'ua' : 'en';
        const msg = lang === 'ua'
            ? 'Немає даних про сутності. Спочатку запустіть вилучення сутностей.'
            : 'No entity data available. Run entity extraction first.';
        root.innerHTML = `<div class="graph-empty">${msg}</div>`;
        return;
    }

    root.innerHTML = '';

    const width  = root.clientWidth  || 800;
    const height = root.clientHeight || 360;

    const mentionMax = d3.max(nodes, d => d.mentions) || 1;
    const nodeRadius = d3.scaleSqrt().domain([0, mentionMax]).range([5, 28]);

    const edgeMax = edges.length ? (d3.max(edges, d => d.shared_videos) || 1) : 1;
    const edgeWidth = d3.scaleLinear().domain([1, edgeMax]).range([1, 5]).clamp(true);

    const nodeById = new Map(nodes.map(n => [n.id, n]));
    const linkData = edges
        .filter(e => nodeById.has(e.source_id) && nodeById.has(e.target_id))
        .map(e => ({ source: e.source_id, target: e.target_id, weight: e.shared_videos }));

    // ── Simulation ──────────────────────────────────────────
    const simulation = d3.forceSimulation(nodes)
        .force('link',      d3.forceLink(linkData).id(d => d.id)
                              .distance(d => Math.max(60, 120 - d.weight * 5)))
        .force('charge',    d3.forceManyBody().strength(-200))
        .force('center',    d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => nodeRadius(d.mentions) + 8));

    // ── SVG ──────────────────────────────────────────────────
    const svg = d3.select(root).append('svg')
        .attr('width',  width)
        .attr('height', height)
        .style('background', 'transparent');

    // Zoomable group
    const g = svg.append('g');
    svg.call(
        d3.zoom().scaleExtent([0.25, 5]).on('zoom', ev => g.attr('transform', ev.transform))
    );

    // ── Legend ───────────────────────────────────────────────
    const lang = state.currentLang === 'ua' ? 'ua' : 'en';
    const presentTypes = [...new Set(nodes.map(n => n.type))];
    const lgd = svg.append('g').attr('transform', 'translate(10, 10)');
    presentTypes.forEach((type, i) => {
        lgd.append('circle')
            .attr('cx', 7).attr('cy', i * 18 + 7).attr('r', 5)
            .style('fill', TYPE_COLORS[type] || '#888');
        lgd.append('text')
            .attr('x', 16).attr('y', i * 18 + 11)
            .style('font-size', '10px').style('fill', 'var(--text-muted)')
            .text((TYPE_LABELS[type] || {})[lang] || type);
    });

    // ── Tooltip ──────────────────────────────────────────────
    const tip = d3.select('body').append('div')
        .attr('class', 'd3-tooltip')
        .style('display', 'none')
        .style('position', 'absolute')
        .style('pointer-events', 'none');

    // ── Links ────────────────────────────────────────────────
    const link = g.append('g').selectAll('line')
        .data(linkData).join('line')
        .style('stroke', 'var(--border-color)')
        .style('stroke-opacity', 0.45)
        .style('stroke-width', d => edgeWidth(d.weight));

    // ── Nodes ────────────────────────────────────────────────
    const node = g.append('g').selectAll('circle')
        .data(nodes).join('circle')
        .attr('r', d => nodeRadius(d.mentions))
        .style('fill', d => TYPE_COLORS[d.type] || '#888')
        .style('opacity', 0.88)
        .style('stroke', 'var(--bg-color)')
        .style('stroke-width', 2)
        .style('cursor', 'pointer')
        .call(
            d3.drag()
                .on('start', (ev, d) => { if (!ev.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
                .on('drag',  (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
                .on('end',   (ev, d) => { if (!ev.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
        )
        .on('mouseover', (ev, d) => {
            const typeLbl = (TYPE_LABELS[d.type] || {})[lang] || d.type;
            const vidsLbl = lang === 'ua' ? 'Відео' : 'Videos';
            const menLbl  = lang === 'ua' ? 'Згадок' : 'Mentions';
            tip.style('display', 'block').html(`
                <div class="d3-tip-body">
                    <div class="d3-tip-title">${d.name}</div>
                    <div class="d3-tip-meta">
                        <span class="d3-tip-metric">${typeLbl}</span>
                        <span class="d3-tip-metric">${menLbl}: <strong>${d.mentions.toLocaleString()}</strong></span>
                        <span class="d3-tip-metric">${vidsLbl}: <strong>${d.video_count}</strong></span>
                    </div>
                </div>
            `).style('left', (ev.pageX + 12) + 'px').style('top', (ev.pageY - 20) + 'px');
        })
        .on('mousemove', ev => tip.style('left', (ev.pageX + 12) + 'px').style('top', (ev.pageY - 20) + 'px'))
        .on('mouseout',  ()  => tip.style('display', 'none'));

    // ── Labels (only for prominent nodes) ───────────────────
    const labelThreshold = mentionMax * 0.12;
    const label = g.append('g').selectAll('text')
        .data(nodes.filter(d => d.mentions >= labelThreshold))
        .join('text')
        .text(d => d.name.length > 20 ? d.name.slice(0, 18) + '…' : d.name)
        .style('font-size', '10px')
        .style('fill', 'var(--text-color)')
        .style('pointer-events', 'none')
        .attr('dy', d => -nodeRadius(d.mentions) - 4)
        .attr('text-anchor', 'middle');

    // ── Tick ─────────────────────────────────────────────────
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        node.attr('cx', d => d.x).attr('cy', d => d.y);
        label.attr('x', d => d.x).attr('y', d => d.y);
    });

    // ── Cleanup hook ─────────────────────────────────────────
    root.cleanup = () => {
        simulation.stop();
        tip.remove();
    };
}
