# 🌊 FloodWatch KZ — Decision Support System for Flash Flood & Debris Flow Risks

**FloodWatch KZ** is a specialized Decision Support System (DSS) operating in the **Human-in-the-Loop (HITL)** paradigm. The system is designed for background interception of primary meteorological triggers (intense rainfall, abnormal temperature spikes, and rapid glacial melt) over the mountain gorges of the Trans-Ili Alatau (Medeu, Talgar, Esik, Kaskelen).

---

## 🎯 Practical and Socio-Economic Value (The "Golden Window" Concept)

In the mountain gorges of the Almaty region, the lead time (water/debris flow run-up time) to foothill settlements and residential areas is **only 1 to 3 hours**. Unlike macro-level long-term forecasting systems (Tasqyn, Delft-FEWS) that provide abstract multi-week forecasts, FloodWatch KZ creates a critical time window (1–3 hours) for immediate local action:

### 1. Population Protection and Saving Lives

* **Timely Alerts:** Emergency service operators or local municipality officers receive alert signals before water enters riverbeds, enabling them to trigger local sirens or send targeted push notifications.
* **Safe Evacuation:** Residents gain a crucial buffer time to evacuate high-risk zones in an organized manner, avoiding panic and traffic gridlock at gorge exits.

### 2. Preservation of Movable and Immovable Property

* **Vehicle Evacuation:** Car owners have time to move vehicles out of underground parking structures, lowlands, and flood-prone riverbanks to higher ground, preventing total loss of property.
* **Personal Property Protection:** Even if a building's structure cannot be shielded from flooding, a 1–2 hour advance notice allows residents to move appliances and furniture to upper floors, shut off electricity and gas mains, and secure documents, valuables, and livestock.

### 3. Economic Impact on State and Insurance Sectors

* **Reduced Burden on Insurance Funds:** Minimizes claim payouts (automobiles, property) by drastically reducing total cumulative damage.
* **Mitigation of Disaster Recovery Deficits:** Requires significantly less state funding for disaster compensation and infrastructure reconstruction when assets are evacuated in advance.

---

## 🏗️ Architecture and Algorithmic Stack

The application functions as a background microservice polling high-altitude grid coordinates via REST API while factoring in elevation above sea level:

```text
┌─────────────────────────┐
│   Open-Meteo REST API   │ (Background polling every 15 minutes)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Validation Module     │ ──► [Anomaly filtering: T ∉ [-50, 50]°C, R ∉ [0, 300] mm]
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Risk Evaluation Model  │ ──► [Two-factor matrix: Precipitation + Temperature]
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Finite State Machine   │ ──► [Spam suppression: Alerts ONLY on risk state change]
└────────────┬────────────┘
             │
   ┌─────────┴────────────────────────┐
   ▼                                  ▼
┌─────────────────────────┐ ┌─────────────────────────┐
│ CSV / System Logging    │ │ Telegram Bot API        │
│ (flood_data.csv)        │ │ (Multilingual Push)     │
└─────────────────────────┘ └─────────────────────────┘

```

---

## 📐 Mathematical Risk Evaluation Model

The danger level is calculated using a two-factor logical matrix:
```text
```text
Risk = HIGH_RISK,   if R >= 20.0 mm OR (T >= 18.0°C AND R >= 15.0 mm)
Risk = MEDIUM_RISK, if T >= 15.0°C AND R >= 5.0 mm
Risk = NORMAL,      otherwise
```

* **Physical IoT Sensor Integration:** Installation of ultrasonic and radar water level gauges along Medeu, Talgar, Esik, and Kaskelen riverbeds for real-time water level tracking.
* **Satellite Snow Cover Analysis (Google Earth Engine):** Automated processing of Sentinel-2 / Landsat imagery to calculate the NDSI (Normalized Difference Snow Index) for glacial melt surface evaluation.
* **Emergency Alert & Insurance Gateways:**
* **SMS / Siren Gateway:** Automated signal dispatch to local loudspeakers and emergency response consoles upon reaching `HIGH_RISK` status.
* **Insurance API:** Provisioning verified weather anomaly logs to insurance providers for automated claim processing and risk assessment.


* **Cloud Web Interface (GIS Dashboard):** Deployment of an interactive map featuring risk heatmaps, precipitation overlays, and flood wave propagation forecasts.
