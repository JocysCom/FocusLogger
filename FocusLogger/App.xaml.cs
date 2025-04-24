using System;
using System.Windows;

namespace JocysCom.FocusLogger
{

	public partial class App : Application
	{
		public App()
		{
			// Ensure application is DPI aware before any window is shown (required for proper scaling on Windows 7+).
			SetDPIAware();
		}

		internal class NativeMethods
		{
			[System.Runtime.InteropServices.DllImport("user32.dll")]
			internal static extern bool SetProcessDPIAware();
		}

		/// <summary>
		/// Sets the process to DPI-aware mode for high-DPI displays; required for correct UI scaling on Windows Vista and later.
		/// Must be called before any WPF window is created.
		/// </summary>
		public static void SetDPIAware()
		{
			// Avoid calling on unsupported OS versions (pre-Vista).
			if (Environment.OSVersion.Version.Major >= 6)
				NativeMethods.SetProcessDPIAware();
		}

	}
}
