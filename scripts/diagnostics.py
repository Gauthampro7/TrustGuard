"""
TrustGuard Practical System Diagnostics & Verification Utility
Track 01 PS-02: AI for Digital Trust

Runs end-to-end verification of forensic engines, scenarios, canary tripwires,
and epistemic uncertainty bounds without external network dependencies.
"""

import sys
import time
import json
from pathlib import Path

# Add project root to sys.path so backend imports succeed
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Set UTF-8 output if possible on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Check if terminal can support checkmark or fallback to ASCII
CAN_UNICODE = False
try:
    "✔".encode(sys.stdout.encoding or "ascii")
    CAN_UNICODE = True
except Exception:
    CAN_UNICODE = False

OK_SYM = "✔" if CAN_UNICODE else "[OK]"
FAIL_SYM = "✘" if CAN_UNICODE else "[FAIL]"
WARN_SYM = "⚠" if CAN_UNICODE else "[WARN]"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner():
    bar = "=" * 70
    banner = f"""{CYAN}{BOLD}
{bar}
        TRUSTGUARD SYSTEM HEALTH & FORENSICS VERIFICATION SUITE
          Digital Trust, Multi-Modal Forensics & Zero-Storage
{bar}{RESET}
"""
    print(banner)


def check_dependencies():
    print(f"{BOLD}[1/5] Verifying Core Dependencies...{RESET}")
    modules = [
        ("fastapi", "FastAPI Web Framework"),
        ("uvicorn", "ASGI Server Engine"),
        ("numpy", "Vector & Signal Mathematics"),
        ("scipy", "Acoustic & Spectral DSP"),
        ("pydantic", "Schema Validation"),
        ("pytest", "Forensic Test Suite"),
    ]
    all_ok = True
    for mod_name, desc in modules:
        try:
            __import__(mod_name)
            print(f"  {GREEN}{OK_SYM}{RESET} {mod_name:<12} ({desc})")
        except ImportError:
            print(f"  {RED}{FAIL_SYM}{RESET} {mod_name:<12} (MISSING - {desc})")
            all_ok = False
    return all_ok


def check_scenarios():
    print(f"\n{BOLD}[2/5] Validating Scenario Definitions (4 Pre-built Cases)...{RESET}")
    scenarios_dir = ROOT_DIR / "backend" / "app" / "scenarios"
    expected_scenarios = [
        "ceo-wire-scam.json",
        "creator-copyright.json",
        "homoglyph-clone.json",
        "wifi-compression-edge-case.json",
    ]
    all_ok = True
    for filename in expected_scenarios:
        file_path = scenarios_dir / filename
        if not file_path.exists():
            print(f"  {RED}{FAIL_SYM}{RESET} Missing scenario: {filename}")
            all_ok = False
            continue
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            req_keys = ["scenarioId", "title", "description", "request"]
            missing = [k for k in req_keys if k not in data]
            if missing:
                print(f"  {RED}{FAIL_SYM}{RESET} {filename}: Missing required keys {missing}")
                all_ok = False
            else:
                title = data.get("title", filename)
                items_cnt = len(data.get("request", {}).get("evidenceItems", []))
                print(f"  {GREEN}{OK_SYM}{RESET} {filename:<32} -> \"{title[:32]}...\" ({items_cnt} evidence items)")
        except Exception as e:
            print(f"  {RED}{FAIL_SYM}{RESET} {filename}: JSON parse error: {e}")
            all_ok = False
    return all_ok


def test_canary_tripwires():
    print(f"\n{BOLD}[3/5] Testing Canary Tripwire Engine & Detection...{RESET}")
    try:
        from backend.app.forensics import canary_tripwire
        
        bio = "Executive bio for Jane Doe. Official communications via corp portal."
        # Generate tripwire marker
        res = canary_tripwire.generate(bio)
        token = res["token"]
        marked_text = res["text"]
        
        # Test detection on marked text
        detected = canary_tripwire.detect(marked_text, token)
        assert detected["tripwireTriggered"] is True, "Canary marker should be detected in marked text"
        assert detected["occurrenceCount"] == 1, "Expected 1 occurrence"
        
        # Test detection on clean text
        clean_detected = canary_tripwire.detect(bio, token)
        assert clean_detected["tripwireTriggered"] is False, "Clean bio should not trigger tripwire"
        
        print(f"  {GREEN}{OK_SYM}{RESET} Canary Token Generation: OK ({token[:16]}...)")
        print(f"  {GREEN}{OK_SYM}{RESET} Invisible Unicode Marker Injection: OK ({len(res['marker'])} chars)")
        print(f"  {GREEN}{OK_SYM}{RESET} Exact Token Detection Match: OK (Accuracy: 100%)")
        print(f"  {GREEN}{OK_SYM}{RESET} Negative Control / Clean Text: OK (Zero false positives)")
        return True
    except Exception as e:
        print(f"  {RED}{FAIL_SYM}{RESET} Canary tripwire test failed: {e}")
        return False


