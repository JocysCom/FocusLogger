﻿using JocysCom.ClassLibrary.Configuration;
using System;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace JocysCom.FocusLogger
{
	public class DataItem : ISettingsItem, INotifyPropertyChanged
	{

		public DateTime Date { get => _Date; set => SetProperty(ref _Date, value); }
		DateTime _Date;

		public int ProcessId { get => _ProcessId; set => SetProperty(ref _ProcessId, value); }
		int _ProcessId;

		public string ProcessName { get => _ProcessName; set => SetProperty(ref _ProcessName, value); }
		string _ProcessName;

		public string ProcessPath { get => _ProcessPath; set => SetProperty(ref _ProcessPath, value); }
		string _ProcessPath;

		public string WindowTitle { get => _WindowTitle; set => SetProperty(ref _WindowTitle, value); }
		string _WindowTitle;

		public bool HasMouse { get => _HasMouse; set => SetProperty(ref _HasMouse, value); }
		bool _HasMouse;

		public bool HasKeyboard { get => _HasKeyboard; set => SetProperty(ref _HasKeyboard, value); }
		bool _HasKeyboard;

		public bool HasCaret { get => _HasCaret; set => SetProperty(ref _HasCaret, value); }
		bool _HasCaret;

		public bool IsActive { get => _IsActive; set => SetProperty(ref _IsActive, value); }
		bool _IsActive;

		public bool NonPath { get => _IsError; set => SetProperty(ref _IsError, value); }
		bool _IsError;

		public bool IsSame(DataItem item)
		{
			return
			item.ProcessId == ProcessId &&
			item.HasMouse == HasMouse &&
			item.HasKeyboard == HasKeyboard &&
			item.HasCaret == HasCaret &&
			item.IsActive == IsActive;
		}

		public System.Windows.MessageBoxImage StatusCode { get => _StatusCode; set => SetProperty(ref _StatusCode, value); }
		System.Windows.MessageBoxImage _StatusCode;

		#region ■ ISettingsItem

		bool ISettingsItem.Enabled { get => IsEnabled; set => IsEnabled = value; }
		private bool IsEnabled;

		public bool IsEmpty =>
			string.IsNullOrEmpty(ProcessName);

		#endregion

		#region ■ INotifyPropertyChanged

		public event PropertyChangedEventHandler PropertyChanged;

		protected void SetProperty<T>(ref T property, T value, [CallerMemberName] string propertyName = null)
		{
			property = value;
			PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
		}

		protected void OnPropertyChanged([CallerMemberName] string propertyName = null)
		{
			PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
		}

		#endregion

	}
}
