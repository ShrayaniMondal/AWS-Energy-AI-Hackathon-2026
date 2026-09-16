# Mud Pump Specifications & Operating Reference
## National 12-P-160 / Gardner Denver PZ-11 / National 10-P-130
### Permian Basin Drilling Operations

---

## 1. Pump Specifications Summary

### 1.1 National 12-P-160 (Primary Pump — Rig Nos. 100–149)

| Parameter | Value |
|---|---|
| Type | Triplex single-acting piston |
| Maximum input power | 1,600 HP |
| Maximum stroke rate | 120 SPM |
| Maximum working pressure | 7,500 psi |
| Liner sizes available | 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0 in |
| Stroke length | 12 in |
| Rod load rating | 162,000 lbf |
| Fluid end material | 4140 steel, chrome-lined bores |
| Suction connection | 8 in flanged |
| Discharge connection | 4 in flanged |

**Output volume by liner size (gal/stroke):**

| Liner (in) | Vol (gal/stroke) | Max flow @ 120 SPM (gpm) |
|---|---|---|
| 4.0 | 0.980 | 117.6 |
| 4.5 | 1.241 | 148.9 |
| 5.0 | 1.531 | 183.7 |
| 5.5 | 1.852 | 222.2 |
| 6.0 | 2.203 | 264.4 |
| 6.5 | 2.584 | 310.1 |
| 7.0 | 2.994 | 359.3 |

**Maximum pressure by liner size:**

| Liner (in) | Max pressure (psi) |
|---|---|
| 4.0 | 7,500 |
| 4.5 | 7,500 |
| 5.0 | 6,000 |
| 5.5 | 5,000 |
| 6.0 | 4,200 |
| 6.5 | 3,500 |
| 7.0 | 3,000 |

---

### 1.2 Gardner Denver PZ-11 (Secondary Pump — Rig Nos. 150–199)

| Parameter | Value |
|---|---|
| Type | Triplex single-acting piston |
| Maximum input power | 1,100 HP |
| Maximum stroke rate | 110 SPM |
| Maximum working pressure | 7,500 psi |
| Liner sizes available | 4.0, 4.5, 5.0, 5.5, 6.0, 6.5 in |
| Stroke length | 11 in |
| Rod load rating | 148,000 lbf |

**Output volume by liner size (gal/stroke):**

| Liner (in) | Vol (gal/stroke) | Max flow @ 110 SPM (gpm) |
|---|---|---|
| 4.0 | 0.899 | 98.9 |
| 4.5 | 1.138 | 125.2 |
| 5.0 | 1.405 | 154.6 |
| 5.5 | 1.700 | 187.0 |
| 6.0 | 2.022 | 222.4 |
| 6.5 | 2.372 | 260.9 |

---

## 2. Liner & Piston Selection Guide

### 2.1 Selection Criteria
- Select liner size to achieve required flow rate at ≤ 80% of maximum SPM
- Verify selected liner pressure rating exceeds maximum anticipated standpipe pressure
- For Wolfcamp A laterals: typical requirement is 400–600 gpm at 3,000–4,500 psi

### 2.2 Recommended Liner for Permian Basin Lateral Drilling
- **5.5 in liner**: 400–500 gpm range, pressure rating 5,000 psi — preferred for 6-1/8 in hole
- **6.0 in liner**: 500–600 gpm range, pressure rating 4,200 psi — preferred for 8-3/4 in hole
- **5.0 in liner**: high-pressure applications >4,500 psi standpipe

### 2.3 Piston Types
| Piston Type | Application | Service Life |
|---|---|---|
| Rubber bonded | WBM, low-abrasion | 200–400 hours |
| Urethane | OBM, high-abrasion | 400–800 hours |
| Bi-directional | High-pressure >5,000 psi | 150–300 hours |

---

## 3. Pump Efficiency & Volumetric Output

### 3.1 Pump Efficiency
- New pump with new liners/pistons: 98–99% volumetric efficiency
- Worn liners (>300 hours): 92–96%
- Worn pistons: 88–94%
- Rule of thumb: assume 95% efficiency for flow calculations

### 3.2 Actual Flow Rate Calculation
```
Q_actual (gpm) = SPM × Vol_per_stroke (gal) × Efficiency
```

