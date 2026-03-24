using System.Text.Json.Serialization;
namespace OpenEpl.TextECode.Model
{
    [JsonSourceGenerationOptions(WriteIndented = true)]
    [JsonSerializable(typeof(ProjectModel))]
    [JsonSerializable(typeof(OrderModel))]
    [JsonSerializable(typeof(FormSnapshotModel))]
    [JsonSerializable(typeof(FormElementSnapshotModel))]
    [JsonSerializable(typeof(FormControlEventBindingModel))]
    internal partial class TextECodeJsonContext : JsonSerializerContext
    {
    }
}
