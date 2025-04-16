using JocysCom.ClassLibrary.Controls;
using System.Reflection;
using System.Windows;

namespace JocysCom.FocusLogger
{
	/// <summary>
	/// Main application window hosting the primary UI and managing cross-thread shutdown signaling.
	/// </summary>
	public partial class MainWindow : Window
	{
		/// <summary>
		/// Initializes the main window, ensures cross-thread invocation context, loads UI components and dynamic help/version data.
		/// </summary>
		public MainWindow()
		{
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			LoadHelpAndInfo();
		}

		/// <summary>
		/// Loads assembly metadata to set the application window title, ensuring dynamic version or branding is displayed based on build information.
		/// </summary>
		void LoadHelpAndInfo()
		{
			// Retrieves assembly info to display version/build details in window title at runtime.
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			Title = ai.GetTitle(true, false, true, false, false);
		}

		/// <summary>
		/// Exposes the help/info UI control linked via XAML; used for dynamic help content display.
		/// </summary>
		public InfoControl HMan;

		/// <summary>
		/// Used as a cross-thread-safe flag so background threads can abort work when the application is closing.
		/// </summary>
		/// <remarks>
		/// Referenced by UI subcomponents (e.g., DataListControl) to properly terminate ongoing operations during application shutdown.
		/// </remarks>
		public static bool IsClosing;

		/// <summary>
		/// Handles the window closing event; sets IsClosing flag for coordinated shutdown of background processes.
		/// </summary>
		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			// This triggers shutdown signals for long-running background threads elsewhere in the UI.
			IsClosing = true;
		}
	}

}
