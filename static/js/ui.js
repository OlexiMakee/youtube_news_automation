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
import { adminFetch, adminFetchSilent, openAdminUrl } from './auth.js';

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

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

const ROLE_LEVELS = {
    reader: 1,
    analyst: 2,
    admin: 3,
    master_admin: 3
};

function normalizeUiRole(role, authStatus = state.authStatus) {
    const clean = String(role || authStatus?.role || state.userRole || "reader").toLowerCase();
    if (authStatus?.admin || clean === "admin" || clean === "master_admin") return "admin";
    if (clean === "analyst") return "analyst";
    return "reader";
}

export function applyRoleVisibility() {
    const role = normalizeUiRole(state.userRole);
    const currentLevel = ROLE_LEVELS[role] || ROLE_LEVELS.reader;
    state.userRole = role;
    document.body?.setAttribute("data-user-role", role);

    document.querySelectorAll("[data-role-min]").forEach(element => {
        const required = String(element.getAttribute("data-role-min") || "reader").toLowerCase();
        const requiredLevel = ROLE_LEVELS[required] || ROLE_LEVELS.reader;
        element.hidden = currentLevel < requiredLevel;
        if (element.hidden) {
            if (!element.dataset.originalDisplay && element.style.display !== 'none') {
                element.dataset.originalDisplay = element.style.display;
            }
            element.style.setProperty('display', 'none', 'important');
        } else {
            if (element.dataset.originalDisplay !== undefined) {
                element.style.display = element.dataset.originalDisplay;
            } else {
                element.style.removeProperty('display');
            }
        }
    });

    const terminalTab = document.getElementById("menu-item-terminal");
    if (terminalTab?.hidden && state.currentSection === "terminal-tab") {
        switchSection("analytics-tab", document.getElementById("menu-item-analytics")?.querySelector("a"));
    }

    const adminChatTab = document.getElementById("chat-tab-admin");
    if (adminChatTab?.hidden && state.agentRole === "admin") {
        switchAgentRole("user");
    }
}

// PROGRESSIVE ENTITLEMENTS UI GATING
export function applyEntitlementsUI() {
    const entitlements = state.entitlements || {};
    
    // Gate the Administration tab (requires operator_runtime)
    const terminalTab = document.getElementById("menu-item-terminal");
    if (terminalTab) {
        terminalTab.style.display = entitlements.operator_runtime ? "block" : "none";
    }

    // Gate the widgets in the sidebar palette
    const widgetsPalette = document.querySelector(".widget-palette");
    if (widgetsPalette) {
        const channelWidgetBtn = widgetsPalette.querySelector('.widget-template[data-widget-type="channel-analytics"]');
        if (channelWidgetBtn) {
            channelWidgetBtn.style.display = entitlements.ready_workspace ? "flex" : "none";
        }
        const anomalyWidgetBtn = widgetsPalette.querySelector('.widget-template[data-widget-type="anomaly-alerts"]');
        if (anomalyWidgetBtn) {
            anomalyWidgetBtn.style.display = entitlements.dense_workspace ? "flex" : "none";
        }
        const briefWidgetBtn = widgetsPalette.querySelector('.widget-template[data-widget-type="daily-brief"]');
        if (briefWidgetBtn) {
            briefWidgetBtn.style.display = entitlements.ready_workspace ? "flex" : "none";
        }
    }

    applyRoleVisibility();
}

// SECTION TOGGLER (For real tab switching)
export function switchSection(tabId, element) {
    state.currentSection = tabId;
    document.querySelectorAll(".sidebar-menu-item, .top-section-tab").forEach(item => {
        item.classList.remove("active");
    });

    const matchingTabs = document.querySelectorAll(`.top-section-tab[data-tab="${tabId}"]`);
    if (matchingTabs.length) {
        matchingTabs.forEach(tab => tab.classList.add("active"));
    } else if (element) {
        const tab = element.closest(".sidebar-menu-item, .top-section-tab") || element;
        tab.classList.add("active");
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
    
    // Toggle proposals inbox visibility based on section (Terminal/Administration only)
    const sidebarProposals = document.querySelector(".sidebar-proposals");
    if (sidebarProposals) {
        if (tabId === "terminal-tab") {
            sidebarProposals.style.display = "";
        } else {
            sidebarProposals.style.display = "none";
        }
    }

    // Show active tab content
    if (tabId === "analytics-tab") {
        document.getElementById("section-data-analytics").classList.add("active");
    } else if (tabId === "terminal-tab") {
        document.getElementById("section-terminal").classList.add("active");
        initOperatorRuntimePanel();
        initTerminal();
        window.loadBriefs?.();
        window.loadBriefSources?.();
    }
    
    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        setSidebarCollapsed(true);
    }
}

function setSidebarCollapsed(isCollapsed) {
    document.body.classList.toggle("sidebar-collapsed", isCollapsed);
    localStorage.setItem("sidebar_collapsed", isCollapsed ? "1" : "0");
    document.querySelectorAll(".sidebar-brand-toggle, .top-bar-menu-toggle").forEach(btn => {
        btn.setAttribute("aria-expanded", isCollapsed ? "false" : "true");
        btn.title = isCollapsed ? "Розгорнути меню" : "Згорнути меню";
    });
}

export function toggleSidebar(forceCollapsed = null) {
    const isCollapsed = forceCollapsed === null
        ? !document.body.classList.contains("sidebar-collapsed")
        : Boolean(forceCollapsed);
    setSidebarCollapsed(isCollapsed);
}

export function closeSidebar() {
    setSidebarCollapsed(true);
}

function _renderProposalActions(row) {
    const id = escapeHtml(row.id);
    const status = row.status || "active";
    if (status !== "active") {
        return `<button type="button" data-proposal-id="${id}" data-proposal-status="active">Reactivate</button>`;
    }
    return `
        <button type="button" data-proposal-id="${id}" data-proposal-status="done">Done</button>
        <button type="button" data-proposal-id="${id}" data-proposal-status="deferred">Defer</button>
        <button type="button" data-proposal-id="${id}" data-proposal-status="rejected">Reject</button>
    `;
}

function _renderProposalInbox(rows, status) {
    const list = document.getElementById("proposal-inbox-list");
    const count = document.getElementById("proposal-inbox-count");
    if (!list || !count) return;

    const label = status === "all" ? "total" : status;
    count.textContent = `${rows.length} ${label}`;
    if (!rows.length) {
        list.innerHTML = `<div class="sidebar-proposal-empty">No ${escapeHtml(label)} proposals</div>`;
        return;
    }

    list.innerHTML = rows.map(row => {
        const type = escapeHtml(row.type || "feature");
        const priority = row.priority ? `<span class="proposal-priority">${escapeHtml(row.priority)}</span>` : "";
        return `
            <article class="sidebar-proposal" data-proposal-row="${escapeHtml(row.id)}">
                <div class="sidebar-proposal-meta">
                    <span>${type}</span>
                    <span>${escapeHtml(row.status || "active")}</span>
                    ${priority}
                </div>
                <div class="sidebar-proposal-desc" title="${escapeHtml(row.desc || "")}">${escapeHtml(row.desc || "")}</div>
                <div class="sidebar-proposal-src">${escapeHtml(row.src || row.el || "")}</div>
                <div class="sidebar-proposal-actions">${_renderProposalActions(row)}</div>
            </article>
        `;
    }).join("");
}

export async function loadProposalInbox(status = null) {
    const filter = document.getElementById("proposal-status-filter");
    const selectedStatus = status || filter?.value || "active";
    if (filter && filter.value !== selectedStatus) filter.value = selectedStatus;

    try {
        const res = await adminFetch(`/api/proposals?status=${encodeURIComponent(selectedStatus)}`);
        const data = await res.json();
        if (!res.ok || data.error) {
            throw new Error(data.error || `HTTP ${res.status}`);
        }
        _renderProposalInbox(data.proposals || [], selectedStatus);
    } catch (err) {
        const list = document.getElementById("proposal-inbox-list");
        const count = document.getElementById("proposal-inbox-count");
        if (count) count.textContent = "Inbox error";
        if (list) list.innerHTML = `<div class="sidebar-proposal-empty">${escapeHtml(err.message)}</div>`;
    }
}

export async function updateProposalStatus(id, status) {
    if (!id || !status) return;
    try {
        const res = await adminFetch("/api/proposals/status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id, status, note: "Updated from sidebar inbox" })
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            throw new Error(data.error || `HTTP ${res.status}`);
        }
        await loadProposalInbox();
    } catch (err) {
        console.warn("[proposals] status update failed:", err);
    }
}

export function initProposalInbox() {
    const list = document.getElementById("proposal-inbox-list");
    if (!list || list.dataset.bound === "true") return;
    list.dataset.bound = "true";
    list.addEventListener("click", (event) => {
        const btn = event.target.closest?.("[data-proposal-id][data-proposal-status]");
        if (!btn) return;
        updateProposalStatus(btn.dataset.proposalId, btn.dataset.proposalStatus);
    });
    loadProposalInbox();
}

function _formatPolicyAction(action) {
    return String(action || "-").replace(/_/g, " ");
}

function _safeExternalUrl(value) {
    try {
        const url = new URL(String(value || ""), window.location.origin);
        if (url.protocol === "http:" || url.protocol === "https:") {
            return url.href;
        }
    } catch {
        return "";
    }
    return "";
}

function _setOperatorStatus(kind, label, message) {
    const badge = document.getElementById("operator-registry-badge");
    const messageEl = document.getElementById("operator-registry-message");
    if (badge) {
        badge.className = `task-badge ${kind}`;
        badge.textContent = label;
    }
    if (messageEl) {
        messageEl.textContent = message || "-";
    }
}

