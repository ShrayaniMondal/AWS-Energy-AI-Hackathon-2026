# Blowout Preventer (BOP) Testing & Operating Procedures
## Reference: API Standard 53 / API RP 64 — Permian Basin Operations

---

## 1. BOP Stack Configuration — Typical Permian Basin Land Rig

### 1.1 Stack Components (Bottom to Top)

| Component | Type | Bore (in) | Working Pressure (psi) |
|---|---|---|---|
| Drilling Spool | — | 13-5/8 | 5,000 |
| Annular BOP | Hydril GK | 13-5/8 | 5,000 |
| Double Ram BOP | Cameron Type U | 13-5/8 | 5,000 |
| Single Ram BOP | Cameron Type U | 13-5/8 | 5,000 |
| Bell Nipple | — | 20 | — |

Ram configurations (bottom to top):
- Lower rams: Pipe rams — 5-1/2 in drill pipe
- Upper rams: Blind/shear rams

### 1.2 Accumulator System
- Minimum accumulator capacity: 1.5× the volume required to close all BOP components
- Usable fluid volume (to 200 psi above pre-charge): ≥ 42 gallons per API 53
- Pre-charge pressure: 1,000 psi nitrogen
- Operating pressure: 3,000 psi
- Minimum closing time (annular): ≤ 30 seconds
- Minimum closing time (rams): ≤ 30 seconds

---

## 2. BOP Testing Requirements

### 2.1 Test Frequency
- **Initial test**: After installation, before spud
- **Routine test**: Every 14 days during drilling operations (per API 53 §5.4)
- **After any repair**: Full function and pressure test required
- **After disconnection**: Full test before reconnecting to wellbore

### 2.2 Pressure Test Procedure

**Low-pressure test (200–300 psi)**
1. Close component to be tested
2. Apply 200–300 psi from test pump
3. Hold for 5 minutes — zero pressure loss required
4. Bleed pressure; confirm zero before proceeding

**High-pressure test (70% of rated WP or MAASP, whichever is lower)**
1. Close component
2. Apply pressure slowly (max 500 psi/min)
3. Hold for 5 minutes — zero pressure loss required
4. For Permian Basin wells: typical high-pressure test = 3,500 psi

**Annular BOP test**
- Test to 70% of rated working pressure
- Annular elements tested with drill pipe in hole
- Acceptable leak rate: zero during 5-minute hold

### 2.3 Function Test Procedure
1. Verify accumulator pressure ≥ 2,800 psi before test
2. Close annular BOP — verify closure on pressure gauge
3. Open annular BOP — verify full open
4. Close lower pipe rams — verify closure
5. Open lower pipe rams
6. Close upper blind/shear rams — verify closure (NO drill string in hole)
7. Open upper blind/shear rams
8. Test choke and kill line valves — open/close cycle
9. Record all opening/closing times
10. Document in BOP test log (IADC BOP Test Report)

### 2.4 Acceptance Criteria
- All function tests: component must fully open and close
- All pressure tests: zero pressure loss over 5-minute hold
- Accumulator recharge time after full closure: ≤ 5 minutes
- Any failure: suspend drilling, notify company man, repair before resuming

---

## 3. Well Control Procedures

### 3.1 Kick Detection — Warning Signs
- Pit gain (flow check required if >1 bbl unexplained gain)
- Increased flow rate with pumps off
- Drilling break (sudden ROP increase >50%)
- Decrease in pump pressure with constant stroke rate
- String weight decrease (gas cutting mud)
- Mud weight out < mud weight in

### 3.2 Shut-In Procedure (Hard Shut-In — Preferred)
1. Pick up off bottom (minimum 1 stand)
2. Stop mud pumps
3. Close annular BOP (or pipe rams if annular unavailable)
4. Open HCR valve to choke manifold
5. Read and record SIDPP (Shut-In Drill Pipe Pressure)
6. Read and record SICP (Shut-In Casing Pressure)
7. Read and record pit gain volume
8. Notify company man and well control supervisor
9. Do NOT bleed pressure without authorization

### 3.3 Kill Methods
**Driller's Method (two-circulation)**
- Circulation 1: Circulate kick out with original mud weight
- Circulation 2: Circulate kill weight mud to surface
- Use when: kick volume >10 bbl or well control supervisor preference

