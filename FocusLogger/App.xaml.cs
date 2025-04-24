using System;
using System.Windows;

namespace JocysCom.FocusLogger
{

	public partial class App : Application
	{
		public App()
		{
			// Ensures DPI awareness is set before any windows are shown, so UI scales correctly on high-DPI displays.
			SetDPIAware();
		}

		internal class NativeMethods
		{
			[System.Runtime.InteropServices.DllImport("user32.dll")]
			internal static extern bool SetProcessDPIAware();
		}

		/// <summary>
		/// Sets the process as DPI-aware on Windows Vista (6.0) and later. Required for proper UI scaling; must be called before creating any windows.
		/// </summary>
		public static void SetDPIAware()
		{
			// Only supported on Windows Vista and newer; see project/README for system requirements.
			// DPI aware property must be set before application window is created.
			if (Environment.OSVersion.Version.Major >= 6)
				NativeMethods.SetProcessDPIAware();
		}

	}
}
