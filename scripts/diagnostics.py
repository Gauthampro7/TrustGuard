"""
TrustGuard Practical System Diagnostics & Verification Utility
Track 01 PS-02: AI for Digital Trust

Runs end-to-end verification of forensic engines, all four scenarios, canary tripwires,
and production epistemic uncertainty bounds without external network dependencies.
"""

from copy import deepcopy
import importlib.metadata
import json
from pathlib import Path
import sys
import time

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
    print(f"{BOLD}[1/5] Verifying Core Dependencies & Package Versions...{RESET}")
    modules = [
        ("fastapi", "FastAPI Web Framework"),
        ("uvicorn", "ASGI Server Engine"),
        ("numpy", "Vector & Signal Mathematics"),
        ("reportlab", "PDF Audit Rendering"),
        ("cryptography", "Ed25519 Record Integrity"),
        ("httpx", "Local API Test Transport"),
        ("pydantic", "Schema Validation"),
        ("pytest", "Forensic Test Suite"),
    ]
    all_ok = True
    for mod_name, desc in modules:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", None)
            if not ver:
                try:
                    ver = importlib.metadata.version(mod_name)
                except Exception:
                    ver = "installed"
            print(f"  {GREEN}{OK_SYM}{RESET} {mod_name:<14} v{ver:<10} ({desc})")
        except ImportError:
            print(f"  {RED}{FAIL_SYM}{RESET} {mod_name:<14} (MISSING - {desc})")
            all_ok = False
    return all_ok


def check_scenarios():
    print(f"\n{BOLD}[2/5] Validating Scenario Definitions (Pydantic Schema & Simulation Labels)...{RESET}")
    from backend.app.models.schemas import TrustGuardInspectionRequest

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

            if data.get("simulation") is not True:
                print(f"  {RED}{FAIL_SYM}{RESET} {filename}: 'simulation' must be explicitly True")
                all_ok = False
                continue

            req_dict = data.get("request")
            if not req_dict:
                print(f"  {RED}{FAIL_SYM}{RESET} {filename}: Missing 'request' object")
                all_ok = False
                continue

            # Validate against production Pydantic model
            req_model = TrustGuardInspectionRequest.model_validate(req_dict)
            title = data.get("title", filename)
            items_cnt = len(req_model.evidenceItems)
            print(f"  {GREEN}{OK_SYM}{RESET} {filename:<32} -> \"{title[:30]}...\" ({items_cnt} evidence items, simulation=True)")
        except Exception as e:
            print(f"  {RED}{FAIL_SYM}{RESET} {filename}: Validation error: {e}")
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
        print(f"  {GREEN}{OK_SYM}{RESET} Exact Token Detection Match: positive control passed")
        print(f"  {GREEN}{OK_SYM}{RESET} Negative Control / Clean Text: negative control passed")
        return True
    except Exception as e:
        print(f"  {RED}{FAIL_SYM}{RESET} Canary tripwire test failed: {e}")
        return False


