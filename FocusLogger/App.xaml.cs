using System;
using System.Windows;

namespace JocysCom.FocusLogger
{

	/// <summary>
	/// Interaction logic for the FocusLogger application.
	/// This class handles application startup routines and global settings.
	/// </summary>
	public partial class App : Application
	{
		/// <summary>
		/// Initializes a new instance of the <see cref="App"/> class, configuring
		/// process-wide DPI awareness at the earliest stage of startup.
		/// </summary>
		public App()
		{
			SetDPIAware();
		}

		/// <summary>
		/// Contains native interop methods related to application process configuration.
		/// </summary>
		internal class NativeMethods
		{
			/// <summary>
			/// Sets the process as DPI-aware. Necessary to prevent automatic DPI virtualization
			/// (bitmap scaling) so the application can handle its own scaling on high-DPI displays.
			/// </summary>
			[System.Runtime.InteropServices.DllImport("user32.dll")]
			internal static extern bool SetProcessDPIAware();
		}

		/// <summary>
		/// Ensures the application opts into DPI awareness before any windows are created.
		/// This prevents scaling issues on high-DPI displays, particularly on Windows Vista and later.
		/// Must be done at startup as retroactive changes are ineffective.
		/// </summary>
		public static void SetDPIAware()
		{
			// DPI aware property must be set before application window is created to ensure all windows and resources are scaled correctly. 
			if (Environment.OSVersion.Version.Major >= 6)
				NativeMethods.SetProcessDPIAware();
		}

	}
}
