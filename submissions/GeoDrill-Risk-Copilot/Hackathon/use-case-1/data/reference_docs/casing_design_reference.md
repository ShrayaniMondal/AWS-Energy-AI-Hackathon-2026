# Casing Design Reference Manual

## Document Information

| Field | Value |
|-------|-------|
| Document Number | CASING-DES-2024-001 |
| Revision | Rev. 3 |
| Effective Date | January 2024 |
| Classification | Drilling Engineering Reference |
| Applicable Basins | Permian (Midland/Delaware), Eagle Ford, Williston (Bakken) |

---

## 1. Casing String Types and Specifications

### 1.1 Conductor Casing — 20" OD

| Parameter | Specification |
|-----------|--------------|
| Outer Diameter | 20.000 in |
| Nominal Weight | 94 lb/ft |
| Grade | H-40 or J-55 |
| Connection | Buttress Thread (BTC) |
| Setting Depth | 80–150 ft (driven or drilled/cemented) |
| Primary Function | Structural support, divert shallow gas, prevent washout |

Conductor casing is the first string set. In the Permian Basin, conductor is typically driven to refusal
in surface sand/shale formations. In the Williston Basin (Bakken wells), glacial till may require
drilling and cementing the conductor to 100–150 ft.

### 1.2 Surface Casing — 13-3/8" OD

| Parameter | Specification |
|-----------|--------------|
| Outer Diameter | 13.375 in |
| Nominal Weight | 54.5–68 lb/ft |
| Grade | J-55 or L-80 |
| Connection | Buttress Thread (BTC) or ST&C |
| Setting Depth | 2,000–3,100 ft (varies by basin) |
| Primary Function | Protect freshwater aquifers, BOP support, kick tolerance |

Surface casing setting depths by well (from `formation_tops.csv`):

| Well | Formation at Shoe | Setting Depth (MD) | Setting Depth (TVD) |
|------|-------------------|--------------------|---------------------|
| PERM-2847 | Surface Casing / Spraberry top | 2,500 ft | 2,500 ft |
| PERM-3201 | Surface Casing / Bone Spring Upper top | 3,000 ft | 3,000 ft |
| EF-1105 | Surface Casing / Pearsall Shale top | 2,000 ft | 2,000 ft |
| BAK-0892 | Surface Casing / Bakken top | 2,500 ft | 2,500 ft |
| PERM-4102 | Surface Casing / Spraberry top | 2,600 ft | 2,600 ft |
| PERM-4305 | Surface Casing / Bone Spring Upper top | 2,800 ft | 2,800 ft |
| EF-2201 | Surface Casing / Pearsall Shale top | 2,100 ft | 2,100 ft |
| BAK-1456 | Surface Casing / Bakken Upper top | 2,600 ft | 2,600 ft |
| DL-0773 | Surface Casing / Bone Spring Upper top | 3,100 ft | 3,100 ft |


### 1.3 Intermediate Casing — 9-5/8" OD

| Parameter | Specification |
|-----------|--------------|
| Outer Diameter | 9.625 in |
| Nominal Weight | 40–53.5 lb/ft |
| Grade | L-80 or P-110 |
| Connection | Buttress Thread (BTC) or Premium (VAM TOP) |
| Setting Depth | 7,000–12,500 ft (formation dependent) |
| Primary Function | Isolate problem zones, manage pore pressure transitions |

Intermediate casing is set across the transition from normal to abnormal pore pressure. Setting
depth is determined by the fracture gradient of the weakest exposed formation versus the mud
weight required to control the next open-hole section.

Intermediate casing setting depth criteria by formation:

