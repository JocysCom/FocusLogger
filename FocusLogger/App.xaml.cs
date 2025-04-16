using System;
using System.Windows;

namespace JocysCom.FocusLogger
{

	public partial class App : Application
	{
		/// <summary>
		/// Initializes the WPF application.
		/// Invokes DPI awareness setting to ensure UI elements render crisply on high-DPI displays.
		/// </summary>
		public App()
		{
			SetDPIAware();
		}

		/// <summary>
		/// Contains native methods for calling Windows API functions related to process behavior.
		/// </summary>
		internal class NativeMethods
		{
			[System.Runtime.InteropServices.DllImport("user32.dll")]
			internal static extern bool SetProcessDPIAware();
		}

		/// <summary>
		/// Ensures the application is DPI aware to prevent blurry UI or scaling issues on high-DPI monitors.
		/// Must be called before any application windows are created (e.g., before loading MainWindow) since DPI context is set once per process.
		/// For WPF applications started via App.xaml, calling this in the constructor guarantees the correct behavior.
		/// </summary>
		public static void SetDPIAware()
		{
			// Only set DPI awareness on Windows Vista or newer (OS version 6+), as older versions do not support this API.
			// This is a crucial step for per-process DPI awareness with WPF, preventing unwanted scaling artifacts.
			if (Environment.OSVersion.Version.Major >= 6)
				NativeMethods.SetProcessDPIAware();
		}

	}
}
