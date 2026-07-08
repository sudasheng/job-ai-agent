/**
 * Job AI Agent - 通用前端脚本
 */

// Token 管理和认证状态
(function () {
    "use strict";

    const TOKEN_KEY = "token";
    const REFRESH_TOKEN_KEY = "refreshToken";
    const USER_KEY = "user";

    window.JobAgent = {
        // ---- Token ----
        getToken: function () {
            return localStorage.getItem(TOKEN_KEY);
        },

        setToken: function (token) {
            localStorage.setItem(TOKEN_KEY, token);
        },

        removeToken: function () {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(REFRESH_TOKEN_KEY);
            localStorage.removeItem(USER_KEY);
        },

        // ---- User ----
        getUser: function () {
            try {
                return JSON.parse(localStorage.getItem(USER_KEY) || "null");
            } catch {
                return null;
            }
        },

        isLoggedIn: function () {
            return !!this.getToken();
        },

        // ---- HTTP ----
        async fetch(url, options = {}) {
            const token = this.getToken();
            const headers = {
                "Content-Type": "application/json",
                ...(options.headers || {}),
            };
            if (token) {
                headers["Authorization"] = "Bearer " + token;
            }

            const resp = await fetch(url, {
                ...options,
                headers,
            });

            // 401 自动跳转登录
            if (resp.status === 401) {
                this.removeToken();
                if (window.location.pathname !== "/login") {
                    window.location.href = "/login";
                }
            }

            return resp;
        },

        // ---- API 快捷方法 ----
        api: {
            get: function (url) {
                return window.JobAgent.fetch(url);
            },
            post: function (url, data) {
                return window.JobAgent.fetch(url, {
                    method: "POST",
                    body: JSON.stringify(data),
                });
            },
            put: function (url, data) {
                return window.JobAgent.fetch(url, {
                    method: "PUT",
                    body: JSON.stringify(data),
                });
            },
            delete: function (url) {
                return window.JobAgent.fetch(url, { method: "DELETE" });
            },
        },
    };

    // ---- 导航栏认证状态 ----
    function updateNavAuth() {
        const navAuth = document.getElementById("navAuth");
        if (!navAuth) return;

        const user = window.JobAgent.getUser();
        if (user) {
            navAuth.innerHTML = `
                <span class="nav-link" style="cursor:default;">${escapeHtml(user.username || user.nickname || "用户")}</span>
                <a href="#" class="nav-link" id="logoutBtn">退出</a>
            `;
            document.getElementById("logoutBtn").addEventListener("click", function (e) {
                e.preventDefault();
                window.JobAgent.removeToken();
                window.location.reload();
            });
        } else {
            navAuth.innerHTML = '<a href="/login" class="nav-link">登录</a>';
        }
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    document.addEventListener("DOMContentLoaded", updateNavAuth);
})();