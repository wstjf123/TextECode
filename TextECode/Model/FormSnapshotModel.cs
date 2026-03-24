using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace OpenEpl.TextECode.Model
{
    public class FormSnapshotModel
    {
        public int FormatVersion { get; set; } = 2;

        public string Name { get; set; }

        public string Comment { get; set; }

        public int UnknownBeforeClass { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string AssociatedClassName { get; set; }

        public List<FormElementSnapshotModel> Elements { get; set; } = new();
    }

    public class FormElementSnapshotModel
    {
        public string Kind { get; set; }

        public int ElementId { get; set; }

        public int DataType { get; set; }

        public string Name { get; set; }

        public bool Visible { get; set; }

        public bool Disable { get; set; }

        public bool IsFormSelf { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string LibraryGuid { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string LibraryName { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string LibraryFileName { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string LibraryVersion { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public int? DataTypeIndex { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string DataTypeName { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string UnknownBeforeNameBase64 { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string UnknownBeforeExtensionDataBase64 { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string UnknownAfterClickEventBase64 { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public List<FormControlEventBindingModel> Events { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string ClickHandlerMethodName { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string Comment { get; set; }

        public int CWndAddress { get; set; }

        public int Left { get; set; }

        public int Top { get; set; }

        public int Width { get; set; }

        public int Height { get; set; }

        public int UnknownBeforeParent { get; set; }

        public int Parent { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public int[] Children { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string CursorBase64 { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string Tag { get; set; }

        public int UnknownBeforeVisible { get; set; }

        public bool TabStop { get; set; }

        public bool Locked { get; set; }

        public int TabIndex { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string ExtensionDataBase64 { get; set; }

        public int HotKey { get; set; }

        public int Level { get; set; }

        public bool Selected { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string Text { get; set; }
    }

    public class FormControlEventBindingModel
    {
        public int EventKey { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string EventName { get; set; }

        public string HandlerMethodName { get; set; }
    }
}
