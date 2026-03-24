using OpenEpl.TextECode.Internal.ProgramElems.User;
using QIQI.EProjectFile;
using System.Collections.Generic;

namespace OpenEpl.TextECode.Internal
{
    internal sealed class PendingFormSnapshotInfo
    {
        public FormInfo FormInfo { get; init; }

        public UserFormDataType FormDataType { get; init; }

        public string AssociatedClassName { get; init; }

        public List<PendingFormControlEventBinding> ControlEventBindings { get; init; } = new();

        public List<PendingFormMenuEventBinding> MenuEventBindings { get; init; } = new();
    }

    internal sealed class PendingFormControlEventBinding
    {
        public int ElementId { get; init; }

        public int EventKey { get; init; }

        public string EventName { get; init; }

        public string HandlerMethodName { get; init; }
    }

    internal sealed class PendingFormMenuEventBinding
    {
        public int ElementId { get; init; }

        public string HandlerMethodName { get; init; }
    }
}
