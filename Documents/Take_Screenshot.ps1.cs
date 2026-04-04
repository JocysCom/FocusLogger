using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Windows.Forms;

public class TakeScreenshot
{
	[DllImport("user32.dll")]
	public static extern bool SetForegroundWindow(IntPtr hWnd);
	[DllImport("user32.dll")]
	public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
	[DllImport("user32.dll")]
	public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
	[DllImport("user32.dll")]
	public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
	[DllImport("user32.dll")]
	public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);
	[DllImport("dwmapi.dll")]
	public static extern int DwmGetWindowAttribute(IntPtr hwnd, int dwAttribute, out RECT pvAttribute, int cbAttribute);

	[StructLayout(LayoutKind.Sequential)]
	public struct RECT
	{
		public int Left, Top, Right, Bottom;
	}

	public static RECT GetExtendedFrameBounds(IntPtr hwnd)
	{
		RECT rect;
		DwmGetWindowAttribute(hwnd, 9, out rect, Marshal.SizeOf(typeof(RECT)));
		return rect;
	}

	public static void CenterAndResize(IntPtr hwnd, int w, int h, int yOffset = 0)
	{
		var screen = Screen.PrimaryScreen.WorkingArea;
		int x = (screen.Width - w) / 2 + screen.Left;
		int y = (screen.Height - h) / 2 + screen.Top + yOffset;
		SetWindowPos(hwnd, IntPtr.Zero, x, y, w, h, 0x0040);
	}

	/// <summary>
	/// Captures a window using CopyFromScreen with DWM extended frame bounds
	/// for accurate visible area (excludes invisible shadow border).
	/// </summary>
	public static void CaptureWindow(IntPtr hwnd, string filePath)
	{
		var rect = GetExtendedFrameBounds(hwnd);
		int w = rect.Right - rect.Left;
		int h = rect.Bottom - rect.Top;
		using (var bitmap = new Bitmap(w, h, PixelFormat.Format32bppArgb))
		{
			using (var graphics = Graphics.FromImage(bitmap))
			{
				graphics.CopyFromScreen(rect.Left, rect.Top, 0, 0, new Size(w, h));
			}
			bitmap.Save(filePath, ImageFormat.Png);
		}
	}
}
