using JocysCom.ClassLibrary.Controls;
using System.Reflection;
using System.Windows;

namespace JocysCom.FocusLogger
{
	/// <summary>
	/// Main application window for FocusLogger.
	/// Hosts the core UI and initializes essential application helpers and display metadata.
	/// </summary>
	public partial class MainWindow : Window
	{
		/// <summary>
		/// Initializes a new instance of the <see cref="MainWindow"/> class.
		/// Sets up the UI-thread invocation context, applies window layout, and loads application metadata for the window.
		/// </summary>
		public MainWindow()
		{
			// Initializes the WPF synchronization context to ensure thread-safe UI operations across the application.
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			LoadHelpAndInfo();
		}

		/// <summary>
		/// Loads application metadata into the window, including dynamic title information.
		/// </summary>
		void LoadHelpAndInfo()
		{
			// Assembly reference is captured for use with AssemblyInfo; other metadata retrieval could be implemented here.
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			// Sets the window title based on product and assembly metadata (e.g., product name, version).
			Title = ai.GetTitle(true, false, true, false, false);
		}

		/// <summary>
		/// Public field referencing the associated <see cref="InfoControl"/>, used to display help or contextual information in the UI.
		/// See InfoControl.xaml for layout details.
		/// </summary>
		public InfoControl HMan;

		/// <summary>
		/// Indicates whether the application is in the process of closing.
		/// Useful for other components to coordinate shutdown or cleanup logic.
		/// </summary>
		public static bool IsClosing;

		/// <summary>
		/// Handles the window closing event to update the <see cref="IsClosing"/> flag.
		/// This informs background operations and other components about imminent shutdown.
		/// </summary>
		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			IsClosing = true;
		}
	}

}
