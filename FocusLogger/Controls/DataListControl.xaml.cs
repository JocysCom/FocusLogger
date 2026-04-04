using JocysCom.ClassLibrary.ComponentModel;
using JocysCom.ClassLibrary.Controls;
using JocysCom.FocusLogger.Resources.Icons;
using Microsoft.Win32;
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows;
using System.Windows.Controls;

namespace JocysCom.FocusLogger.Controls
{
	/// <summary>
	/// Interaction logic for DataListControl.xaml
	/// </summary>
	public partial class DataListControl : UserControl
	{
		public DataListControl()
		{
			InitializeComponent();
			if (ControlsHelper.IsDesignMode(this))
				return;
			// Configure converter.
			MainDataGrid.ItemsSource = DataItems;
			var gridFormattingConverter = MainDataGrid.Resources.Values.OfType<ItemFormattingConverter>().First();
			gridFormattingConverter.ConvertFunction = _MainDataGridFormattingConverter_Convert;
		}

		object _MainDataGridFormattingConverter_Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
		{
			var sender = (FrameworkElement)values[0];
			var template = (FrameworkElement)values[1];
			var value = values[2];
			var cell = (DataGridCell)(template ?? sender).Parent;
			var item = (DataItem)cell.DataContext;
			if (cell.Column == IsActiveImageColumn)
			{
				return item.IsActive ? Icons_Default.Current[Icons_Default.Icon_window] : null;
			}
			if (cell.Column == IsActiveColumn)
			{
				cell.Opacity = 0.5;
				return item.IsActive ? "Active" : "";
			}
			// Mouse.
			if (cell.Column == HasMouseColumn)
				return item.HasMouse ? "Mouse" : "";
			if (cell.Column == HasMouseImageColumn)
				return item.HasMouse ? Icons_Default.Current[Icons_Default.Icon_mouse2] : null;
			// Keyboard.
			if (cell.Column == HasKeyboardImageColumn)
				return item.HasKeyboard ? Icons_Default.Current[Icons_Default.Icon_keyboard] : null;
			if (cell.Column == HasKeyboardColumn)
				return item.HasKeyboard ? "Keyboard" : "";
			// Caret.
			if (cell.Column == HasCaretImageColumn)
				return item.HasCaret ? Icons_Default.Current[Icons_Default.Icon_text_field] : null;
			if (cell.Column == HasCaretColumn)
				return item.HasCaret ? "Caret" : "";
			if (cell.Column == DateColumn)
			{
				value = string.Format("{0:HH:mm:ss:fff}", item.Date);
				cell.Opacity = 0.5;
			}
			if (cell.Column == ProcessPathColumn)
			{
				if (item.NonPath)
					cell.Opacity = 0.3;
			}
			// Other.
			return value;
		}

		public SortableBindingList<DataItem> DataItems { get; set; } = new SortableBindingList<DataItem>();

		private void UserControl_Loaded(object sender, RoutedEventArgs e)
		{
			if (ControlsHelper.IsDesignMode(this))
				return;
			InitTimer();
		}

		private string _lastSavedCsvPath;

		private void SaveCsvButton_Click(object sender, RoutedEventArgs e)
		{
			if (DataItems.Count == 0)
			{
				MessageBox.Show("No log entries to save.", "Save CSV", MessageBoxButton.OK, MessageBoxImage.Information);
				return;
			}
			var dialog = new SaveFileDialog
			{
				Filter = "CSV files (*.csv)|*.csv",
				DefaultExt = ".csv",
				FileName = $"FocusLog_{DateTime.Now:yyyy-MM-dd_HHmmss}.csv",
			};
			if (dialog.ShowDialog() != true)
				return;
			var csv = BuildCsvContent(DataItems);
			File.WriteAllText(dialog.FileName, csv, Encoding.UTF8);
			_lastSavedCsvPath = dialog.FileName;
		}

		private void ExploreCsvButton_Click(object sender, RoutedEventArgs e)
		{
			if (string.IsNullOrEmpty(_lastSavedCsvPath) || !File.Exists(_lastSavedCsvPath))
			{
				MessageBox.Show("No CSV file saved yet. Use 'Save CSV' first.", "Explore", MessageBoxButton.OK, MessageBoxImage.Information);
				return;
			}
			Process.Start("explorer.exe", $"/select,\"{_lastSavedCsvPath}\"");
		}

		public static string BuildCsvContent(System.Collections.Generic.IEnumerable<DataItem> items)
		{
			var sb = new StringBuilder();
			sb.AppendLine("Date,PID,Process Name,Active,Mouse,Keyboard,Caret,Window Title,Path");
			foreach (var item in items)
			{
				sb.AppendLine(string.Join(",",
					CsvEscape(item.Date.ToString("yyyy-MM-dd HH:mm:ss.fff")),
					item.ProcessId,
					CsvEscape(item.ProcessName),
					item.IsActive,
					item.HasMouse,
					item.HasKeyboard,
					item.HasCaret,
					CsvEscape(item.WindowTitle),
					CsvEscape(item.ProcessPath)
				));
			}
			return sb.ToString();
		}

