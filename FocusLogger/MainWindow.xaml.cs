using JocysCom.ClassLibrary.Controls;
using System.Reflection;
using System.Windows;

namespace JocysCom.FocusLogger
{
	public partial class MainWindow : Window
	{
		public MainWindow()
		{
			// Initializes the context for cross-thread UI operations before any WPF controls are interacted with.
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			// Loads window title and help information from assembly metadata after UI is set up.
			LoadHelpAndInfo();
		}

		void LoadHelpAndInfo()
		{
			// Uses AssemblyInfo to extract application metadata for display in window title.
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			Title = ai.GetTitle(true, false, true, false, false);
		}

		public InfoControl HMan;

		public static bool IsClosing;

		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			// Signals to other operations that the main window is closing (used for graceful shutdown logic elsewhere).
			IsClosing = true;
		}
	}

}
