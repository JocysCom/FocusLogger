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
		/// Initializes the controls invocation context (likely for managing UI thread dispatching and synchronization),
		/// initializes all visual components as defined in the associated XAML file, and loads application metadata into the window title.
		/// This setup is critical for ensuring the UI thread is properly configured before interaction,
		/// and for providing dynamic assembly information to users to aid in identification and troubleshooting.
		/// </summary>
		public MainWindow()
		{
			// Initialize the UI thread context to enable safe cross-thread operations on controls,
			// which is a foundational setup step for a responsive WPF application handling user focus logging.
			ControlsHelper.InitInvokeContext();

			// Load and apply all UI components defined in the corresponding XAML file.
			InitializeComponent();

			// Dynamically set the window title using assembly metadata,
			// ensuring the UI reflects accurate version and descriptive information for users.
			LoadHelpAndInfo();
		}

		/// <summary>
		/// Retrieves the executing assembly's metadata to dynamically set the window title.
		/// This helps to display current application version or descriptive info directly in the UI,
		/// improving user awareness of the application's identity and state without hardcoding values.
		/// </summary>
		void LoadHelpAndInfo()
		{
			// Get the assembly that contains this code to extract metadata like version and product information.
			var assembly = Assembly.GetExecutingAssembly();

			// Utilize the AssemblyInfo helper class to format and retrieve the desired title string,
			// choosing which parts such as version or description to include, to present a concise app identity.
			var ai = new ClassLibrary.Configuration.AssemblyInfo();

			// Set the window's title property to the dynamically generated assembly title string.
			Title = ai.GetTitle(true, false, true, false, false);
		}

		/// <summary>
		/// Holds a reference to an InfoControl instance embedded within the MainWindow.
		/// InfoControl is a user control defined in InfoControl.xaml that likely manages
		/// display and interaction with help or instructional content for the user.
		/// This allows the main window to present context-sensitive help or guidance,
		/// enhancing the user experience and supporting the application's goal of logging and user focus assistance.
		/// </summary>
		public InfoControl HMan; // Reference to help/info UI control embedded in the main window.

		/// <summary>
		/// Static flag to indicate if the main window is currently closing.
		/// This provides a way for other components or background workers to detect shutdown state
		/// and gracefully terminate operations such as logging or resource handling,
		/// which is essential to maintain application stability and data integrity on exit.
		/// </summary>
		public static bool IsClosing; // Indicates whether the main window is in the process of closing.

		/// <summary>
		/// Event handler for the window's Closing event.
		/// Sets the IsClosing flag to true to signal application shutdown is underway,
		/// allowing other parts of the application to react accordingly (e.g., stopping background tasks).
		/// This is part of a coordinated shutdown strategy intended to ensure smooth application exit.
		/// </summary>
		private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
		{
			// Mark that the application is closing to notify subsystems and prevent further operations.
			IsClosing = true;
		}
	}

}
