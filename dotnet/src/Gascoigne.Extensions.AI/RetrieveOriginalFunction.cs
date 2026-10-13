using System.ComponentModel;
using Microsoft.Extensions.AI;

namespace Gascoigne;

/// <summary>A tool that lets a model follow a "gascoigne raw" hint.</summary>
public static class RetrieveOriginalFunction
{
    /// <summary>
    /// Creates the <c>retrieve_original</c> function. Add it to <c>ChatOptions.Tools</c> and list
    /// it in <see cref="GascoigneToolOptions.Skip"/>, so an original is not shortened again.
    /// </summary>
    public static AIFunction Create(GascoigneClient gascoigne)
    {
        ArgumentNullException.ThrowIfNull(gascoigne);
        return AIFunctionFactory.Create(
            ([Description("the id from the hint")] string rawId,
             [Description("regex matched per line")] string grep = "",
             [Description("line range such as 10-40")] string lines = "",
             CancellationToken ct = default) => gascoigne.RetrieveAsync(rawId, grep, lines, ct),
            "retrieve_original",
            "Get lines of the original output behind a 'gascoigne raw <id>' hint. "
            + "Use grep (a regex) or lines (like 10-40) to ask for a part.");
    }
}
