"""
Script to run all integration tests sequentially and fix errors
"""

import asyncio
import sys
import subprocess
from pathlib import Path


def run_test(test_name: str) -> tuple[bool, str]:
    """
    Run a single integration test
    
    Args:
        test_name: Test method name
        
    Returns:
        (success, output)
    """
    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/test_integration_all_functions.py::TestAllFunctions::{test_name}",
        "-v", "-s", "--tb=short", "-m", "integration"
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    
    success = result.returncode == 0
    output = result.stdout + result.stderr
    
    return success, output


def main():
    """Run all integration tests sequentially"""
    tests = [
        "test_1_create_task",
        "test_2_update_task",
        "test_3_delete_task",
        "test_4_move_task",
        "test_5_bulk_move_overdue",
        "test_6_manage_tags",
        "test_7_manage_notes",
        "test_8_recurring_tasks",
        "test_9_reminders",
        "test_10_voice_recognition",
        "test_11_gpt_command_parsing",
        "test_12_urgency_determination",
        "test_13_work_time_analytics",
        "test_14_schedule_optimization",
    ]
    
    results = {}
    
    for test_name in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print(f"{'='*60}\n")
        
        success, output = run_test(test_name)
        results[test_name] = {
            "success": success,
            "output": output,
        }
        
        if success:
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
            print(output[-500:])  # Last 500 chars
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}\n")
    
    passed = sum(1 for r in results.values() if r["success"])
    failed = len(results) - passed
    
    print(f"Total: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    return results


if __name__ == "__main__":
    main()

