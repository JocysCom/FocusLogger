using System;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows;

namespace JocysCom.ClassLibrary.ComponentModel
{
	/// <summary>
	/// INotifyPropertyChanged base with optional WPF Dispatcher marshalling of property-change notifications to the UI thread.
	/// </summary>
	/// <remarks>
	/// Supports MVVM data binding scenarios, with optional UI-thread invocation of property change events.
	/// </remarks>
	public class NotifyPropertyChanged : INotifyPropertyChanged
	{

		#region ■ INotifyPropertyChanged

		/// <summary>
		/// Notifies clients that a property value has changed.
		/// </summary>
		// SUPPRESS: CWE-502: Deserialization of Untrusted Data
		// Fix: Apply [field: NonSerialized] attribute to an event inside class with [Serialized] attribute.
		[field: NonSerialized]
		public event PropertyChangedEventHandler PropertyChanged;

		/// <summary>
		/// Raises the PropertyChanged event. When UseApplicationDispatcher is true, the invocation is marshaled to the WPF UI thread via Application.Current.Dispatcher.
		/// </summary>
		/// <param name="propertyName">Name of the property.</param>
		protected virtual void OnPropertyChanged([CallerMemberName] string propertyName = null)
		{
			if (UseApplicationDispatcher)
			{
				var dispatcher = Application.Current.Dispatcher;
				if (dispatcher.CheckAccess())
					PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
				else
					Application.Current.Dispatcher.Invoke(() =>
						PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName)));
				return;
			}
			PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
		}

		/// <summary>
		/// When true, marshals property-change notifications to the WPF UI thread via Application.Current.Dispatcher. Defaults to false.
		/// </summary>
		[field: NonSerialized, DefaultValue(false)]
		public bool UseApplicationDispatcher = false;

		/// <summary>
		/// Sets the backing field if the new value differs (per Equals), then invokes OnPropertyChanged. Skips notifications when value is unchanged.
		/// </summary>
		/// <typeparam name="T">Type of the backing field.</typeparam>
		/// <param name="property">Reference to the backing field.</param>
		/// <param name="value">New value to assign.</param>
		/// <param name="propertyName">Name of the property; supplied by CallerMemberName automatically.</param>
		protected void SetProperty<T>(ref T property, T value, [CallerMemberName] string propertyName = null)
		{
			if (Equals(property, value))
				return;
			property = value;
			// Invoke overridden OnPropertyChanged method in the most derived class of the object.
			OnPropertyChanged(propertyName);
		}


		#endregion
	}
}