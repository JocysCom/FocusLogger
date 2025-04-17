using JocysCom.ClassLibrary.Controls;
using System.Reflection;
using System.Windows;

namespace JocysCom.FocusLogger
{
	/// <summary>
	/// Main window of the FocusLogger application responsible for initializing core UI components,
	/// setting window title from assembly metadata, and managing application lifecycle events.
	/// </summary>
	public partial class MainWindow : Window
	{
		/// <summary>
		/// Initializes a new instance of the <see cref="MainWindow"/> class.
		/// Ensures correct UI synchronization context for controls, loads the UI, and sets up window information.
		/// </summary>
		public MainWindow()
		{
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			LoadHelpAndInfo();
		}

		/// <summary>
		/// Loads assembly metadata and updates the window title to reflect product name and version.
		/// </summary>
		void LoadHelpAndInfo()
		{
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			// Set window title based on configurable assembly metadata (e.g., product, version).
			Title = ai.GetTitle(true, false, true, false, false);
		}

		/// <summary>
		/// Exposes the InfoControl UI element, which displays contextual help and product information in the window.
		/// </summary>
		public InfoControl HMan;

		/// <summary>
		/// Static flag indicating if the window is in the process of closing. Used for global shutdown detection.
		/// </summary>
		public static bool IsClosing;

		/// <summary>
		/// Handles the window closing event and updates <see cref="IsClosing"/> to signal application shutdown logic.
		/// </summary>
		/// <param name="sender">The source of the event.</param>
		/// <param name="e">Event data for the cancelable close operation.</param>
		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			IsClosing = true;
		}
	}

}
