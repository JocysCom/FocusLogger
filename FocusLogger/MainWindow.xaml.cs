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
		public MainWindow()
		{
			ControlsHelper.InitInvokeContext();
			InitializeComponent();
			LoadHelpAndInfo();
		}

		void LoadHelpAndInfo()
		{
			var assembly = Assembly.GetExecutingAssembly();
			var ai = new ClassLibrary.Configuration.AssemblyInfo();
			Title = ai.GetTitle(true, false, true, false, false);
		}

		public InfoControl HMan;

		public static bool IsClosing;

		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			IsClosing = true;
		}
	}

}
