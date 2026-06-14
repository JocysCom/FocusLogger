using JocysCom.ClassLibrary.ComponentModel;
using JocysCom.FocusLogger;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.ComponentModel;
using System.Linq;

namespace JocysCom.FocusLogger.Tests
{
	[TestClass]
	public class SortableBindingListTests
	{
		private static PropertyDescriptor DateDescriptor()
			=> TypeDescriptor.GetProperties(typeof(DataItem))[nameof(DataItem.Date)];

		private static PropertyDescriptor ProcessPathDescriptor()
			=> TypeDescriptor.GetProperties(typeof(DataItem))[nameof(DataItem.ProcessPath)];

		private static DataItem ItemAt(DateTime date)
			=> new DataItem { Date = date };

		private static DataItem ItemWithPath(string path)
			=> new DataItem { ProcessPath = path };

		[TestMethod]
		public void ApplySort_ByDateAscending_OrdersByActualDateTime()
		{
			// Spread across hour and day boundaries — the original "format string"
			// sort path produced wrong order here because HH:mm:ss:fff
			// lexicographic sort breaks at 23:59 → 00:00.
			var list = new SortableBindingList<DataItem>
			{
				ItemAt(new DateTime(2026, 4, 4, 23, 59, 50, 0)),
				ItemAt(new DateTime(2026, 4, 5, 0, 0, 5, 0)),
				ItemAt(new DateTime(2026, 4, 4, 10, 30, 0, 0)),
			};
			((IBindingList)list).ApplySort(DateDescriptor(), ListSortDirection.Ascending);
			var ticks = list.Select(x => x.Date).ToArray();
			CollectionAssert.AreEqual(
				new[]
				{
					new DateTime(2026, 4, 4, 10, 30, 0, 0),
					new DateTime(2026, 4, 4, 23, 59, 50, 0),
					new DateTime(2026, 4, 5, 0, 0, 5, 0),
				},
				ticks);
		}

		[TestMethod]
		public void ApplySort_ByDateDescending_NewestFirst()
		{
			var list = new SortableBindingList<DataItem>
			{
				ItemAt(new DateTime(2026, 4, 4, 10, 30, 0, 0)),
				ItemAt(new DateTime(2026, 4, 5, 0, 0, 5, 0)),
				ItemAt(new DateTime(2026, 4, 4, 23, 59, 50, 0)),
			};
			((IBindingList)list).ApplySort(DateDescriptor(), ListSortDirection.Descending);
			CollectionAssert.AreEqual(
				new[]
				{
					new DateTime(2026, 4, 5, 0, 0, 5, 0),
					new DateTime(2026, 4, 4, 23, 59, 50, 0),
					new DateTime(2026, 4, 4, 10, 30, 0, 0),
				},
				list.Select(x => x.Date).ToArray());
		}

		[TestMethod]
		public void ApplySort_ByProcessPathAscending_OrdersLexicographically()
		{
			// Mirrors the Date-sort tests: confirms that once the Path column wires
			// SortMemberPath="ProcessPath" through to SortableBindingList, string
			// values sort alphabetically via PropertyComparer<DataItem>.
			var list = new SortableBindingList<DataItem>
			{
				ItemWithPath(@"C:\Windows\explorer.exe"),
				ItemWithPath(@"C:\Program Files\App\app.exe"),
				ItemWithPath(@"D:\Tools\utility.exe"),
			};
			((IBindingList)list).ApplySort(ProcessPathDescriptor(), ListSortDirection.Ascending);
			CollectionAssert.AreEqual(
				new[]
				{
					@"C:\Program Files\App\app.exe",
					@"C:\Windows\explorer.exe",
					@"D:\Tools\utility.exe",
				},
				list.Select(x => x.ProcessPath).ToArray());
		}

		[TestMethod]
		public void ApplySort_ByProcessPathDescending_OrdersLexicographicallyReversed()
		{
			var list = new SortableBindingList<DataItem>
			{
				ItemWithPath(@"C:\Program Files\App\app.exe"),
				ItemWithPath(@"D:\Tools\utility.exe"),
				ItemWithPath(@"C:\Windows\explorer.exe"),
			};
			((IBindingList)list).ApplySort(ProcessPathDescriptor(), ListSortDirection.Descending);
			CollectionAssert.AreEqual(
				new[]
				{
					@"D:\Tools\utility.exe",
					@"C:\Windows\explorer.exe",
					@"C:\Program Files\App\app.exe",
				},
				list.Select(x => x.ProcessPath).ToArray());
		}

