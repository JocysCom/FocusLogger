using JocysCom.ClassLibrary.Controls;
using System.Reflection;
using System.Windows;

namespace JocysCom.FocusLogger
{
	public partial class MainWindow : Window
	{
		/// <summary>
		/// Initializes a new instance of the MainWindow class.
		/// Sets up control invocation context, loads components, and sets window info.
		/// </summary>
		public MainWindow()
		{
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			LoadHelpAndInfo();
		}

		/// <summary>
		/// Sets the main window title using assembly/application info for branding and version display.
		/// </summary>
		void LoadHelpAndInfo()
		{
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			Title = ai.GetTitle(true, false, true, false, false);
		}

		/// <summary>
		/// Reference to the main info/help control displayed on the window.
		/// </summary>
		public InfoControl HMan;

		/// <summary>
		/// Global flag to signal that the main window is closing.
		/// Allows other components (e.g., timer threads in data/logging controls) to react and terminate gracefully.
		/// </summary>
		public static bool IsClosing;

		/// <summary>
		/// Handles the window closing event.
		/// Sets the IsClosing flag to inform dependent components of shutdown, allowing for safe resource cleanup.
		/// </summary>
		/// <param name="sender">The sender object.</param>
		/// <param name="e">Cancellation event arguments.</param>
		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			IsClosing = true;
		}
	}

}
