using System;
using System.Windows;

namespace JocysCom.FocusLogger
{

    /// <summary>
    /// Represents the main entry point for the FocusLogger WPF application. Responsible for initializing DPI awareness
    /// before any UI windows are created, ensuring proper scaling and resource usage across different system DPI settings.
    /// </summary>
    public partial class App : Application
    {
        /// <summary>
        /// Initializes the application and ensures the process is marked as DPI-aware
        /// prior to window creation. This prevents blurry or incorrectly scaled UI,
        /// especially on high-DPI displays.
        /// </summary>
        public App()
        {
            SetDPIAware();
        }

        /// <summary>
        /// Provides native Win32 methods required for application-wide settings such as DPI awareness.
        /// </summary>
        internal class NativeMethods
        {
            [System.Runtime.InteropServices.DllImport("user32.dll")]
            internal static extern bool SetProcessDPIAware();
        }

        /// <summary>
        /// Sets the current process as DPI-aware on supported Windows versions.
        /// Must be called before creating any UI windows to ensure correct control scaling and layout.
        /// </summary>
        /// <remarks>
        /// This method checks the OS version (Vista/Server 2008 or above, i.e., version >= 6) before invoking the native call.
        /// It is critical to invoke this before App.xaml's StartupUri is processed, as the main window will reference themes and resources
        /// that depend on accurate DPI information to display correctly. This setup is essential for loading merged resource dictionaries
        /// (styling/icons) with the intended visual fidelity throughout the application.
        /// </remarks>
        public static void SetDPIAware()
        {
            // Ensure DPI awareness is set before any windows/resources are created, affecting all subsequent visual behavior.
            if (Environment.OSVersion.Version.Major >= 6)
                NativeMethods.SetProcessDPIAware();
        }

    }
}
