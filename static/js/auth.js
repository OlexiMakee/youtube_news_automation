import { state } from './state.js';

let authStatus = null;
let authStatusPromise = null;

function normalizeUiRole(status) {
    const role = String(status?.role || "user").toLowerCase();
    if (status?.admin || role === "admin" || role === "master_admin") return "admin";
    if (role === "analyst") return "analyst";
    return "reader";
}

function authText() {
    if (state.currentLang === "ua") {
        return {
            prompt: "Введіть адмін-токен для цієї дії. Токен не зберігається у браузері.",
            required: "Потрібна адмін-сесія.",
            denied: "Адмін-доступ не підтверджено."
        };
    }
    return {
        prompt: "Enter the admin token for this action. The token is not stored in the browser.",
        required: "Admin session required.",
        denied: "Admin access was not confirmed."
    };
}

export async function loadAuthStatus(force = false) {
    if (authStatus && !force) return authStatus;
    if (authStatusPromise && !force) return authStatusPromise;

    authStatusPromise = fetch("/api/auth/status", { credentials: "same-origin" })
        .then(async res => {
            const data = await res.json();
            authStatus = data;
            state.authStatus = data;
            state.userRole = normalizeUiRole(data);
            return data;
        })
        .finally(() => {
            authStatusPromise = null;
        });

    return authStatusPromise;
}

export async function ensureAdminSession(options = {}) {
    const shouldPrompt = options.prompt !== false;
    const status = await loadAuthStatus();
    if (!status.token_configured || status.admin) return true;
    if (!shouldPrompt) return false;

    const labels = authText();
    const token = window.prompt(labels.prompt);
    if (!token || !token.trim()) return false;

    const response = await fetch("/api/auth/session", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-Admin-Token": token.trim() }
    });

    if (!response.ok) {
        authStatus = null;
        window.alert(labels.denied);
        return false;
    }

    const nextStatus = await loadAuthStatus(true);
    return Boolean(nextStatus.admin);
}

function deniedResponse() {
    return new Response(JSON.stringify({ error: authText().required }), {
        status: 403,
        headers: { "Content-Type": "application/json" }
    });
}

export async function adminFetch(input, init = {}, options = {}) {
    if (!(await ensureAdminSession(options))) return deniedResponse();

    const requestInit = {
        ...init,
        credentials: init.credentials || "same-origin"
    };
    let response = await fetch(input, requestInit);
    if (response.status !== 403) return response;

    authStatus = null;
    if (!(await ensureAdminSession(options))) return response;
    response = await fetch(input, requestInit);
    return response;
}

export async function adminFetchSilent(input, init = {}) {
    return adminFetch(input, init, { prompt: false });
}

export async function openAdminUrl(url) {
    if (await ensureAdminSession()) {
        window.location.href = url;
        return true;
    }
    return false;
}
