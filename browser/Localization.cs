using System.Globalization;
using System.Reflection;
using System.Text.Json;

namespace ATBridge.FabBrowser;

static class L
{
    static readonly IReadOnlyDictionary<string, string> English = Load();
    public static string Language { get; private set; } = Normalize(CultureInfo.CurrentUICulture.Name);
    public static bool IsChinese => Language == "zh-CN";
    public static string Normalize(string? language) =>
        (language ?? "").Replace('_', '-').Split('-')[0].Equals("zh", StringComparison.OrdinalIgnoreCase) ? "zh-CN" : "en-US";
    public static void Configure(string? language) => Language = Normalize(
        string.IsNullOrWhiteSpace(language) || language.Equals("auto", StringComparison.OrdinalIgnoreCase)
            ? CultureInfo.CurrentUICulture.Name : language);
    public static string T(string key) => IsChinese ? key : English.GetValueOrDefault(key, key);
    public static string F(string key, params object[] values) => string.Format(CultureInfo.GetCultureInfo(Language), T(key), values);
    static IReadOnlyDictionary<string, string> Load()
    {
        using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("ATBridge.Fab.en.json")
            ?? throw new InvalidOperationException("Missing bundled UI translations");
        return JsonSerializer.Deserialize<Dictionary<string, string>>(stream)!;
    }
}
