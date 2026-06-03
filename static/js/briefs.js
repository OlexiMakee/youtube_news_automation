import { state } from './state.js';
import { adminFetch, adminFetchSilent } from './auth.js';

let activeBriefId = null;

function briefText(key, fallback) {
    const dict = {
        copy_brief: {
            ua: "Копіювати",
            en: "Copy",
        },
        copied: {
            ua: "Дайджест скопійовано в буфер.",
            en: "Brief copied to clipboard.",
        },
        copy_failed: {
            ua: "Не вдалося скопіювати дайджест.",
            en: "Failed to copy brief.",
        },
    };
    return dict[key]?.[state.currentLang] || dict[key]?.en || fallback;
}

export async function loadBriefs() {
    const list = document.getElementById("briefs-history-list");
    if (!list) return;

    try {
        const res = await adminFetchSilent("/api/briefs");
        const data = await res.json();
        
        if (!res.ok || data.error) {
            list.innerHTML = `<div class="operator-empty">Failed to load briefs.</div>`;
            return;
        }

        if (!data.registry_ready) {
            list.innerHTML = `<div class="operator-empty">Governance registry pending. Please apply migration.</div>`;
            return;
        }

        if (!data.briefs || data.briefs.length === 0) {
            const emptyLabel = state.currentLang === "ua" ? "Дайджести ще не створювалися." : "No briefs generated yet.";
            list.innerHTML = `<div class="operator-empty">${emptyLabel}</div>`;
            return;
        }

        list.innerHTML = data.briefs.map(b => {
            const dateStr = b.created_at ? b.created_at.substring(0, 19).replace('T', ' ') : 'no date';
            return `
                <article class="operator-source-row" style="cursor: pointer; padding: 10px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-color);" onclick="viewBriefDetails(${b.id})">
                    <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
                        <div style="display: flex; flex-direction: column; gap: 4px;">
                            <strong style="color: var(--text-color); font-size: 13px;">${escapeHtml(b.title || 'Untitled Brief')}</strong>
                            <span style="font-size: 11px; color: var(--text-muted);">${dateStr} | Status: ${escapeHtml(b.status)}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <button class="btn-secondary brief-row-copy-btn" type="button" onclick="event.stopPropagation(); copyBriefMarkdown(${b.id})" title="${escapeHtml(briefText("copy_brief", "Copy"))}">
                                <i class="fa-solid fa-copy"></i>
                            </button>
                            <i class="fa-solid fa-chevron-right" style="color: var(--text-muted); font-size: 12px;"></i>
                        </div>
                    </div>
                </article>
            `;
        }).join("");

    } catch (err) {
        console.error("Failed to load briefs list:", err);
        list.innerHTML = `<div class="operator-empty">Error loading briefs history.</div>`;
    }
}

export async function loadBriefSources() {
    const selector = document.getElementById("brief-sources-selector");
    if (!selector) return;

    try {
        const res = await adminFetchSilent("/api/sources");
        const data = await res.json();
        
        const allLabel = state.currentLang === "ua" ? "Всі джерела" : "All Sources";
        selector.innerHTML = `<option value="">${allLabel}</option>`;

        if (res.ok && data.registry_ready && data.sources) {
            data.sources.forEach(src => {
                const opt = document.createElement("option");
                opt.value = src.id;
                opt.textContent = `${src.name} (${src.type})`;
                selector.appendChild(opt);
            });
        }
    } catch (err) {
        console.error("Failed to load brief sources:", err);
    }
}

export async function generateDailyBrief() {
    const dateInput = document.getElementById("brief-date-picker");
    const sourceSelector = document.getElementById("brief-sources-selector");
    const badge = document.getElementById("brief-badge");

    if (!dateInput) return;
    const date = dateInput.value;
    if (!date) {
        const alertMsg = state.currentLang === "ua" ? "Будь ласка, оберіть дату." : "Please select a date.";
        window.alert(alertMsg);
        return;
    }

    const selectedSource = sourceSelector ? sourceSelector.value : "";
    let url = `/api/briefs/generate?date=${date}`;
    if (selectedSource) {
        url += `&sources=${selectedSource}`;
    }

    if (badge) {
        badge.className = "task-badge active";
        badge.innerText = state.currentLang === "ua" ? "ГЕНЕРАЦІЯ" : "GENERATING";
        badge.style.display = "inline-block";
    }

    try {
        const res = await adminFetch(url, { method: "POST" });
        const data = await res.json();

        if (badge) badge.style.display = "none";

        if (!res.ok || data.error) {
            window.alert(data.error || "Failed to generate brief.");
            return;
        }

        const successMsg = state.currentLang === "ua" ? "Дайджест успішно згенеровано!" : "Brief generated successfully!";
        window.alert(successMsg);
        loadBriefs();
    } catch (err) {
        if (badge) badge.style.display = "none";
        console.error("Failed to generate brief:", err);
        window.alert("Connection error during brief generation.");
    }
}