### 3.3 Lag Time Calculation (Bottoms-Up)
```
Lag_strokes = Annular_volume (bbl) / Output_per_stroke (bbl/stroke)
Lag_time (min) = Lag_strokes / SPM
```
- 1 bbl = 42 gallons

---

## 4. Maintenance Procedures

### 4.1 Daily Checks
- [ ] Liner wash fluid level and condition (should be clean, no mud contamination)
- [ ] Piston rod packing — check for leaks at stuffing box
- [ ] Suction and discharge valve covers — no leaks
- [ ] Dampener pre-charge pressure (nitrogen): should be 1/3 of operating pressure
- [ ] Gear oil level in power end
- [ ] Crosshead pin lubrication

### 4.2 Liner & Piston Inspection Intervals
- **Every 100 hours**: Inspect piston condition; measure liner bore for wear
- **Every 200 hours**: Pull and inspect suction/discharge valves and seats
- **Every 500 hours**: Full fluid end inspection; replace all expendables

### 4.3 Liner Wear Limits
- Maximum liner bore wear: +0.010 in from nominal
- If bore is out-of-round by >0.005 in: replace liner
- Scoring or pitting >1/16 in deep: replace liner

### 4.4 Valve & Seat Replacement
Symptoms requiring immediate valve inspection:
- Pump pressure fluctuation >200 psi at constant SPM
- Knocking or chattering noise from fluid end
- Reduced output at same SPM (>5% drop in efficiency)

Valve replacement procedure:
1. Shut down pump; bleed pressure from discharge line
2. Remove valve cover (torque: 250–300 ft-lbs)
3. Extract valve assembly using valve puller tool
4. Inspect seat for erosion, pitting, or cracking
5. Replace valve and seat as a matched set
6. Torque valve cover to spec; pressure test to 500 psi before returning to service

### 4.5 Piston Rod Packing Adjustment
- Acceptable leak rate: 1–3 drops per minute at operating pressure
- If leaking >10 drops/min: tighten packing gland 1/4 turn; recheck
- If leaking persists after 3 adjustments: replace packing

---

## 5. Troubleshooting Guide

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| Pressure fluctuation ±200 psi | Worn/damaged valve | Inspect and replace valves |
| Low output at normal SPM | Worn liner or piston | Measure liner; replace piston |
| Knocking from fluid end | Cavitation or valve failure | Check suction pressure; inspect valves |
| Overheating power end | Low gear oil or bearing failure | Check oil level; inspect bearings |
| Piston rod leak | Worn packing | Adjust or replace packing |
| Suction pressure <15 psi | Plugged suction screen | Clean suction screen |
| Pump won't reach rated pressure | Worn liners, piston bypass | Replace fluid end expendables |

---

## 6. Hydraulics Reference

### 6.1 Equivalent Circulating Density (ECD)
```
ECD (ppg) = MW + (Annular_Pressure_Loss_psi / (0.052 × TVD_ft))
```

### 6.2 Annular Velocity
```
AV (ft/min) = (24.51 × Q_gpm) / (D_hole² - D_pipe²)
```
Where D_hole and D_pipe are in inches.

Minimum AV for cuttings transport:
- Vertical: 100–150 ft/min
- Deviated (>45°): 150–200 ft/min
- Horizontal: 200–300 ft/min (with rotation)

### 6.3 Bit Hydraulics — Nozzle Sizing
```
HHP_bit = (P_standpipe × Q_gpm) / 1714
Nozzle_area (in²) = Q_gpm / (C_d × √(P_nozzle_psi × 12,032))
```
- C_d (discharge coefficient) = 0.95 for standard nozzles
- Target: 3.5–5.0 HHP/in² for PDC bits in Wolfcamp A

## Pump Efficiency and Volumetric Output

### Volumetric Efficiency Factors
| Condition | Efficiency | Notes |
|-----------|-----------|-------|
| New liners/pistons | 97-99% | Factory specification |
| After 500 hours | 95-97% | Normal wear |
| After 1000 hours | 92-95% | Plan liner replacement |
| Worn liners (>1500 hrs) | < 90% | Replace immediately |
| Air in suction | 80-90% | Check suction line, charging pump |
| Plugged suction screen | 70-85% | Clean screen, check mud properties |
