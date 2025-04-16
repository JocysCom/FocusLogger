using System;
using System.Windows;

namespace JocysCom.FocusLogger
{
	/// <summary>
	/// Main application entry class for FocusLogger.
	/// Handles startup initialization including process-wide DPI awareness,
	/// ensuring correct UI scaling before any windows are created.
	/// </summary>
	public partial class App : Application
	{
		/// <summary>
		/// Constructs the application and applies vital process-level settings before UI instantiation.
		/// </summary>
		public App()
		{
			SetDPIAware();
		}

		/// <summary>
		/// Contains P/Invoke signatures for interacting with native Win32 APIs needed for startup configuration.
		/// </summary>
		internal class NativeMethods
		{
			/// <summary>
			/// Declares the SetProcessDPIAware Win32 call, enabling DPI scaling support at the process level.
			/// </summary>
			[System.Runtime.InteropServices.DllImport("user32.dll")]
			internal static extern bool SetProcessDPIAware();
		}

		/// <summary>
		/// Ensures DPI awareness is set at process-level before any UI is created.
		/// This is necessary for proper scaling on high-DPI displays, as required by many modern Windows systems (Vista/7+).
		/// Setting this here enforces correct per-monitor scaling and prevents blurry or improperly scaled UI controls throughout the app.
		/// Must be called before any window or resource is loaded (including MainWindow.xaml), otherwise system defaults are applied and cannot be overridden at runtime.
		/// </summary>
		public static void SetDPIAware()
		{
			// DPI aware property must be set before application window is created.
			// Windows Vista and later: enable DPI aware mode for proper application scaling.
			if (Environment.OSVersion.Version.Major >= 6)
				NativeMethods.SetProcessDPIAware();
		}
	}
}
