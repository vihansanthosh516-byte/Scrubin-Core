"""
ScrubIn Simulation Test Agent
============================
Automated verification of the physiological reserve & cumulative damage systems:
  1. Happy Path (stock -> complete)
  2. Complication & Recovery (stock -> branched -> stock)
  3. Mortality Path (branched -> deceased via vital decay)
  4. Vitals Drift (vitals vary naturally)
  5. Refractory Shock / Point of No Return (reserve < 30% keeps mode 'branched')
  6. Direct Mistake Limit Death (4 complications = death)
"""

import time
import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

FASTAPI_URL = "http://localhost:8001"

def _correct_option(options, complication):
    """Pick the intervention that treats the active complication.

    The API sanitizes decisions (no correctForComplications), so match the
    known clinical intervention labels for each complication."""
    hints = {
        "infection": ["antibiotic", "irrigat", "source control", "debride"],
        "hemorrhage": ["ligat", "cautery", "pack", "transfuse", "fluid bolus"],
        "hypoxia": ["intubat", "oxygen", "o₂", "o2", "cricothyroidotomy", "airway"],
        "anaphylaxis": ["intubat", "cricothyroidotomy", "epinephrine"],
        "cardiac_arrhythmia": ["cardioversion"],
        "fluid_overload": ["diuretic", "furosemide", "lasix"],
        "nerve_injury": ["opioid", "analges"],
        "thrombosis": ["anticoagul", "heparin"],
    }
    for o in options or []:
        label = (o.get("label") or "").lower()
        if any(h in label for h in hints.get(complication, [])):
            return o
    return options[0] if options else None