		[TestMethod]
		public void Insert_WhenSortedDescending_PlacesItemAtCorrectIndexNotAtZero()
		{
			// Live-collection pattern: the app sorts descending and continuously
			// Insert(0, newItem)s. Without the fix, new items always end up at
			// index 0 regardless of their Date — breaking the sort order.
			var list = new SortableBindingList<DataItem>
			{
				ItemAt(new DateTime(2026, 4, 5, 12, 0, 0, 0)),
				ItemAt(new DateTime(2026, 4, 4, 12, 0, 0, 0)),
				ItemAt(new DateTime(2026, 4, 3, 12, 0, 0, 0)),
			};
			((IBindingList)list).ApplySort(DateDescriptor(), ListSortDirection.Descending);
			// New item is older than the newest — should land in the middle.
			var olderThanTop = ItemAt(new DateTime(2026, 4, 4, 18, 0, 0, 0));
			list.Insert(0, olderThanTop);
			CollectionAssert.AreEqual(
				new[]
				{
					new DateTime(2026, 4, 5, 12, 0, 0, 0),
					new DateTime(2026, 4, 4, 18, 0, 0, 0),
					new DateTime(2026, 4, 4, 12, 0, 0, 0),
					new DateTime(2026, 4, 3, 12, 0, 0, 0),
				},
				list.Select(x => x.Date).ToArray());
		}

		[TestMethod]
		public void Insert_WhenSortedAscending_PlacesItemAtCorrectIndexNotAtZero()
		{
			var list = new SortableBindingList<DataItem>
			{
				ItemAt(new DateTime(2026, 4, 3, 12, 0, 0, 0)),
				ItemAt(new DateTime(2026, 4, 4, 12, 0, 0, 0)),
				ItemAt(new DateTime(2026, 4, 5, 12, 0, 0, 0)),
			};
			((IBindingList)list).ApplySort(DateDescriptor(), ListSortDirection.Ascending);
			var middle = ItemAt(new DateTime(2026, 4, 4, 18, 0, 0, 0));
			list.Insert(0, middle);
			CollectionAssert.AreEqual(
				new[]
				{
					new DateTime(2026, 4, 3, 12, 0, 0, 0),
					new DateTime(2026, 4, 4, 12, 0, 0, 0),
					new DateTime(2026, 4, 4, 18, 0, 0, 0),
					new DateTime(2026, 4, 5, 12, 0, 0, 0),
				},
				list.Select(x => x.Date).ToArray());
		}

		[TestMethod]
		public void Insert_WhenNotSorted_HonoursCallerIndex()
		{
			var list = new SortableBindingList<DataItem>
			{
				ItemAt(new DateTime(2026, 4, 4, 12, 0, 0, 0)),
				ItemAt(new DateTime(2026, 4, 5, 12, 0, 0, 0)),
			};
			var newItem = ItemAt(new DateTime(2026, 4, 1, 0, 0, 0, 0));
			list.Insert(0, newItem);
			Assert.AreSame(newItem, list[0]);
		}

		[TestMethod]
		public void RemoveSort_AfterSortAndInsert_PreservesInsertedItems()
		{
			var list = new SortableBindingList<DataItem>
			{
				ItemAt(new DateTime(2026, 4, 5, 12, 0, 0, 0)),
				ItemAt(new DateTime(2026, 4, 4, 12, 0, 0, 0)),
			};
			((IBindingList)list).ApplySort(DateDescriptor(), ListSortDirection.Descending);
			var inserted = ItemAt(new DateTime(2026, 4, 6, 12, 0, 0, 0));
			list.Insert(0, inserted);
			((IBindingList)list).RemoveSort();
			Assert.IsTrue(list.Contains(inserted),
				"Items inserted while sorted must survive RemoveSort.");
		}

		[TestMethod]
		public void RemoveSort_AfterSortAndRemove_DropsRemovedItems()
		{
			// Symmetric to the insert case above: an item removed while sorted must
			// not be resurrected from the backing _OriginalCollection when the sort
			// is cleared. Without the matching RemoveItem fix it reappears.
			var list = new SortableBindingList<DataItem>
			{
				ItemAt(new DateTime(2026, 4, 5, 12, 0, 0, 0)),
				ItemAt(new DateTime(2026, 4, 4, 12, 0, 0, 0)),
				ItemAt(new DateTime(2026, 4, 3, 12, 0, 0, 0)),
			};
			((IBindingList)list).ApplySort(DateDescriptor(), ListSortDirection.Descending);
			var removed = list[0];
			list.Remove(removed);
			((IBindingList)list).RemoveSort();
			Assert.IsFalse(list.Contains(removed),
				"Items removed while sorted must not reappear after RemoveSort.");
			Assert.AreEqual(2, list.Count);
		}

		[TestMethod]
		public void RemoveSort_AfterSortAndClear_DoesNotResurrectClearedItems()
		{
			// sort -> Clear -> unsort must yield an empty list. Clear() has to drop the
			// backing _OriginalCollection too, otherwise RemoveSort re-adds the rows.
			var list = new SortableBindingList<DataItem>
			{
				ItemAt(new DateTime(2026, 4, 5, 12, 0, 0, 0)),
				ItemAt(new DateTime(2026, 4, 4, 12, 0, 0, 0)),
				ItemAt(new DateTime(2026, 4, 3, 12, 0, 0, 0)),
			};
			((IBindingList)list).ApplySort(DateDescriptor(), ListSortDirection.Descending);
			list.Clear();
			((IBindingList)list).RemoveSort();
			Assert.AreEqual(0, list.Count,
				"Rows cleared while sorted must not reappear after the sort is removed.");
		}
	}
}
