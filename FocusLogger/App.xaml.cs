using System;
using System.Windows;

namespace JocysCom.FocusLogger
{
	/// <summary>
	/// Application entry point for FocusLogger.
	/// Handles global WPF startup logic, including initialization of system-level settings before main window creation.
	/// </summary>
	public partial class App : Application
	{
		/// <summary>
		/// Initializes the application, ensuring the process is set to be DPI-aware prior to creating any UI elements.
		/// </summary>
		public App()
		{
			SetDPIAware();
		}

		/// <summary>
		/// Contains native methods for interacting with Windows system DLLs.
		/// </summary>
		internal class NativeMethods
		{
			/// <summary>
			/// Sets the current process as DPI-aware to ensure correct scaling of the UI on high-DPI displays.
			/// </summary>
			[System.Runtime.InteropServices.DllImport("user32.dll")]
			internal static extern bool SetProcessDPIAware();
		}

		/// <summary>
		/// Ensures the process is marked as DPI-aware if running on Windows Vista (version 6) or newer.
		/// Call this before any windows are created to prevent display scaling issues.
		/// </summary>
		public static void SetDPIAware()
		{
			// Windows requires DPI-awareness to be set before any window is instantiated
			//—see project readme and docs for display correctness rationale.
			if (Environment.OSVersion.Version.Major >= 6)
				NativeMethods.SetProcessDPIAware();
		}
	}
}
