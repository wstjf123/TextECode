using Microsoft.Extensions.Logging;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Xml;
using System.Linq;
using QIQI.EProjectFile;
using OpenEpl.TextECode.Internal.ProgramElems.User;
using OpenEpl.TextECode.Internal.ProgramElems;
using OpenEpl.TextECode.Model;
using OpenEpl.ELibInfo.Loader;
using System.Collections.Immutable;

namespace OpenEpl.TextECode.Internal
{
    internal class FormInfoRestorer
    {
        private readonly TextECodeRestorer P;
        private readonly XmlDocument doc = new();
        private FormInfo formInfo;
        private FormSnapshotModel snapshotModel;

        public bool HasSnapshot => snapshotModel != null;

        public FormInfoRestorer(TextECodeRestorer p)
        {
            P = p ?? throw new ArgumentNullException(nameof(p));
        }
        public void Load(Stream stream)
        {
            doc.Load(stream);
        }

        public void LoadSnapshot(Stream stream)
        {
            snapshotModel = JsonSerializer.Deserialize(stream, TextECodeJsonContext.Default.FormSnapshotModel)
                ?? throw new Exception("读取窗口快照失败");
        }

        public UserFormDataType Restore()
        {
            if (snapshotModel != null)
            {
                return RestoreFromSnapshot();
            }

            var formXmlElem = doc.DocumentElement;
            formInfo = new FormInfo(P.AllocId(EplSystemId.Type_Form))
            {
                Name = formXmlElem.GetAttribute("名称"),
                Comment = formXmlElem.GetAttribute("备注"),
                Elements = new()
            };
            var formSelfControl = new FormControlInfo(P.AllocId(EplSystemId.Type_FormSelf))
            {
                DataType = 65537,
                Events = Array.Empty<KeyValuePair<int, int>>()
            };
            ReadProperty(formXmlElem, formSelfControl);
            formInfo.Elements.Add(formSelfControl);

            var formMenus = formXmlElem.ChildNodes
                .OfType<XmlElement>()
                .Where(x => x.Name == "窗口.菜单")
                .SingleOrDefault();
            if (formMenus != null)
            {
                HandleMenuChildren(formMenus, 0);
            }

            HandleControlChildren(formXmlElem, 0);

            var result = new UserFormDataType(P, formInfo);
            P.Forms.Add(result);
            return result;
        }

        private UserFormDataType RestoreFromSnapshot()
        {
            if (snapshotModel.Elements == null)
            {
                throw new Exception("窗口快照缺少 Elements 数据");
            }

            var metadataById = snapshotModel.Elements?.ToDictionary(x => x.ElementId) ?? new Dictionary<int, FormElementSnapshotModel>();
            var idMap = new Dictionary<int, int>();

            formInfo = new FormInfo(P.AllocId(EplSystemId.Type_Form))
            {
                Name = snapshotModel.Name,
                Comment = snapshotModel.Comment,
                UnknownBeforeClass = snapshotModel.UnknownBeforeClass,
                Class = 0,
                Elements = new()
            };

            foreach (var element in snapshotModel.Elements)
            {
                switch (element.Kind)
                {
                    case "Menu":
                    {
                        var restoredMenu = new FormMenuInfo(P.AllocId(EplSystemId.Type_FormMenu))
                        {
                            DataType = element.DataType,
                            Name = element.Name,
                            Visible = element.Visible,
                            Disable = element.Disable,
                            HotKey = element.HotKey,
                            Level = element.Level,
                            Selected = element.Selected,
                            Text = element.Text,
                            ClickEvent = 0,
                        };
                        ApplyExtraSnapshotData(restoredMenu, element);
                        idMap[element.ElementId] = restoredMenu.Id;
                        formInfo.Elements.Add(restoredMenu);
                        break;
                    }
                    case "Control":
                    {
                        var restoredControl = new FormControlInfo(P.AllocId(element.IsFormSelf
                            ? EplSystemId.Type_FormSelf
                            : EplSystemId.Type_FormControl))
                        {
                            DataType = ResolveControlDataType(element),
                            Name = element.Name,
                            Visible = element.Visible,
                            Disable = element.Disable,
                            Comment = element.Comment,
                            CWndAddress = element.CWndAddress,
                            Left = element.Left,
                            Top = element.Top,
                            Width = element.Width,
                            Height = element.Height,
                            UnknownBeforeParent = element.UnknownBeforeParent,
                            Cursor = DecodeBase64(element.CursorBase64),
                            Tag = element.Tag,
                            UnknownBeforeVisible = element.UnknownBeforeVisible,
                            TabStop = element.TabStop,
                            Locked = element.Locked,
                            TabIndex = element.TabIndex,
                            Events = Array.Empty<KeyValuePair<int, int>>(),
                            ExtensionData = DecodeBase64(element.ExtensionDataBase64),
                        };
                        ApplyExtraSnapshotData(restoredControl, element);
                        idMap[element.ElementId] = restoredControl.Id;
                        formInfo.Elements.Add(restoredControl);
                        break;
                    }
                    default:
                        throw new Exception($"窗口快照包含未知元素类型: {element.Kind}");
                }
            }

            foreach (var pair in snapshotModel.Elements.Where(x => x.Kind == "Control").Zip(formInfo.Elements.OfType<FormControlInfo>(), (source, restored) => (source, restored)))
            {
                pair.restored.Parent = pair.source.Parent != 0 && idMap.TryGetValue(pair.source.Parent, out var parentId)
                    ? parentId
                    : 0;
                pair.restored.Children = pair.source.Children?.Select(x => x == 0 ? 0 : idMap.TryGetValue(x, out var childId) ? childId : 0).ToArray()
                    ?? Array.Empty<int>();
            }

            var result = new UserFormDataType(P, formInfo);
            P.Forms.Add(result);
            RegisterSnapshotBindings(result, idMap, metadataById);
            return result;
        }