export async function viewBriefDetails(briefId) {
    const modal = document.getElementById("brief-details-modal");
    const title = document.getElementById("brief-modal-title");
    const content = document.getElementById("brief-modal-content-container");
    const evidenceContainer = document.getElementById("brief-modal-evidence-container");

    if (!modal || !content) return;

    activeBriefId = briefId;
    content.innerText = "Loading details...";
    if (evidenceContainer) evidenceContainer.innerHTML = "";
    modal.style.display = "flex";

    try {
        const res = await adminFetch(`/api/briefs/${briefId}`);
        const data = await res.json();

        if (!res.ok || data.error) {
            content.innerText = data.error || "Failed to load brief details.";
            return;
        }

        const brief = data.brief;
        if (title) title.textContent = brief.title || `Brief #${briefId}`;
        content.innerText = brief.content_text || "No content.";

        if (evidenceContainer) {
            if (brief.claims && brief.claims.length > 0) {
                evidenceContainer.innerHTML = brief.claims.map((c, i) => {
                    const src = c.sources && c.sources[0] ? c.sources[0] : {};
                    return `
                        <div style="background: var(--bg-color); border: 1px solid var(--border-color); padding: 8px; border-radius: 6px; margin-bottom: 6px; font-size: 11px;">
                            <strong>Claim ${i + 1}:</strong> ${escapeHtml(c.text)}<br/>
                            <span style="color: var(--text-muted);">Source Reference: [${escapeHtml(src.source_name || "Unknown")}] <a href="${escapeHtml(src.url || '#')}" target="_blank" style="color: var(--yellow-color); text-decoration: underline;">${escapeHtml(src.title || 'Link')}</a></span>
                        </div>
                    `;
                }).join("");
            } else {
                evidenceContainer.innerHTML = `<div style="font-size: 11px; color: var(--text-muted);">No evidence links or claims configured.</div>`;
            }
        }

    } catch (err) {
        console.error("Failed to fetch brief details:", err);
        content.innerText = "Connection error while fetching details.";
    }
}

export function closeBriefModal() {
    const modal = document.getElementById("brief-details-modal");
    if (modal) modal.style.display = "none";
    activeBriefId = null;
}

export async function exportBriefFromModal(format) {
    if (!activeBriefId) return;

    try {
        const res = await adminFetch(`/api/briefs/${activeBriefId}/export?format=${format}`, {
            method: "POST"
        });
        
        if (!res.ok) {
            window.alert("Failed to export brief.");
            return;
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        
        let filename = `brief_${activeBriefId}.${format === 'markdown' ? 'md' : format}`;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (err) {
        console.error("Export brief failed:", err);
        window.alert("Connection error during brief export.");
    }
}

async function fetchBriefExportText(briefId, format = "markdown") {
    const res = await adminFetch(`/api/briefs/${briefId}/export?format=${format}`, {
        method: "POST"
    });
    if (!res.ok) {
        throw new Error(`Brief export failed: HTTP ${res.status}`);
    }
    return res.text();
}

async function writeClipboardText(text) {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
    }

    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.top = "0";
    document.body.appendChild(textarea);
    textarea.select();
    try {
        return document.execCommand("copy");
    } finally {
        document.body.removeChild(textarea);
    }
}

function showBriefCopyStatus(message, isError = false) {
    const status = document.getElementById("brief-copy-status");
    const modal = document.getElementById("brief-details-modal");
    if (status && modal?.style.display !== "none") {
        status.hidden = false;
        status.textContent = message;
        status.className = `brief-copy-status${isError ? " error" : ""}`;
        window.setTimeout(() => {
            status.hidden = true;
        }, 2600);
        return;
    }
    window.alert(message);
}

export async function copyBriefMarkdown(briefId) {
    try {
        const text = await fetchBriefExportText(briefId, "markdown");
        const copied = await writeClipboardText(text);
        if (!copied) {
            throw new Error("Clipboard command returned false.");
        }
        showBriefCopyStatus(briefText("copied", "Brief copied to clipboard."));
        return text;
    } catch (err) {
        console.error("Copy brief failed:", err);
        showBriefCopyStatus(briefText("copy_failed", "Failed to copy brief."), true);
        return null;
    }
}

export async function copyBriefMarkdownFromModal() {
    if (!activeBriefId) return null;
    return copyBriefMarkdown(activeBriefId);
}

// Helpers
function escapeHtml(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Bind to window for HTML inline invocation
window.viewBriefDetails = viewBriefDetails;
window.closeBriefModal = closeBriefModal;
window.exportBriefFromModal = exportBriefFromModal;
window.copyBriefMarkdown = copyBriefMarkdown;
window.copyBriefMarkdownFromModal = copyBriefMarkdownFromModal;
window.generateDailyBrief = generateDailyBrief;
window.loadBriefs = loadBriefs;
window.loadBriefSources = loadBriefSources;