| Formation | Typical Pore Pressure (ppg) | Fracture Gradient (ppg) | Recommended Shoe Depth |
|-----------|-----------------------------|-------------------------|------------------------|
| Wolfcamp A | 10.0–10.4 | 13.0–13.2 | 7,200–8,600 ft MD |
| Wolfcamp B | 10.2–10.7 | 12.8–13.0 | 8,100–9,600 ft MD |
| Eagle Ford Shale | 9.3–9.8 | 13.0–13.1 | 6,500–9,900 ft MD |
| Bakken | 10.5–11.1 | 13.5–13.6 | 9,200–9,600 ft MD |
| Bone Spring Upper | 9.9–10.6 | 13.4–13.6 | 8,200–8,800 ft MD |
| Bone Spring Lower | 10.4–12.7 | 13.0–14.1 | 8,500–12,200 ft MD |
| Spraberry | 9.2–9.6 | 13.5–13.6 | 5,500–5,600 ft MD |
| Dean | 9.5–9.9 | 13.2–13.3 | 7,000–7,300 ft MD |
| Austin Chalk | 9.5–10.0 | 12.8–12.9 | 9,800–13,000 ft MD |
| Three Forks | 11.0–11.6 | 13.0–13.1 | 9,500–10,400 ft MD |

### 1.4 Production Casing — 5-1/2" OD

| Parameter | Specification |
|-----------|--------------|
| Outer Diameter | 5.500 in |
| Nominal Weight | 17–23 lb/ft |
| Grade | P-110 or Q-125 |
| Connection | Premium (VAM TOP, TenarisHydril Blue, Hunting SEAL-LOCK) |
| Setting Depth | TD (total depth, through lateral in horizontal wells) |
| Primary Function | Wellbore integrity for production, completion isolation |

Production casing must withstand burst pressures during stimulation (frac operations up to
10,000 psi treating pressure) and collapse pressures during production drawdown. Premium
connections are mandatory for horizontal wells to ensure gas-tight seals through the build section.

---

## 2. Casing Grade Specifications

### 2.1 J-55

