// Compile for: net7.0-windows
// NuGet: Nefarius.Drivers.HidHide
// Purpose: --enable/--disable, --whitelist-add <path>, --whitelist-remove <path>, --whitelist-print

using System;
using System.IO;
using System.Linq;
using Nefarius.Drivers.HidHide;

class Program
{
    static int Main(string[] args)
    {
        try
        {
            var svc = new HidHideControlService(); // managed API
            if (args.Length == 0) { PrintHelp(); return 0; }

            for (int i = 0; i < args.Length; i++)
            {
                switch (args[i])
                {
                    case "--enable":
                        svc.IsActive = true;
                        Console.WriteLine("HidHide enabled.");
                        break;
                    case "--disable":
                        svc.IsActive = false;
                        Console.WriteLine("HidHide disabled.");
                        break;
                    case "--whitelist-add":
                        {
                            var p = args[++i];
                            var full = Path.GetFullPath(p);
                            var list = svc.ApplicationPaths.ToList();
                            if (!list.Contains(full, StringComparer.OrdinalIgnoreCase))
                            {
                                list.Add(full);
                                svc.ApplicationPaths = list.ToArray();
                                Console.WriteLine($"Whitelisted: {full}");
                            }
                            break;
                        }
                    case "--whitelist-remove":
                        {
                            var p = args[++i];
                            var full = Path.GetFullPath(p);
                            var list = svc.ApplicationPaths.ToList();
                            list.RemoveAll(x => string.Equals(x, full, StringComparison.OrdinalIgnoreCase));
                            svc.ApplicationPaths = list.ToArray();
                            Console.WriteLine($"Removed: {full}");
                            break;
                        }
                    case "--whitelist-print":
                        foreach (var pth in svc.ApplicationPaths) Console.WriteLine(pth);
                        break;
                    default:
                        PrintHelp();
                        break;
                }
            }
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"HidHideHelper error: {ex.Message}");
            return 1;
        }
    }

    static void PrintHelp()
    {
        Console.WriteLine("HidHideHelper usage:");
        Console.WriteLine("  --enable | --disable");
        Console.WriteLine("  --whitelist-add <exePath>");
        Console.WriteLine("  --whitelist-remove <exePath>");
        Console.WriteLine("  --whitelist-print");
    }
}
