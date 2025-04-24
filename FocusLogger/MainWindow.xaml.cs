using JocysCom.ClassLibrary.Controls;
using System.Reflection;
using System.Windows;

namespace JocysCom.FocusLogger
{
	public partial class MainWindow : Window
	{
		public MainWindow()
		{
			// Ensures that WPF threading context is set up for cross-thread UI operations.
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			LoadHelpAndInfo();
		}

		/// <summary>
		/// Sets the window title using assembly metadata; shows build/config/environment details in the title bar.
		/// </summary>
		void LoadHelpAndInfo()
		{
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			Title = ai.GetTitle(true, false, true, false, false);
		}

		public InfoControl HMan;

		/// <summary>
		/// Indicates whether the main window is in the process of closing; static for cross-component status.
		/// </summary>
		public static bool IsClosing;

		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			// Flag triggers shutdown routines elsewhere when main window closes.
			IsClosing = true;
		}
	}

}