		public static string CsvEscape(string value)
		{
			if (string.IsNullOrEmpty(value))
				return "";
			if (value.Contains(",") || value.Contains("\"") || value.Contains("\n"))
				return "\"" + value.Replace("\"", "\"\"") + "\"";
			return value;
		}

		private void CopyAiPromptButton_Click(object sender, RoutedEventArgs e)
		{
			var prompt = ClassLibrary.Helper.FindResource<string>("Resources/AiAnalysisPrompt.md").TrimEnd();
			var box = new MessageBoxWindow();
			box.SetSize(600, 400);
			box.ShowPrompt(prompt, "AI Analysis Prompt - Copy and paste into your AI assistant", MessageBoxButton.OK, MessageBoxImage.Information, MessageBoxResult.OK);
		}

		private void ClearButton_Click(object sender, RoutedEventArgs e)
		{
			DataItems.Clear();
		}

		private void UserControl_Unloaded(object sender, RoutedEventArgs e)
		{
			if (ControlsHelper.IsDesignMode(this))
				return;
		}

		object AddLock = new object();

		public bool IsElevated
		{
			get
			{
				var id = System.Security.Principal.WindowsIdentity.GetCurrent();
				return id.Owner != id.User;
			}
		}

		public void UpdateFromProcess(DataItem item)
		{
			using (var process = Process.GetProcessById(item.ProcessId))
			{
				item.ProcessName = process.ProcessName;
				if (item.ProcessId == 0)
				{
					item.ProcessPath = "System Idle Process";
					item.NonPath = true;
				}
				if (item.ProcessId > 0)
				{
					try
					{
						item.ProcessPath = process.MainModule?.FileName;
					}
					catch (Exception ex)
					{
						const int E_FAIL = unchecked((int)0x80004005); // -2147467259
						item.ProcessPath = $"Error: {ex.Message}";
						item.NonPath = true;
						// If Win32 Acccess is denied exception, then...
						if (ex is Win32Exception && ex.HResult == E_FAIL)
							item.ProcessPath += " Run as Administrator";

					}
				}
			}
		}

		System.Timers.Timer _Timer;

		void InitTimer()
		{
			_Timer = new System.Timers.Timer();
			_Timer.Elapsed += _Timer_Elapsed;
			_Timer.AutoReset = false;
			_Timer.Interval = 1;
			_Timer.Start();
		}

		private void _Timer_Elapsed(object sender, System.Timers.ElapsedEventArgs e)
		{
			if (MainWindow.IsClosing)
				return;
			UpdateInfo();
			_Timer.Start();
		}

		DataItem oldActiveItem = new DataItem();
		DataItem oldForegroundItem = new DataItem();

		public void UpdateInfo()
		{
			// Active window -  Window that appears in the foreground with a highlighted title bar.
			// Foreground window - Window with which the user is currently working.
			//   The system assigns a slightly higher priority to the thread used to create the foreground window.
			// Focus window - Window that is currently receiving keyboard input.
			//   The focus window is always the active window, a descendent of the active window, or NULL.
			// Top-Level window -  A window that has no parent window.
			//
			lock (AddLock)
			{
				// Get window which or child window of which receives keyboard input.
				var activeHandle = NativeMethods.GetActiveWindow();
				var activeItem = GetItemFromHandle(activeHandle, true);
				// If active window changed then...
				if (!activeItem.IsSame(oldActiveItem))
				{
					oldActiveItem = activeItem;
					UpdateFromProcess(activeItem);
					ControlsHelper.BeginInvoke(() => DataItems.Insert(0, activeItem));
				}
				// Get foreground window.
				var foregroundHandle = NativeMethods.GetForegroundWindow();
				var foregroundItem = GetItemFromHandle(foregroundHandle);
				// If foreground window changed then...
				if (!foregroundItem.IsSame(oldForegroundItem))
				{
					oldForegroundItem = foregroundItem;
					UpdateFromProcess(foregroundItem);
					ControlsHelper.BeginInvoke(() => DataItems.Insert(0, foregroundItem));
				}
			}
		}

		DataItem GetItemFromHandle(IntPtr hWnd, bool isActive = false)
		{
			var item = new DataItem();
			item.Date = DateTime.Now;
			item.IsActive = isActive;
			var info = NativeMethods.GetInfo(hWnd);
			if (info.HasValue)
			{
				item.HasMouse = info.Value.hwndCapture != IntPtr.Zero;
				item.HasKeyboard = info.Value.hwndFocus != IntPtr.Zero;
				item.HasCaret = info.Value.hwndCaret != IntPtr.Zero;
			}
			int processId;
			if (isActive)
			{
				hWnd = NativeMethods.GetTopWindow(hWnd);
			}
			item.WindowTitle = NativeMethods.GetWindowText(hWnd);
			NativeMethods.GetWindowThreadProcessId(hWnd, out processId);
			item.ProcessId = processId;
			return item;
		}

	}
}