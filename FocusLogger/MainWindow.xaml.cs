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
		/// Initializes the controls invocation context for UI thread synchronization,
		/// ensures that all XAML-defined components are loaded, and populates
		/// the window title with dynamic application information for versioning and troubleshooting.
		/// This sequence is necessary for safe cross-thread UI operations and to provide
		/// accurate application identity to the user.
		/// </summary>
		public MainWindow()
		{
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			LoadHelpAndInfo();
		}

		/// <summary>
		/// Dynamically loads assembly metadata (such as version and descriptive info) for the window's title,
		/// avoiding hardcoding and ensuring users see the current app state directly in the UI.
		/// </summary>
		void LoadHelpAndInfo()
		{
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			Title = ai.GetTitle(true, false, true, false, false);
		}

		/// <summary>
		/// Reference to InfoControl user control (defined in MainWindow.xaml),
		/// permitting context-sensitive help or user guidance consistent with FocusLogger's aim.
		/// </summary>
		public InfoControl HMan;

		/// <summary>
		/// Global flag for coordinated app shutdown.
		/// Signals to background/logging components when it is unsafe to proceed due to imminent closing.
		/// </summary>
		public static bool IsClosing;

		/// <summary>
		/// Handles window's Closing event by setting IsClosing flag.
		/// Enables cooperative shutdown for critical operations (e.g. focus logging persistence).
		/// </summary>
		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			IsClosing = true;
		}
	}

}
