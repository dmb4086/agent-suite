/* Agent Suite - Email Inbox Web UI */

(function () {
    "use strict";

    // ─── State ───────────────────────────────────────────────

    var state = {
        apiKey: localStorage.getItem("agent_suite_api_key") || "",
        messages: [],
        total: 0,
        currentPage: 0,
        pageSize: 50,
    };

    // ─── DOM References ──────────────────────────────────────

    var appEl = document.getElementById("app");
    var modalOverlay = document.getElementById("modal-overlay");
    var apiKeyInput = document.getElementById("api-key-input");
    var showKeyCheckbox = document.getElementById("show-key");
    var settingsBtn = document.getElementById("settings-btn");
    var saveKeyBtn = document.getElementById("save-key-btn");

    // ─── API Client ──────────────────────────────────────────

    var api = {
        request: function (path, options) {
            options = options || {};
            if (!state.apiKey) {
                return Promise.reject(
                    new Error("No API key configured. Click the gear icon to set your API key.")
                );
            }
            var headers = {
                Authorization: "Bearer " + state.apiKey,
                "Content-Type": "application/json",
            };
            if (options.headers) {
                Object.keys(options.headers).forEach(function (k) {
                    headers[k] = options.headers[k];
                });
            }
            return fetch(window.location.origin + path, {
                method: options.method || "GET",
                headers: headers,
                body: options.body || undefined,
            }).then(function (res) {
                if (!res.ok) {
                    return res.json().catch(function () {
                        return {};
                    }).then(function (data) {
                        throw new Error(data.detail || "Request failed (" + res.status + ")");
                    });
                }
                return res.json();
            });
        },

        getMessages: function (skip, limit) {
            skip = skip || 0;
            limit = limit || 50;
            return api.request(
                "/v1/inboxes/me/messages?skip=" + skip + "&limit=" + limit
            );
        },

        getInbox: function () {
            return api.request("/v1/inboxes/me");
        },

        sendEmail: function (to, subject, body) {
            return api.request("/v1/inboxes/me/send", {
                method: "POST",
                body: JSON.stringify({ to: to, subject: subject, body: body }),
            });
        },
    };

    // ─── Toast Notifications ─────────────────────────────────

    function showToast(message, type) {
        type = type || "success";
        var container = document.getElementById("toast-container");
        var toast = document.createElement("div");
        toast.className = "toast " + type;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(function () {
            toast.style.opacity = "0";
            toast.style.transition = "opacity 200ms";
            setTimeout(function () {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 200);
        }, 4000);
    }

    // ─── Utility ─────────────────────────────────────────────

    function formatDate(dateStr) {
        var d = new Date(dateStr);
        var now = new Date();
        var diff = now - d;
        if (diff < 60000) return "just now";
        if (diff < 3600000) return Math.floor(diff / 60000) + "m ago";
        if (diff < 86400000) return Math.floor(diff / 3600000) + "h ago";
        if (diff < 604800000) return Math.floor(diff / 86400000) + "d ago";
        return d.toLocaleDateString();
    }

    function escapeHtml(str) {
        if (!str) return "";
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    function truncate(str, len) {
        if (!str) return "";
        return str.length > len ? str.substring(0, len) + "..." : str;
    }

    // ─── Views ───────────────────────────────────────────────

    function renderLoading() {
        return '<div class="loading"><div class="spinner"></div> Loading...</div>';
    }

    function renderError(message) {
        return '<div class="error-banner">' + escapeHtml(message) + "</div>";
    }

    function renderNoApiKey() {
        return (
            '<div class="empty-state">' +
            '<div class="icon">&#128273;</div>' +
            "<h3>API Key Required</h3>" +
            '<p>Set your API key using the gear icon in the navigation bar to access your inbox.</p>' +
            "</div>"
        );
    }

    function renderEmptyInbox() {
        return (
            '<div class="empty-state">' +
            '<div class="icon">&#128235;</div>' +
            "<h3>No messages yet</h3>" +
            "<p>Your inbox is empty. Messages sent to your agent email address will appear here.</p>" +
            "</div>"
        );
    }

    // ─── Inbox View ──────────────────────────────────────────

    function renderInboxView() {
        updateActiveNav("/inbox");

        if (!state.apiKey) {
            appEl.innerHTML = renderNoApiKey();
            return;
        }

        appEl.innerHTML =
            '<div class="page-header">' +
            "<h1>Inbox</h1>" +
            '<button class="btn" id="refresh-btn">Refresh</button>' +
            "</div>" +
            renderLoading();

        var refreshBtn = document.getElementById("refresh-btn");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", function () {
                loadMessages();
            });
        }

        loadMessages();
    }

    function loadMessages() {
        var skip = state.currentPage * state.pageSize;

        api.getMessages(skip, state.pageSize)
            .then(function (data) {
                state.messages = data.messages;
                state.total = data.total;
                renderMessageList();
            })
            .catch(function (err) {
                // Keep the page header, replace only the content area
                var existing = appEl.querySelector(".message-list, .loading, .error-banner, .empty-state");
                var html = renderError(err.message);
                if (existing) {
                    existing.outerHTML = html;
                } else {
                    appEl.innerHTML =
                        '<div class="page-header">' +
                        "<h1>Inbox</h1>" +
                        '<button class="btn" id="refresh-btn">Refresh</button>' +
                        "</div>" +
                        html;
                }
            });
    }

    function renderMessageList() {
        var header =
            '<div class="page-header">' +
            "<h1>Inbox<span class=\"badge\">" + state.total + "</span></h1>" +
            '<button class="btn" id="refresh-btn">Refresh</button>' +
            "</div>";

        if (state.messages.length === 0) {
            appEl.innerHTML = header + renderEmptyInbox();
            bindRefresh();
            return;
        }

        var items = state.messages
            .map(function (msg) {
                var unreadClass = msg.is_read ? "" : " unread";
                var dotClass = msg.is_read ? "unread-dot read" : "unread-dot";
                return (
                    '<div class="message-item' + unreadClass + '" data-id="' + msg.id + '">' +
                    '<div class="' + dotClass + '"></div>' +
                    '<div class="message-content">' +
                    '<div class="message-sender">' + escapeHtml(msg.sender) + "</div>" +
                    '<div class="message-subject">' + escapeHtml(msg.subject || "(no subject)") + "</div>" +
                    '<div class="message-preview">' + escapeHtml(truncate(msg.body_text, 100)) + "</div>" +
                    "</div>" +
                    '<div class="message-time">' + formatDate(msg.received_at) + "</div>" +
                    "</div>"
                );
            })
            .join("");

        var pagination = "";
        if (state.total > state.pageSize) {
            var totalPages = Math.ceil(state.total / state.pageSize);
            pagination =
                '<div style="display:flex;justify-content:center;gap:0.5rem;margin-top:1rem;">' +
                '<button class="btn btn-secondary" id="prev-page"' +
                (state.currentPage === 0 ? " disabled" : "") +
                ">Previous</button>" +
                '<span style="padding:0.5rem;color:var(--text-secondary);font-size:0.875rem;">' +
                "Page " + (state.currentPage + 1) + " of " + totalPages +
                "</span>" +
                '<button class="btn btn-secondary" id="next-page"' +
                (state.currentPage >= totalPages - 1 ? " disabled" : "") +
                ">Next</button>" +
                "</div>";
        }

        appEl.innerHTML =
            header +
            '<div class="message-list">' + items + "</div>" +
            pagination;

        bindRefresh();
        bindPagination();
        bindMessageClicks();
    }

    function bindRefresh() {
        var refreshBtn = document.getElementById("refresh-btn");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", function () {
                loadMessages();
            });
        }
    }

    function bindPagination() {
        var prevBtn = document.getElementById("prev-page");
        var nextBtn = document.getElementById("next-page");
        if (prevBtn) {
            prevBtn.addEventListener("click", function () {
                if (state.currentPage > 0) {
                    state.currentPage--;
                    loadMessages();
                }
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener("click", function () {
                state.currentPage++;
                loadMessages();
            });
        }
    }

    function bindMessageClicks() {
        var items = appEl.querySelectorAll(".message-item");
        items.forEach(function (item) {
            item.addEventListener("click", function () {
                var id = item.getAttribute("data-id");
                navigate("/inbox/" + id);
            });
        });
    }

    // ─── Message Detail View ─────────────────────────────────

    function renderMessageDetailView(messageId) {
        updateActiveNav("/inbox");

        // Find message in current state
        var msg = state.messages.find(function (m) {
            return m.id === messageId;
        });

        if (!msg) {
            // If message not in state, try to reload messages first
            if (!state.apiKey) {
                appEl.innerHTML = renderNoApiKey();
                return;
            }
            appEl.innerHTML = renderLoading();
            api.getMessages(0, 200)
                .then(function (data) {
                    state.messages = data.messages;
                    state.total = data.total;
                    msg = state.messages.find(function (m) {
                        return m.id === messageId;
                    });
                    if (msg) {
                        showMessageDetail(msg);
                    } else {
                        appEl.innerHTML =
                            renderError("Message not found.") +
                            '<a href="/inbox" data-link class="back-link">&larr; Back to Inbox</a>';
                        bindLinks();
                    }
                })
                .catch(function (err) {
                    appEl.innerHTML = renderError(err.message);
                });
            return;
        }

        showMessageDetail(msg);
    }

    function showMessageDetail(msg) {
        appEl.innerHTML =
            '<a href="/inbox" data-link class="back-link">&larr; Back to Inbox</a>' +
            '<div class="message-detail">' +
            '<div class="message-detail-header">' +
            "<h2>" + escapeHtml(msg.subject || "(no subject)") + "</h2>" +
            '<div class="message-meta">' +
            "<span><span class=\"label\">From</span> " + escapeHtml(msg.sender) + "</span>" +
            "<span><span class=\"label\">To</span> " + escapeHtml(msg.recipient) + "</span>" +
            "<span><span class=\"label\">Date</span> " + new Date(msg.received_at).toLocaleString() + "</span>" +
            "</div>" +
            "</div>" +
            '<div class="message-detail-body">' +
            escapeHtml(msg.body_text || "(no content)") +
            "</div>" +
            "</div>";

        bindLinks();
    }

    // ─── Compose View ────────────────────────────────────────

    function renderComposeView() {
        updateActiveNav("/compose");

        if (!state.apiKey) {
            appEl.innerHTML = renderNoApiKey();
            return;
        }

        appEl.innerHTML =
            '<div class="page-header"><h1>Compose</h1></div>' +
            '<form id="compose-form" class="compose-form">' +
            '<div class="form-group">' +
            '<label for="compose-to">To</label>' +
            '<input type="email" id="compose-to" placeholder="recipient@example.com" required>' +
            "</div>" +
            '<div class="form-group">' +
            '<label for="compose-subject">Subject</label>' +
            '<input type="text" id="compose-subject" placeholder="Email subject">' +
            "</div>" +
            '<div class="form-group">' +
            '<label for="compose-body">Body</label>' +
            '<textarea id="compose-body" placeholder="Write your message..." required></textarea>' +
            "</div>" +
            '<div class="form-actions">' +
            '<button type="button" class="btn btn-secondary" id="discard-btn">Discard</button>' +
            '<button type="submit" class="btn btn-primary" id="send-btn">Send</button>' +
            "</div>" +
            "</form>";

        var form = document.getElementById("compose-form");
        var sendBtn = document.getElementById("send-btn");
        var discardBtn = document.getElementById("discard-btn");

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            var to = document.getElementById("compose-to").value.trim();
            var subject = document.getElementById("compose-subject").value.trim();
            var body = document.getElementById("compose-body").value.trim();

            if (!to || !body) {
                showToast("Please fill in the recipient and message body.", "error");
                return;
            }

            sendBtn.disabled = true;
            sendBtn.textContent = "Sending...";

            api.sendEmail(to, subject, body)
                .then(function (res) {
                    showToast("Email sent to " + res.to);
                    navigate("/inbox");
                })
                .catch(function (err) {
                    showToast(err.message, "error");
                    sendBtn.disabled = false;
                    sendBtn.textContent = "Send";
                });
        });

        discardBtn.addEventListener("click", function () {
            navigate("/inbox");
        });
    }

    // ─── Router ──────────────────────────────────────────────

    function navigate(path) {
        window.history.pushState({}, "", path);
        route();
    }

    function route() {
        var path = window.location.pathname;

        if (path === "/compose") {
            renderComposeView();
        } else if (path.match(/^\/inbox\/[a-f0-9-]+$/)) {
            var id = path.split("/inbox/")[1];
            renderMessageDetailView(id);
        } else {
            // Default to inbox (covers /inbox, /, etc.)
            renderInboxView();
        }
    }

    function updateActiveNav(activePath) {
        var links = document.querySelectorAll(".nav-link");
        links.forEach(function (link) {
            if (link.getAttribute("href") === activePath) {
                link.classList.add("active");
            } else {
                link.classList.remove("active");
            }
        });
    }

    function bindLinks() {
        document.querySelectorAll("[data-link]").forEach(function (link) {
            // Remove existing listener by cloning
            var newLink = link.cloneNode(true);
            link.parentNode.replaceChild(newLink, link);
            newLink.addEventListener("click", function (e) {
                e.preventDefault();
                navigate(newLink.getAttribute("href"));
            });
        });
    }

    // ─── Settings Modal ──────────────────────────────────────

    function openModal() {
        apiKeyInput.value = state.apiKey;
        apiKeyInput.type = "password";
        showKeyCheckbox.checked = false;
        modalOverlay.classList.remove("hidden");
        apiKeyInput.focus();
    }

    function closeModal() {
        modalOverlay.classList.add("hidden");
    }

    function saveApiKey() {
        var key = apiKeyInput.value.trim();
        state.apiKey = key;
        if (key) {
            localStorage.setItem("agent_suite_api_key", key);
            showToast("API key saved");
        } else {
            localStorage.removeItem("agent_suite_api_key");
            showToast("API key cleared");
        }
        closeModal();
        route(); // Re-render current view
    }

    // ─── Event Bindings ──────────────────────────────────────

    // Navigation links (client-side routing)
    document.addEventListener("click", function (e) {
        var link = e.target.closest("[data-link]");
        if (link) {
            e.preventDefault();
            navigate(link.getAttribute("href"));
        }
    });

    // Browser back/forward
    window.addEventListener("popstate", function () {
        route();
    });

    // Settings modal
    settingsBtn.addEventListener("click", openModal);
    saveKeyBtn.addEventListener("click", saveApiKey);
    apiKeyInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") saveApiKey();
    });

    // Close modal on overlay click or close button
    modalOverlay.addEventListener("click", function (e) {
        if (e.target === modalOverlay || e.target.classList.contains("modal-close")) {
            closeModal();
        }
    });

    // Close modal on Escape
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !modalOverlay.classList.contains("hidden")) {
            closeModal();
        }
    });

    // Show/hide API key
    showKeyCheckbox.addEventListener("change", function () {
        apiKeyInput.type = showKeyCheckbox.checked ? "text" : "password";
    });

    // ─── Initialize ──────────────────────────────────────────

    route();
})();
