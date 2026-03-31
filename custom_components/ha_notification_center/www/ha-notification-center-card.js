/**
 * UNiNUS Notification Center — Lovelace Custom Card
 *
 * Renders a notification chip + floating panel from
 * sensor.ha_notification_center_feed attributes.
 *
 * Dependencies: none (standalone web component)
 * Install: automatic via integration static path
 */
class HaNotificationCenterCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      show_chip: true,
      show_panel: true,
      max_items: 50,
      entity: "sensor.ha_notification_center_feed",
      critical_entity: "binary_sensor.ha_notification_center_any_critical",
      ...config,
    };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    const feed = this._hass?.states?.[this._config.entity];
    return feed?.state > 0 ? 3 : 1;
  }

  _render() {
    if (!this._hass) return;

    const feed = this._hass.states[this._config.entity];
    const anyCritical = this._hass.states[this._config.critical_entity];
    const count = feed ? parseInt(feed.state) || 0 : 0;
    const isCritical = anyCritical?.state === "on";
    const notifications = feed?.attributes?.notifications || [];

    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }

    const priorityOrder = { critical: 0, warning: 1, info: 2 };
    const sorted = [...notifications].sort(
      (a, b) => (priorityOrder[a.priority] ?? 9) - (priorityOrder[b.priority] ?? 9)
    );

    const items = sorted.slice(0, this._config.max_items).map((n) => {
      const priClass = `pri-${n.priority || "info"}`;
      const ackClass = n.acknowledged ? "ack" : "";
      return `
        <div class="notif-item ${priClass} ${ackClass}" data-entity="${n.tap_action_entity || ""}">
          <div class="notif-icon">
            <ha-icon icon="${n.icon || "mdi:bell"}"></ha-icon>
          </div>
          <div class="notif-body">
            <div class="notif-name">${this._esc(n.name)}</div>
            ${n.description ? `<div class="notif-desc">${this._esc(n.description)}</div>` : ""}
            <div class="notif-meta">
              <span class="notif-priority">${n.priority || "info"}</span>
              <span class="notif-time">${this._relativeTime(n.timestamp)}</span>
            </div>
          </div>
          <div class="notif-actions">
            <ha-icon-button icon="mdi:bell-off" title="Snooze 1h"
              data-snooze="${n.source_id}"></ha-icon-button>
            <ha-icon-button icon="mdi:check" title="Acknowledge"
              data-ack="${n.source_id}"></ha-icon-button>
          </div>
        </div>`;
    });

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; font-family: var(--ha-font-family, sans-serif); }
        .chip {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 6px 14px; border-radius: 20px;
          background: var(--primary-color); color: #fff;
          font-size: 14px; font-weight: 500; cursor: pointer;
          transition: background 0.2s;
        }
        .chip.critical { background: var(--error-color, #d32f2f); animation: pulse 2s infinite; }
        .chip:hover { opacity: 0.9; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        .panel {
          position: fixed; top: 64px; right: 16px; z-index: 999;
          width: 380px; max-height: 70vh; overflow-y: auto;
          background: var(--card-background-color, #fff);
          border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.2);
          padding: 0; display: none;
        }
        .panel.open { display: block; }
        .panel-header {
          padding: 16px; border-bottom: 1px solid var(--divider-color);
          font-size: 16px; font-weight: 600;
          display: flex; justify-content: space-between; align-items: center;
        }
        .panel-header .close { cursor: pointer; opacity: 0.6; }
        .panel-header .close:hover { opacity: 1; }
        .notif-item {
          display: flex; align-items: flex-start; gap: 12px;
          padding: 12px 16px; border-bottom: 1px solid var(--divider-color);
          transition: background 0.15s;
        }
        .notif-item:hover { background: var(--secondary-background-color); }
        .notif-item.ack { opacity: 0.5; }
        .notif-icon { font-size: 24px; padding-top: 2px; flex-shrink: 0; }
        .notif-body { flex: 1; min-width: 0; }
        .notif-name { font-weight: 500; font-size: 14px; }
        .notif-desc { font-size: 12px; color: var(--secondary-text-color); margin-top: 2px; }
        .notif-meta { display: flex; gap: 8px; margin-top: 4px; font-size: 11px; color: var(--secondary-text-color); }
        .notif-priority {
          padding: 1px 6px; border-radius: 8px; font-weight: 600; text-transform: uppercase;
        }
        .pri-critical .notif-priority { background: #ffcdd2; color: #b71c1c; }
        .pri-warning .notif-priority { background: #fff3e0; color: #e65100; }
        .pri-info .notif-priority { background: #e3f2fd; color: #0d47a1; }
        .notif-actions { display: flex; flex-direction: column; gap: 4px; flex-shrink: 0; }
        .empty { padding: 32px 16px; text-align: center; color: var(--secondary-text-color); }
      </style>
      ${this._config.show_chip ? `
        <div class="chip ${isCritical ? "critical" : ""}" id="chip">
          <ha-icon icon="${isCritical ? "mdi:alert-circle" : "mdi:bell"}"></ha-icon>
          <span>通知 ${count > 0 ? `(${count})` : ""}</span>
        </div>` : ""}
      ${this._config.show_panel ? `
        <div class="panel" id="panel">
          <div class="panel-header">
            <span>通知 (${count})</span>
            <ha-icon class="close" icon="mdi:close" id="close"></ha-icon>
          </div>
          ${count === 0 ? '<div class="empty">沒有通知</div>' : items.join("")}
        </div>` : ""}
    `;

    // Bind events
    const chip = this.shadowRoot.getElementById("chip");
    const panel = this.shadowRoot.getElementById("panel");
    const closeBtn = this.shadowRoot.getElementById("close");

    if (chip && panel) {
      chip.onclick = () => panel.classList.toggle("open");
    }
    if (closeBtn && panel) {
      closeBtn.onclick = () => panel.classList.remove("open");
    }

    // Snooze buttons
    this.shadowRoot.querySelectorAll("[data-snooze]").forEach((btn) => {
      btn.onclick = (e) => {
        e.stopPropagation();
        this._hass.callService("ha_notification_center", "snooze", {
          source_id: btn.dataset.snooze,
          duration_hours: 1,
        });
      };
    });

    // Acknowledge buttons
    this.shadowRoot.querySelectorAll("[data-ack]").forEach((btn) => {
      btn.onclick = (e) => {
        e.stopPropagation();
        this._hass.callService("ha_notification_center", "acknowledge", {
          source_id: btn.dataset.ack,
        });
      };
    });

    // Tap on notification body → navigate to entity
    this.shadowRoot.querySelectorAll(".notif-item").forEach((item) => {
      const entity = item.dataset.entity;
      if (entity) {
        item.querySelector(".notif-body").style.cursor = "pointer";
        item.querySelector(".notif-body").onclick = () => {
          this._hass.navigatePath(`/config/devices/dashboard?entity=${entity}`);
        };
      }
    });
  }

  _esc(str) {
    if (!str) return "";
    const el = document.createElement("span");
    el.textContent = str;
    return el.innerHTML;
  }

  _relativeTime(ts) {
    if (!ts) return "";
    const diff = Date.now() - new Date(ts).getTime();
    if (diff < 60000) return "剛剛";
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分鐘前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小時前`;
    return `${Math.floor(diff / 86400000)} 天前`;
  }
}

customElements.define("ha-notification-center-card", HaNotificationCenterCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "custom:ha-notification-center-card",
  name: "UNiNUS Notification Center",
  description: "通知中心晶片 + 浮動面板",
  preview: true,
});