| Property | Value |
|----------|-------|
| Minimum Yield Strength | 55,000 psi |
| Minimum Tensile Strength | 75,000 psi |
| Collapse Resistance (5-1/2", 17 lb/ft) | 4,740 psi |
| Burst Resistance (5-1/2", 17 lb/ft) | 6,190 psi |
| Body Yield (5-1/2", 17 lb/ft) | 367,000 lb |
| Typical Application | Conductor, surface casing in low-pressure environments |
| Heat Treatment | Normalized or normalized and tempered |
| H₂S Service | Not recommended (non-sour service only) |

### 2.2 L-80

| Property | Value |
|----------|-------|
| Minimum Yield Strength | 80,000 psi |
| Maximum Yield Strength | 95,000 psi |
| Minimum Tensile Strength | 95,000 psi |
| Collapse Resistance (9-5/8", 47 lb/ft) | 5,310 psi |
| Burst Resistance (9-5/8", 47 lb/ft) | 6,870 psi |
| Body Yield (9-5/8", 47 lb/ft) | 1,086,000 lb |
| Typical Application | Surface and intermediate casing, sour service environments |
| Heat Treatment | Quenched and tempered |
| H₂S Service | Suitable per NACE MR0175 / ISO 15156 |

### 2.3 P-110

| Property | Value |
|----------|-------|
| Minimum Yield Strength | 110,000 psi |
| Maximum Yield Strength | 140,000 psi |
| Minimum Tensile Strength | 125,000 psi |
| Collapse Resistance (5-1/2", 23 lb/ft) | 10,430 psi |
| Burst Resistance (5-1/2", 23 lb/ft) | 12,960 psi |
| Body Yield (5-1/2", 23 lb/ft) | 694,000 lb |
| Typical Application | Intermediate and production casing, high-pressure wells |
| Heat Treatment | Quenched and tempered |
| H₂S Service | Not recommended without special processing |

---

## 3. Cement Program

### 3.1 Lead Slurry Design

| Parameter | Specification |
|-----------|--------------|
| Slurry Weight | 12.5–13.5 ppg |
| Yield | 1.50–1.75 ft³/sack |
| Thickening Time | 4–6 hours (BHCT dependent) |
| Compressive Strength (24 hr) | ≥ 500 psi |
| Free Water | ≤ 0.5 mL |
| Fluid Loss | ≤ 200 mL/30 min |
| Additives | Extenders (bentonite, pozzolan), retarders, fluid loss agents |

### 3.2 Tail Slurry Design

| Parameter | Specification |
|-----------|--------------|
| Slurry Weight | 15.8–16.4 ppg |
| Yield | 1.15–1.22 ft³/sack |
| Thickening Time | 3–5 hours (BHCT dependent) |
| Compressive Strength (24 hr) | ≥ 2,000 psi |
| Free Water | 0 mL |
| Fluid Loss | ≤ 50 mL/30 min |
| Additives | Dispersants, retarders, gas migration agents, fluid loss agents |

### 3.3 Top of Cement (TOC) Requirements

| Casing String | TOC Requirement | Regulatory Basis |
|---------------|-----------------|------------------|
| Conductor (20") | Surface | State regulations |
| Surface (13-3/8") | Surface (full returns) | 40 CFR 146 / state UIC rules |
| Intermediate (9-5/8") | 500 ft above previous shoe | API RP 10B-2, operator policy |
| Production (5-1/2") | Above kickoff point (KOP) | Operator policy, frac isolation |

### 3.4 Pressure Test Criteria

| Test | Pressure | Hold Time | Pass Criteria |
|------|----------|-----------|---------------|
| Surface casing shoe test | FIT to 14.0 ppg EMW | 10 minutes | ≤ 5% pressure decline |
| Intermediate casing shoe test | FIT to next section MW + 0.5 ppg | 10 minutes | ≤ 5% pressure decline |
| Production casing pressure test | 80% of burst rating or max treating pressure | 30 minutes | ≤ 5% pressure decline |
| Casing lap test (liner) | 500 psi above max expected annular pressure | 10 minutes | ≤ 5% pressure decline |

---

## 4. Casing Wear Limits and Inspection Criteria

### 4.1 Wear Classification

| Wear Category | Wall Loss (%) | Action Required |
|---------------|---------------|-----------------|
| Class A (New) | 0% | No restrictions |
| Class B (Good) | ≤ 20% | Full service, document wear |
| Class C (Fair) | 20–30% | Reduced pressure rating, monitor |
| Class D (Marginal) | 30–40% | Restricted service, engineering review |
| Reject | > 40% | Remove from service |

### 4.2 Inspection Methods

| Method | Application | Detection Capability |
|--------|-------------|---------------------|
| Electromagnetic (EM) | Internal/external wall loss | ± 5% wall thickness |
| Ultrasonic (UT) | Precise wall thickness | ± 0.5% wall thickness |
| Caliper (multi-finger) | Internal diameter profiling | ± 0.001 in |
| Visual / borescope | Surface defects, corrosion | Qualitative |

### 4.3 Wear Prediction

Casing wear rate depends on rotating hours, dogleg severity, and tool joint hardfacing:

- Wear rate (in/hr) ≈ 0.0001 × DLS (°/100ft) × RPM / 100
- Maximum allowable wear before re-evaluation: 25% of nominal wall thickness
- Wear monitoring interval: every 500 rotating hours or at each casing point

---

## 5. Casing Running Procedures

### 5.1 Pre-Run Checklist

1. Verify casing tally matches well plan (joint count, weights, grades)
2. Drift all joints with API drift mandrel (5-1/2": 4.653 in drift diameter)
3. Inspect threads for damage — reject any joint with thread galling or cross-threading
4. Verify float equipment (float collar, float shoe, centralizers) quantity and placement
5. Confirm centralizer placement plan: one per joint through build section, every third joint in vertical
6. Verify fill-up schedule: fill every 5 joints to prevent collapse from hydrostatic imbalance

### 5.2 Makeup Torque Specifications

| Casing Size | Connection | Optimal Torque (ft-lb) | Min Torque (ft-lb) | Max Torque (ft-lb) |
|-------------|------------|------------------------|---------------------|---------------------|
| 20" (94 lb/ft) | BTC | 18,500 | 15,700 | 21,300 |
| 13-3/8" (68 lb/ft) | BTC | 13,200 | 11,200 | 15,200 |
| 9-5/8" (47 lb/ft) | BTC | 8,800 | 7,500 | 10,100 |
| 9-5/8" (47 lb/ft) | VAM TOP | 12,500 | 10,600 | 14,400 |
| 5-1/2" (23 lb/ft) | BTC | 5,400 | 4,600 | 6,200 |
| 5-1/2" (23 lb/ft) | VAM TOP | 7,800 | 6,600 | 9,000 |
| 5-1/2" (17 lb/ft) | BTC | 4,100 | 3,500 | 4,700 |

### 5.3 Running Speed Limits

| Condition | Maximum Running Speed |
|-----------|-----------------------|
| Open hole, no restrictions | 3 joints/min (≈ 120 ft/min) |
| Through tight spots or doglegs | 1 joint/min (≈ 40 ft/min) |
| Through BOP stack | Controlled, no spinning |
| Last 500 ft to TD | 1 joint/min, circulate bottoms-up |

### 5.4 Post-Run Verification

1. Circulate bottoms-up (minimum 1.5× annular volume)
2. Reciprocate casing ± 30 ft during circulation (if hole conditions allow)
3. Pressure test casing to specified test pressure before cementing
4. Verify casing is at planned depth (± 5 ft tolerance)
5. Record final hanging weight and compare to calculated string weight (± 10% tolerance)

---

## 6. Formation-Specific Casing Design Considerations

### 6.1 Wolfcamp A/B (Permian Basin)

- Pore pressure: 10.0–10.7 ppg; fracture gradient: 12.8–13.2 ppg
- Intermediate casing (9-5/8") set at Wolfcamp A top (7,200–8,600 ft MD)
- Production casing (5-1/2") P-110 required for frac operations (10,000+ psi treating)
- H₂S potential: low to moderate — L-80 acceptable for intermediate string

### 6.2 Eagle Ford Shale

- Pore pressure: 9.3–9.8 ppg; fracture gradient: 13.0–13.1 ppg
- Intermediate casing set at Eagle Ford top (6,500–6,600 ft MD)
- Austin Chalk above Eagle Ford may require lost circulation material (LCM)
- Production casing: P-110 with premium connections for horizontal lateral

### 6.3 Bakken / Three Forks (Williston Basin)

- Pore pressure: 10.5–11.6 ppg; fracture gradient: 13.0–13.6 ppg
- Higher pore pressures require L-80 minimum for intermediate casing
- Three Forks dolomite is abrasive — monitor casing wear during drilling
- Long horizontal laterals (10,000+ ft) require torque-and-drag analysis for casing running

### 6.4 Bone Spring (Delaware Basin)

- Pore pressure: 9.9–12.7 ppg (wide range, depth dependent)
- Lower Bone Spring may approach fracture gradient — careful mud weight management
- Intermediate casing set at Bone Spring Lower top or within Bone Spring interval
- DL-0773 example: Bone Spring Lower pore pressure 12.1 ppg vs fracture gradient 14.1 ppg

### 6.5 Spraberry / Dean (Midland Basin)

- Pore pressure: 9.2–9.9 ppg; fracture gradient: 13.2–13.6 ppg
- Relatively benign pressure environment — J-55 or L-80 surface casing acceptable
- Dean sandstone may produce water — cement integrity critical at Dean shoe
- Spraberry siltstone can cause differential sticking — maintain adequate overbalance

---

## Appendix A: API Casing Dimensions Quick Reference

| OD (in) | Weight (lb/ft) | ID (in) | Drift (in) | Wall (in) |
|---------|----------------|---------|------------|-----------|
| 20.000 | 94.00 | 19.124 | 18.936 | 0.438 |
| 13.375 | 54.50 | 12.615 | 12.459 | 0.380 |
| 13.375 | 68.00 | 12.415 | 12.259 | 0.480 |
| 9.625 | 40.00 | 8.835 | 8.679 | 0.395 |
| 9.625 | 47.00 | 8.681 | 8.525 | 0.472 |
| 9.625 | 53.50 | 8.535 | 8.379 | 0.545 |
| 5.500 | 17.00 | 4.892 | 4.653 | 0.304 |
| 5.500 | 20.00 | 4.778 | 4.539 | 0.361 |
| 5.500 | 23.00 | 4.670 | 4.431 | 0.415 |

---

*Reference Standards: API 5CT (Casing and Tubing), API RP 10B-2 (Cement Testing), API RP 65-2 (Cementing Annular Spaces), NACE MR0175/ISO 15156 (Sour Service Materials)*
