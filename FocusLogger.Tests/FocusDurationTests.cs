using JocysCom.ClassLibrary.ComponentModel;
using JocysCom.FocusLogger;
using JocysCom.FocusLogger.Controls;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.ComponentModel;
using System.Linq;

namespace JocysCom.FocusLogger.Tests
{
	[TestClass]
	public class FocusDurationTests
	{
		private static PropertyDescriptor DateDescriptor()
			=> TypeDescriptor.GetProperties(typeof(DataItem))[nameof(DataItem.Date)];

		[TestMethod]
		public void RecordFocusChange_FinalizesPreviousEntryDuration()
		{
			var list = new SortableBindingList<DataItem>();
			DataItem prev = null;
			prev = DataListControl.RecordFocusChange(list, prev,
				new DataItem { Date = new DateTime(2026, 4, 4, 10, 0, 0, 0) });
			prev = DataListControl.RecordFocusChange(list, prev,
				new DataItem { Date = new DateTime(2026, 4, 4, 10, 0, 1, 0) });
			// The first entry stayed focused exactly one second before the second arrived.
			Assert.AreEqual(1000, list.Single(x => x.Date.Second == 0).Duration);
			// The newest entry has no successor yet, so its Duration stays 0.
			Assert.AreEqual(0, list.Single(x => x.Date.Second == 1).Duration);
		}

		[TestMethod]
		public void RecordFocusChange_AfterAscendingSort_DoesNotInflateOldestDuration()
		{
			// Reproduces the issue #41 follow-up: once the grid is sorted by Date
			// ascending, the oldest row moves to index 0. The old DataItems[0]-based
			// math then recomputed that row's Duration from its fixed timestamp on
			// every refresh, so it grew without bound. Tracking the previous entry by
			// reference keeps already-finalized durations frozen.
			var list = new SortableBindingList<DataItem>();
			DataItem prev = null;
			var a = new DataItem { Date = new DateTime(2026, 4, 4, 10, 0, 0, 0) };
			var b = new DataItem { Date = new DateTime(2026, 4, 4, 10, 0, 5, 0) };
			var c = new DataItem { Date = new DateTime(2026, 4, 4, 10, 0, 12, 0) };
			prev = DataListControl.RecordFocusChange(list, prev, a); // a.Duration set when b arrives
			prev = DataListControl.RecordFocusChange(list, prev, b); // a.Duration = 5000
			prev = DataListControl.RecordFocusChange(list, prev, c); // b.Duration = 7000
			Assert.AreEqual(5000, a.Duration);
			Assert.AreEqual(7000, b.Duration);
			// User sorts ascending: oldest (a) is now at the top of the grid.
			((IBindingList)list).ApplySort(DateDescriptor(), ListSortDirection.Ascending);
			Assert.AreSame(a, list[0]);
			// Many later focus changes (refreshes) arrive, an hour and two hours on.
			prev = DataListControl.RecordFocusChange(list, prev,
				new DataItem { Date = new DateTime(2026, 4, 4, 11, 0, 0, 0) });
			prev = DataListControl.RecordFocusChange(list, prev,
				new DataItem { Date = new DateTime(2026, 4, 4, 12, 0, 0, 0) });
			// The already-finalized durations must stay frozen, not grow toward "now".
			Assert.AreEqual(5000, a.Duration);
			Assert.AreEqual(7000, b.Duration);
		}
	}
}
