using System.Text.Json.Serialization;

namespace OpenEpl.TextECode.Model
{
    [JsonSourceGenerationOptions(WriteIndented = true)]
    [JsonSerializable(typeof(ProjectModel))]
    [JsonSerializable(typeof(OrderModel))]
    internal partial class TextECodeJsonContext : JsonSerializerContext
    {
    }
}
