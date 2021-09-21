using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

namespace JocysCom.FocusLogger
{
	internal class NativeMethods
	{
		// https://docs.microsoft.com/en-gb/windows/win32/api/winuser/

		/// <summary>
		/// Get handle to the window with the keyboard focus.
		/// </summary>
		/// <remarks>
		/// If the calling thread's message queue does not have an associated window
		/// with the keyboard focus, the return value is NULL.
		/// </remarks>
		[DllImport("user32.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
		internal static extern IntPtr GetFocus();

		/// <summary>
		/// Window which is active.
		/// </summary>
		[DllImport("user32.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
		internal static extern IntPtr GetActiveWindow();

		/// <summary>
		/// A handle to the window that will receive the keyboard input. 
		/// </summary>
		[DllImport("user32.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
		internal static extern IntPtr GetForegroundWindow();

		/// <summary>
		/// Retrieves the identifier of the thread that created the specified window and,
		/// optionally, the identifier of the process that created the window.
		/// </summary>
		/// <param name="handle">A handle to the window.</param>
		/// <param name="processId">A pointer to a variable that receives the process identifier</param>
		/// <returns></returns>
		[DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
		internal static extern int GetWindowThreadProcessId(IntPtr handle, out int processId);

		/// <summary>
		/// Retrieves information about the active window or a specified GUI thread.
		/// </summary>
		/// <param name="hTreadID">
		/// The identifier for the thread for which information is to be retrieved.
		/// To retrieve this value, use the GetWindowThreadProcessId function.
		/// If this parameter is NULL, the function returns information for the foreground thread.
		/// </param>
		/// <param name="lpgui">
		/// A pointer to a GUITHREADINFO structure that receives information describing the thread. 
		/// </param>
		/// <returns></returns>
		[DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
		internal static extern bool GetGUIThreadInfo(uint hTreadID, ref GUITHREADINFO lpgui);

		/// <summary>
		/// Retrieves the identifier of the thread that created the specified window and,
		/// optionally, the identifier of the process that created the window.
		/// </summary>
		/// <param name="hwnd">A handle to the window.</param>
		/// <param name="lpdwProcessId">A pointer to a variable that receives the process identifier.</param>
		/// <returns></returns>
		[DllImport("user32.dll")]
		internal static extern uint GetWindowThreadProcessId(uint hwnd, out uint lpdwProcessId);

		[StructLayout(LayoutKind.Sequential)]
		internal struct RECT
		{
			public int iLeft;
			public int iTop;
			public int iRight;
			public int iBottom;
		}

		[Flags]
		internal enum GUI
		{
			/// <summary>The caret's blink state. This bit is set if the caret is visible.</summary>
			GUI_CARETBLINKING = 0x00000001,
			/// <summary>The thread's menu state. This bit is set if the thread is in menu mode.</summary>
			GUI_INMENUMODE = 0x00000004,
			/// <summary>The thread's move state. This bit is set if the thread is in a move or size loop.</summary>
			GUI_INMOVESIZE = 0x00000002,
			/// <summary>The thread's pop-up menu state. This bit is set if the thread has an active pop-up menu.</summary>
			GUI_POPUPMENUMODE = 0x00000010,
			/// <summary>The thread's system menu state. This bit is set if the thread is in a system menu mode.</summary>
			GUI_SYSTEMMENUMODE = 0x00000008,
		}

		[StructLayout(LayoutKind.Sequential)]
		internal struct GUITHREADINFO
		{
			/// <summary>The size of this structure, in bytes.</summary>
			public int cbSize;
			/// <summary>The thread state.</summary>
			public GUI flags;
			/// <summary>A handle to the active window within the thread.</summary>
			public IntPtr hwndActive;
			/// <summary>A handle to the window that has the keyboard focus.</summary>
			public IntPtr hwndFocus;
			/// <summary>A handle to the window that has captured the mouse.</summary>
			public IntPtr hwndCapture;
			/// <summary>A handle to the window that owns any active menus.</summary>
			public IntPtr hwndMenuOwner;
			/// <summary>A handle to the window in a move or size loop.</summary>
			public IntPtr hwndMoveSize;
			/// <summary>A handle to the window that is displaying the caret.</summary>
			public IntPtr hwndCaret;
			/// <summary>The caret's bounding rectangle, in client coordinates, relative to the window specified by the hwndCaret member.</summary>
			public RECT rectCaret;
		}

		internal static bool GetInfo(uint hwnd, out GUITHREADINFO lpgui)
		{
			uint lpdwProcessId;
			uint threadId = GetWindowThreadProcessId(hwnd, out lpdwProcessId);
			lpgui = new GUITHREADINFO();
			lpgui.cbSize = Marshal.SizeOf(lpgui);
			return GetGUIThreadInfo(threadId, ref lpgui);
		}


	}
}
