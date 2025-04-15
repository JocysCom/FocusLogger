using System;
using System.Windows;

namespace JocysCom.FocusLogger
{

	/// <summary>
	/// Main application class for the FocusLogger WPF application.
	/// Handles global application initialization, including configuration of system DPI awareness to ensure proper window scaling.
	/// </summary>
	public partial class App : Application
	{
		/// <summary>
		/// Initializes the application and sets process DPI awareness prior to creating any windows.
		/// </summary>
		public App()
		{
			SetDPIAware();
		}

		// Contains native method declarations required for process DPI configuration.
		internal class NativeMethods
		{
			[System.Runtime.InteropServices.DllImport("user32.dll")]
			internal static extern bool SetProcessDPIAware();
		}

		/// <summary>
		/// Sets process-wide DPI awareness before any window is created to ensure correct scaling on high-DPI displays.
		/// Should be called before WPF windows (such as MainWindow) are created, as required by WPF application startup sequence.
		/// Only applies on Windows Vista (version 6) or newer; older versions do not support this setting.
		/// </summary>
		public static void SetDPIAware()
		{
			// IMPORTANT: DPI awareness must be configured before any UI is created to avoid scaling issues on high-DPI displays.
			// This ensures windows like MainWindow.xaml load with proper DPI scaling from application startup.
			if (Environment.OSVersion.Version.Major >= 6)
				NativeMethods.SetProcessDPIAware();
		}

	}
}
