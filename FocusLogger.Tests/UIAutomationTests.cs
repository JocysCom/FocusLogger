using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Windows.Automation;

namespace JocysCom.FocusLogger.Tests
{
	[TestClass]
	public class UIAutomationTests
	{
		private static string GetAppPath()
		{
			var dir = AppDomain.CurrentDomain.BaseDirectory;
			// Navigate from test bin to the main project bin.
			var appDir = Path.GetFullPath(Path.Combine(dir, "..", "..", "..", "..", "FocusLogger", "bin", "Debug", "net8.0-windows"));
			return Path.Combine(appDir, "JocysCom.FocusLogger.exe");
		}

		private static AutomationElement FindDescendant(AutomationElement parent, string automationId, int timeoutMs = 5000)
		{
			var condition = new PropertyCondition(AutomationElement.AutomationIdProperty, automationId);
			var sw = Stopwatch.StartNew();
			while (sw.ElapsedMilliseconds < timeoutMs)
			{
				var element = parent.FindFirst(TreeScope.Descendants, condition);
				if (element != null)
					return element;
				Thread.Sleep(200);
			}
			return null;
		}

		[TestMethod]
		public void App_LaunchAndDetectNotepadFocus()
		{
			var appPath = GetAppPath();
			if (!File.Exists(appPath))
				Assert.Inconclusive($"App not built at: {appPath}. Build the main project first.");

			Process appProcess = null;
			Process notepadProcess = null;
			try
			{
				// Launch FocusLogger.
				appProcess = Process.Start(new ProcessStartInfo(appPath) { UseShellExecute = true });
				Thread.Sleep(2000);

				// Find the main window via UI Automation.
				var mainWindow = FindMainWindow(appProcess.Id);
				Assert.IsNotNull(mainWindow, "FocusLogger main window not found.");

				// Find the DataGrid.
				var dataGrid = FindDescendant(mainWindow, "MainDataGrid");
				Assert.IsNotNull(dataGrid, "MainDataGrid not found.");

				// Launch Notepad to trigger a focus change.
				notepadProcess = Process.Start("notepad.exe");
				Thread.Sleep(2000);

				// Bring FocusLogger back to check the grid.
				notepadProcess.Kill();
				notepadProcess.WaitForExit();
				notepadProcess = null;
				Thread.Sleep(1000);

				// Verify the DataGrid has rows (focus events were logged).
				var gridPattern = dataGrid.GetCurrentPattern(GridPattern.Pattern) as GridPattern;
				Assert.IsNotNull(gridPattern, "DataGrid does not support GridPattern.");
				Assert.IsTrue(gridPattern.Current.RowCount > 0, "DataGrid should have logged focus change events.");

				// Verify Clear button works.
				var clearButton = FindDescendant(mainWindow, "ClearButton");
				Assert.IsNotNull(clearButton, "ClearButton not found.");
				var invokePattern = clearButton.GetCurrentPattern(InvokePattern.Pattern) as InvokePattern;
				invokePattern.Invoke();
				Thread.Sleep(500);
				Assert.AreEqual(0, gridPattern.Current.RowCount, "DataGrid should be empty after Clear.");
			}
			finally
			{
				notepadProcess?.Kill();
				if (appProcess != null && !appProcess.HasExited)
				{
					appProcess.Kill();
					appProcess.WaitForExit();
				}
			}
		}

		private static AutomationElement FindMainWindow(int processId, int timeoutMs = 10000)
		{
			var desktop = AutomationElement.RootElement;
			var sw = Stopwatch.StartNew();
			while (sw.ElapsedMilliseconds < timeoutMs)
			{
				var condition = new AndCondition(
					new PropertyCondition(AutomationElement.ProcessIdProperty, processId),
					new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Window)
				);
				var window = desktop.FindFirst(TreeScope.Children, condition);
				if (window != null)
					return window;
				Thread.Sleep(300);
			}
			return null;
		}
	}
}