**Wait-and-Weight Method (Engineer's Method)**
- Weight up mud to kill weight before circulating
- Single circulation to kill well
- Use when: kick volume <10 bbl, time permits

**Kill mud weight calculation:**
```
KMW (ppg) = OMW + (SIDPP / (0.052 × TVD))
```
Where: OMW = original mud weight, TVD = true vertical depth (ft)

### 3.4 Choke Manifold Operation
- Maintain constant BHP during kill circulation
- Adjust choke to hold SICP constant (Driller's Method) or calculated casing pressure schedule (W&W)
- Choke operator and pump operator must communicate every 5 strokes
- Record casing pressure, pump pressure, and strokes every 5 minutes

---

## 4. BOP Maintenance

### 4.1 Daily Inspection Checklist
- [ ] Accumulator pressure ≥ 2,800 psi
- [ ] Hydraulic fluid level in accumulator unit reservoir
- [ ] No visible leaks on BOP stack, choke/kill lines
- [ ] Remote panel indicators functional
- [ ] Choke manifold valves free-moving

### 4.2 Weekly Maintenance
- Lubricate all BOP operating rods and pins
- Check annular element condition (inspect for cuts or extrusion)
- Test remote BOP panel from driller's console
- Verify kill/choke line valve operation

### 4.3 Ram Packer Replacement Criteria
- Replace if: visible cuts, tears, or extrusion beyond 1/4 inch
- Replace if: fails to hold pressure during test
- Replace after: any shear event
- Typical service life: 50–75 closures or 6 months, whichever comes first

---

## 5. Emergency Procedures

### 5.1 Loss of Accumulator Pressure
1. Switch to manual pump (hand pump) immediately
2. Close nearest BOP component manually
3. Notify company man
4. Do not resume drilling until accumulator repaired and recharged

### 5.2 BOP Failure During Kick
1. Attempt secondary closure method (pipe rams if annular fails)
2. If all BOPs fail: activate emergency disconnect (if applicable)
3. Evacuate non-essential personnel
4. Notify operator, regulatory authority (Texas RRC), and well control company
5. Activate emergency response plan

### 5.3 Regulatory Reporting (Texas RRC)
- Blowout or loss of well control: notify Texas RRC within 24 hours
- Form W-3 (Well Blowout Report) required within 10 days
- Contact: Texas Railroad Commission, Oil & Gas Division, (512) 463-6792

## BOP Testing Requirements (API RP 53)

### Pressure Test Schedule
| Test Type | Frequency | Test Pressure | Hold Time | Acceptance |
|-----------|-----------|---------------|-----------|------------|
| Low pressure | Every 7 days | 200-300 psi | 5 min | No pressure drop |
| High pressure | Every 14 days | Rated WP | 5 min | No pressure drop |
| After BOP repair | Before resuming ops | Rated WP | 10 min | No pressure drop |
| After disconnection | Before resuming ops | Rated WP | 5 min | No pressure drop |
| Casing test | After cement job | 80% of min yield | 10 min | < 10 psi drop |

### Function Test Schedule
- Ram close/open: Every 7 days
- Annular close/open: Every 7 days
- Choke/kill valve operation: Every 7 days
- Accumulator precharge: Monthly (nitrogen pressure check)
- Remote panel operation: Every 7 days

### Accumulator Performance Requirements
- Close all BOPs + open one HCR valve with pumps off
- Minimum usable volume: 1.5× total close volume
- Precharge pressure: 1000 psi (nitrogen)
- Operating pressure: 1500-3000 psi
- Response time: annular close < 30 sec, ram close < 30 sec

## Well Control Decision Matrix

### Kick Detection Indicators
| Indicator | Severity | Action |
|-----------|----------|--------|
| Pit gain > 5 bbl | High | Flow check, shut in if confirmed |
| Pit gain 2-5 bbl | Medium | Flow check, monitor closely |
| Drilling break (ROP increase > 50%) | Medium | Flow check |
| Increase in return flow rate | High | Flow check, prepare to shut in |
| Decrease in pump pressure | Medium | Check for washout, flow check |
| Gas cut mud (< 0.5 ppg reduction) | Low | Monitor, treat mud |
| Gas cut mud (> 0.5 ppg reduction) | High | Weight up, flow check |

### Shut-In Procedures
1. Driller's Method: Shut in, record SIDPP/SICP, circulate kill weight mud
2. Wait and Weight: Shut in, weight up mud, circulate in one pass
3. Volumetric Method: For when circulation is not possible
