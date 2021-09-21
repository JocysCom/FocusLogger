using System;
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
		/// <returns>
		/// The return value is the handle to the window with the keyboard focus.
		/// If the calling thread's message queue does not have an associated window with the keyboard focus, the return value is NULL.
		/// </returns>
		[DllImport("user32.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
		internal static extern IntPtr GetFocus();

		/// <summary>
		/// Window which is active.
		/// </summary>
		/// <returns>
		/// The return value is the handle to the active window attached to the calling thread's message queue.
		/// Otherwise, the return value is NULL.
		/// </returns>
		[DllImport("user32.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
		internal static extern IntPtr GetActiveWindow();

		/// <summary>
		/// Get handle to the child window at the top of the Z order.
		/// </summary>
		[DllImport("user32.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
		internal static extern IntPtr GetTopWindow(IntPtr hWnd);

		[DllImport("user32.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
		internal static extern bool IsWindowVisible(IntPtr hWnd);

		[DllImport("user32.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
		internal static extern int GetWindowTextLengthW(IntPtr hWnd);

		/// <summary>
		/// Copies the text of the specified window's title bar (if it has one) into a buffer.
		/// </summary>
		/// <param name="hWnd">A handle to the window or control containing the text.</param>
		/// <param name="lpString">The buffer that will receive the text.</param>
		/// <param name="nMaxCount">The maximum number of characters to copy to the buffer, including the null character.</param>
		/// <returns>If the function succeeds, the return value is the length, in characters, of the copied string, not including the terminating null character.</returns>
		[DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
		static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

		/// <summary>
		/// A handle to the window that will receive the keyboard input. 
		/// </summary>
		/// <returns>
		/// The return value is a handle to the foreground window.
		/// The foreground window can be NULL in certain circumstances, such as when a window is losing activation.
		/// </returns>
		[DllImport("user32.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
		internal static extern IntPtr GetForegroundWindow();

		/// <summary>
		/// Retrieves the identifier of the thread that created the specified window and,
		/// optionally, the identifier of the process that created the window.
		/// </summary>
		/// <param name="hWnd">A handle to the window.</param>
		/// <param name="lpdwProcessId">A pointer to a variable that receives the process identifier</param>
		/// <returns>Identifier of the thread that created the window.</returns>
		[DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
		internal static extern int GetWindowThreadProcessId(IntPtr hWnd, out int lpdwProcessId);

		/// <summary>
		/// Retrieves information about the active window or a specified GUI thread.
		/// </summary>
		/// <param name="idThread">
		/// The identifier for the thread for which information is to be retrieved.
		/// To retrieve this value, use the GetWindowThreadProcessId function.
		/// If this parameter is NULL, the function returns information for the foreground thread.
		/// </param>
		/// <param name="pgui">
		/// A pointer to a GUITHREADINFO structure that receives information describing the thread. 
		/// </param>
		/// <returns>If the function succeeds, the return value is nonzero.</returns>
		[DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
		internal static extern bool GetGUIThreadInfo(int idThread, ref GUITHREADINFO pgui);

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

		internal static GUITHREADINFO? GetInfo(IntPtr hWnd)
		{
			int lpdwProcessId;
			int threadId = GetWindowThreadProcessId(hWnd, out lpdwProcessId);
			var pgui = new GUITHREADINFO();
			pgui.cbSize = Marshal.SizeOf(pgui);
			if (GetGUIThreadInfo(threadId, ref pgui))
				return pgui;
			return null;
		}

		internal static string GetWindowText(IntPtr hWnd)
		{
			int textLength = GetWindowTextLengthW(hWnd);
			var lpString = new StringBuilder(textLength + 1);
			var length = GetWindowText(hWnd, lpString, lpString.Capacity);
			return lpString.ToString();
		}

	}
}
