using JocysCom.ClassLibrary.Controls;
using System.Reflection;
using System.Windows;

namespace JocysCom.FocusLogger
{
	public partial class MainWindow : Window
	{
		/// <summary>
		/// Initializes a new instance of the <see cref="MainWindow"/> class.
		/// Sets up the invoke context for safe cross-thread UI updates, initializes UI components,
		/// and loads application metadata. Called on application startup as specified in App.xaml.
		/// </summary>
		public MainWindow()
		{
			// Ensure invoke context is initialized for cross-thread UI updates, which are common due to background monitoring.
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			LoadHelpAndInfo();
		}

		/// <summary>
		/// Loads application metadata to set a descriptive window title. Displays detailed version info for user support and diagnostics.
		/// </summary>
		void LoadHelpAndInfo()
		{
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			Title = ai.GetTitle(true, false, true, false, false);
		}

		/// <summary>
		/// Holds a reference to the main help or information panel for the window, typically representing the UI help area.
		/// </summary>
		public InfoControl HMan;

		/// <summary>
		/// Static flag used for graceful shutdown signaling to child components (like periodic timers in controls) during application closure.
		/// Checked by controls (such as DataListControl) to halt background tasks safely as the window closes.
		/// </summary>
		public static bool IsClosing;

		/// <summary>
		/// Handles the window closing event.
		/// Sets <see cref="IsClosing"/> to true, allowing child controls and background operations to detect shutdown and terminate cleanly.
		/// </summary>
		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			IsClosing = true;
		}
	}

}