        public void HandleMenuChildren(XmlElement parentElem, int level)
        {
            foreach (var child in parentElem.ChildNodes.OfType<XmlElement>().Where(x => x.Name == "菜单"))
            {
                HandleMenu(child, level);
            }
        }

        public void HandleMenu(XmlElement xmlElem, int level)
        {
            var menu = new FormMenuInfo(P.AllocId(EplSystemId.Type_FormMenu))
            {
                DataType = 65539,
                Name = xmlElem.GetAttribute("名称"),
                Level = level
            };
            formInfo.Elements.Add(menu);
            ReadProperty(xmlElem, menu);
            HandleMenuChildren(xmlElem, level + 1);
        }

        public int HandleControl(XmlElement xmlElem, int parentId)
        {
            P.TopLevelScope.TryGetValue(ProgramElemName.Type(xmlElem.Name), out var elem);
            int dataTypeId;
            if (elem is BaseDataTypeElem dataTypeElem)
            {
                dataTypeId = dataTypeElem.Id;
            }
            else
            {
                var nameGroup = xmlElem.Name.Split('.');
                if (nameGroup.Length != 3 && nameGroup[0] != "未知类型")
                {
                    throw new Exception($"未知的窗口数据类型: {xmlElem.Name}");
                }
                var libId = P.libraryRefInfos.FindIndex(x => x.Name == nameGroup[1]);
                if (libId == -1)
                {
                    throw new Exception($"未知的窗口数据类型: {nameGroup[1]}.{nameGroup[2]}");
                }
                dataTypeId = EplSystemId.MakeLibDataTypeId(checked((short)libId), short.Parse(nameGroup[2]));
            }
            var control = new FormControlInfo(P.AllocId(EplSystemId.Type_FormControl))
            {
                DataType = dataTypeId,
                Name = xmlElem.GetAttribute("名称"),
                Comment = xmlElem.GetAttribute("备注"),
                Parent = parentId,
                Events = Array.Empty<KeyValuePair<int, int>>()
            };
            var children = new List<int>();
            HandleControlChildren(xmlElem, control.Id, children);
            var tabsEnumerator = xmlElem
                .ChildNodes
                .OfType<XmlElement>()
                .Where(x => x.Name == $"{xmlElem.Name}.子夹")
                .GetEnumerator();
            if (tabsEnumerator.MoveNext())
            {
                var tab = tabsEnumerator.Current;
                HandleControlChildren(tab, control.Id, children);
                while (tabsEnumerator.MoveNext())
                {
                    children.Add(0);
                    tab = tabsEnumerator.Current;
                    HandleControlChildren(tab, control.Id, children);
                }
            }
            ReadProperty(xmlElem, control);
            control.Children = children.ToArray();
            // Add parent (container) after all children are added
            // See https://github.com/OpenEpl/TextECode/issues/13
            formInfo.Elements.Add(control);
            return control.Id;
        }


