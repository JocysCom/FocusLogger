using System.Windows;

namespace JocysCom.FocusLogger.Resources.Icons
{
	partial class Icons_Default : ResourceDictionary
	{
		public Icons_Default()
		{
			InitializeComponent();
		}

		public static Icons_Default Current => _Current = _Current ?? new Icons_Default();
		private static Icons_Default _Current;

		public const string Icon_keyboard = nameof(Icon_keyboard);
		public const string Icon_mouse2 = nameof(Icon_mouse2);
		public const string Icon_text_field = nameof(Icon_text_field);
		public const string Icon_window = nameof(Icon_window);
		public const string Icon_windows = nameof(Icon_windows);

	}
}