function _renderPolicyTiers(policyTiers) {
    const target = document.getElementById("operator-policy-tiers");
    if (!target) return;

    const entries = Object.entries(policyTiers || {}).sort(([left], [right]) => left.localeCompare(right));
    if (!entries.length) {
        target.innerHTML = `<div class="operator-empty">No policy tiers returned.</div>`;
        return;
    }

    target.innerHTML = entries.map(([tier, meta]) => {
        const action = meta?.default_action || "";
        const label = meta?.label || "Unlabeled tier";
        const blockedClass = tier === "X" || action === "blocked" ? " blocked" : "";
        return `
            <article class="operator-tier-card${blockedClass}">
                <div class="operator-tier-head">
                    <span>Tier ${escapeHtml(tier)}</span>
                    <span>${escapeHtml(_formatPolicyAction(action))}</span>
                </div>
                <div class="operator-tier-label">${escapeHtml(label)}</div>
            </article>
        `;
    }).join("");
}

let operatorSourceCache = [];
let operatorConnectorCache = {};

function _operatorText(key, fallback) {
    return translations[state.currentLang]?.[key] || fallback;
}

function _operatorSources(data) {
    return Array.isArray(data?.sources) ? data.sources : [];
}

function _findOperatorSource(sourceId) {
    const id = String(sourceId || "");
    return operatorSourceCache.find(source => String(source.id) === id) || null;
}

function _connectorHelp(source) {
    if (!source) return "Select a governed source, preview normalized records, then persist intentionally.";
    const type = source.type || "unknown";
    if (type === "manual") {
        return "Manual source: paste JSON records/items or CSV rows with title, url, and published_at.";
    }
    if (type === "rss") {
        return "RSS source: paste RSS/Atom XML for a deterministic preview, paste a URL to fetch, or leave empty to use source_url.";
    }
    if (type === "youtube") {
        return "YouTube source: optional JSON input such as {\"limit\":25,\"date_after\":\"2026-01-01\"}. Tier E requires explicit approval.";
    }
    return `${type} source: connector input is optional unless the backend reports it as required.`;
}

function _renderConnectorSummary(source) {
    if (!source) return "";
    const meta = operatorConnectorCache[source.type] || {};
    const policy = meta.default_policy_tier || source.policy_tier || "-";
    const recordType = meta.record_type || "-";
    const liveWrites = meta.writes_live_database ? "yes" : "no";
    return `Connector: ${source.type || "-"} | Default tier: ${policy} | Record type: ${recordType} | Live DB writes: ${liveWrites}`;
}

function _renderSourceRegistry(data) {
    const target = document.getElementById("operator-source-list");
    if (!target) return;

    if (!data?.registry_ready) {
        target.innerHTML = `
            <div class="operator-empty">
                ${escapeHtml(data?.message || "Governance registry migration is pending.")}
            </div>
        `;
        return;
    }

    const sources = data.sources || [];
    if (!sources.length) {
        target.innerHTML = `<div class="operator-empty">Registry ready. No sources registered.</div>`;
        return;
    }

    target.innerHTML = sources.map(source => {
        const safeUrl = _safeExternalUrl(source.source_url);
        const sourceUrl = safeUrl
            ? `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.source_url)}</a>`
            : "No source URL";
        return `
            <article class="operator-source-row" style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                <div style="flex: 1;">
                    <div class="operator-source-main">
                        <strong>${escapeHtml(source.name || "Untitled source")}</strong>
                        <span class="operator-source-meta">${escapeHtml(source.type || "unknown")} | Tier ${escapeHtml(source.policy_tier || "-")} | ${escapeHtml(source.status || "-")}</span>
                    </div>
                    <div class="operator-source-url">${sourceUrl}</div>
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <button class="btn-primary" id="btn-ingest-${source.id}" onclick="prepareIngestSource(${source.id})" style="padding: 4px 8px; font-size: 10px; cursor: pointer; display: flex; align-items: center; gap: 4px;">
                        <i class="fa-solid fa-play"></i>
                        <span id="txt-ingest-${source.id}">${escapeHtml(_operatorText("btn_prepare_ingest", "Prepare"))}</span>
                    </button>
                    <button class="btn-secondary" onclick="deleteSource(${source.id})" style="padding: 4px 8px; font-size: 10px; color: var(--danger-color, #ff4d4d); border-color: var(--danger-color, #ff4d4d); cursor: pointer; display: flex; align-items: center; justify-content: center; width: 28px; height: 28px;">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </article>
        `;
    }).join("");
}

function _renderIngestionConsole(sourcesData, connectorsData) {
    const consoleEl = document.getElementById("operator-ingest-console");
    const select = document.getElementById("operator-ingest-source");
    const result = document.getElementById("operator-ingest-result");
    if (!consoleEl || !select) return;

    operatorSourceCache = _operatorSources(sourcesData);
    operatorConnectorCache = connectorsData?.connectors || {};

    if (!sourcesData?.registry_ready) {
        select.innerHTML = `<option value="">Registry pending</option>`;
        select.disabled = true;
        if (result) result.innerHTML = `<div class="operator-empty">${escapeHtml(sourcesData?.message || "Source registry is pending.")}</div>`;
        return;
    }

    if (!operatorSourceCache.length) {
        select.innerHTML = `<option value="">No sources registered</option>`;
        select.disabled = true;
        if (result) result.innerHTML = `<div class="operator-empty">Add a governed source before running ingestion.</div>`;
        return;
    }

    const previous = select.value;
    select.disabled = false;
    select.innerHTML = operatorSourceCache.map(source => {
        const label = `${source.name || "Untitled source"} (${source.type || "unknown"} | Tier ${source.policy_tier || "-"})`;
        return `<option value="${escapeHtml(source.id)}">${escapeHtml(label)}</option>`;
    }).join("");
    if (previous && operatorSourceCache.some(source => String(source.id) === previous)) {
        select.value = previous;
    }
    if (!select.value) {
        select.value = String(operatorSourceCache[0].id);
    }
    prepareIngestSource(select.value, { focus: false, preserveInput: true });
}

function _summarizeMissing(items) {
    const values = items || [];
    if (!values.length) return "None";
    const shown = values.slice(0, 4).join(", ");
    const remaining = values.length - 4;
    return remaining > 0 ? `${shown} +${remaining} more` : shown;
}

function _renderMigrationReadiness(data) {
    const target = document.getElementById("operator-migration-readiness");
    if (!target) return;

    if (!data?.database_present) {
        target.innerHTML = `<div class="operator-empty">Local database file not found.</div>`;
        return;
    }

    const status = data.registry_ready ? "Ready" : "Pending";
    const migrationState = data.migration_applied ? "migration logged" : "migration not logged";
    target.innerHTML = `
        <article class="operator-source-row">
            <div class="operator-source-main">
                <strong>${escapeHtml(status)}</strong>
                <span class="operator-source-meta">${escapeHtml(data.migration_version || "governance migration")} | ${escapeHtml(migrationState)}</span>
            </div>
            <div class="operator-source-url">Dry run only</div>
        </article>
        <article class="operator-source-row">
            <div class="operator-source-main">
                <strong>Missing tables</strong>
                <span class="operator-source-meta">${escapeHtml(_summarizeMissing(data.missing_tables))}</span>
            </div>
        </article>
        <article class="operator-source-row">
            <div class="operator-source-main">
                <strong>Missing indexes</strong>
                <span class="operator-source-meta">${escapeHtml(_summarizeMissing(data.missing_indexes))}</span>
            </div>
        </article>
    `;
}

function _renderConnectorRuns(data) {
    const target = document.getElementById("operator-connector-runs");
    if (!target) return;

    if (!data?.registry_ready) {
        target.innerHTML = `
            <div class="operator-empty">
                ${escapeHtml(data?.message || "Connector run registry is pending.")}
            </div>
        `;
        return;
    }

    const runs = data.connector_runs || [];
    if (!runs.length) {
        target.innerHTML = `<div class="operator-empty">Registry ready. No connector runs recorded.</div>`;
        return;
    }

    target.innerHTML = runs.map(run => `
        <article class="operator-source-row">
            <div class="operator-source-main">
                <strong>${escapeHtml(run.job_type || "connector job")}</strong>
                <span class="operator-source-meta">${escapeHtml(run.source_name || "No source")} | ${escapeHtml(run.status || "-")} | ${escapeHtml(run.created_at || "-")}</span>
            </div>
            <div class="operator-source-url">
                Seen ${escapeHtml(run.records_seen ?? 0)} | New ${escapeHtml(run.records_created ?? 0)}
            </div>
        </article>
    `).join("");
}

function _renderSourceRecords(data) {
    const target = document.getElementById("operator-source-records");
    if (!target) return;

    if (!data?.registry_ready) {
        target.innerHTML = `
            <div class="operator-empty">
                ${escapeHtml(data?.message || "Source record registry is pending.")}
            </div>
        `;
        return;
    }

    const records = data.source_records || [];
    if (!records.length) {
        target.innerHTML = `<div class="operator-empty">Registry ready. No source records ingested.</div>`;
        return;
    }

    target.innerHTML = records.map(record => {
        const safeUrl = _safeExternalUrl(record.url);
        const title = record.title || record.external_record_id || "Untitled record";
        const recordUrl = safeUrl
            ? `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(record.url)}</a>`
            : "No URL";
        return `
            <article class="operator-source-row">
                <div class="operator-source-main">
                    <strong>${escapeHtml(title)}</strong>
                    <span class="operator-source-meta">${escapeHtml(record.source_name || "No source")} | ${escapeHtml(record.record_type || "-")} | ${escapeHtml(record.published_at || record.captured_at || "-")}</span>
                    <span class="operator-source-meta">Hash: ${record.has_content_hash ? "present" : "missing"}</span>
                </div>
                <div class="operator-source-url">${recordUrl}</div>
            </article>
        `;
    }).join("");
}

function _formatPercent(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return "-";
    return `${Math.round(parsed * 100)}%`;
}

function _formatMetric(value, digits = 2) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return "-";
    if (Math.abs(parsed) >= 100) return parsed.toFixed(0);
    return parsed.toFixed(digits).replace(/\.?0+$/, "");
}

function _formatRecommendation(value) {
    return String(value || "unknown").replace(/_/g, " ");
}

