namespace JocysCom.ClassLibrary.Configuration
{
	public interface ISettingsItem
	{
		bool Enabled { get; set; }

		bool IsEmpty { get; }

	}
}