        public void HandleControlChildren(XmlElement parentElem, int parentId)
        {
            foreach (var child in parentElem.ChildNodes.OfType<XmlElement>())
            {
                if (child.Name.StartsWith($"{parentElem.Name}."))
                {
                    continue;
                }
                HandleControl(child, parentId);
            }
        }

        public void HandleControlChildren(XmlElement parentElem, int parentId, List<int> childrenId)
        {
            foreach (var child in parentElem.ChildNodes.OfType<XmlElement>())
            {
                if (child.Name.StartsWith($"{parentElem.Name}."))
                {
                    continue;
                }
                childrenId.Add(HandleControl(child, parentId));
            }
        }

        private void ReadProperty(XmlElement xmlElement, FormMenuInfo menu)
        {
            menu.Text = xmlElement.GetAttribute("标题");
            menu.Selected = GetBoolAttribute(xmlElement, "选中", false);
            menu.Disable = GetBoolAttribute(xmlElement, "禁止", false);
            menu.Visible = GetBoolAttribute(xmlElement, "可视", true);
            menu.HotKey = GetIntAttribute(xmlElement, "快捷键", 0);
        }

        private void ReadProperty(XmlElement xmlElement, FormControlInfo control)
        {
            control.Left = GetIntAttribute(xmlElement, "左边", 0);
            control.Top = GetIntAttribute(xmlElement, "顶边", 0);
            control.Width = GetIntAttribute(xmlElement, "宽度", 0);
            control.Height = GetIntAttribute(xmlElement, "高度", 0);
            control.Tag = xmlElement.GetAttribute("标记");
            control.Disable = GetBoolAttribute(xmlElement, "禁止", false);
            control.Visible = GetBoolAttribute(xmlElement, "可视", true);
            control.Cursor = Convert.FromBase64String(xmlElement.GetAttribute("鼠标指针"));
            control.TabStop = GetBoolAttribute(xmlElement, "可停留焦点", true);
            control.TabIndex = GetIntAttribute(xmlElement, "停留顺序", 0);
            control.ExtensionData = Convert.FromBase64String(xmlElement.GetAttribute("扩展属性数据"));
        }

        private static bool GetBoolAttribute(XmlElement xmlElement, string name, bool defaultValue)
        {
            var attr = xmlElement.Attributes.GetNamedItem(name);
            if (attr is null)
            {
                return defaultValue;
            }
            return EStrToBool(attr.Value);
        }

        private static int GetIntAttribute(XmlElement xmlElement, string name, int defaultValue)
        {
            var attr = xmlElement.Attributes.GetNamedItem(name);
            if (attr is null)
            {
                return defaultValue;
            }
            return int.Parse(attr.Value);
        }

        private static bool EStrToBool(string value) => value.Trim().ToLowerInvariant() switch
        {
            "真" => true,
            "1" => true,
            "true" => true,
            "yes" => true,
            "on" => true,
            _ => false,
        };

        private int ResolveControlDataType(FormElementSnapshotModel metadata)
        {
            if (metadata?.DataTypeIndex == null)
            {
                return metadata?.DataType ?? 0;
            }

            var libIndex = ResolveLibraryIndex(metadata);
            if (libIndex == -1)
            {
                P.logger.LogWarning("无法解析窗口控件 {ControlName} 的支持库信息，回退使用原始数据类型值 {DataType}", metadata.Name, metadata.DataType);
                return metadata.DataType;
            }

            return EplSystemId.MakeLibDataTypeId(checked((short)libIndex), checked((short)metadata.DataTypeIndex.Value));
        }