function _renderDataMethodReview(payload) {
    const target = document.getElementById("operator-data-method-review");
    if (!target) return;

    const data = payload?.review || payload || {};
    if (!data.log_exists) {
        target.innerHTML = `
            <div class="operator-empty">
                No method experiment log found. Run ingestion experiments with method logging before ranking.
            </div>
        `;
        return;
    }

    const methods = data.ranked_methods || [];
    if (!methods.length) {
        target.innerHTML = `
            <div class="operator-empty">
                ${escapeHtml(data.total_runs ?? 0)} runs logged. No methods meet the current review threshold.
            </div>
        `;
        return;
    }

    const topMethods = methods.slice(0, 4).map(method => `
        <article class="operator-source-row operator-method-row">
            <div class="operator-source-main">
                <strong>${escapeHtml(method.method_id || "unknown_method")}</strong>
                <span class="operator-source-meta">
                    ${escapeHtml(method.source_type || "unknown")} | ${escapeHtml(_formatRecommendation(method.recommendation))} | last ${escapeHtml(method.last_seen || "-")}
                </span>
                <span class="operator-source-meta">
                    Runs ${escapeHtml(method.runs ?? 0)} | Success ${escapeHtml(_formatPercent(method.success_rate))} | Records/sec ${escapeHtml(_formatMetric(method.avg_records_per_second))}
                </span>
            </div>
            <div class="operator-source-url">
                Score ${escapeHtml(_formatMetric(method.score, 4))}
            </div>
        </article>
    `).join("");

    const insight = (data.insights || [])[0];
    const insightHtml = insight ? `
        <article class="operator-source-row">
            <div class="operator-source-main">
                <strong>${escapeHtml(_formatRecommendation(insight.type))}</strong>
                <span class="operator-source-meta">${escapeHtml(insight.message || "")}</span>
            </div>
        </article>
    ` : "";

    target.innerHTML = `
        <article class="operator-source-row">
            <div class="operator-source-main">
                <strong>${escapeHtml(data.method_count ?? methods.length)} ranked methods</strong>
                <span class="operator-source-meta">${escapeHtml(data.total_runs ?? 0)} runs | generated ${escapeHtml(data.generated_at || "-")}</span>
            </div>
        </article>
        ${topMethods}
        ${insightHtml}
    `;
}

export async function runDataMethodReview() {
    const button = document.getElementById("operator-run-method-review");
    const previousHtml = button?.innerHTML;
    if (button) {
        button.disabled = true;
        button.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Run`;
    }

    try {
        const response = await adminFetch("/api/analytics/data-methods/review", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({min_runs: 1})
        });
        const payload = await response.json();
        if (!response.ok || payload.error) {
            throw new Error(payload.error || `Method review failed: HTTP ${response.status}`);
        }
        _renderDataMethodReview(payload);
        _setOperatorStatus("active", "Review saved", "Data method review snapshot written.");
    } catch (err) {
        const target = document.getElementById("operator-data-method-review");
        if (target) {
            target.innerHTML = `<div class="operator-empty">${escapeHtml(err.message || "Data method review unavailable.")}</div>`;
        }
        _setOperatorStatus("error", "Error", err.message || "Unable to run data method review.");
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = previousHtml || `<i class="fa-solid fa-chart-line"></i> Run`;
        }
    }
}

export async function generateMethodProposals() {
    const button = document.getElementById("operator-generate-method-proposals");
    const previousHtml = button?.innerHTML;
    if (button) {
        button.disabled = true;
        button.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Proposals`;
    }

    try {
        const response = await adminFetch("/api/analytics/data-methods/proposals", {
            method: "POST",
            headers: {"Content-Type": "application/json"}
        });
        const payload = await response.json();
        if (!response.ok || payload.error) {
            throw new Error(payload.error || `Failed to generate proposals: HTTP ${response.status}`);
        }
        
        const count = payload.created_count ?? 0;
        const msg = `${count} proposals generated (skipped ${payload.skipped_existing_count ?? 0} existing).`;
        _setOperatorStatus("active", "Proposals generated", msg);
        
        if (typeof loadProposalInbox === 'function') {
            loadProposalInbox();
        }
    } catch (err) {
        _setOperatorStatus("error", "Error", err.message || "Unable to generate method proposals.");
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = previousHtml || `<i class="fa-solid fa-lightbulb"></i> Proposals`;
        }
    }
}

function _renderAuditEvents(data) {
    const target = document.getElementById("operator-audit-events");
    if (!target) return;

    if (!data?.registry_ready) {
        target.innerHTML = `
            <div class="operator-empty">
                ${escapeHtml(data?.message || "Audit event registry is pending.")}
            </div>
        `;
        return;
    }

    const events = data.audit_events || [];
    if (!events.length) {
        target.innerHTML = `<div class="operator-empty">Registry ready. No audit events recorded.</div>`;
        return;
    }

    target.innerHTML = events.map(event => {
        const metadataFlag = event.has_metadata ? "metadata retained server-side" : "no metadata";
        return `
            <article class="operator-source-row">
                <div class="operator-source-main">
                    <strong>${escapeHtml(event.action || "audit event")}</strong>
                    <span class="operator-source-meta">${escapeHtml(event.object_type || "-")} | ${escapeHtml(event.object_id || "-")} | ${escapeHtml(event.created_at || "-")}</span>
                </div>
                <div class="operator-source-url">${escapeHtml(metadataFlag)}</div>
            </article>
        `;
    }).join("");
}

function _renderEvidenceLinks(data) {
    const target = document.getElementById("operator-evidence-links");
    if (!target) return;

    if (!data?.registry_ready) {
        target.innerHTML = `
            <div class="operator-empty">
                ${escapeHtml(data?.message || "Evidence link registry is pending.")}
            </div>
        `;
        return;
    }

    const links = data.evidence_links || [];
    if (!links.length) {
        target.innerHTML = `<div class="operator-empty">Registry ready. No evidence links recorded.</div>`;
        return;
    }

    target.innerHTML = links.map(link => {
        const targetTitle = link.video_title || link.source_record_title || link.source_record_url || "No evidence target";
        const confidence = link.confidence == null ? "-" : Number(link.confidence).toFixed(2);
        return `
            <article class="operator-source-row">
                <div class="operator-source-main">
                    <strong>${escapeHtml(link.claim_preview || "Untitled claim")}</strong>
                    <span class="operator-source-meta">${escapeHtml(link.ai_output_title || "AI output")} | ${escapeHtml(link.source_name || "No source")} | confidence ${escapeHtml(confidence)}</span>
                    <span class="operator-source-meta">${escapeHtml(link.evidence_preview || targetTitle)}</span>
                </div>
            </article>
        `;
    }).join("");
}

function _renderCredentialStatus(data) {
    const target = document.getElementById("operator-credential-status");
    if (!target) return;

    if (!data?.registry_ready) {
        target.innerHTML = `
            <div class="operator-empty">
                ${escapeHtml(data?.message || "Credential registry is pending.")}
            </div>
        `;
        return;
    }

    const credentials = data.source_credentials || [];
    if (!credentials.length) {
        target.innerHTML = `<div class="operator-empty">Registry ready. No source credentials registered.</div>`;
        return;
    }

    target.innerHTML = credentials.map(credential => {
        const secretState = credential.has_secret_ref ? "reference present" : "reference missing";
        const byok = credential.byok ? "BYOK" : "managed";
        const expiry = credential.expires_at || "no expiry";
        return `
            <article class="operator-source-row">
                <div class="operator-source-main">
                    <strong>${escapeHtml(credential.source_name || "No source")}</strong>
                    <span class="operator-source-meta">${escapeHtml(credential.rotation_status || "unknown")} | ${escapeHtml(byok)} | ${escapeHtml(secretState)}</span>
                    <span class="operator-source-meta">Expires: ${escapeHtml(expiry)}</span>
                </div>
            </article>
        `;
    }).join("");
}

