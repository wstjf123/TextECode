using Microsoft.Extensions.Logging;
using OpenEpl.ELibInfo;
using OpenEpl.TextECode.Model;
using QIQI.EProjectFile;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace OpenEpl.TextECode.Internal
{
    internal sealed class FormSnapshotGenerator
    {
        private readonly FormInfo formInfo;
        private readonly IReadOnlyDictionary<int, ClassInfo> classIdMap;
        private readonly IReadOnlyDictionary<int, MethodInfo> methodIdMap;
        private readonly LibraryRefInfo[] libraryRefInfos;
        private readonly IReadOnlyList<ELibManifest> eLibs;
        private readonly IdToNameMap idToNameMap;
        private readonly ILogger logger;

        public FormSnapshotGenerator(
            FormInfo formInfo,
            IReadOnlyDictionary<int, ClassInfo> classIdMap,
            IReadOnlyDictionary<int, MethodInfo> methodIdMap,
            LibraryRefInfo[] libraryRefInfos,
            IReadOnlyList<ELibManifest> eLibs,
            IdToNameMap idToNameMap,
            ILoggerFactory loggerFactory)
        {
            this.formInfo = formInfo ?? throw new ArgumentNullException(nameof(formInfo));
            this.classIdMap = classIdMap ?? throw new ArgumentNullException(nameof(classIdMap));
            this.methodIdMap = methodIdMap ?? throw new ArgumentNullException(nameof(methodIdMap));
            this.libraryRefInfos = libraryRefInfos ?? throw new ArgumentNullException(nameof(libraryRefInfos));
            this.eLibs = eLibs ?? throw new ArgumentNullException(nameof(eLibs));
            this.idToNameMap = idToNameMap ?? throw new ArgumentNullException(nameof(idToNameMap));
            logger = loggerFactory.CreateLogger<FormSnapshotGenerator>();
        }

        public void Save(Stream stream)
        {
            if (stream == null)
            {
                throw new ArgumentNullException(nameof(stream));
            }

            var snapshot = Build();
            using var writer = new Utf8JsonWriter(stream, new JsonWriterOptions()
            {
                Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
                Indented = true
            });
            JsonSerializer.Serialize(writer, snapshot);
        }

        private FormSnapshotModel Build()
        {
            var snapshot = new FormSnapshotModel()
            {
                Name = formInfo.Name,
                AssociatedClassName = GetAssociatedClassName(),
                Form = formInfo,
            };

            var methodsById = GetAssociatedMethodsById();
            foreach (var element in formInfo.Elements)
            {
                var elementSnapshot = new FormElementSnapshotModel()
                {
                    ElementId = element.Id,
                    DataType = element.DataType,
                };

                switch (element)
                {
                    case FormControlInfo control:
                        PopulateControlSnapshot(elementSnapshot, control, methodsById);
                        break;
                    case FormMenuInfo menu:
                        PopulateMenuSnapshot(elementSnapshot, menu, methodsById);
                        break;
                }

                snapshot.Elements.Add(elementSnapshot);
            }

            return snapshot;
        }

        private string GetAssociatedClassName()
        {
            if (formInfo.Class == 0 || !classIdMap.TryGetValue(formInfo.Class, out var classInfo))
            {
                return null;
            }
            return idToNameMap.GetUserDefinedName(classInfo.Id);
        }

        private Dictionary<int, string> GetAssociatedMethodsById()
        {
            if (formInfo.Class == 0 || !classIdMap.TryGetValue(formInfo.Class, out var classInfo))
            {
                return new Dictionary<int, string>();
            }

            return classInfo.Methods
                .Where(methodIdMap.ContainsKey)
                .Distinct()
                .ToDictionary(x => x, x => idToNameMap.GetUserDefinedName(x));
        }

        private void PopulateControlSnapshot(FormElementSnapshotModel snapshot, FormControlInfo control, IReadOnlyDictionary<int, string> methodsById)
        {
            PopulateDataTypeIdentity(snapshot, control.DataType);

            if (!control.UnknownBeforeName.IsDefaultOrEmpty)
            {
                snapshot.UnknownBeforeNameBase64 = Convert.ToBase64String(control.UnknownBeforeName.ToArray());
            }
            if (!control.UnknownBeforeExtensionData.IsDefaultOrEmpty)
            {
                snapshot.UnknownBeforeExtensionDataBase64 = Convert.ToBase64String(control.UnknownBeforeExtensionData.ToArray());
            }
            if (control.Events != null)
            {
                foreach (var item in control.Events)
                {
                    if (!methodsById.TryGetValue(item.Value, out var handlerMethodName) || string.IsNullOrEmpty(handlerMethodName))
                    {
                        continue;
                    }
                    snapshot.Events ??= new List<FormControlEventBindingModel>();
                    snapshot.Events.Add(new FormControlEventBindingModel()
                    {
                        EventKey = item.Key,
                        EventName = ResolveEventName(control.DataType, item.Key),
                        HandlerMethodName = handlerMethodName,
                    });
                }
            }
        }

        private void PopulateMenuSnapshot(FormElementSnapshotModel snapshot, FormMenuInfo menu, IReadOnlyDictionary<int, string> methodsById)
        {
            if (!menu.UnknownBeforeName.IsDefaultOrEmpty)
            {
                snapshot.UnknownBeforeNameBase64 = Convert.ToBase64String(menu.UnknownBeforeName.ToArray());
            }
            if (!menu.UnknownAfterClickEvent.IsDefaultOrEmpty)
            {
                snapshot.UnknownAfterClickEventBase64 = Convert.ToBase64String(menu.UnknownAfterClickEvent.ToArray());
            }
            if (menu.ClickEvent != 0 && methodsById.TryGetValue(menu.ClickEvent, out var handlerMethodName))
            {
                snapshot.ClickHandlerMethodName = handlerMethodName;
            }
        }

        private void PopulateDataTypeIdentity(FormElementSnapshotModel snapshot, int dataType)
        {
            EplSystemId.DecomposeLibDataTypeId(dataType, out var lib, out var type);
            if (lib < 0 || lib >= libraryRefInfos.Length)
            {
                return;
            }

            var library = libraryRefInfos[lib];
            snapshot.LibraryGuid = library.GuidString;
            snapshot.LibraryName = library.Name;
            snapshot.LibraryFileName = library.FileName;
            snapshot.LibraryVersion = library.Version?.ToString();
            snapshot.DataTypeIndex = type;
            snapshot.DataTypeName = eLibs.ElementAtOrDefault(lib)?.DataTypes.ElementAtOrDefault(type)?.Name;
        }

        private string ResolveEventName(int dataType, int eventKey)
        {
            EplSystemId.DecomposeLibDataTypeId(dataType, out var lib, out var type);
            var dataTypeInfo = eLibs.ElementAtOrDefault(lib)?.DataTypes.ElementAtOrDefault(type);
            if (dataTypeInfo == null || dataTypeInfo.Events.IsDefaultOrEmpty)
            {
                return null;
            }
            var events = dataTypeInfo.Events;

            if (eventKey > 0 && eventKey <= events.Length)
            {
                return events[eventKey - 1].Name;
            }
            if (eventKey >= 0 && eventKey < events.Length)
            {
                return events[eventKey].Name;
            }

            logger.LogWarning("无法解析窗口事件名称，DataType={DataType}, EventKey={EventKey}", dataType, eventKey);
            return null;
        }
    }
}
