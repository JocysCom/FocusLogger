using JocysCom.ClassLibrary.Controls;
using System.Reflection;
using System.Windows;

namespace JocysCom.FocusLogger
{
	public partial class MainWindow : Window
	{
		/// <summary>
		/// Initializes the main window.
		/// Ensures early task invocation context setup for WPF cross-thread operations,
		/// followed by UI component initialization and dynamic window title loading.
		/// </summary>
		public MainWindow()
		{
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			LoadHelpAndInfo();
		}

		/// <summary>
		/// Sets the window's title using assembly metadata.
		/// Provides dynamic branding/version information for support and user clarity.
		/// </summary>
		void LoadHelpAndInfo()
		{
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			Title = ai.GetTitle(true, false, true, false, false);
		}

		/// <summary>
		/// Public reference to the InfoControl instance that displays contextual help or information.
		/// Typically assigned by XAML; integrates with InfoHelpProvider for dynamic assistance in UI.
		/// </summary>
		public InfoControl HMan;

		/// <summary>
		/// Static flag indicating if the window/application is in the process of closing.
		/// Other components monitor this for orderly shutdown in multi-threaded or background processes.
		/// </summary>
		public static bool IsClosing;

		/// <summary>
		/// Handles the window closing event by setting the IsClosing flag.
		/// Allows external services and worker threads to detect when application exit is in progress,
		/// preventing improper operations or enabling graceful shutdown.
		/// </summary>
		/// <param name="sender">The window triggering the event.</param>
		/// <param name="e">Event arguments supporting cancellation of the close.</param>
		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			IsClosing = true;
		}
	}

}
