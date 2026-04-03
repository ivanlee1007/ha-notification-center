# UNiNUS Notification Center

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Home Assistant 通知中心 — 一站式通知管理整合，支援分級、自動解除、Snooze、重複推送、Email 聯動。

> 基於 [HA Notification Framework (YAML)](https://github.com/community-forks/ha-notification-framework) 重構為 HACS Custom Integration，移除對 HACS Variable 整合的依賴，改用 HA 內建 Storage。

---

## 功能特色

| 功能 | 說明 |
|---|---|
| 🔔 **通知源管理** | 透過 Service Call 註冊通知源，自動追蹤 `binary_sensor.notification_*` 狀態 |
| 📊 **聚合感測器** | `sensor.notification_feed` (通知數 + 詳細資料)、`sensor.notification_count_warning/critical` |
| 🚨 **分級投遞** | `info` / `warning` / `critical` 三級，critical 自動 Email 聯動 |
| ⏰ **Snooze** | 暫停通知 1h / 4h / 8h / 24h，使用 HA Storage 儲存（無字元限制） |
| 🔁 **Critical 重複** | 緊急通知每隔 N 分鐘自動重送，直到 Acknowledge |
| ✅ **自動解除** | 通知源狀態恢復正常 → 自動清除 |
| 📨 **Direct Push API** | HA automation 可直接用 service 把通知送進卡片 feed |
| 🎨 **Lovelace 卡片** | 搭配獨立 HACS Dashboard repo `ha-notification-center-card` 使用 |

---

## 安裝

### HACS（自訂 Repo）

1. HACS → 整合 → 右上角 `⋮` → **自訂儲存庫**
2. URL: `https://github.com/ivanlee1007/ha-notification-center`
3. 類別: **Integration**
4. 安裝「UNiNUS Notification Center」
5. **重啟 Home Assistant**

### Lovelace 卡片（獨立 HACS Dashboard Repo）

這個 repo 現在只負責 **Integration**。Lovelace 卡片已拆成獨立 repo：

- `https://github.com/ivanlee1007/ha-notification-center-card`

安裝方式：

1. HACS → **Dashboard** → 右上角 `⋮` → **自訂儲存庫**
2. URL: `https://github.com/ivanlee1007/ha-notification-center-card`
3. 類別: **Dashboard**
4. 安裝 `UNiNUS Notification Center Card`
5. 到 **設定 → 儀表板 → 資源** 確認 HACS 自動加入：

```text
/hacsfiles/ha-notification-center-card/ha-notification-center-card.js
```

### 手動安裝

```bash
cd /config
mkdir -p custom_components/ha_notification_center
# 將 custom_components/ha_notification_center/ 下的所有檔案複製進去

# 可選：安裝 button-card 模板
cp -r www/button_card_templates /config/www/
```

重啟 Home Assistant。

---

## 設定

### UI 設定（推薦）

1. **設定** → **裝置與服務** → **新增整合**
2. 搜尋「UNiNUS Notification Center」
3. 填寫：
   - **手機推送通知服務**（必填）：你的 notify service 名稱，例如 `notify`
   - **Email 通知服務**（選填）：例如 `notify.gmail_smtp`
   - **緊急重複間隔**：Critical 通知重送間隔分鐘數（預設 10）
   - **低電量閾值**：低電量警示 %（預設 20）

### YAML 設定（選填）

如果你想用 YAML 自動註冊通知源，在 `configuration.yaml` 或自動化中呼叫：

```yaml
# 方式一：直接呼叫 service
automation:
  - alias: "Register water leak notification"
    trigger:
      - platform: state
        entity_id: binary_sensor.water_leak
        to: "on"
    action:
      - service: ha_notification_center.register_source
        data:
          name: "漏水警報"
          icon: "mdi:water-alert"
          priority: critical
          description: "廚房漏水偵測器觸發"
          tap_action_entity: binary_sensor.water_leak
```

---

## 核心概念

### 通知源（Notification Source）

一個通知源是一個 `binary_sensor.notification_*` 實體：
- 狀態 `on` = 通知活躍
- 狀態 `off` = 正常（自動解除）

**屬性（設定在 binary_sensor 上）：**

| 屬性 | 必填 | 說明 |
|---|---|---|
| `friendly_name` | ✅ | 顯示名稱 |
| `icon` | ✅ | MDI 圖示 |
| `priority` | ✅ | `info` / `warning` / `critical` |
| `description` | ❌ | 通知說明文字 |
| `tap_action_entity` | ❌ | 點擊導航目標實體 |

### 實體總覽

| 實體 | 類型 | 說明 |
|---|---|---|
| `sensor.notification_feed` | sensor | 通知數量（attributes 含完整通知列表） |
| `sensor.notification_count_warning` | sensor | Warning 通知數 |
| `sensor.notification_count_critical` | sensor | Critical 通知數 |
| `binary_sensor.notification_any_active` | binary_sensor | 有通知活躍時為 `on` |
| `binary_sensor.notification_any_critical` | binary_sensor | 有 Critical 通知時為 `on` |
| `binary_sensor.notification_any_warning` | binary_sensor | 有 Warning/Critical 通知時為 `on` |

### Service Call

| Service | 參數 | 說明 |
|---|---|---|
| `ha_notification_center.register_source` | `name`, `icon`, `priority`, `description`, `tap_action_entity` | 註冊通知源 |
| `ha_notification_center.push_notification` | `source_id`, `name`, `priority`, `description`, `icon`, `tap_action_entity`, `auto_clear_seconds` | 直接把通知推進 feed |
| `ha_notification_center.clear_notification` | `source_id` | 清除直接推進 feed 的通知 |
| `ha_notification_center.snooze` | `source_id`, `duration_hours` | 暫停通知 |
| `ha_notification_center.unsnooze` | `source_id` | 取消暫停 |
| `ha_notification_center.acknowledge` | `source_id` | 確認通知（停止重複推送） |

---

## 使用範例

### 範例 1：漏水警報（Critical）

```yaml
# configuration.yaml
binary_sensor:
  - platform: template
    sensors:
      notification_water_leak:
        friendly_name: "漏水警報"
        icon: "mdi:water-alert"
        value_template: "{{ is_state('binary_sensor.kitchen_leak', 'on') }}"
        attribute_templates:
          priority: "critical"
          description: "廚房漏水偵測器觸發"
          tap_action_entity: "binary_sensor.kitchen_leak"
```

### 範例 2：低電量提醒（Warning）

```yaml
binary_sensor:
  - platform: template
    sensors:
      notification_low_battery:
        friendly_name: "低電量設備"
        icon: "material-symbols-light:battery-android-1"
        value_template: >-
          {{ states.sensor | selectattr('attributes.device_class', 'defined')
             | selectattr('attributes.device_class', 'eq', 'battery')
             | selectattr('state', 'is_number')
             | selectattr('state', 'lt', states('input_number.notification_battery_threshold_pct'))
             | list | count > 0 }}
        attribute_templates:
          priority: "warning"
          description: "有設備電量低於閾值"
```

### 範例 3：HA 更新通知（Info）

```yaml
binary_sensor:
  - platform: template
    sensors:
      notification_hass_update:
        friendly_name: "HA 更新可用"
        icon: "mdi:update"
        value_template: "{{ states('update.home_assistant_core_update') == 'on' }}"
        attribute_templates:
          priority: "info"
          description: "Home Assistant Core 有新版本可用"
```

### 範例 4：降雨提醒（Info）

```yaml
binary_sensor:
  - platform: template
    sensors:
      notification_raining:
        friendly_name: "正在下雨"
        icon: "mdi:weather-rainy"
        value_template: "{{ is_state('binary_sensor.rain_sensor', 'on') }}"
        attribute_templates:
          priority: "info"
          description: "感測器偵測到降雨"
          tap_action_entity: "weather.home"
```

### 範例 5：Automation 直接送通知到卡片（推薦給動態告警）

如果你的告警不是天然對應某顆 `binary_sensor.notification_*`，而是想由 automation / script / AI 流程直接送進卡片，請改用 `push_notification`：

```yaml
automation:
  - alias: "主泵浦異常時送到 Notification Center"
    trigger:
      - platform: numeric_state
        entity_id: sensor.pump_pressure
        below: 1.2
    action:
      - service: ha_notification_center.push_notification
        data:
          source_id: pump_alarm_main
          name: 主泵浦異常
          priority: critical
          icon: mdi:pump
          description: 壓力低於安全值，請立即檢查
          tap_action_entity: switch.pump_main
          auto_clear_seconds: 3600
```

解除時：

```yaml
automation:
  - alias: "主泵浦恢復時清除 Notification Center 告警"
    trigger:
      - platform: numeric_state
        entity_id: sensor.pump_pressure
        above: 1.2
    action:
      - service: ha_notification_center.clear_notification
        data:
          source_id: pump_alarm_main
```

### 什麼時候用 binary_sensor，什麼時候用 push_notification？

- **固定設備狀態型告警**：用 `binary_sensor.notification_*`
- **動態文字 / workflow / AI 判讀 / 臨時事件**：用 `push_notification`

兩條路都會進到同一個 `sensor.notification_feed`，卡片不需要分開處理。

---

## Lovelace 卡片

卡片已拆成獨立 HACS Dashboard repo，安裝完成後可直接在 Lovelace 中使用：

```yaml
type: custom:ha-notification-center-card
show_chip: true
show_panel: true
max_items: 20
```

或使用 button-card 模板（需安裝 [button-card](https://github.com/custom-cards/button-card)）：

1. 將 repo 內的 `www/button_card_templates/` 複製到你的 HA config 目錄：
   ```bash
   cp -r www/button_card_templates /config/www/
   ```
2. 在 Lovelace 的 `configuration.yaml` 或 dashboard config 加入：
   ```yaml
   button_card_templates: !include_dir_merge_named www/button_card_templates/
   ```
3. 在 Lovelace 中使用：
   ```yaml
   type: custom:button-card
   entity: sensor.notification_feed
   template: notif_chip_2
   ```

可用模板：`notif_chip_2`、`notif_list`、`notif_pills`、`notif_banner`（均依賴 `notif_shared`）

---

## 從 YAML 框架遷移

如果你原本使用 YAML 版本的 Notification Framework：

1. **不需要**安裝 HACS Variable 整合（snooze/repeat 已改用 Storage）
2. 將 `notif_sources.yaml` 中的 notification source 改成 `binary_sensor.template` 格式
3. 通知自動投遞由整合接管，不需要 `notif_automations.yaml`
4. button_card_templates 可直接保留使用
5. `packages/notifications.yaml` 不再需要

---

## 與原始 YAML 框架的差異

| 項目 | YAML Framework | 本整合 |
|---|---|---|
| 安裝 | 手動複製 7 個檔案 | HACS 一鍵安裝 |
| Snooze 存儲 | HACS Variable 整合 | HA 內建 Storage |
| 自動化 | 6 個 YAML automation | Python 內建 |
| 通知源定義 | YAML template binary_sensor | 同上 + Service Call 註冊 |
| UI 元件 | button_card templates | 自訂卡片 + button_card 模板 |
| 設定 | 改 YAML | Config Flow UI |

---

## 開發

```bash
# 複製到 HA 測試
cp -r custom_components/ha_notification_center /path/to/ha/config/custom_components/

# 檢查語法
python3 -m py_compile custom_components/ha_notification_center/__init__.py
python3 -m py_compile custom_components/ha_notification_center/sensor.py
python3 -m py_compile custom_components/ha_notification_center/binary_sensor.py
python3 -m py_compile custom_components/ha_notification_center/config_flow.py
python3 -m py_compile custom_components/ha_notification_center/storage.py
```

---

## License

MIT
