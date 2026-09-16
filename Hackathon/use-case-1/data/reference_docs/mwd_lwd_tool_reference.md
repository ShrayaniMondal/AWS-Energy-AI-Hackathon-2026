# MWD/LWD Tool Operating Ranges & Interpretation Reference
## Measurement While Drilling / Logging While Drilling
### Permian Basin Horizontal Drilling Operations

---

## 1. MWD System Overview

### 1.1 Mud Pulse Telemetry (Standard Configuration)
- Telemetry type: Positive pulse (mud siren)
- Data rate: 3–12 bits/second (depth-dependent)
- Operating mud weight range: 7.0–20.0 ppg
- Minimum flow rate for telemetry: 150 gpm
- Maximum flow rate: 650 gpm
- Maximum standpipe pressure: 5,000 psi
- Operating temperature: -4°F to 302°F (–20°C to 150°C)
- Pressure rating: 20,000 psi

### 1.2 Electromagnetic (EM) Telemetry (Alternative — used in air/mist drilling)
- Does not require mud flow
- Range limited by formation resistivity (max ~8,000 ft in conductive formations)
- Not recommended for Wolfcamp A laterals >6,000 ft

---

## 2. Directional Sensors

### 2.1 Survey Accuracy Specifications

| Parameter | Standard MWD | High-Accuracy MWD |
|---|---|---|
| Inclination accuracy | ±0.1° | ±0.05° |
| Azimuth accuracy | ±1.0° | ±0.5° |
| Toolface accuracy | ±1.5° | ±1.0° |
| Survey interval | 30–90 ft | 30 ft |

### 2.2 Survey Acceptance Criteria (Permian Basin)
- Maximum dogleg severity: 8°/100 ft (build section), 3°/100 ft (lateral)
- Inclination tolerance in lateral: 88°–92° (target: 90°)
- Azimuth tolerance: ±5° from planned azimuth
- Closure distance from target: ≤ 50 ft at TD

### 2.3 Magnetic Interference
- Minimum distance from casing for valid magnetic survey: 50 ft
- If within 50 ft of casing: use gyro survey or non-magnetic drill collars
- Non-magnetic collar length required: minimum 30 ft above and below sensor sub

### 2.4 Survey Frequency
- Build section: every 30 ft
- Tangent/lateral section: every 60–90 ft
- Near target zone (within 200 ft of formation top): every 30 ft

---

## 3. Gamma Ray (GR) Sensor

### 3.1 Specifications
- Measurement type: Total natural gamma ray (API units)
- Detector: NaI scintillation crystal
- Vertical resolution: 18–24 in
- Depth of investigation: 12–18 in
- Operating temperature: up to 302°F (150°C)
- Logging speed: up to 200 ft/hr (LWD mode)

### 3.2 Permian Basin Formation GR Signatures

| Formation | Typical GR Range (API) | Interpretation |
|---|---|---|
| Wolfcamp A shale | 80–140 API | Organic-rich shale — target zone |
| Wolfcamp A carbonate | 20–45 API | Carbonate interbeds — avoid if possible |
| Spraberry siltstone | 55–85 API | Moderate GR — target zone |
| Bone Spring carbonate | 15–40 API | Low GR carbonate |
| Bone Spring shale | 90–130 API | High GR shale |
| Dean sandstone | 30–60 API | Low-moderate GR |
| Wolfcamp B | 70–110 API | Below Wolfcamp A target |

### 3.3 Geosteering Using GR
- Landing target: GR > 80 API sustained over 30 ft = confirmed Wolfcamp A shale
- Steer up if: GR drops below 50 API (entering carbonate)
- Steer down if: GR exceeds 150 API (entering organic-rich zone below target)
- Formation top pick: first sustained GR increase >20 API above background

---

## 4. Resistivity Sensor (LWD)

### 4.1 Specifications — ARC (Array Resistivity Compensated)
- Measurement depths: 10, 20, 30, 60, 90 in (5 depths of investigation)
- Frequency: 2 MHz and 400 kHz
- Vertical resolution: 12–24 in (frequency dependent)
- Operating temperature: up to 302°F
- Operating pressure: 20,000 psi

### 4.2 Resistivity Interpretation — Wolfcamp A

| Zone | Resistivity Range (ohm-m) | Interpretation |
|---|---|---|
| Organic shale (oil-saturated) | 8–25 ohm-m | Target — good oil saturation |
| Organic shale (water-saturated) | 1–4 ohm-m | Avoid — water-bearing |
| Carbonate stringer | 50–500 ohm-m | Hard stringer — potential drilling hazard |
| Tight siltstone | 15–40 ohm-m | Moderate reservoir quality |
| Brine-saturated zone | 0.5–2 ohm-m | Avoid — high water cut risk |

### 4.3 Rt/Rxo Ratio (Invasion Analysis)
- Rt/Rxo > 1.5: oil-based mud invasion, oil-bearing formation
- Rt/Rxo ≈ 1.0: no invasion contrast (tight formation or water-bearing)
- Rt/Rxo < 0.8: water-bearing formation (mud filtrate displacing formation water)

---

## 5. Downhole Dynamics Sensors

