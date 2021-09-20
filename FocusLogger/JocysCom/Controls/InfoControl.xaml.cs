using System;
using System.Reflection;
using System.Windows.Controls;


namespace JocysCom.ClassLibrary.Controls
{
	/// <summary>
	/// Interaction logic for InfoControl.xaml
	/// </summary>
	public partial class InfoControl : UserControl
	{
		public InfoControl()
		{
			InitializeComponent();
			HMan = new BaseWithHeaderManager<object>(HelpHeadLabel, HelpBodyLabel, LeftIcon, RightIcon, this);
			var assembly = Assembly.GetExecutingAssembly();
			var product = ((AssemblyProductAttribute)Attribute.GetCustomAttribute(assembly, typeof(AssemblyProductAttribute))).Product;
			var description = ((AssemblyDescriptionAttribute)Attribute.GetCustomAttribute(assembly, typeof(AssemblyDescriptionAttribute))).Description;
			HMan.SetBodyInfo(description);
			HMan.SetHead(product);
		}

		public BaseWithHeaderManager<object> HMan;


		#region ■ Properties

		public object RightIconContent
		{
			get => RightIcon.GetValue(ContentProperty);
			set => RightIcon.SetValue(ContentProperty, value);
		}

		#endregion
	}
}
