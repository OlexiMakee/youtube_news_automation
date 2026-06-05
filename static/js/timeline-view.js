import { state } from './state.js';
import { formatNumber, escapeHtml } from './utils.js';

export function renderTimelineView(data, chartDef, rootNode) {
    const root = rootNode || document.getElementById("timeline-view-root");
    if (!root) return;

    if (!data || data.length === 0) {
        root.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 12px;">No data available for timeline view.</div>';
        return;
    }
    
    // Clear previous timeline
    root.innerHTML = '';
    
    if (typeof d3 === 'undefined') {
        root.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--danger-color); font-size: 12px;">D3.js is not loaded.</div>';
        return;
    }

    let metricKey = 'views';
    if (chartDef) {
        if (chartDef.id.includes('liked')) metricKey = 'likes';
        else if (chartDef.id.includes('commented')) metricKey = 'comments';
        else if (chartDef.id.includes('viewed')) metricKey = 'views';
        else metricKey = 'value'; 
    }

    // Filter out items without valid dates
    const validData = data.map(d => {
        let val = d.value !== undefined ? d.value : (d[metricKey] || 0);
        let dateStr = d.date || d.published_at || d.label;
        let dateObj = new Date(dateStr);
        return {
            ...d,
            metricValue: val,
            dateObj: isNaN(dateObj.getTime()) ? null : dateObj
        };
    }).filter(d => d.dateObj !== null && d.metricValue > 0);

    if (validData.length === 0) {
        root.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 12px;">No valid dates found in data.</div>';
        return;
    }

    const width = root.clientWidth || 800;
    const height = root.clientHeight || 280;
    const margin = { top: 20, right: 30, bottom: 30, left: 50 };

    const svg = d3.select(root)
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    const x = d3.scaleTime()
        .domain(d3.extent(validData, d => d.dateObj))
        .range([margin.left, width - margin.right]);

    const y = d3.scaleLinear()
        .domain([0, d3.max(validData, d => d.metricValue)])
        .nice()
        .range([height - margin.bottom, margin.top]);

    const sizeScale = d3.scaleSqrt()
        .domain([0, d3.max(validData, d => d.metricValue)])
        .range([4, 20]);

    // Add X axis
    svg.append("g")
        .attr("transform", `translate(0,${height - margin.bottom})`)
        .call(d3.axisBottom(x).ticks(5))
        .attr("font-size", "10px")
        .attr("color", "var(--text-muted)");

    // Add Y axis
    svg.append("g")
        .attr("transform", `translate(${margin.left},0)`)
        .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format("~s")))
        .attr("font-size", "10px")
        .attr("color", "var(--text-muted)");

    // Draw grid lines
    svg.append("g")
        .attr("class", "grid")
        .attr("transform", `translate(${margin.left},0)`)
        .call(d3.axisLeft(y).ticks(5).tickSize(-width + margin.left + margin.right).tickFormat(""))
        .attr("stroke-dasharray", "2,2")
        .attr("stroke-opacity", 0.1)
        .attr("color", "var(--text-muted)");

    // Tooltip
    const tooltip = d3.select("body").append("div")
        .attr("class", "d3-tooltip")
        .style("opacity", 0)
        .style("position", "absolute")
        .style("background", "var(--card-bg)")
        .style("border", "1px solid var(--border-color)")
        .style("padding", "8px")
        .style("border-radius", "4px")
        .style("pointer-events", "none")
        .style("font-size", "11px")
        .style("color", "var(--text-color)")
        .style("box-shadow", "0 4px 6px rgba(0,0,0,0.1)")
        .style("z-index", "9999");

    // Draw circles
    svg.append("g")
        .selectAll("circle")
        .data(validData)
        .join("circle")
        .attr("cx", d => x(d.dateObj))
        .attr("cy", d => y(d.metricValue))
        .attr("r", 0)
        .attr("fill", "var(--accent-color)")
        .attr("opacity", 0.7)
        .attr("stroke", "var(--bg-color)")
        .attr("stroke-width", 1)
        .on("mouseover", function(event, d) {
            d3.select(this).attr("opacity", 1).attr("stroke", "white").attr("stroke-width", 2);
            let title = d.title || d.label || '';
            let valStr = formatNumber(d.metricValue);
            tooltip.transition().duration(200).style("opacity", 1);
            tooltip.html(`
                <div style="font-weight:700; margin-bottom:4px;">${escapeHtml(title)}</div>
                <div style="color:var(--text-muted);">${d.dateObj.toLocaleDateString()}</div>
                <div>${metricKey}: <strong>${valStr}</strong></div>
            `)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 28) + "px");
        })
        .on("mouseout", function() {
            d3.select(this).attr("opacity", 0.7).attr("stroke", "var(--bg-color)").attr("stroke-width", 1);
            tooltip.transition().duration(500).style("opacity", 0);
        })
        .transition()
        .duration(800)
        .attr("r", d => sizeScale(d.metricValue));

    // Cleanup tooltip when view is destroyed or toggled
    const oldCleanup = root.cleanup;
    if (oldCleanup) oldCleanup();
    root.cleanup = () => {
        tooltip.remove();
    };
}
