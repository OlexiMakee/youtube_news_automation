import { state } from './state.js';
import { translations } from './translations.js';
import { adminFetch, adminFetchSilent, ensureAdminSession } from './auth.js';

export function initTerminal() {
    const container = document.getElementById("xterm-container");
    if (!container) return;
    
    if (state.termInitialized) {
        // Just fit the terminal if already initialized
        if (state.fitAddon) {
            setTimeout(() => {
                try {
                    state.fitAddon.fit();
                    sendTerminalResize(state.term.cols, state.term.rows);
                } catch(e) {
                    console.error("Xterm fit failed:", e);
                }
            }, 80);
        }
        return;
    }
    
    state.termInitialized = true;
    
    // Create xterm Terminal instance from window global
    state.term = new window.Terminal({
        cursorBlink: true,
        fontFamily: 'Courier New, Courier, monospace',
        fontSize: 13,
        theme: {
            background: '#0d1117',
            foreground: '#c9d1d9',
            cursor: '#58a6ff',
            selection: '#33b3ae33',
            black: '#000000',
            red: '#ff5555',
            green: '#2ea44f',
            yellow: '#f1fa8c',
            blue: '#58a6ff',
            magenta: '#ff79c6',
            cyan: '#39d353',
            white: '#bfbfbf'
        }
    });
    
    state.fitAddon = new window.FitAddon.FitAddon();
    state.term.loadAddon(state.fitAddon);
    state.term.open(container);
    
    // Attach custom key event handler to intercept Ctrl+Q (Ctrl+q)
    state.term.attachCustomKeyEventHandler((event) => {
        if (event.ctrlKey && event.key.toLowerCase() === 'q') {
            const confirmMsg = state.currentLang === 'ua' 
                ? "Ви впевнені, що хочете зупинити сервер і завершити процес?" 
                : "Are you sure you want to stop the server and terminate the process?";
            if (confirm(confirmMsg)) {
                adminFetch('/api/action/shutdown', { method: 'POST' })
                    .then(() => {
                        const alertMsg = state.currentLang === 'ua'
                            ? "Сервер зупинено. Цю вкладку можна закрити."
                            : "Server stopped. You can close this tab now.";
                        alert(alertMsg);
                    })
                    .catch(err => {
                        console.error("Shutdown request failed:", err);
                    });
            }
            return false; // Prevent sending Ctrl+Q to PTY
        }
        return true;
    });
    
    // Fit to container dimensions
    setTimeout(() => {
        try {
            state.fitAddon.fit();
            sendTerminalResize(state.term.cols, state.term.rows);
        } catch(e) {
            console.error("Xterm initial fit failed:", e);
        }
    }, 150);
    
    // Setup resize hook
    window.addEventListener('resize', () => {
        if (state.fitAddon && state.term) {
            try {
                state.fitAddon.fit();
                sendTerminalResize(state.term.cols, state.term.rows);
            } catch (e) {}
        }
    });
    
    // Capture user keyboard input and send to PTY
    state.term.onData(data => {
        sendTerminalInput(data);
    });
    
    // Connect output stream
    connectTerminalStream();
}

export async function connectTerminalStream() {
    if (!(await ensureAdminSession())) return;

    if (state.termEventSource) {
        state.termEventSource.close();
    }
    
    const badge = document.getElementById("terminal-status-badge");
    if (badge) {
        badge.classList.remove("active");
        badge.innerText = state.currentLang === "ua" ? "ПІДКЛЮЧЕННЯ..." : "CONNECTING...";
    }
    
    state.termEventSource = new EventSource("/api/terminal/stream");
    
    state.termEventSource.onopen = () => {
        if (badge) {
            badge.classList.add("active");
            badge.innerText = state.currentLang === "ua" ? "АКТИВНИЙ" : "ACTIVE";
        }
    };
    
    state.termEventSource.onmessage = (event) => {
        // Decode base64 bytes to utf-8 string cleanly
        try {
            const binaryString = window.atob(event.data);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            state.term.write(bytes);
        } catch (e) {
            console.error("Failed to decode terminal output:", e);
        }
    };
    
    state.termEventSource.onerror = (err) => {
        console.error("Terminal SSE connection error:", err);
        if (badge) {
            badge.classList.remove("active");
            badge.innerText = state.currentLang === "ua" ? "РОЗ'ЄДНАНО" : "DISCONNECTED";
        }
    };
}

export async function sendTerminalInput(dataString) {
    try {
        await adminFetch("/api/terminal/input", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ input: dataString })
        });
    } catch (e) {
        console.error("Failed to send terminal input:", e);
    }
}

export async function sendTerminalResize(cols, rows) {
    try {
        await adminFetchSilent("/api/terminal/resize", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ cols, rows })
        });
    } catch (e) {
        console.error("Failed to send terminal resize:", e);
    }
}

// Injects command into terminal
export function injectCommand(cmd) {
    // Hide any open dropdowns
    document.querySelectorAll(".term-dropdown-menu").forEach(menu => {
        menu.style.display = "none";
    });
    
    // Focus terminal window
    if (state.term) {
        state.term.focus();
    }
    
    // Write command to terminal stdin
    sendTerminalInput(cmd);
}

// Dropdown toggle
export function toggleDropdown(event, menuId) {
    event.stopPropagation();
    const menu = document.getElementById(menuId);
    if (!menu) return;
    
    const wasVisible = menu.style.display === "block";
    
    // Hide all dropdowns
    document.querySelectorAll(".term-dropdown-menu").forEach(m => {
        m.style.display = "none";
    });
    
    if (!wasVisible) {
        menu.style.display = "block";
    }
}
