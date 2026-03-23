using Microsoft.Extensions.Logging.Abstractions;
using OpenEpl.TextECode;
using QIQI.EProjectFile;
using System;
using System.IO;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Text;

namespace OpenEpl.TextECode.NativeBridge
{
    public static unsafe class Exports
    {
        private static readonly object initLock = new();
        private static bool initialized;

        [ThreadStatic]
        private static string lastError;

        [UnmanagedCallersOnly(EntryPoint = "textecode_generate", CallConvs = new[] { typeof(CallConvCdecl) })]
        public static int Generate(nint inputEFile, nint outputProjectFile)
        {
            return Run(() =>
            {
                var input = ReadUtf8(inputEFile, nameof(inputEFile));
                var output = ReadUtf8(outputProjectFile, nameof(outputProjectFile));

                var doc = new EplDocument();
                using (var file = File.OpenRead(input))
                {
                    doc.Load(file);
                }

                var originDir = Path.GetDirectoryName(Path.GetFullPath(input))
                    ?? throw new InvalidOperationException("Failed to resolve input directory.");
                var generator = new TextECodeGenerator(
                    NullLoggerFactory.Instance,
                    doc,
                    output,
                    new EComSearcher(new[] { originDir }),
                    originDir);

                generator.Generate();
                generator.DeleteNonGeneratedFiles();
            });
        }

        [UnmanagedCallersOnly(EntryPoint = "textecode_restore", CallConvs = new[] { typeof(CallConvCdecl) })]
        public static int Restore(nint inputProjectFile, nint outputEFile)
        {
            return Run(() =>
            {
                var input = ReadUtf8(inputProjectFile, nameof(inputProjectFile));
                var output = ReadUtf8(outputEFile, nameof(outputEFile));

                var doc = new TextECodeRestorer(NullLoggerFactory.Instance, input).Restore();
                using var file = File.Open(output, FileMode.Create);
                doc.Save(file);
            });
        }

        [UnmanagedCallersOnly(EntryPoint = "textecode_last_error", CallConvs = new[] { typeof(CallConvCdecl) })]
        public static nint LastError()
        {
            return string.IsNullOrEmpty(lastError)
                ? nint.Zero
                : Marshal.StringToCoTaskMemUTF8(lastError);
        }

        [UnmanagedCallersOnly(EntryPoint = "textecode_version", CallConvs = new[] { typeof(CallConvCdecl) })]
        public static nint Version()
        {
            var version = typeof(TextECodeGenerator).Assembly.GetName().Version?.ToString() ?? "0.0.0.0";
            return Marshal.StringToCoTaskMemUTF8(version);
        }

        [UnmanagedCallersOnly(EntryPoint = "textecode_free", CallConvs = new[] { typeof(CallConvCdecl) })]
        public static void Free(nint ptr)
        {
            if (ptr != nint.Zero)
            {
                Marshal.FreeCoTaskMem(ptr);
            }
        }

        private static int Run(Action action)
        {
            EnsureInitialized();
            lastError = null;
            try
            {
                action();
                return 0;
            }
            catch (Exception ex)
            {
                lastError = ex.ToString();
                return -1;
            }
        }

        private static void EnsureInitialized()
        {
            if (initialized)
            {
                return;
            }

            lock (initLock)
            {
                if (initialized)
                {
                    return;
                }

                Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
                initialized = true;
            }
        }

        private static string ReadUtf8(nint ptr, string paramName)
        {
            if (ptr == nint.Zero)
            {
                throw new ArgumentNullException(paramName);
            }

            return Marshal.PtrToStringUTF8(ptr)
                ?? throw new ArgumentException("Invalid UTF-8 string.", paramName);
        }
    }
}