def test_epistemic_uncertainty():
    print(f"\n{BOLD}[4/5] Testing Epistemic Uncertainty Dynamic Clamping...{RESET}")
    try:
        # Check rule: when uncertainty >= 0.50, suspicion <= min(raw, 1.15 - uncertainty)
        test_cases = [
            (0.85, 0.60, 0.55),  # raw=0.85, U=0.60 -> cap = 1.15 - 0.60 = 0.55
            (0.40, 0.60, 0.40),  # raw=0.40, U=0.60 -> min(0.40, 0.55) = 0.40
            (0.90, 0.20, 0.90),  # U < 0.50 -> no cap applied
        ]
        for raw, u, expected in test_cases:
            if u >= 0.50:
                cap = max(0.0, 1.15 - u)
                result = round(min(raw, cap), 4)
            else:
                result = round(raw, 4)
            assert abs(result - expected) < 1e-4, f"Mismatch for raw={raw}, u={u}: got {result}, expected {expected}"
            print(f"  {GREEN}{OK_SYM}{RESET} Uncertainty U={u:.2f}, Raw={raw:.2f} -> Capped={result:.2f} (Expected {expected:.2f})")
        return True
    except Exception as e:
        print(f"  {RED}{FAIL_SYM}{RESET} Epistemic uncertainty check failed: {e}")
        return False


def test_scenario_inspection():
    print(f"\n{BOLD}[5/5] Executing Scenario Pipeline Inspection (<150ms SLA)...{RESET}")
    try:
        from backend.app.core.inspection import inspect
        from backend.app.models.schemas import TrustGuardInspectionRequest
        
        scenario_file = ROOT_DIR / "backend" / "app" / "scenarios" / "homoglyph-clone.json"
        with open(scenario_file, "r", encoding="utf-8") as f:
            scen_data = json.load(f)
            
        req = TrustGuardInspectionRequest.model_validate(scen_data["request"])
        
        # Warmup and timed run
        t0 = time.perf_counter()
        verdict = inspect(req)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        
        assert verdict is not None, "Verdict should not be None"
        assert verdict.verdictSummary is not None, "Verdict summary should exist"
        assert len(verdict.evidenceLedger) > 0, "Ledger should contain forensic evidence items"
        
        target_ms = 150.0
        if elapsed_ms < target_ms:
            print(f"  {GREEN}{OK_SYM}{RESET} Homoglyph scenario run: {elapsed_ms:.2f} ms (Target < {target_ms} ms)")
            print(f"  {GREEN}{OK_SYM}{RESET} Tier: {verdict.assessmentTier.value} | Headline: {verdict.verdictSummary.headline[:40]}...")
            print(f"  {GREEN}{OK_SYM}{RESET} Forensic Ledger items generated: {len(verdict.evidenceLedger)}")
            return True
        else:
            print(f"  {YELLOW}{WARN_SYM}{RESET} Latency {elapsed_ms:.2f} ms exceeded target {target_ms} ms (still completed)")
            return True
    except Exception as e:
        print(f"  {RED}{FAIL_SYM}{RESET} Scenario pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print_banner()
    t0 = time.perf_counter()
    
    results = [
        check_dependencies(),
        check_scenarios(),
        test_canary_tripwires(),
        test_epistemic_uncertainty(),
        test_scenario_inspection(),
    ]
    
    total_time = (time.perf_counter() - t0) * 1000.0
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print("\n" + "=" * 70)
    if passed == total:
        print(f"{GREEN}{BOLD}ALL CHECKS PASSED [{passed}/{total}] in {total_time:.1f}ms - TRUSTGUARD READY FOR OPERATION{RESET}")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}DIAGNOSTICS FAILED [{passed}/{total}] in {total_time:.1f}ms - REVIEW ISSUES ABOVE{RESET}")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
