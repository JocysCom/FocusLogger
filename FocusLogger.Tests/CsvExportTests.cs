using JocysCom.FocusLogger;
using JocysCom.FocusLogger.Controls;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.IO;
using System.Linq;
using System.Text;

namespace JocysCom.FocusLogger.Tests
{
	[TestClass]
	public class CsvExportTests
	{
		[TestMethod]
		public void CsvEscape_PlainText_ReturnsUnchanged()
		{
			Assert.AreEqual("notepad", DataListControl.CsvEscape("notepad"));
		}

		[TestMethod]
		public void CsvEscape_TextWithComma_WrapsInQuotes()
		{
			Assert.AreEqual("\"hello,world\"", DataListControl.CsvEscape("hello,world"));
		}

		[TestMethod]
		public void CsvEscape_TextWithQuotes_EscapesQuotes()
		{
			Assert.AreEqual("\"say \"\"hi\"\"\"", DataListControl.CsvEscape("say \"hi\""));
		}

		[TestMethod]
		public void CsvEscape_TextWithNewline_WrapsInQuotes()
		{
			Assert.AreEqual("\"line1\nline2\"", DataListControl.CsvEscape("line1\nline2"));
		}

		[TestMethod]
		public void CsvEscape_NullOrEmpty_ReturnsEmpty()
		{
			Assert.AreEqual("", DataListControl.CsvEscape(null));
			Assert.AreEqual("", DataListControl.CsvEscape(""));
		}

		[TestMethod]
		public void BuildCsvContent_WithItems_ProducesValidCsv()
		{
			var items = new[]
			{
				new DataItem
				{
					Date = new DateTime(2026, 4, 4, 10, 30, 0, 123),
					ProcessId = 1234,
					ProcessName = "notepad",
					IsActive = true,
					HasMouse = false,
					HasKeyboard = true,
					HasCaret = true,
					WindowTitle = "Untitled - Notepad",
					ProcessPath = @"C:\Windows\notepad.exe",
				},
				new DataItem
				{
					Date = new DateTime(2026, 4, 4, 10, 30, 1, 456),
					ProcessId = 5678,
					ProcessName = "explorer",
					IsActive = false,
					HasMouse = true,
					HasKeyboard = false,
					HasCaret = false,
					WindowTitle = "File, \"Explorer\"",
					ProcessPath = @"C:\Windows\explorer.exe",
				},
			};
			var csv = DataListControl.BuildCsvContent(items);
			var lines = csv.Split(new[] { Environment.NewLine }, StringSplitOptions.None);
			// Header + 2 data rows + trailing empty line.
			Assert.AreEqual("Date,PID,Process Name,Active,Mouse,Keyboard,Caret,Window Title,Path", lines[0]);
			Assert.AreEqual(4, lines.Length);
			// Verify comma/quote in WindowTitle is escaped.
			Assert.IsTrue(lines[2].Contains("\"File, \"\"Explorer\"\"\""));
		}

		[TestMethod]
		public void BuildCsvContent_Empty_ReturnsHeaderOnly()
		{
			var csv = DataListControl.BuildCsvContent(Array.Empty<DataItem>());
			var lines = csv.Split(new[] { Environment.NewLine }, StringSplitOptions.RemoveEmptyEntries);
			Assert.AreEqual(1, lines.Length);
			Assert.AreEqual("Date,PID,Process Name,Active,Mouse,Keyboard,Caret,Window Title,Path", lines[0]);
		}
	}
}
