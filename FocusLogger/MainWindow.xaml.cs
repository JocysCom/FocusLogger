using JocysCom.ClassLibrary.Controls;
using System.Reflection;
using System.Windows;

namespace JocysCom.FocusLogger
{
	/// <summary>
	/// Interaction logic for MainWindow.xaml
	/// </summary>
	public partial class MainWindow : Window
	{
		/// <summary>
		/// Constructs the main window instance.
		/// Initializes the controls invocation context (likely for managing UI thread operations),
		/// initializes WPF components as defined in the XAML, and loads help/info data into the window title.
		/// </summary>
		public MainWindow()
		{
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			LoadHelpAndInfo();
		}

		/// <summary>
		/// Loads assembly metadata and sets the window Title to a formatted assembly title string.
		/// This typically provides application identification and version info dynamically in the window UI.
		/// </summary>
		void LoadHelpAndInfo()
		{
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			Title = ai.GetTitle(true, false, true, false, false);
		}

		/// <summary>
		/// Reference to an InfoControl instance, presumably for managing or displaying help information within the UI.
		/// </summary>
		public InfoControl HMan;

		/// <summary>
		/// Static flag indicating when the main window is in the process of closing,
		/// useful for other components to check whether the application is shutting down.
		/// </summary>
		public static bool IsClosing;

		/// <summary>
		/// Handles the window closing event, marking the IsClosing flag as true.
		/// This ensures proper signaling for shutdown-related logic or cancelation if needed.
		/// </summary>
		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			IsClosing = true;
		}
	}

}
