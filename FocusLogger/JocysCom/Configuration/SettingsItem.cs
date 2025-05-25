using JocysCom.ClassLibrary.ComponentModel;
using System.ComponentModel;

namespace JocysCom.ClassLibrary.Configuration
{
	/// <summary>Base configuration entity implementing ISettingsItem with change notification support.</summary>
	/// <remarks>
	/// Exposes enabled state and emptiness checks.
	/// Extended by SettingsFileItem for file-based entries.
	/// Edited via a WinForms SettingsItemForm.
	/// </remarks>
	public class SettingsItem : NotifyPropertyChanged, ISettingsItem
	{
		/// <inheritdoc />
		[DefaultValue(true)]
		public bool IsEnabled { get => _IsEnabled; set => SetProperty(ref _IsEnabled, value); }
		bool _IsEnabled = true;

		/// <inheritdoc />
		public virtual bool IsEmpty => true;

	}
}
