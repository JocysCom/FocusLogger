using JocysCom.ClassLibrary.Controls;
using System.Reflection;
using System.Windows;

namespace JocysCom.FocusLogger
{
	public partial class MainWindow : Window
	{
		/// <summary>
		/// Initializes a new instance of the <see cref="MainWindow"/> class, sets up control invocation context, loads the UI, and populates application metadata for display.
		/// </summary>
		public MainWindow()
		{
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			LoadHelpAndInfo();
		}

		/// <summary>
		/// Loads assembly metadata and sets the window title to display application info, ensuring users see current build details as part of branding and support diagnostics.
		/// </summary>
		void LoadHelpAndInfo()
		{
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			Title = ai.GetTitle(true, false, true, false, false);
		}

		/// <summary>
		/// Reference to the main info/help control displayed in the UI. Populated by XAML.
		/// </summary>
		public InfoControl HMan;

		/// <summary>
		/// Indicates whether the application is in the process of closing. This static flag is checked by background operations (such as timer loops in DataListControl) to prevent actions during shutdown.
		/// </summary>
		public static bool IsClosing;

		/// <summary>
		/// Handles the window closing event. Sets the <see cref="IsClosing"/> flag to true so that background processes (e.g., focus update timers) can safely detect shutdown and avoid race conditions or invalid operations during exit.
		/// </summary>
		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			IsClosing = true;
		}
	}

}