        private int ResolveLibraryIndex(FormElementSnapshotModel metadata)
        {
            if (!string.IsNullOrEmpty(metadata.LibraryGuid))
            {
                try
                {
                    var guid = GuidUtils.ParseGuidLosely(metadata.LibraryGuid);
                    if (P.ELibIndexMap.TryGetValue(guid, out var libIndex))
                    {
                        return libIndex;
                    }
                }
                catch (Exception)
                {
                }
            }

            var exactIndex = P.libraryRefInfos.FindIndex(x =>
                string.Equals(x.FileName, metadata.LibraryFileName, StringComparison.OrdinalIgnoreCase)
                && string.Equals(x.Name, metadata.LibraryName, StringComparison.Ordinal)
                && string.Equals(x.GuidString, metadata.LibraryGuid, StringComparison.OrdinalIgnoreCase));
            if (exactIndex != -1)
            {
                return exactIndex;
            }

            var fileIndex = P.libraryRefInfos.FindIndex(x => string.Equals(x.FileName, metadata.LibraryFileName, StringComparison.OrdinalIgnoreCase));
            if (fileIndex != -1)
            {
                return fileIndex;
            }

            return P.libraryRefInfos.FindIndex(x => string.Equals(x.Name, metadata.LibraryName, StringComparison.Ordinal));
        }

        private void ApplyExtraSnapshotData(FormControlInfo control, FormElementSnapshotModel metadata)
        {
            if (!string.IsNullOrEmpty(metadata?.UnknownBeforeNameBase64))
            {
                control.UnknownBeforeName = ImmutableArray.Create(Convert.FromBase64String(metadata.UnknownBeforeNameBase64));
            }
            if (!string.IsNullOrEmpty(metadata?.UnknownBeforeExtensionDataBase64))
            {
                control.UnknownBeforeExtensionData = ImmutableArray.Create(Convert.FromBase64String(metadata.UnknownBeforeExtensionDataBase64));
            }
        }

        private static byte[] DecodeBase64(string value)
        {
            return string.IsNullOrEmpty(value) ? Array.Empty<byte>() : Convert.FromBase64String(value);
        }

        private void ApplyExtraSnapshotData(FormMenuInfo menu, FormElementSnapshotModel metadata)
        {
            if (!string.IsNullOrEmpty(metadata?.UnknownBeforeNameBase64))
            {
                menu.UnknownBeforeName = ImmutableArray.Create(Convert.FromBase64String(metadata.UnknownBeforeNameBase64));
            }
            if (!string.IsNullOrEmpty(metadata?.UnknownAfterClickEventBase64))
            {
                menu.UnknownAfterClickEvent = ImmutableArray.Create(Convert.FromBase64String(metadata.UnknownAfterClickEventBase64));
            }
        }

        private void RegisterSnapshotBindings(UserFormDataType formDataType, IReadOnlyDictionary<int, int> idMap, IReadOnlyDictionary<int, FormElementSnapshotModel> metadataById)
        {
            if (string.IsNullOrEmpty(snapshotModel.AssociatedClassName)
                && metadataById.Values.All(x => (x.Events?.Count ?? 0) == 0 && string.IsNullOrEmpty(x.ClickHandlerMethodName)))
            {
                return;
            }

            var pending = new PendingFormSnapshotInfo()
            {
                FormInfo = formInfo,
                FormDataType = formDataType,
                AssociatedClassName = snapshotModel.AssociatedClassName,
            };

            foreach (var metadata in metadataById.Values)
            {
                if (!idMap.TryGetValue(metadata.ElementId, out var newElementId))
                {
                    continue;
                }
                foreach (var item in metadata.Events ?? Enumerable.Empty<FormControlEventBindingModel>())
                {
                    if (string.IsNullOrEmpty(item.HandlerMethodName))
                    {
                        continue;
                    }
                    pending.ControlEventBindings.Add(new PendingFormControlEventBinding()
                    {
                        ElementId = newElementId,
                        EventKey = item.EventKey,
                        EventName = item.EventName,
                        HandlerMethodName = item.HandlerMethodName,
                    });
                }
                if (!string.IsNullOrEmpty(metadata.ClickHandlerMethodName))
                {
                    pending.MenuEventBindings.Add(new PendingFormMenuEventBinding()
                    {
                        ElementId = newElementId,
                        HandlerMethodName = metadata.ClickHandlerMethodName,
                    });
                }
            }

            P.PendingFormSnapshots.Add(pending);
        }
    }
}