### 5.1 Shock & Vibration
- Axial shock limit: 50 g (peak)
- Lateral shock limit: 100 g (peak)
- Torsional vibration (stick-slip) indicator: RPM variation >±20% of surface RPM
- Recommended action if limits exceeded: reduce WOB by 20%, adjust RPM

### 5.2 Downhole WOB/Torque
- Downhole WOB sensor accuracy: ±2 klbs
- Downhole torque sensor accuracy: ±500 ft-lbs
- Bit bounce indicator: axial vibration >25 g at >10 Hz
- Whirl indicator: lateral vibration >50 g with backward rotation signature

### 5.3 Annular Pressure While Drilling (APWD)
- Measures ECD directly at sensor depth
- Sensor location: typically 50–80 ft above bit
- ECD accuracy: ±0.05 ppg
- Use for: real-time pore pressure monitoring, lost circulation detection
- Alert threshold: ECD > mud weight + 0.3 ppg (potential fracture gradient approach)

---

## 6. Tool Failure Modes & Troubleshooting

### 6.1 Loss of Telemetry Signal
| Cause | Diagnosis | Action |
|---|---|---|
| Plugged pulser | No signal at surface, pump pressure normal | Increase flow rate 50 gpm; if no recovery, POOH |
| Pulser erosion | Weak/intermittent signal | Reduce flow rate; plan tool replacement |
| Battery depletion | Signal loss after >200 hrs | POOH for battery replacement |
| Mud motor bypass | Signal present but no rotation | Check motor differential pressure |

### 6.2 Erratic Survey Data
| Symptom | Probable Cause | Action |
|---|---|---|
| Azimuth jumps >5° between surveys | Magnetic interference | Check proximity to casing; use gyro |
| Inclination drift >0.5°/survey | Accelerometer failure | POOH for tool replacement |
| Toolface not responding | Stuck motor or bent sub | Check WOB; inspect BHA |

### 6.3 GR Sensor Issues
| Symptom | Probable Cause | Action |
|---|---|---|
| GR reads zero | Detector failure or cable fault | POOH for replacement |
| GR reads constant high value | Radioactive tracer in mud | Check mud system; flush if needed |
| GR spikes | Shock damage to crystal | Reduce vibration; check shock data |

---

## 7. BHA Design Guidelines — Permian Basin Horizontal

### 7.1 Typical BHA Configuration (Lateral Section)
1. PDC bit (6-1/8 in)
2. Bit sub
3. Mud motor (6-1/4 in, 1.15° bend)
4. MWD/LWD sub (GR + Resistivity + APWD)
5. Non-magnetic drill collar (30 ft)
6. Jar (hydraulic)
7. HWDP (5 in, 3 joints)
8. Drill pipe to surface

### 7.2 Motor Specifications (6-1/4 in, 7/8 Lobe)
- Differential pressure at bit: 400–600 psi (normal drilling)
- Maximum differential pressure: 800 psi
- Stall pressure: 900–1,000 psi (do not exceed)
- Motor output RPM: 120–180 RPM at 400 gpm
- Bend setting: 1.15° (standard for Wolfcamp A laterals)
- Maximum dogleg from motor: 8°/100 ft

### 7.3 Operating Limits Summary

| Parameter | Minimum | Maximum | Optimal |
|---|---|---|---|
| Flow rate (gpm) | 250 | 600 | 400–500 |
| WOB (klbs) | 5 | 35 | 15–25 |
| Surface RPM | 40 | 120 | 60–80 |
| Differential pressure (psi) | 200 | 800 | 400–600 |
| ECD (ppg) | MW | MW + 0.5 | MW + 0.2–0.4 |
| Standpipe pressure (psi) | — | 4,500 | 3,000–4,000 |

## Survey Quality Control

### Definitive Survey Requirements (ISCWSA)
| Parameter | Tolerance | Check Method |
|-----------|-----------|-------------|
| Inclination | ±0.1° | Multi-station analysis |
| Azimuth | ±0.5° | Comparison with gyro |
| Toolface | ±1.0° | Repeat survey |
| Total field strength | ±200 nT of reference | IGRF model comparison |
| Dip angle | ±0.3° of reference | IGRF model comparison |
| Gravity | ±0.003 g | Accelerometer calibration |

### Anti-Collision Monitoring
- Separation factor (SF) > 1.0 required at all times
- Ellipse of uncertainty (EOU) calculated per ISCWSA error model
- Closest approach distance monitored in real-time
- Alert at SF < 1.5, alarm at SF < 1.2, stop drilling at SF < 1.0

## Gamma Ray Log Interpretation

### Formation Identification
| GR Range (API) | Lithology | Typical Formation |
|----------------|-----------|-------------------|
| 0-20 | Clean sandstone | Reservoir sand |
| 20-45 | Silty sandstone | Transition zone |
| 45-75 | Shale/siltstone | Cap rock |
| 75-150 | Shale | Seal |
| > 150 | Hot shale / organic | Source rock |

### Correlation with Drilling Parameters
- GR increase + ROP decrease: Entering shale (harder formation)
- GR decrease + ROP increase: Entering sand (softer, potential reservoir)
- GR spike + gas show: Possible hydrocarbon-bearing zone
- GR baseline shift: Formation boundary or unconformity
