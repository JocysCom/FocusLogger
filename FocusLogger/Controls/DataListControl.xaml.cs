﻿using JocysCom.ClassLibrary.ComponentModel;
using JocysCom.ClassLibrary.Controls;
using JocysCom.ClassLibrary.Controls.Themes;
using System;
using System.Data;
using System.Diagnostics;
using System.Globalization;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Automation;
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
			if (!IsElevated)
			{
				WindowTiteColumn.Visibility = Visibility.Hidden;
			}
			// Configure converter.
			MainDataGrid.ItemsSource = DataItems;
			var gridFormattingConverter = MainDataGrid.Resources.Values.OfType<ItemFormattingConverter>().First();
			gridFormattingConverter.ConvertFunction = _MainDataGridFormattingConverter_Convert;
		}

		object _MainDataGridFormattingConverter_Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
		{
			var sender = (FrameworkElement)values[0];
			var template = (FrameworkElement)values[1];
			var cell = (DataGridCell)(template ?? sender).Parent;
			var value = values[2];
			var item = (DataItem)cell.DataContext;
			if (cell.Column == ProcessPathColumn)
			{
			}
			return value;
		}

		public SortableBindingList<DataItem> DataItems { get; set; } = new SortableBindingList<DataItem>();

		private void UserControl_Loaded(object sender, RoutedEventArgs e)
		{
			if (ControlsHelper.IsDesignMode(this))
				return;
			InitTimer();
			//Automation.AddAutomationFocusChangedEventHandler(OnFocusChangedHandler);
		}

		private void ClearButton_Click(object sender, RoutedEventArgs e)
		{
			DataItems.Clear();
		}

		private void UserControl_Unloaded(object sender, RoutedEventArgs e)
		{
			if (ControlsHelper.IsDesignMode(this))
				return;
			//Automation.RemoveAutomationFocusChangedEventHandler(OnFocusChangedHandler);
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

		int lastProcessId;

		private void OnFocusChangedHandler(object src, AutomationFocusChangedEventArgs args)
		{
			if (MainWindow.IsClosing)
				return;
			var element = src as AutomationElement;
			if (element != null)
			{
				var name = element.Current.Name;
				var id = element.Current.AutomationId;
				var processId = element.Current.ProcessId;
				AddProcess(processId);
			}
		}

		public void AddProcess(int processId)
		{
			lock (AddLock)
			{
				// Add only if process changed.
				if (lastProcessId == processId)
					return;
				lastProcessId = processId;
			}
			using (var process = Process.GetProcessById(processId))
			{
				var item = new DataItem();
				item.Date = DateTime.Now;
				item.ProcessId = process.Id;
				item.ProcessName = process.ProcessName;
				if (processId > 0)
				{
					item.ProcessPath = process.MainModule?.FileName;
					if (IsElevated)
					{
						try
						{
							item.WindowTitle = process.MainWindowTitle;
						}
						catch { }
					}
				}
				ControlsHelper.BeginInvoke(() =>
				{
					DataItems.Insert(0, item);
				});
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
			_Timer.Start();
			var processId = GetActiveProcessId();
			AddProcess(processId);
		}

		public static int GetActiveProcessId()
		{
			var activatedHandle = GetForegroundWindow();
			if (activatedHandle == IntPtr.Zero)
				return 0;       // No window is currently activated
			int activeProcId;
			GetWindowThreadProcessId(activatedHandle, out activeProcId);
			return activeProcId;
		}


		[DllImport("user32.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
		private static extern IntPtr GetForegroundWindow();

		[DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
		private static extern int GetWindowThreadProcessId(IntPtr handle, out int processId);

	}
}