class SimulationTestAgent:
    def __init__(self, base_url=FASTAPI_URL):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0
        print(f"\n[Test Agent] Target: {self.base_url}")

    def _assert(self, condition, msg):
        if condition:
            self.passed += 1
        else:
            self.failed += 1
            print(f"   [FAIL] ASSERTION FAILED: {msg}")

    # -- TEST 1 ──────────────────────────────────────────────────────────────
    def test_happy_path(self):
        """Start -> advance ticks (stock mode) -> complete."""
        print("\n=== TEST 1: Happy Path (Stock -> Complete) ===")

        res = requests.post(f"{self.base_url}/start", json={"procedure": "appendectomy"})
        self._assert(res.status_code == 200, f"Start returned {res.status_code}")
        data = res.json()
        sid = data.get("session_id")
        print(f"   Session started: {sid}")
        self._assert(data.get("mode") == "stock", f"Initial mode should be 'stock', got '{data.get('mode')}'")
        self._assert(data.get("physiological_reserve") == 100.0, f"Initial reserve should be 100, got {data.get('physiological_reserve')}")

        for i in range(3):
            tick_res = requests.post(f"{self.base_url}/tick", json={"session_id": sid})
            self._assert(tick_res.status_code == 200, f"Tick {i+1} failed")
            td = tick_res.json()
            vitals = td.get("vitals", {})
            self._assert(td.get("mode") == "stock", f"Mode drifted to {td.get('mode')} on tick {i+1}")
            print(f"   Tick {i+1}: mode={td.get('mode')} | BP={vitals.get('bp_systolic')} | HR={vitals.get('heart_rate')} | SpO2={vitals.get('spo2')}")

        comp_res = requests.post(f"{self.base_url}/complete", json={"session_id": sid})
        self._assert(comp_res.status_code == 200, f"Complete returned {comp_res.status_code}")
        comp_data = comp_res.json()
        self._assert(comp_data.get("completed") == True, f"completed should be True, got {comp_data.get('completed')}")
        print(f"   Procedure completed! completed={comp_data.get('completed')}")

    # -- TEST 2 ──────────────────────────────────────────────────────────────
    def test_complication_and_recovery(self):
        """Start -> trigger complication (branched) -> resolve decision -> back to stock."""
        print("\n=== TEST 2: Complication & Recovery (Stock -> Branched -> Stock) ===")

        res = requests.post(f"{self.base_url}/start", json={"procedure": "appendectomy"})
        data = res.json()
        sid = data.get("session_id")
        print(f"   Session started: {sid}")

        comp_res = requests.post(f"{self.base_url}/complicate", json={
            "session_id": sid,
            "complication": "hemorrhage"
        })
        self._assert(comp_res.status_code == 200, f"Complicate returned {comp_res.status_code}")
        comp_data = comp_res.json()
        self._assert(comp_data.get("mode") == "branched", f"Mode should be 'branched', got '{comp_data.get('mode')}'")
        self._assert(comp_data.get("active_complication") == "hemorrhage", f"Active complication mismatch")
        self._assert(comp_data.get("physiological_reserve") == 75.0, f"Reserve should drop to 75.0, got {comp_data.get('physiological_reserve')}")
        print(f"   Complication triggered! mode={comp_data.get('mode')} | reserve={comp_data.get('physiological_reserve')}%")

        pending = comp_data.get("pending_decision")
        self._assert(pending is not None, "Pending decision should exist after complication")

        if pending:
            decision_id = pending["id"]
            options = pending.get("options", [])
            correct_opt = _correct_option(options, "hemorrhage")

            if correct_opt:
                decide_res = requests.post(f"{self.base_url}/decide", json={
                    "session_id": sid,
                    "decision_id": decision_id,
                    "option_id": correct_opt["id"]
                })
                self._assert(decide_res.status_code == 200, f"Decide returned {decide_res.status_code}")
                decide_data = decide_res.json()
                dr = decide_data.get("decision_result", {})
                print(f"   Decision result: wasCorrect={dr.get('wasCorrect')} | mode={decide_data.get('mode')} | reserve={decide_data.get('physiological_reserve')}%")
                if dr.get("wasCorrect"):
                    self._assert(decide_data.get("mode") == "stock", f"Mode should recover to 'stock', got '{decide_data.get('mode')}'")
                    self._assert(decide_data.get("physiological_reserve") == 75.0, "Reserve should remain at 75.0 upon stock recovery")

    # -- TEST 3 ──────────────────────────────────────────────────────────────
    def test_mortality_path(self):
        """Start -> trigger complication -> tick until vitals decay causes death."""
        print("\n=== TEST 3: Mortality Path (Branched -> Deceased via Vital Decay) ===")

        res = requests.post(f"{self.base_url}/start", json={"procedure": "appendectomy"})
        sid = res.json().get("session_id")

        requests.post(f"{self.base_url}/complicate", json={
            "session_id": sid,
            "complication": "hemorrhage"
        })
        print(f"   Hemorrhage triggered! Ticking vitals to death...")

        max_ticks = 50
        deceased = False
        for i in range(max_ticks):
            tick_res = requests.post(f"{self.base_url}/tick", json={"session_id": sid})
            td = tick_res.json()
            mode = td.get("mode")
            vitals = td.get("vitals", {})
            bp = vitals.get("bp_systolic", 0)
            reserve = td.get("physiological_reserve", 0)

            if i % 5 == 0 or mode == "deceased":
                print(f"   Tick {i+1:02d}: mode={mode} | BP={bp:.1f} | Reserve={reserve:.1f}%")

            if mode == "deceased":
                deceased = True
                print(f"   Patient DECEASED at tick {i+1}!")
                self._assert(td.get("completed") == True, "completed should be True on death")
                break

            time.sleep(0.05)

        self._assert(deceased, "Patient should have died within 50 ticks of hemorrhage")

    # -- TEST 4 ──────────────────────────────────────────────────────────────
    def test_vitals_not_stationary(self):
        """Verify that vitals change over time (not flatlined)."""
        print("\n=== TEST 4: Vitals Drift (Not Stationary) ===")

        res = requests.post(f"{self.base_url}/start", json={"procedure": "appendectomy"})
        sid = res.json().get("session_id")

        snapshots = []
        for i in range(5):
            tick_res = requests.post(f"{self.base_url}/tick", json={"session_id": sid})
            vitals = tick_res.json().get("vitals", {})
            snapshots.append(vitals.get("heart_rate", 0))

        unique_hr = len(set(round(v, 1) for v in snapshots))
        self._assert(unique_hr > 1, f"HR should vary over ticks, got {snapshots}")
        print(f"   HR snapshots: {[f'{v:.1f}' for v in snapshots]} | Unique values: {unique_hr}")

    # -- TEST 5 ──────────────────────────────────────────────────────────────
    def test_refractory_shock(self):
        """Start -> 3 complications (reserve drops to 25%) -> correct option -> mode remains branched."""
        print("\n=== TEST 5: Refractory Shock / Point of No Return (<30% Reserve) ===")

        # 1. Start session
        res = requests.post(f"{self.base_url}/start", json={"procedure": "appendectomy"})
        sid = res.json().get("session_id")

        # 2. Trigger first mistake
        comp1 = requests.post(f"{self.base_url}/complicate", json={"session_id": sid, "complication": "hemorrhage"}).json()
        self._assert(comp1.get("physiological_reserve") == 75.0, f"Expected 75.0 reserve, got {comp1.get('physiological_reserve')}")

        # 3. Trigger second mistake
        comp2 = requests.post(f"{self.base_url}/complicate", json={"session_id": sid, "complication": "hypoxia"}).json()
        self._assert(comp2.get("physiological_reserve") == 50.0, f"Expected 50.0 reserve, got {comp2.get('physiological_reserve')}")

        # 4. Trigger third mistake -> reserve drops to 25.0% (Refractory Shock threshold < 30%)
        comp3 = requests.post(f"{self.base_url}/complicate", json={"session_id": sid, "complication": "infection"}).json()
        self._assert(comp3.get("physiological_reserve") == 25.0, f"Expected 25.0 reserve, got {comp3.get('physiological_reserve')}")
        self._assert(comp3.get("mode") == "branched", f"Expected mode to be 'branched', got '{comp3.get('mode')}'")

        pending = comp3.get("pending_decision")
        self._assert(pending is not None, "Pending decision should exist")

        if pending:
            decision_id = pending["id"]
            options = pending.get("options", [])
            correct_opt = _correct_option(options, "infection")

            if correct_opt:
                # Submit correct recovery choice
                decide_res = requests.post(f"{self.base_url}/decide", json={
                    "session_id": sid,
                    "decision_id": decision_id,
                    "option_id": correct_opt["id"]
                })
                decide_data = decide_res.json()
                print(f"   Correct decision submitted at 25% reserve.")
                
                # Check that mode remains branched due to refractory shock
                self._assert(decide_data.get("mode") == "branched", f"Mode should remain 'branched' due to low reserve, got '{decide_data.get('mode')}'")
                
                # Check that the refractory warning was appended to events
                events = decide_data.get("events", [])
                warning_found = any("Refractory Shock" in ev for ev in events)
                self._assert(warning_found, "Refractory Shock event warning should be appended")
                print("   Patient is locked in Refractory Shock as expected!")

    # -- TEST 6 ──────────────────────────────────────────────────────────────
    def test_direct_mistake_limit_death(self):
        """Start -> 4 complications (reserve drops to 0%) -> immediate death (deceased mode)."""
        print("\n=== TEST 6: Mistake Limit Death (4 Complications = Death) ===")

        res = requests.post(f"{self.base_url}/start", json={"procedure": "appendectomy"})
        sid = res.json().get("session_id")

        # 1-3 mistakes
        requests.post(f"{self.base_url}/complicate", json={"session_id": sid, "complication": "hemorrhage"})
        requests.post(f"{self.base_url}/complicate", json={"session_id": sid, "complication": "hypoxia"})
        requests.post(f"{self.base_url}/complicate", json={"session_id": sid, "complication": "infection"})

        # 4th mistake -> reserve goes to 0 -> immediate transition to deceased
        death_res = requests.post(f"{self.base_url}/complicate", json={"session_id": sid, "complication": "thrombosis"})
        self._assert(death_res.status_code == 200, f"Complicate returned {death_res.status_code}")
        death_data = death_res.json()
        self._assert(death_data.get("mode") == "deceased", f"Expected mode to be 'deceased', got '{death_data.get('mode')}'")
        self._assert(death_data.get("completed") == True, "completed should be True")
        self._assert(death_data.get("physiological_reserve") == 0.0, f"Expected reserve to be 0.0, got {death_data.get('physiological_reserve')}")
        
        events = death_data.get("events", [])
        death_msg_found = any("reserve exhausted" in ev.lower() or "reserve depleted" in ev.lower() for ev in events)
        self._assert(death_msg_found, "Exhaustion failure message should be present in events")
        print(f"   Patient died immediately on 4th mistake. Completed: {death_data.get('completed')} | Reserve: {death_data.get('physiological_reserve')}%")


    def run_all(self):
        try:
            hc = requests.get(f"{self.base_url}/health", timeout=3)
            print(f"   Health: {hc.json()}")
        except Exception as e:
            print(f"   Cannot reach {self.base_url}: {e}")
            print("   Make sure the FastAPI server is running: python server.py")
            sys.exit(1)

        self.test_happy_path()
        self.test_complication_and_recovery()
        self.test_mortality_path()
        self.test_vitals_not_stationary()
        self.test_refractory_shock()
        self.test_direct_mistake_limit_death()

        print(f"\n{'='*60}")
        print(f"  RESULTS: {self.passed} passed, {self.failed} failed")
        print(f"{'='*60}")
        if self.failed > 0:
            print("  SOME TESTS FAILED")
            sys.exit(1)
        else:
            print("  ALL TESTS PASSED!")


if __name__ == "__main__":
    agent = SimulationTestAgent()
    agent.run_all()
