using System.Text.Json.Serialization;
using QIQI.EProjectFile;

namespace OpenEpl.TextECode.Model
{
    [JsonSourceGenerationOptions(WriteIndented = true)]
    [JsonSerializable(typeof(ProjectModel))]
    [JsonSerializable(typeof(OrderModel))]
    [JsonSerializable(typeof(FormSnapshotModel))]
    [JsonSerializable(typeof(FormInfo))]
    [JsonSerializable(typeof(FormControlInfo))]
    [JsonSerializable(typeof(FormMenuInfo))]
    internal partial class TextECodeJsonContext : JsonSerializerContext
    {
    }
}