export async function loadOperatorRuntimePanel() {
    const panel = document.getElementById("operator-runtime-panel");
    if (!panel) return;

    _setOperatorStatus("idle", "Checking", "Loading governance policy...");

    try {
        const policyRes = await adminFetch("/api/governance/policy");
        const policy = await policyRes.json();
        if (!policyRes.ok || policy.error) {
            throw new Error(policy.error || `Policy request failed: HTTP ${policyRes.status}`);
        }

        const [readinessRes, sourcesRes, connectorsRes, runsRes, recordsRes, dataMethodsRes, eventsRes, evidenceRes, credentialsRes] = await Promise.all([
            adminFetch("/api/governance/readiness"),
            adminFetch("/api/sources"),
            adminFetch("/api/source-connectors"),
            adminFetch("/api/connector-runs?limit=5"),
            adminFetch("/api/source-records?limit=8"),
            adminFetch("/api/analytics/data-methods?min_runs=1"),
            adminFetch("/api/audit-events?limit=5"),
            adminFetch("/api/evidence-links?limit=5"),
            adminFetch("/api/source-credentials/status?limit=5")
        ]);
        const readiness = await readinessRes.json();
        const sources = await sourcesRes.json();
        const connectors = await connectorsRes.json();
        const runs = await runsRes.json();
        const records = await recordsRes.json();
        const dataMethods = await dataMethodsRes.json();
        const events = await eventsRes.json();
        const evidence = await evidenceRes.json();
        const credentials = await credentialsRes.json();
        if (!readinessRes.ok || readiness.error) {
            throw new Error(readiness.error || `Readiness request failed: HTTP ${readinessRes.status}`);
        }
        if (!sourcesRes.ok || sources.error) {
            throw new Error(sources.error || `Source registry request failed: HTTP ${sourcesRes.status}`);
        }
        if (!connectorsRes.ok || connectors.error) {
            throw new Error(connectors.error || `Connector metadata request failed: HTTP ${connectorsRes.status}`);
        }
        if (!runsRes.ok || runs.error) {
            throw new Error(runs.error || `Connector runs request failed: HTTP ${runsRes.status}`);
        }
        if (!recordsRes.ok || records.error) {
            throw new Error(records.error || `Source records request failed: HTTP ${recordsRes.status}`);
        }
        if (!dataMethodsRes.ok || dataMethods.error) {
            throw new Error(dataMethods.error || `Data methods request failed: HTTP ${dataMethodsRes.status}`);
        }
        if (!eventsRes.ok || events.error) {
            throw new Error(events.error || `Audit events request failed: HTTP ${eventsRes.status}`);
        }
        if (!evidenceRes.ok || evidence.error) {
            throw new Error(evidence.error || `Evidence links request failed: HTTP ${evidenceRes.status}`);
        }
        if (!credentialsRes.ok || credentials.error) {
            throw new Error(credentials.error || `Credential status request failed: HTTP ${credentialsRes.status}`);
        }

        _renderPolicyTiers(policy.policy_tiers);
        _renderMigrationReadiness(readiness);
        _renderSourceRegistry(sources);
        _renderIngestionConsole(sources, connectors);
        _renderConnectorRuns(runs);
        _renderSourceRecords(records);
        _renderDataMethodReview(dataMethods);
        _renderAuditEvents(events);
        _renderEvidenceLinks(evidence);
        _renderCredentialStatus(credentials);

        const ready = Boolean(readiness.registry_ready && policy.registry_ready && sources.registry_ready && runs.registry_ready && records.registry_ready && events.registry_ready && evidence.registry_ready && credentials.registry_ready);
        if (ready) {
            _setOperatorStatus("active", "Ready", "Governance registry tables and indexes are available.");
        } else {
            _setOperatorStatus("idle", "Pending", sources.message || "Governance registry migration is pending or incomplete. Live DB unchanged.");
        }
    } catch (err) {
        _setOperatorStatus("error", "Error", err.message || "Unable to load Operator Runtime status.");
        const tiers = document.getElementById("operator-policy-tiers");
        const readiness = document.getElementById("operator-migration-readiness");
        const sources = document.getElementById("operator-source-list");
        const runs = document.getElementById("operator-connector-runs");
        const records = document.getElementById("operator-source-records");
        const dataMethods = document.getElementById("operator-data-method-review");
        const events = document.getElementById("operator-audit-events");
        const evidence = document.getElementById("operator-evidence-links");
        const credentials = document.getElementById("operator-credential-status");
        const ingest = document.getElementById("operator-ingest-result");
        if (tiers) tiers.innerHTML = `<div class="operator-empty">${escapeHtml(err.message || "Unable to load policy tiers.")}</div>`;
        if (readiness) readiness.innerHTML = `<div class="operator-empty">Migration readiness unavailable.</div>`;
        if (sources) sources.innerHTML = `<div class="operator-empty">Source registry unavailable.</div>`;
        if (ingest) ingest.innerHTML = `<div class="operator-empty">Ingestion console unavailable.</div>`;
        if (runs) runs.innerHTML = `<div class="operator-empty">Connector runs unavailable.</div>`;
        if (records) records.innerHTML = `<div class="operator-empty">Source records unavailable.</div>`;
        if (dataMethods) dataMethods.innerHTML = `<div class="operator-empty">Data method review unavailable.</div>`;
        if (events) events.innerHTML = `<div class="operator-empty">Audit events unavailable.</div>`;
        if (evidence) evidence.innerHTML = `<div class="operator-empty">Evidence links unavailable.</div>`;
        if (credentials) credentials.innerHTML = `<div class="operator-empty">Credential status unavailable.</div>`;
    }
}

