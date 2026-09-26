// Authentication Management for CalorieCast

const Auth = {
  getToken() {
    return localStorage.getItem("caloriecast_token");
  },

  setToken(token) {
    localStorage.setItem("caloriecast_token", token);
  },

  getUser() {
    const raw = localStorage.getItem("caloriecast_user");
    return raw ? JSON.parse(raw) : null;
  },

  setUser(user) {
    localStorage.setItem("caloriecast_user", JSON.stringify(user));
  },

  clear() {
    localStorage.removeItem("caloriecast_token");
    localStorage.removeItem("caloriecast_user");
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  logout() {
    this.clear();
    window.location.href = "/static/login.html";
  },

  requireAuth(adminOnly = false) {
    if (!this.isLoggedIn()) {
      window.location.href = "/static/login.html";
      return false;
    }
    const user = this.getUser();
    if (adminOnly && (!user || user.role !== "admin")) {
      alert("Admin privileges required.");
      window.location.href = "/static/dashboard.html";
      return false;
    }
    return true;
  },

  initNav() {
    const navUser = document.getElementById("nav-user");
    const navLinks = document.getElementById("nav-links");
    const user = this.getUser();

    if (this.isLoggedIn() && user) {
      if (navUser) {
        navUser.innerHTML = `
          <div class="user-badge">
            <span>👤 <strong>${user.name}</strong> (${user.role})</span>
            <button class="btn btn-secondary btn-sm" onclick="Auth.logout()">Logout</button>
          </div>
        `;
      }
      if (navLinks && user.role === "admin") {
        if (!document.getElementById("nav-admin-link")) {
          const adminLink = document.createElement("a");
          adminLink.id = "nav-admin-link";
          adminLink.href = "/static/admin.html";
          adminLink.textContent = "Admin Portal";
          navLinks.appendChild(adminLink);
        }
      }
    } else {
      if (navUser) {
        navUser.innerHTML = `<a href="/static/login.html" class="btn btn-primary btn-sm">Login / Register</a>`;
      }
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  Auth.initNav();
});
