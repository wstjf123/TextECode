using QIQI.EProjectFile;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace OpenEpl.TextECode.Model
{
    public class FormSnapshotModel
    {
        public int FormatVersion { get; set; } = 1;

        public string Name { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string AssociatedClassName { get; set; }

        public FormInfo Form { get; set; }

        public List<FormElementSnapshotModel> Elements { get; set; } = new();
    }

    public class FormElementSnapshotModel
    {
        public int ElementId { get; set; }

        public int DataType { get; set; }

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
    }

    public class FormControlEventBindingModel
    {
        public int EventKey { get; set; }

        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string EventName { get; set; }

        public string HandlerMethodName { get; set; }
    }
}
