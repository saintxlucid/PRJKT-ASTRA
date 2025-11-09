# examples/os_verbs_demo.py
"""
Demonstration of OS Verbs for Windows automation.
Shows window control, app launching, and system info capabilities.
"""
import time

from controller.os_verbs import (
    PYWIN32_AVAILABLE,
    app_launch,
    process_kill,
    screen_get_size,
    window_find_by_title,
    window_focus,
    window_list,
    window_maximize,
    window_minimize,
    window_move,
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def demo_system_info():
    """Demo: Get system information."""
    print_section("System Information")

    # Check if pywin32 is available
    print(f"pywin32 available: {PYWIN32_AVAILABLE}")

    if not PYWIN32_AVAILABLE:
        print("⚠️  pywin32 not installed - OS automation disabled")
        print("   Install with: pip install pywin32")
        return False

    # Get screen size
    screen = screen_get_size()
    if screen["ok"]:
        print(f"✓ Screen size: {screen['width']}x{screen['height']} pixels")
    else:
        print(f"✗ Failed to get screen size: {screen['error']}")

    return True


def demo_window_list():
    """Demo: List all visible windows."""
    print_section("Window List")

    result = window_list()

    if not result["ok"]:
        print(f"✗ Failed to list windows: {result['error']}")
        return

    print(f"✓ Found {result['count']} visible windows:\n")

    # Show first 10 windows
    for i, window in enumerate(result["windows"][:10], 1):
        print(f"  {i}. [{window['hwnd']:6d}] {window['title'][:50]}")
        print(f"     PID: {window['pid']}")

    if result["count"] > 10:
        print(f"\n  ... and {result['count'] - 10} more windows")


def demo_window_find():
    """Demo: Find windows by title."""
    print_section("Find Windows by Title")

    # Try to find common browsers
    search_terms = ["Chrome", "Firefox", "Edge", "Notepad", "Explorer"]

    for term in search_terms:
        result = window_find_by_title(term, exact=False)

        if result["ok"] and result["count"] > 0:
            print(f"✓ Found {result['count']} window(s) matching '{term}':")
            for window in result["matches"][:3]:  # Show first 3
                print(f"  - [{window['hwnd']}] {window['title']}")
        else:
            print(f"○ No windows matching '{term}'")


def demo_app_launch():
    """Demo: Launch applications."""
    print_section("Launch Application")

    print("Launching Notepad...")
    result = app_launch("notepad.exe")

    if result["ok"]:
        print(f"✓ Launched Notepad with PID: {result['pid']}")
        print(f"  Executable: {result['exe']}")

        # Wait a moment for window to appear
        time.sleep(1)

        # Try to find the Notepad window
        find_result = window_find_by_title("Notepad", exact=False)
        if find_result["ok"] and find_result["count"] > 0:
            notepad_window = find_result["matches"][0]
            print(f"✓ Found Notepad window: [{notepad_window['hwnd']}] {notepad_window['title']}")
            return notepad_window
        else:
            print("○ Notepad window not found yet")
            return None
    else:
        print(f"✗ Failed to launch Notepad: {result['error']}")
        return None


def demo_window_control(window):
    """Demo: Control window (move, maximize, minimize)."""
    if not window:
        print("\n⊘ Skipping window control demo (no window available)")
        return

    print_section("Window Control")

    hwnd = window["hwnd"]
    title = window["title"]

    # Focus the window
    print(f"Focusing window: {title}")
    result = window_focus(hwnd)
    if result["ok"]:
        print(f"✓ Focused window: {result['title']}")
    else:
        print(f"✗ Failed to focus: {result['error']}")
        return

    time.sleep(0.5)

    # Move and resize
    print("\nMoving window to (100, 100) with size 600x400")
    result = window_move(hwnd, 100, 100, 600, 400)
    if result["ok"]:
        geo = result["geometry"]
        print(f"✓ Moved window to ({geo['x']}, {geo['y']}) size {geo['width']}x{geo['height']}")
    else:
        print(f"✗ Failed to move: {result['error']}")

    time.sleep(0.5)

    # Maximize
    print("\nMaximizing window")
    result = window_maximize(hwnd)
    if result["ok"]:
        print(f"✓ Window state: {result['state']}")
    else:
        print(f"✗ Failed to maximize: {result['error']}")

    time.sleep(0.5)

    # Minimize
    print("\nMinimizing window")
    result = window_minimize(hwnd)
    if result["ok"]:
        print(f"✓ Window state: {result['state']}")
    else:
        print(f"✗ Failed to minimize: {result['error']}")


def demo_cleanup(window):
    """Demo: Clean up by closing the launched app."""
    if not window:
        return

    print_section("Cleanup")

    # Ask user before closing
    print(f"Demo complete. The Notepad window will remain open.")
    print(f"You can manually close it or uncomment the cleanup code.")

    # Uncomment to auto-close:
    # from controller.os_verbs import window_close
    # result = window_close(window["hwnd"])
    # if result["ok"]:
    #     print(f"✓ Closed window")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("  ASTRA OS - Windows Automation Demo")
    print("  OS Verbs: Window Control, App Launching, System Info")
    print("=" * 60)

    # Check system info first
    if not demo_system_info():
        print("\n⚠️  Cannot continue without pywin32")
        print("   Install with: pip install pywin32")
        return

    # List current windows
    demo_window_list()

    # Find windows by title
    demo_window_find()

    # Launch Notepad and get window
    notepad_window = demo_app_launch()

    # Control the window
    demo_window_control(notepad_window)

    # Cleanup
    demo_cleanup(notepad_window)

    print("\n" + "=" * 60)
    print("  Demo Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
