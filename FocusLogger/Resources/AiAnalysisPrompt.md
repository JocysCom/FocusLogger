I have a Focus Logger CSV file that records which Windows process or program takes window focus.
Each row contains: Date, PID, Process Name, Active, Mouse, Keyboard, Caret, Window Title, Window Class, and Path.

The "Window Class" column contains the Win32 window class name (e.g., "Shell_TrayWnd" for the taskbar, "tooltips_class32" for tooltip popups, "MSCTFIME UI" for text input framework, "Chrome_WidgetWin_1" for Chromium-based browsers). This helps identify the type of window that took focus.

Please analyse the attached CSV file and:
1. Identify which processes are stealing focus unexpectedly (e.g., briefly appearing then disappearing).
2. Use the Window Class to determine what type of window stole focus (notification, tooltip, taskbar, input method, dialog, etc.) and explain what it means.
3. Flag any unusual patterns such as rapid focus switching, background processes taking foreground, or processes that shouldn't normally grab focus.
4. If a game or fullscreen application is present, highlight any process that interrupted it.
5. Summarise the most frequent focus-stealing offenders with timestamps.
6. Suggest possible causes and fixes for each offender.