export function initOperatorRuntimePanel() {
    const panel = document.getElementById("operator-runtime-panel");
    if (!panel || panel.dataset.loaded === "true") return;
    panel.dataset.loaded = "true";
    loadOperatorRuntimePanel();
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
        adminFetchSilent("/api/videos/ocr_thumbnails", {
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
    window.syncDateRangeSliderFromInputs?.();
    
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
    window.dashboardWorkspace?.refreshAll();
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
    window.syncDateRangeSliderFromInputs?.();
    
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
    window.dashboardWorkspace?.refreshAll();
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
    
    void openAdminUrl(`/api/videos/export?${params.toString()}`);
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
    
    // Reset transcript UI state
    const transcriptBtn = document.getElementById("mv-modal-transcript-btn");
    const transcriptText = document.getElementById("mv-modal-transcript-text");
    if (transcriptBtn && transcriptText) {
        transcriptBtn.disabled = false;
        transcriptText.innerText = translations[state.currentLang].modal_extract_transcript || "Extract Transcript";
    }
    const transcriptTitle = document.getElementById("mv-modal-transcript-title");
    const transcriptBox = document.getElementById("mv-modal-transcript-box");
    if (transcriptTitle) {
        transcriptTitle.style.display = "none";
    }
    if (transcriptBox) {
        transcriptBox.style.display = "none";
        transcriptBox.innerText = "";
    }
    
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
    
    // Reset transcript UI state
    const transcriptBtn = document.getElementById("mv-modal-transcript-btn");
    const transcriptText = document.getElementById("mv-modal-transcript-text");
    if (transcriptBtn && transcriptText) {
        transcriptBtn.disabled = false;
        transcriptText.innerText = translations[state.currentLang].modal_extract_transcript || "Extract Transcript";
    }
    const transcriptTitle = document.getElementById("mv-modal-transcript-title");
    const transcriptBox = document.getElementById("mv-modal-transcript-box");
    if (transcriptTitle) {
        transcriptTitle.style.display = "none";
    }
    if (transcriptBox) {
        transcriptBox.style.display = "none";
        transcriptBox.innerText = "";
    }
    
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
        const res = await adminFetch(`/api/videos/${state.activeModalVideoId}/formats`);
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
        const response = await adminFetch(downloadUrl);
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
        const res = await adminFetch(`/api/videos/${state.activeModalVideoId}/scrape_details`, {
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

export async function getTranscriptFromModal() {
    const btn = document.getElementById("mv-modal-transcript-btn");
    const txt = document.getElementById("mv-modal-transcript-text");
    if (!state.activeModalVideoId || btn.disabled) return;

    const oldText = txt.innerText;
    txt.innerText = translations[state.currentLang].modal_extracting_transcript || "Extracting...";
    btn.disabled = true;

    try {
        const res = await adminFetch(`/api/videos/${state.activeModalVideoId}/transcript`);
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.error || "Failed to extract transcript");
        }

        const transcriptTitle = document.getElementById("mv-modal-transcript-title");
        const transcriptBox = document.getElementById("mv-modal-transcript-box");

        if (transcriptBox) {
            transcriptBox.innerText = data.transcript || "";
            transcriptBox.style.display = "block";
        }
        if (transcriptTitle) {
            transcriptTitle.style.display = "block";
        }

    } catch (err) {
        alert(state.currentLang === 'ua' ? `Не вдалося отримати транскрипт: ${err.message}` : `Failed to extract transcript: ${err.message}`);
    } finally {
        if (btn) btn.disabled = false;
        if (txt) txt.innerText = oldText;
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
        const res = await adminFetch("/api/action/update_views", {
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
    switchSection("terminal-tab", document.getElementById("menu-item-terminal")?.querySelector("a"));
    
    try {
        const res = await adminFetch("/api/action/add_channel", {
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

function _formatAssistantFilterContext() {
    const ctx = _getChatContext();
    const selectedNames = (ctx.channel_ids || []).map(id => {
        const channel = state.allChannels.find(ch => ch.channel_id === id);
        return channel?.channel_name || id;
    });
    return [
        "Поточний контекст фільтрів дашборду:",
        `- Поточна дата/час: ${new Date().toLocaleString()}`,
        `- Діапазон дат: ${ctx.start_date || "-"} → ${ctx.end_date || "-"}`,
        `- Обрані канали: ${selectedNames.length ? selectedNames.join(", ") : "усі або не обрано"}`,
        `- ID каналів: ${(ctx.channel_ids || []).join(", ") || "-"}`
    ].join("\n");
}

/** Selected model id from the dropdown (empty = server default) */
function _getSelectedModel() {
    const sel = document.getElementById("chat-model-select");
    return sel ? sel.value : "";
}

function _setModelSelectorValue(modelId) {
    const sel = document.getElementById("chat-model-select");
    if (!sel) return;

    const value = modelId || "";
    if (value && !Array.from(sel.options).some(opt => opt.value === value)) {
        const opt = document.createElement("option");
        opt.value = value;
        opt.textContent = value;
        sel.appendChild(opt);
    }
    sel.value = value;
    localStorage.setItem(`${CHAT_STORAGE_MODEL_PREFIX}${state.agentProvider}`, value);
}

async function _syncActiveModelFromStream(provider, modelId) {
    if (!provider) return;

    if (state.agentProvider !== provider) {
        state.agentProvider = provider;
        localStorage.setItem(CHAT_STORAGE_PROVIDER, provider);
        const providerSel = document.getElementById("chat-provider-select");
        if (providerSel) providerSel.value = provider;
        await _loadModels(false);
    }
    _setModelSelectorValue(modelId);
}

export async function changeChatProvider(provider) {
    state.agentProvider = provider;
    localStorage.setItem(CHAT_STORAGE_PROVIDER, provider);
    await _loadModels(true);
    window.chatUIManager?.updateContextMeter();
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
    window.chatUIManager?.updateContextMeter();
}

/** Loads model list from backend and populates the selector */
async function _loadModels(promptForAuth = false) {
    const sel = document.getElementById("chat-model-select");
    if (!sel) return;
    const providerSel = document.getElementById("chat-provider-select");
    if (providerSel && providerSel.value !== state.agentProvider) {
        providerSel.value = state.agentProvider;
    }
    if (sel.dataset.persistBound !== "true") {
        sel.dataset.persistBound = "true";
        sel.addEventListener("change", () => {
            localStorage.setItem(`${CHAT_STORAGE_MODEL_PREFIX}${state.agentProvider}`, sel.value || "");
        });
    }
    try {
        sel.disabled = true;
        const fetchModels = promptForAuth ? adminFetch : adminFetchSilent;
        const res  = await fetchModels(`/api/agent/models?provider=${state.agentProvider}`);
        if (res.status === 403) return;
        const data = await res.json();
        const models = (data.models || []).slice(0, 50);
        sel.innerHTML = "";
        if (models.length === 0) {
            sel.innerHTML = '<option value="">Авто (за замовчуванням)</option>';
        } else {
            const fragment = document.createDocumentFragment();
            const def = document.createElement("option");
            def.value = ""; def.textContent = "Авто (за замовчуванням)";
            fragment.appendChild(def);
            models.forEach(m => {
                const opt = document.createElement("option");
                opt.value = m.id;
                opt.textContent = m.name || m.id;
                fragment.appendChild(opt);
            });
            sel.appendChild(fragment);
        }
        const storedModel = localStorage.getItem(`${CHAT_STORAGE_MODEL_PREFIX}${state.agentProvider}`) || "";
        if (storedModel && Array.from(sel.options).some(opt => opt.value === storedModel)) {
            sel.value = storedModel;
        } else {
            sel.value = "";
        }
    } catch (e) {
        sel.innerHTML = '<option value="">Авто (за замовчуванням)</option>';
        console.warn("[chat] loadModels error:", e);
    } finally {
        sel.disabled = false;
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

const CHAT_CONTEXT_MAX_TOKENS = 24000;
const CHAT_STAGED_FILES = [];
let chatContextWarningShown = false;

function _estimateTokens(text) {
    return Math.ceil((text || "").length * 1.2);
}

function _getStagedFilesRaw() {
    if (CHAT_STAGED_FILES.length === 0) return "";
    return CHAT_STAGED_FILES.map(file => {
        return `--- Attached text file: ${file.name} (${file.tokens} estimated tokens) ---\n${file.content}`;
    }).join("\n\n");
}

function _renderStagedFileChips() {
    const tray = document.getElementById("chat-file-chips");
    if (!tray) return;
    tray.innerHTML = "";
    tray.hidden = CHAT_STAGED_FILES.length === 0;

    CHAT_STAGED_FILES.forEach((file, index) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "chat-file-chip";
        chip.title = file.name;
        chip.innerHTML = `<i class="fa-solid fa-file-lines"></i><span></span><small></small><i class="fa-solid fa-xmark"></i>`;
        chip.querySelector("span").textContent = file.name;
        chip.querySelector("small").textContent = `${file.tokens.toLocaleString()} tok`;
        chip.addEventListener("click", () => {
            CHAT_STAGED_FILES.splice(index, 1);
            _renderStagedFileChips();
            window.chatUIManager?.updateContextMeter();
        });
        tray.appendChild(chip);
    });
}

function _clearStagedFiles() {
    CHAT_STAGED_FILES.splice(0, CHAT_STAGED_FILES.length);
    _renderStagedFileChips();
}

function _appendUserBubble(containerEl, message, stagedFiles = []) {
    if (!containerEl) return null;
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble user";

    const stagedRaw = stagedFiles.length ? _getStagedFilesRaw() : "";
    bubble.dataset.raw = [message, stagedRaw].filter(Boolean).join("\n\n");

    const messageText = document.createElement("div");
    messageText.textContent = message || "[attached files]";
    bubble.appendChild(messageText);

    if (stagedFiles.length) {
        const fileList = document.createElement("div");
        fileList.className = "chat-bubble-files";
        stagedFiles.forEach(file => {
            const fileChip = document.createElement("span");
            fileChip.className = "chat-bubble-file";
            fileChip.textContent = `${file.name} · ${file.tokens.toLocaleString()} tok`;
            fileList.appendChild(fileChip);
        });
        bubble.appendChild(fileList);
    }

    containerEl.appendChild(bubble);
    return bubble;
}

export function exportChatMarkdown() {
    const history = _getChatHistory();
    if (history.length === 0) return;

    const createdAt = new Date().toISOString();
    const roleLabels = {
        user: "User",
        assistant: "Assistant"
    };
    const body = history.map((item, index) => {
        const label = roleLabels[item.role] || item.role;
        return `## ${index + 1}. ${label}\n\n${item.content.trim()}`;
    }).join("\n\n---\n\n");
    const markdown = `# Chat Session\n\nExported: ${createdAt}\n\n${body}\n`;

    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `chat-session-${createdAt.replace(/[:.]/g, "-")}.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

export async function clearChatHistory() {
    const containerEl = document.getElementById("chat-messages");
    const inputEl = document.getElementById("chat-input");
    const hasMessages = _getChatHistory().length > 0;
    const hasStagedFiles = CHAT_STAGED_FILES.length > 0;
    const hasInput = Boolean(inputEl && inputEl.value.trim());
    if (!hasMessages && !hasStagedFiles && !hasInput) return;

    const shouldClear = window.confirm("Очистити історію чату?");
    if (!shouldClear) return;

    if (containerEl) {
        containerEl.innerHTML = "";
    }
    if (inputEl) {
        inputEl.value = "";
        inputEl.disabled = false;
        inputEl.placeholder = "Напишіть повідомлення...";
    }
    _clearStagedFiles();
    chatContextWarningShown = false;
    localStorage.removeItem(CHAT_STORAGE_HISTORY);
    window.chatUIManager?.updateContextMeter();

    try {
        await adminFetchSilent("/api/chat/clear-context", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scope: "active_session" })
        });
    } catch (err) {
        console.warn("[chat] clear-context endpoint unavailable:", err);
    }
}

function _renderChatMarkdown(targetEl, rawText) {
    if (!targetEl) return;
    if (window.marked) {
        targetEl.innerHTML = window.marked.parse ? window.marked.parse(rawText) : window.marked(rawText);
    } else {
        targetEl.innerText = rawText;
    }
}

function _appendChatBubble(containerEl, role, content) {
    if (!containerEl || !content) return null;
    const bubble = document.createElement("div");
    bubble.className = role === "user" ? "chat-bubble user" : "chat-bubble bot";
    bubble.dataset.raw = content;
    if (role === "user") {
        bubble.innerText = content;
    } else {
        _renderChatMarkdown(bubble, content);
    }
    containerEl.appendChild(bubble);
    return bubble;
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

        const res = await adminFetch("/api/agent/chat/stream", {
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
                    _renderChatMarkdown(botDiv, accumulatedText);
                    botDiv.dataset.raw = accumulatedText;
                    window.chatUIManager?.saveHistory();
                    return;
                }
                try {
                    const obj = JSON.parse(payload);
                    if (obj.error) {
                        hasError = true;
                        botDiv.classList.add("error");
                        botDiv.innerText = `Помилка: ${obj.error}`;
                        botDiv.dataset.raw = botDiv.innerText;
                        botDiv.classList.remove("streaming");
                        return;
                    }
                    if (obj.provider || obj.model) {
                        void _syncActiveModelFromStream(obj.provider, obj.model);
                    }
                    if (obj.text) {
                        accumulatedText += obj.text;
                        botDiv.dataset.raw = accumulatedText;
                        _renderChatMarkdown(botDiv, accumulatedText);
                        containerEl.scrollTop = containerEl.scrollHeight;
                    }
                } catch (_) { /* skip malformed */ }
            }
        }
    } catch (err) {
        if (!hasError) {
            botDiv.classList.add("error");
            botDiv.innerText = `Помилка з'єднання: ${err.message}`;
            botDiv.dataset.raw = botDiv.innerText;
        }
    } finally {
        botDiv.classList.remove("streaming");
        window.chatUIManager?.saveHistory();
    }
}

function _setChatDrawerOpenState(isOpen) {
    const drawer = document.getElementById("chat-drawer");
    if (!drawer) return;

    drawer.classList.toggle("open", isOpen);
    if (window.innerWidth > 768) {
        document.body.classList.toggle("chat-drawer-open", isOpen);
    } else {
        document.body.classList.remove("chat-drawer-open");
    }
    localStorage.setItem("ui_drawer_open", isOpen ? "true" : "false");
    const openBtn = document.getElementById("chat-open-btn");
    if (openBtn) {
        openBtn.hidden = isOpen;
    }
    window.chatUIManager?.syncOpenState(isOpen);
}

export function openChatDrawer() {
    _setChatDrawerOpenState(true);
    _loadModels(true);
}

export function closeChatDrawer() {
    _setChatDrawerOpenState(false);
}

export function toggleChatDrawer(forceClose = false) {
    if (forceClose) {
        closeChatDrawer();
        return;
    }
    const drawer = document.getElementById("chat-drawer");
    if (!drawer) return;
    if (drawer.classList.contains("open")) {
        closeChatDrawer();
    } else {
        openChatDrawer();
    }
}

export async function summarizeCurrentScreen() {
    const drawer = document.getElementById("chat-drawer");
    if (drawer && !drawer.classList.contains("open")) {
        openChatDrawer();
    }
    await _requestAddScreenSummary();
}

export async function handleSendChatMessage(event) {
    if (event) { event.preventDefault(); event.stopPropagation(); }

    const inputEl     = document.getElementById("chat-input");
    const containerEl = document.getElementById("chat-messages");
    if (!inputEl || !containerEl) return;

    const message = inputEl.value.trim();
    const stagedSnapshot = CHAT_STAGED_FILES.map(file => ({ ...file }));
    if (!message && stagedSnapshot.length === 0) return;
    inputEl.value = "";
    inputEl.disabled = false;
    inputEl.placeholder = "Напишіть повідомлення...";
    _clearStagedFiles();

    // Collect history before appending new user bubble
    const history = _getChatHistory();

    const attachmentRaw = stagedSnapshot.map(file => {
        return `--- Attached text file: ${file.name} (${file.tokens} estimated tokens) ---\n${file.content}`;
    }).join("\n\n");
    const outboundMessage = [message, attachmentRaw].filter(Boolean).join("\n\n");

    _appendUserBubble(containerEl, message, stagedSnapshot);
    containerEl.scrollTop = containerEl.scrollHeight;
    window.chatUIManager?.saveHistory();

    // Stream bot reply with context of current screen
    const screenText = _scrapeCurrentScreenText();
    await _streamBotMessage(outboundMessage, containerEl, screenText, history);
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
    let bodyText = "";
    if (state.activeModalVideoId) {
        const modal = document.getElementById("video-details-modal");
        if (modal && modal.style.display === "flex") {
            bodyText = _scrapeVideoModalText();
        }
    }
    if (!bodyText && state.currentSection === "terminal-tab") {
        bodyText = _scrapeTerminalAndTableText();
    }
    if (!bodyText) {
        bodyText = _scrapeDashboardWidgetsText();
    }
    return [_formatAssistantFilterContext(), bodyText].filter(Boolean).join("\n\n---\n\n");
}

function _scrapeDashboardWidgetsText() {
    const sections = [_scrapeActiveChartText()];
    const widgetSummaries = window.dashboardWorkspace?.serializeForSummary?.() || [];
    widgetSummaries.forEach(summary => {
        if (summary && summary.trim()) sections.push(summary);
    });
    return sections.filter(Boolean).join("\n\n---\n\n");
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

const CHAT_MIN_WIDTH = 380;
const CHAT_STORAGE_WIDTH = "ui_chat_width";

function _getChatMaxWidth() {
    return Math.max(CHAT_MIN_WIDTH, Math.floor(window.innerWidth / 2));
}

function _clampChatWidth(width) {
    const numericWidth = Number.parseInt(width, 10);
    if (Number.isNaN(numericWidth)) return CHAT_MIN_WIDTH;
    return Math.min(Math.max(numericWidth, CHAT_MIN_WIDTH), _getChatMaxWidth());
}

function _applyChatWidth(width, persist = false) {
    const nextWidth = _clampChatWidth(width);
    document.documentElement.style.setProperty("--chat-width", `${nextWidth}px`);
    if (persist) {
        localStorage.setItem(CHAT_STORAGE_WIDTH, String(nextWidth));
    }
    return nextWidth;
}

export function initChatResizer() {
    const resizer = document.getElementById("chat-resizer");
    const drawer = document.getElementById("chat-drawer");
    if (!resizer || !drawer) return;
    if (resizer.dataset.chatResizerBound === "true") return;
    resizer.dataset.chatResizerBound = "true";

    const storedWidth = localStorage.getItem(CHAT_STORAGE_WIDTH);
    if (storedWidth) {
        _applyChatWidth(storedWidth);
    }

    let isResizing = false;
    let pendingFrame = null;
    let latestPointerX = window.innerWidth - _clampChatWidth(storedWidth || CHAT_MIN_WIDTH);

    const scheduleWidthUpdate = (clientX) => {
        latestPointerX = clientX;
        if (pendingFrame !== null) return;
        pendingFrame = requestAnimationFrame(() => {
            pendingFrame = null;
            _applyChatWidth(window.innerWidth - latestPointerX);
            window.chatUIManager?.updateContextMeter();
        });
    };

    const finishResize = () => {
        if (!isResizing) return;
        isResizing = false;
        if (pendingFrame !== null) {
            cancelAnimationFrame(pendingFrame);
            pendingFrame = null;
            _applyChatWidth(window.innerWidth - latestPointerX);
        }
        _applyChatWidth(getComputedStyle(document.documentElement).getPropertyValue("--chat-width"), true);
        resizer.classList.remove("active");
        document.body.classList.remove("dragging-chat");
        window.dispatchEvent(new Event('resize'));
        window.chatUIManager?.updateContextMeter();
    };

    // Mouse events
    resizer.addEventListener("mousedown", function(e) {
        e.preventDefault();
        isResizing = true;
        resizer.classList.add("active");
        document.body.classList.add("dragging-chat");
    });

    window.addEventListener("mousemove", function(e) {
        if (!isResizing) return;
        scheduleWidthUpdate(e.clientX);
    });

    window.addEventListener("mouseup", finishResize);

    // Touch events
    resizer.addEventListener("touchstart", function(e) {
        isResizing = true;
        resizer.classList.add("active");
        document.body.classList.add("dragging-chat");
    });

    window.addEventListener("touchmove", function(e) {
        if (!isResizing) return;
        if (e.touches.length === 0) return;
        e.preventDefault();
        scheduleWidthUpdate(e.touches[0].clientX);
    }, { passive: false });

    window.addEventListener("touchend", finishResize);
    window.addEventListener("touchcancel", finishResize);

    window.addEventListener("resize", () => {
        _applyChatWidth(getComputedStyle(document.documentElement).getPropertyValue("--chat-width"), true);
    });
}

const CHAT_UI_SCHEMA_VERSION = "1.1.0";
const CHAT_STORAGE_OPEN = "ui_drawer_open";
const CHAT_STORAGE_SCHEMA = "ui_schema_version";
const CHAT_STORAGE_HISTORY = "ui_chat_history";
const CHAT_STORAGE_PROVIDER = "ui_chat_provider";
const CHAT_STORAGE_MODEL_PREFIX = "ui_chat_model_";
const CHAT_MANAGED_STORAGE_KEYS = [
    CHAT_STORAGE_WIDTH,
    CHAT_STORAGE_OPEN,
    CHAT_STORAGE_HISTORY,
    CHAT_STORAGE_PROVIDER
];

function _getElementPath(el) {
    if (!el || el === document.body) return "body";
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && node !== document.body && parts.length < 6) {
        let part = node.tagName.toLowerCase();
        if (node.id) {
            part += `#${node.id}`;
            parts.unshift(part);
            break;
        }
        const className = Array.from(node.classList || []).slice(0, 2).join(".");
        if (className) {
            part += `.${className}`;
        }
        const parent = node.parentElement;
        if (parent) {
            const siblings = Array.from(parent.children).filter(child => child.tagName === node.tagName);
            if (siblings.length > 1) {
                part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
            }
        }
        parts.unshift(part);
        node = parent;
    }
    return parts.join(" > ") || "body";
}

function _getCodeSourceFromElement(el) {
    const traced = el?.closest?.("[data-code-src]");
    if (traced) return traced.dataset.codeSrc || "";
    return document.body?.dataset?.template || "templates/index.html";
}

export class ChatUIManager {
    constructor() {
        this.drawer = document.getElementById("chat-drawer");
        this.messages = document.getElementById("chat-messages");
        this.input = document.getElementById("chat-input");
        this.modelBar = document.getElementById("chat-model-bar");
        this.contextBar = null;
        this.contextToast = null;
        this.fileTray = null;
        this.dropOverlay = null;
        this.contextMenu = null;
        this.feedbackModal = null;
        this.messageObserver = null;
    }

    init() {
        if (!this.drawer) return;
        if (this.drawer.dataset.chatUiManagerBound === "true") return;
        this.drawer.dataset.chatUiManagerBound = "true";

        this._ensureStorageSchema();
        this._ensureContextMeter();
        this._ensureContextToast();
        this._ensureFileChipTray();
        this._ensureDropOverlay();
        this._ensureContextFeedbackUI();
        this._restoreHistory();
        this._restoreWidth();
        this._restoreOpenState();
        _loadModels();
        this._bindEvents();
        this.updateContextMeter();
        initChatResizer();
    }

    syncOpenState(isOpen) {
        if (!this.drawer) return;
        this.drawer.classList.toggle("open", isOpen);
        if (window.innerWidth > 768) {
            document.body.classList.toggle("chat-drawer-open", isOpen);
        } else {
            document.body.classList.remove("chat-drawer-open");
        }
        localStorage.setItem(CHAT_STORAGE_OPEN, isOpen ? "true" : "false");
        this._syncToggleIcons(isOpen);
        this.updateContextMeter();
    }

    saveHistory() {
        if (!this.messages) return;
        const history = _getChatHistory().slice(-80);
        localStorage.setItem(CHAT_STORAGE_HISTORY, JSON.stringify(history));
        this.updateContextMeter();
    }

    updateContextMeter() {
        if (!this.contextBar) return;

        let contextText = "";
        try {
            contextText = _scrapeCurrentScreenText();
        } catch (err) {
            contextText = "";
        }

        const historyText = _getChatHistory()
            .map(item => item.content)
            .join("\n");
        const inputText = this.input ? this.input.value : "";
        const stagedText = _getStagedFilesRaw();
        const estimatedTokens = _estimateTokens(contextText + historyText + inputText + stagedText);
        const rawPercent = (estimatedTokens / CHAT_CONTEXT_MAX_TOKENS) * 100;
        const saturation = Math.min(100, Math.round(rawPercent));

        let color = "#2ecc71";
        let heightPx = 1 + Math.min(3, Math.max(0, rawPercent) / 100 * 3);
        let critical = false;
        if (rawPercent > 100) {
            color = "#c0392b";
            heightPx = 6;
            critical = true;
        } else if (saturation > 75) {
            color = "#e74c3c";
            critical = true;
        } else if (saturation > 40) {
            color = "#f1c40f";
        }
        const height = `${Math.round(heightPx * 10) / 10}px`;

        if (this.input) {
            this.input.disabled = false;
            if (rawPercent > 95) {
                this.input.placeholder = "Напишіть повідомлення...";
                this._showContextToast(estimatedTokens, rawPercent);
            } else {
                this.input.placeholder = "Напишіть повідомлення...";
                chatContextWarningShown = false;
                this._hideContextToast();
            }
        }

        this.contextBar.parentElement.style.height = height;
        this.contextBar.style.width = `${saturation}%`;
        this.contextBar.style.background = color;
        this.contextBar.style.height = height;
        this.contextBar.classList.toggle("chat-context-critical", critical);
        this.contextBar.parentElement.title = `Context load: ${saturation}% (${estimatedTokens.toLocaleString()} estimated tokens)`;
    }

    _ensureStorageSchema() {
        const storedVersion = localStorage.getItem(CHAT_STORAGE_SCHEMA);
        if (storedVersion && storedVersion !== CHAT_UI_SCHEMA_VERSION) {
            CHAT_MANAGED_STORAGE_KEYS.forEach(key => localStorage.removeItem(key));
            Object.keys(localStorage)
                .filter(key => key.startsWith(CHAT_STORAGE_MODEL_PREFIX))
                .forEach(key => localStorage.removeItem(key));
        }
        localStorage.setItem(CHAT_STORAGE_SCHEMA, CHAT_UI_SCHEMA_VERSION);
    }

    _ensureContextMeter() {
        if (document.getElementById("chat-context-meter")) {
            this.contextBar = document.getElementById("chat-context-bar");
            return;
        }
        if (!this.modelBar) return;

        const meter = document.createElement("div");
        meter.className = "chat-context-meter";
        meter.id = "chat-context-meter";

        const bar = document.createElement("div");
        bar.id = "chat-context-bar";
        meter.appendChild(bar);

        this.modelBar.insertAdjacentElement("afterend", meter);
        this.contextBar = bar;
    }

    _ensureContextToast() {
        if (document.getElementById("chat-context-toast")) {
            this.contextToast = document.getElementById("chat-context-toast");
            return;
        }
        const meter = document.getElementById("chat-context-meter");
        if (!meter) return;

        const toast = document.createElement("div");
        toast.className = "chat-context-toast";
        toast.id = "chat-context-toast";
        toast.hidden = true;
        meter.appendChild(toast);
        this.contextToast = toast;
    }

    _ensureFileChipTray() {
        if (!this.input || document.getElementById("chat-file-chips")) return;
        const tray = document.createElement("div");
        tray.className = "chat-file-chips";
        tray.id = "chat-file-chips";
        tray.hidden = true;
        this.input.insertAdjacentElement("beforebegin", tray);
        this.fileTray = tray;
    }

    _ensureDropOverlay() {
        if (!this.drawer || document.getElementById("chat-drop-overlay")) return;
        const overlay = document.createElement("div");
        overlay.className = "chat-drop-overlay";
        overlay.id = "chat-drop-overlay";
        overlay.innerHTML = `<div><i class="fa-solid fa-file-arrow-up"></i><span>Drop text file</span></div>`;
        this.drawer.appendChild(overlay);
        this.dropOverlay = overlay;
    }

    _ensureContextFeedbackUI() {
        if (document.getElementById("context-feedback-menu")) return;

        const menu = document.createElement("div");
        menu.className = "context-feedback-menu";
        menu.id = "context-feedback-menu";
        menu.hidden = true;
        menu.innerHTML = `
            <button type="button" data-feedback-type="bug"><i class="fa-solid fa-bug"></i><span>Bug</span></button>
            <button type="button" data-feedback-type="feature"><i class="fa-solid fa-lightbulb"></i><span>Feature</span></button>
        `;

        const modal = document.createElement("div");
        modal.className = "context-feedback-modal";
        modal.id = "context-feedback-modal";
        modal.hidden = true;
        modal.innerHTML = `
            <div class="context-feedback-dialog">
                <div class="context-feedback-head">
                    <strong>Context feedback</strong>
                    <button type="button" data-feedback-close title="Close"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div class="context-feedback-meta" id="context-feedback-meta"></div>
                <div class="context-feedback-types">
                    <label><input type="radio" name="context-feedback-type" value="bug"> Bug</label>
                    <label><input type="radio" name="context-feedback-type" value="feature"> Feature</label>
                </div>
                <textarea id="context-feedback-desc" rows="4" placeholder="What should change?"></textarea>
                <button type="button" id="context-feedback-send" disabled>Send</button>
            </div>
        `;

        document.body.appendChild(menu);
        document.body.appendChild(modal);
        this.contextMenu = menu;
        this.feedbackModal = modal;
    }

    _restoreWidth() {
        const storedWidth = localStorage.getItem(CHAT_STORAGE_WIDTH);
        if (storedWidth) {
            _applyChatWidth(storedWidth, true);
        }
    }

    _restoreOpenState() {
        const shouldOpen = localStorage.getItem(CHAT_STORAGE_OPEN) === "true";
        this.syncOpenState(shouldOpen);
    }

    _restoreHistory() {
        if (!this.messages || this.messages.children.length > 0) return;
        let history = [];
        try {
            history = JSON.parse(localStorage.getItem(CHAT_STORAGE_HISTORY) || "[]");
        } catch (err) {
            history = [];
        }
        if (!Array.isArray(history)) return;

        history.forEach(item => {
            if (!item || !item.role || !item.content) return;
            _appendChatBubble(this.messages, item.role, item.content);
        });
        this.messages.scrollTop = this.messages.scrollHeight;
    }

    _syncToggleIcons(isOpen) {
        const openBtn = document.getElementById("chat-open-btn");
        const toggleBtn = document.getElementById("chat-toggle-btn");
        const toggleIcon = document.getElementById("chat-toggle-icon");
        const collapseBtn = document.getElementById("chat-collapse-btn");
        if (openBtn) {
            openBtn.hidden = isOpen;
            openBtn.title = isOpen ? "Чат відкрито" : "Розгорнути чат";
        }
        if (toggleBtn) {
            toggleBtn.title = "Додати поточний екран у чат";
        }
        if (toggleIcon) {
            toggleIcon.className = "fa-solid fa-wand-magic-sparkles";
        }
        if (collapseBtn) {
            collapseBtn.title = "Згорнути чат";
        }
    }

    _bindEvents() {
        window.addEventListener("resize", () => {
            _applyChatWidth(getComputedStyle(document.documentElement).getPropertyValue("--chat-width"), true);
            this.syncOpenState(this.drawer.classList.contains("open"));
        });

        if (this.input) {
            this.input.addEventListener("input", () => this.updateContextMeter());
        }

        this._bindDragDrop();
        this._bindContextFeedback();

        if (this.messages && window.MutationObserver) {
            this.messageObserver = new MutationObserver(() => this.updateContextMeter());
            this.messageObserver.observe(this.messages, {
                childList: true,
                subtree: true,
                characterData: true
            });
        }
    }

    _bindDragDrop() {
        if (!this.drawer || this.drawer.dataset.chatDropBound === "true") return;
        this.drawer.dataset.chatDropBound = "true";

        const showOverlay = (event) => {
            event.preventDefault();
            if (this.dropOverlay) this.dropOverlay.style.display = "flex";
        };
        const hideOverlay = () => {
            if (this.dropOverlay) this.dropOverlay.style.display = "none";
        };

        this.drawer.addEventListener("dragenter", showOverlay);
        this.drawer.addEventListener("dragover", showOverlay);
        this.drawer.addEventListener("dragleave", (event) => {
            if (!this.drawer.contains(event.relatedTarget)) hideOverlay();
        });
        this.drawer.addEventListener("drop", (event) => {
            event.preventDefault();
            hideOverlay();
            const files = Array.from(event.dataTransfer?.files || []);
            files.forEach(file => {
                const looksText = file.type.startsWith("text/") || /\.(txt|md|csv|json|log)$/i.test(file.name);
                if (!looksText) return;
                const reader = new FileReader();
                reader.onload = () => {
                    const content = String(reader.result || "");
                    CHAT_STAGED_FILES.push({
                        name: file.name,
                        content,
                        tokens: _estimateTokens(content)
                    });
                    _renderStagedFileChips();
                    this.updateContextMeter();
                };
                reader.readAsText(file);
            });
        });
    }

    _bindContextFeedback() {
        if (document.body.dataset.contextFeedbackBound === "true") return;
        document.body.dataset.contextFeedbackBound = "true";

        const stateObj = {
            el: "",
            src: "",
            type: ""
        };

        const closeMenu = () => {
            if (this.contextMenu) this.contextMenu.hidden = true;
        };
        const closeModal = () => {
            if (this.feedbackModal) this.feedbackModal.hidden = true;
        };
        const validate = () => {
            const descEl = document.getElementById("context-feedback-desc");
            const sendBtn = document.getElementById("context-feedback-send");
            const checked = document.querySelector("input[name='context-feedback-type']:checked");
            if (!sendBtn || !descEl) return;
            sendBtn.disabled = !(descEl.value.trim().length > 0 && checked);
        };
        const openModal = (type) => {
            stateObj.type = type || stateObj.type || "bug";
            const metaEl = document.getElementById("context-feedback-meta");
            const descEl = document.getElementById("context-feedback-desc");
            const typeInput = document.querySelector(`input[name='context-feedback-type'][value='${stateObj.type}']`);
            if (metaEl) metaEl.textContent = `${stateObj.el} · ${stateObj.src}`;
            if (descEl) descEl.value = "";
            if (typeInput) typeInput.checked = true;
            if (this.feedbackModal) this.feedbackModal.hidden = false;
            validate();
        };

        document.addEventListener("contextmenu", (event) => {
            const tagName = event.target?.tagName?.toLowerCase();
            if (["input", "textarea", "select", "option"].includes(tagName)) return;
            stateObj.el = _getElementPath(event.target);
            stateObj.src = _getCodeSourceFromElement(event.target);
            if (!this.contextMenu) return;
            this.contextMenu.hidden = false;
            const menuWidth = this.contextMenu.offsetWidth || 132;
            const menuHeight = this.contextMenu.offsetHeight || 80;
            const left = Math.max(8, event.clientX - menuWidth - 12);
            const top = Math.min(
                Math.max(8, event.clientY),
                Math.max(8, window.innerHeight - menuHeight - 8)
            );
            this.contextMenu.style.left = `${left}px`;
            this.contextMenu.style.top = `${top}px`;
        });

        document.addEventListener("click", (event) => {
            const typeBtn = event.target.closest?.("[data-feedback-type]");
            if (typeBtn) {
                closeMenu();
                openModal(typeBtn.dataset.feedbackType);
                return;
            }
            if (event.target.closest?.("[data-feedback-close]")) {
                closeModal();
                return;
            }
            if (event.target.id === "context-feedback-send") {
                this._submitContextFeedback(stateObj).then(closeModal);
                return;
            }
            if (this.contextMenu && !event.target.closest?.("#context-feedback-menu")) {
                closeMenu();
            }
        });

        document.addEventListener("input", (event) => {
            if (event.target.id === "context-feedback-desc") validate();
        });
        document.addEventListener("change", (event) => {
            if (event.target.name === "context-feedback-type") {
                stateObj.type = event.target.value;
                validate();
            }
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closeMenu();
                closeModal();
            }
        });
    }

    async _submitContextFeedback(stateObj) {
        const descEl = document.getElementById("context-feedback-desc");
        const checked = document.querySelector("input[name='context-feedback-type']:checked");
        const desc = descEl ? descEl.value.trim() : "";
        const type = checked ? checked.value : stateObj.type;
        if (!desc || !type) return;

        try {
            await adminFetch("/api/proposals/submit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    type,
                    el: stateObj.el,
                    src: stateObj.src,
                    desc
                })
            });
        } catch (err) {
            console.warn("[feedback] proposal submit failed:", err);
        }
    }

    _showContextToast(estimatedTokens, rawPercent) {
        if (!this.contextToast) return;
        const percentText = Math.round(rawPercent);
        this.contextToast.textContent = `Context ${percentText}% (${estimatedTokens.toLocaleString()} tok). Remove files or clear history.`;
        this.contextToast.hidden = false;
        chatContextWarningShown = true;
    }

    _hideContextToast() {
        if (this.contextToast) this.contextToast.hidden = true;
    }
}

export function initChatUIManager() {
    if (!window.chatUIManager) {
        window.chatUIManager = new ChatUIManager();
    }
    window.chatUIManager.init();
    return window.chatUIManager;
}

document.addEventListener("DOMContentLoaded", () => {
    initChatUIManager();
});

export function openAddSourceModal() {
    const modal = document.getElementById("add-source-modal");
    if (modal) modal.style.display = "flex";
}

export function closeAddSourceModal() {
    const modal = document.getElementById("add-source-modal");
    if (modal) {
        modal.style.display = "none";
        document.getElementById("add-source-form")?.reset();
    }
}

export async function submitAddSource(event) {
    event.preventDefault();
    const name = document.getElementById("as-name")?.value;
    const type = document.getElementById("as-type")?.value;
    const policy_tier = document.getElementById("as-tier")?.value;
    const status = document.getElementById("as-status")?.value;
    const credentials = document.getElementById("as-credentials")?.value || null;
    const source_url = document.getElementById("as-url")?.value || null;
    const retention_days = document.getElementById("as-retention")?.value
        ? parseInt(document.getElementById("as-retention").value, 10)
        : null;
    const policy_notes = document.getElementById("as-notes")?.value || null;

    try {
        const payload = { name, type, policy_tier, status, credentials, source_url, retention_days, policy_notes };
        const res = await adminFetch("/api/sources", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            window.alert(data.error || "Failed to create source.");
            return;
        }

        window.alert(state.currentLang === "ua" ? "Джерело успішно додано!" : "Source registered successfully!");
        closeAddSourceModal();
        loadOperatorRuntimePanel();
        if (window.loadBriefSources) window.loadBriefSources();
    } catch (err) {
        console.error("Failed to add source:", err);
        window.alert("Error connecting to server.");
    }
}

export async function deleteSource(sourceId) {
    const confirmMsg = state.currentLang === "ua"
        ? "Ви впевнені, що хочете видалити це джерело?"
        : "Are you sure you want to delete this source?";
    if (!window.confirm(confirmMsg)) return;

    try {
        const res = await adminFetch(`/api/sources/${sourceId}`, {
            method: "DELETE"
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            window.alert(data.error || "Failed to delete source.");
            return;
        }

        window.alert(state.currentLang === "ua" ? "Джерело видалено!" : "Source deleted successfully!");
        loadOperatorRuntimePanel();
        if (window.loadBriefSources) window.loadBriefSources();
    } catch (err) {
        console.error("Failed to delete source:", err);
        window.alert("Error connecting to server.");
    }
}

export function prepareIngestSource(sourceId, options = {}) {
    const select = document.getElementById("operator-ingest-source");
    const input = document.getElementById("operator-ingest-input");
    const format = document.getElementById("operator-ingest-format");
    const help = document.getElementById("operator-ingest-help");
    const result = document.getElementById("operator-ingest-result");
    if (!select || !input) return false;

    const source = _findOperatorSource(sourceId);
    if (!source) return false;
    select.value = String(source.id);
    if (format) {
        format.disabled = source.type !== "manual";
        format.value = "json";
    }
    if (!options.preserveInput) {
        input.value = "";
    }
    input.placeholder = _connectorHelp(source);
    if (help) {
        help.textContent = _renderConnectorSummary(source) || _connectorHelp(source);
    }
    if (result && !options.preserveInput) {
        result.innerHTML = `<div class="operator-empty">${escapeHtml(_connectorHelp(source))}</div>`;
    }
    if (options.focus !== false) {
        document.getElementById("operator-ingest-console")?.scrollIntoView({ behavior: "smooth", block: "start" });
        input.focus({ preventScroll: true });
    }
    return false;
}

function _ingestLimit() {
    const el = document.getElementById("operator-ingest-limit");
    const value = Number.parseInt(el?.value || "20", 10);
    if (!Number.isFinite(value)) return 20;
    return Math.max(1, Math.min(100, value));
}

function _parseOperatorJsonInput(raw) {
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Connector JSON input must be an object.");
    }
    return parsed;
}

function _buildIngestionPayload({ persist = false } = {}) {
    const select = document.getElementById("operator-ingest-source");
    const input = document.getElementById("operator-ingest-input");
    const format = document.getElementById("operator-ingest-format");
    const allowTierE = document.getElementById("operator-ingest-allow-tier-e");
    const source = _findOperatorSource(select?.value);
    if (!source) {
        throw new Error("Select a registered source before running ingestion.");
    }

    const raw = (input?.value || "").trim();
    const payload = {
        source_id: source.id,
        preview_limit: _ingestLimit(),
        persist: Boolean(persist),
    };
    if (allowTierE?.checked) {
        payload.allow_tier_e = true;
    }

    if (source.type === "manual") {
        if (!raw) {
            throw new Error("Manual ingestion requires JSON or CSV input.");
        }
        payload.input = {
            text: raw,
            fmt: format?.value || "json",
        };
        return payload;
    }

    if (source.type === "rss") {
        if (raw) {
            payload.input = raw.startsWith("<")
                ? { xml_text: raw }
                : { url: raw };
        }
        return payload;
    }

    if (source.type === "youtube") {
        payload.input = raw ? _parseOperatorJsonInput(raw) : {};
        if (!payload.input.limit) {
            payload.input.limit = _ingestLimit();
        }
        return payload;
    }

    payload.input = raw ? _parseOperatorJsonInput(raw) : {};
    return payload;
}

function _setIngestionBusy(isBusy, label = "Working...") {
    const preview = document.getElementById("operator-ingest-preview");
    const persist = document.getElementById("operator-ingest-persist");
    const result = document.getElementById("operator-ingest-result");
    [preview, persist].forEach(btn => {
        if (btn) btn.disabled = isBusy;
    });
    if (isBusy && result) {
        result.innerHTML = `<div class="operator-empty">${escapeHtml(label)}</div>`;
    }
}

function _renderIngestionResult(data) {
    const target = document.getElementById("operator-ingest-result");
    if (!target) return;

    const summary = data?.summary || {};
    const records = data?.records || [];
    const warnings = data?.warnings || [];
    const rejected = data?.rejected || [];
    const status = data?.persisted ? "Persisted" : "Dry-run preview";
    const recordCards = records.length
        ? records.slice(0, 10).map(record => `
            <article class="operator-ingest-record">
                <strong>${escapeHtml(record.title || "Untitled record")}</strong>
                <span>${escapeHtml(record.url || "No URL")}</span>
                <span>${escapeHtml(record.published_at || "No published date")}</span>
            </article>
        `).join("")
        : `<div class="operator-empty">No normalized records returned.</div>`;
    const warningBlock = warnings.length
        ? `<div class="operator-ingest-warnings"><strong>Warnings:</strong> ${escapeHtml(warnings.join(" | "))}</div>`
        : "";
    const rejectedBlock = rejected.length
        ? `<div class="operator-ingest-warnings"><strong>Rejected:</strong> ${escapeHtml(rejected.map(item => `#${item.row_number}: ${item.reason}`).join(" | "))}</div>`
        : "";

    target.innerHTML = `
        <div class="operator-ingest-summary">
            <span>${escapeHtml(status)}</span>
            <span>Seen: ${escapeHtml(summary.records_seen ?? 0)}</span>
            <span>Created: ${escapeHtml(summary.records_created ?? data?.records_created ?? 0)}</span>
            <span>Failed: ${escapeHtml(summary.records_failed ?? 0)}</span>
            <span>Run ID: ${escapeHtml(data?.connector_run_id || "-")}</span>
        </div>
        ${warningBlock}
        ${rejectedBlock}
        <div class="operator-ingest-records">${recordCards}</div>
    `;
}

async function _runIngestion({ persist = false } = {}) {
    let payload;
    try {
        payload = _buildIngestionPayload({ persist });
    } catch (err) {
        _renderIngestionResult({
            summary: { records_seen: 0, records_created: 0, records_failed: 1 },
            warnings: [err.message || "Invalid ingestion input."],
            records: [],
        });
        return null;
    }

    _setIngestionBusy(true, persist ? "Persisting connector records..." : "Running dry-run preview...");
    try {
        const res = await adminFetch("/api/sources/ingest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            throw new Error(data.error || `Ingestion failed: HTTP ${res.status}`);
        }
        _renderIngestionResult(data);
        if (persist) {
            loadOperatorRuntimePanel();
            if (window.loadBriefSources) window.loadBriefSources();
        }
        return data;
    } catch (err) {
        console.error("Ingestion failed:", err);
        _renderIngestionResult({
            summary: { records_seen: 0, records_created: 0, records_failed: 1 },
            warnings: [err.message || "Error connecting to server."],
            records: [],
        });
        return null;
    } finally {
        _setIngestionBusy(false);
    }
}

export async function runIngestionPreview() {
    return _runIngestion({ persist: false });
}

export async function runIngestionPersist() {
    return _runIngestion({ persist: true });
}

export async function runIngest(sourceId) {
    prepareIngestSource(sourceId, { focus: true, preserveInput: true });
    return runIngestionPreview();
}
