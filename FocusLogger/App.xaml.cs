using System;
using System.Windows;

namespace JocysCom.FocusLogger
{
	/// <summary>
	/// Core application class inheriting from WPF Application.
	/// It ensures system DPI awareness is set early, which is critical for crisp UI rendering
	/// especially when the application window (main UI) is initialized.
	/// This class is tightly coupled with App.xaml which defines the application's startup,
	/// linking this logic to the UI defined in XAML.
	/// </summary>
	public partial class App : Application
	{
		/// <summary>
		/// Constructor initializes application-wide settings.
		/// Here it sets the process DPI awareness before any windows are created to ensure correct scaling.
		/// This is done early to prevent any DPI virtualization and to support the user experience
		/// of crisp and properly scaled UI elements when the main window launches (referenced in App.xaml).
		/// </summary>
		public App()
		{
			SetDPIAware();
		}

		/// <summary>
		/// Contains native method imports to call Win32 APIs.
		/// Encapsulates unmanaged code call to set process DPI awareness.
		/// This pattern improves maintainability and isolates platform invocation details from other logic.
		/// This class could be extended in the future for additional platform-specific calls,
		/// making it reusable for this and similar applications needing Windows API calls.
		/// </summary>
		internal class NativeMethods
		{
			/// <summary>
			/// Calls user32.dll to set the current process as DPI aware,
			/// which helps the WPF application render UI correctly on high-DPI displays.
			/// Setting this property ensures the application opts out of DPI virtualization,
			/// which would otherwise cause the UI to appear blurry or improperly scaled.
			/// </summary>
			[System.Runtime.InteropServices.DllImport("user32.dll")]
			internal static extern bool SetProcessDPIAware();
		}

		/// <summary>
		/// Makes the process DPI aware if the operating system supports it (Windows Vista/Server 2008 or later).
		/// This check prevents calling the method on unsupported OS versions where it may fail.
		/// Setting DPI awareness early helps maintain sharp UI and prevents automatic DPI virtualization,
		/// which can cause blurred or scaled appearances.
		/// This method can be reused in other WPF or Windows applications to handle DPI scaling.
		/// </summary>
		public static void SetDPIAware()
		{
			// DPI aware property must be set before application window is created.
			if (Environment.OSVersion.Version.Major >= 6)
				NativeMethods.SetProcessDPIAware();
		}

	}
}
