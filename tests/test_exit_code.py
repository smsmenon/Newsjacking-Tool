"""A dry run is a success; a failed send is not.

Run #1 on GitHub Actions spent 19 minutes doing the work correctly and then reported
failure, because a skipped send looks like an unsuccessful one.
"""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def exit_code_for(send_result: dict) -> int:
    """Run main() with the pipeline stubbed out, and report what it returns."""
    import tada_ci.run_newsjacking as rn

    stub = types.ModuleType("tada_ci.services.newsjacking")
    stub.run_newsjacking = lambda **kw: {
        "subject": "Newsjacking Articles - Test",
        "send_result": send_result,
        "website_usage_stats": {},
        "linkedin_summary": {},
    }
    sys.modules["tada_ci.services.newsjacking"] = stub
    try:
        return rn.main()
    finally:
        del sys.modules["tada_ci.services.newsjacking"]


sent = {"success": True, "id": "abc123"}
dry = {"success": False, "skipped": True, "reason": "SEND_EMAIL disabled"}
failed = {"success": False, "error": "401 Unauthorized"}

assert exit_code_for(sent) == 0, "a real send should pass"
assert exit_code_for(dry) == 0, "a dry run should pass — this is what broke run #1"
assert exit_code_for(failed) == 1, "a failed send must still fail the job"
print("OK: dry run passes, failed send fails")