def test_epistemic_uncertainty():
    print(f"\n{BOLD}[4/5] Testing Epistemic Uncertainty Dynamic Clamping in Production inspect()...{RESET}")
    try:
        from backend.app.core.inspection import inspect, DIMENSIONS
        from backend.app.models.schemas import TrustGuardInspectionRequest

        scenarios_dir = ROOT_DIR / "backend" / "app" / "scenarios"

        # 1. Test high-uncertainty production scenario (wifi-compression-edge-case)
        with open(scenarios_dir / "wifi-compression-edge-case.json", "r", encoding="utf-8") as f:
            wifi_data = json.load(f)
        wifi_req = TrustGuardInspectionRequest.model_validate(wifi_data["request"])
        verdict = inspect(wifi_req)

        u = verdict.calibratedTrustVector.epistemicUncertainty
        assert u >= 0.80, f"Expected high uncertainty >= 0.80 for wifi edge case, got {u}"
        expected_cap = 1.15 - u
        for dim in DIMENSIONS:
            score = getattr(verdict.calibratedTrustVector, dim)
            assert score <= expected_cap + 0.0001, f"Dimension {dim}={score} exceeded cap {expected_cap}"
        print(f"  {GREEN}{OK_SYM}{RESET} High Uncertainty Scenario (wifi-compression): U={u:.2f} -> Max Suspicion Capped at {expected_cap:.2f}")

        # 2. Test synthetic injection with custom degradation
        synthetic_bundle = deepcopy(wifi_data["request"])
        synthetic_bundle["evidenceItems"][0]["metadata"]["extraMetadata"]["qualityDegradation"] = "0.60"
        deg_verdict = inspect(TrustGuardInspectionRequest.model_validate(synthetic_bundle))
        deg_u = deg_verdict.calibratedTrustVector.epistemicUncertainty
        assert deg_u >= 0.60
        deg_cap = 1.15 - deg_u
        for dim in DIMENSIONS:
            score = getattr(deg_verdict.calibratedTrustVector, dim)
            assert score <= deg_cap + 0.0001
        print(f"  {GREEN}{OK_SYM}{RESET} Synthetically Degraded (degradation=0.60): U={deg_u:.2f} -> Capped at {deg_cap:.2f}")

        # 3. Test clean scenario (homoglyph-clone) where U < 0.50
        with open(scenarios_dir / "homoglyph-clone.json", "r", encoding="utf-8") as f:
            homo_data = json.load(f)
        clean_verdict = inspect(TrustGuardInspectionRequest.model_validate(homo_data["request"]))
        clean_u = clean_verdict.calibratedTrustVector.epistemicUncertainty
        assert clean_u < 0.50, f"Expected low uncertainty < 0.50 for clean scenario, got {clean_u}"
        print(f"  {GREEN}{OK_SYM}{RESET} Low Uncertainty Scenario (homoglyph-clone): U={clean_u:.2f} -> No clamp applied")

        # 4. Incomplete modalities (evaluated without multi-modal enforcement)
        single_item_bundle = {
            "requestId": "single_modality_test",
            "timestamp": "2026-09-24T12:00:00Z",
            "sourceChannel": "web_portal",
            "evidenceItems": [homo_data["request"]["evidenceItems"][1]],  # text only
        }
        partial_verdict = inspect(TrustGuardInspectionRequest.model_validate(single_item_bundle), require_multimodal=False)
        partial_u = partial_verdict.calibratedTrustVector.epistemicUncertainty
        assert partial_u >= 0.90, f"Incomplete modalities must force U >= 0.90, got {partial_u}"
        print(f"  {GREEN}{OK_SYM}{RESET} Incomplete Modality (<2 evaluated): U={partial_u:.2f} -> Suspicion strictly bounded")

        return True
    except Exception as e:
        print(f"  {RED}{FAIL_SYM}{RESET} Epistemic uncertainty check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_scenarios_live_extractors():
    print(f"\n{BOLD}[5/5] Executing All Four Scenarios through Live Extractors...{RESET}")
    try:
        from backend.app.core.inspection import inspect
        from backend.app.models.schemas import TrustGuardInspectionRequest

        scenarios_dir = ROOT_DIR / "backend" / "app" / "scenarios"
        scenario_files = [
            ("ceo-wire-scam.json", "CEO Wire Scam"),
            ("homoglyph-clone.json", "Homoglyph Clone"),
            ("creator-copyright.json", "Creator Copyright"),
            ("wifi-compression-edge-case.json", "Wi-Fi Compression"),
        ]

        registered_tokens = ("creator_canary_token_2026",)
        all_passed = True

        for filename, label in scenario_files:
            file_path = scenarios_dir / filename
            with open(file_path, "r", encoding="utf-8") as f:
                scen_data = json.load(f)

            req = TrustGuardInspectionRequest.model_validate(scen_data["request"])

            t0 = time.perf_counter()
            verdict = inspect(req, registered_tokens=registered_tokens)
            run_ms = (time.perf_counter() - t0) * 1000.0

            assert verdict is not None
            assert verdict.innovationMetadata["simulation"] == "true", "Synthetic fixtures must be explicitly labeled"
            evaluated = verdict.innovationMetadata.get("evaluatedModalities", "")
            unavailable = verdict.innovationMetadata.get("unavailableDimensions", "") or "none"
            u = verdict.calibratedTrustVector.epistemicUncertainty
            ledger_cnt = len(verdict.evidenceLedger)

            # Extract per-extractor timings
            timings = json.loads(verdict.innovationMetadata.get("extractorTimingsMs", "{}"))
            timing_summary = ", ".join(f"{k.split(':')[-1]}:{v}ms" for k, v in list(timings.items())[:4])
            if len(timings) > 4:
                timing_summary += f", +{len(timings) - 4} more"

            print(f"\n  {CYAN}{BOLD}Scenario: {label} ({filename}){RESET}")
            print(f"    Tier: {verdict.assessmentTier.value}")
            print(f"    Evaluated Modalities: [{evaluated}] | Missing Dimensions: [{unavailable}]")
            print(f"    Epistemic Uncertainty: {u:.2f} | Evidence Ledger: {ledger_cnt} items")
            print(f"    Per-Extractor Timings: {timing_summary}")
            print(f"    Total Request Run: {run_ms:.2f} ms (host measurement, not individual extractor SLA)")

        return all_passed
    except Exception as e:
        print(f"  {RED}{FAIL_SYM}{RESET} Live extractor execution failed: {e}")
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
        test_all_scenarios_live_extractors(),
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
