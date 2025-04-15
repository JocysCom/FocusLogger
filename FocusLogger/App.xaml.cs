using System;
using System.Windows;

namespace JocysCom.FocusLogger
{

	/// <summary>
	/// Interaction logic for the FocusLogger application.
	/// Responsible for essential application-wide setup, such as DPI awareness,
	/// that must occur before any UI components are created. 
	/// </summary>
	public partial class App : Application
	{
		/// <summary>
		/// Initializes a new instance of the <see cref="App"/> class.
		/// Sets the process to be DPI aware at startup, ensuring high-DPI support
		/// before any windows are created.
		/// </summary>
		public App()
		{
			SetDPIAware();
		}

		/// <summary>
		/// Contains native Win32 methods for process configuration.
		/// </summary>
		internal class NativeMethods
		{
			/// <summary>
			/// Sets the current process to be DPI aware, preventing Windows from scaling the application.
			/// This P/Invoke is necessary for proper high-DPI handling on Windows Vista (NT 6.0) and later.
			/// </summary>
			[System.Runtime.InteropServices.DllImport("user32.dll")]
			internal static extern bool SetProcessDPIAware();
		}

		/// <summary>
		/// Ensures process-wide DPI awareness to prevent display scaling issues.
		/// Must be called before creating any UI windows as per Windows requirements,
		/// so it's invoked at application construction. This approach supports
		/// high-DPI displays, essential for modern Windows environments.
		/// </summary>
		public static void SetDPIAware()
		{
			// Important: This must happen before any window is created, including MainWindow (see App.xaml StartupUri),
			// to prevent blurry UI and layout issues on high-DPI screens.
			if (Environment.OSVersion.Version.Major >= 6)
				NativeMethods.SetProcessDPIAware();
		}

	}
}
