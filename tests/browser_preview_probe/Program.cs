// Offline WebView2 regressions: dotnet run --project tests/browser_preview_probe
using System.Reflection;
using System.Text;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
namespace ATBridge.FabBrowser;
static class PreviewTests
{
    const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;
    const string Listing = "https://www.fab.com/listings/11111111-1111-4111-8111-111111111111";
    const string Other = "https://www.fab.com/listings/22222222-2222-4222-8222-222222222222";
    const string Raw = "forest_european_rock_xlpgfgm_raw.zip";
    const string Image = "https://media.fab.com/image_previews/gallery_images/test/rock.jpg";
    static void Check(bool ok, string message) { if (!ok) throw new Exception(message); }
    static string Document(bool modal, bool unrelated = false) => $"""
        <!doctype html><body data-fixture="true"><main>
        <h1>Forest Rock</h1><img src="{Image}" alt="Media for Forest Rock">
        <p>forest_rock_zbrush.zip</p></main>
        {(modal ? $"<div role='dialog'><h3>{(unrelated ? "Another product" : "Forest Rock")}</h3><p>{Raw}</p></div>" : "")}
        </body>
        """;
    [STAThread] static void Main()
    {
        ApplicationConfiguration.Initialize();
        var root = Path.Combine(Path.GetTempPath(), "atb-preview-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        using var window = new BrowserWindow(root, root, "about:blank");
        var web = (WebView2)typeof(BrowserWindow).GetField("web", Private)!.GetValue(window)!;
        string html = Document(true);
        async Task<ProductPage?> Read() => await (Task<ProductPage?>)typeof(BrowserWindow)
            .GetMethod("ReadProductPage", Private)!.Invoke(window, null)!;
        async Task Load(string url)
        {
            web.CoreWebView2.Navigate(url);
            for (int i = 0; i < 100; i++)
            {
                await Task.Delay(50);
                if (web.Source?.ToString() == url &&
                    await web.CoreWebView2.ExecuteScriptAsync("document.body?.dataset.fixture === 'true'") == "true") return;
            }
            throw new Exception("Fixture navigation timed out");
        }
        window.Shown += async (_, _) =>
        {
            try
            {
                for (int i = 0; web.CoreWebView2 == null && i < 100; i++) await Task.Delay(50);
                Check(web.CoreWebView2 != null, "WebView2 did not start");
                web.CoreWebView2!.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.All);
                web.CoreWebView2.WebResourceRequested += (_, e) =>
                    e.Response = web.CoreWebView2.Environment.CreateWebResourceResponse(
                        new MemoryStream(Encoding.UTF8.GetBytes(e.Request.Uri is Listing or Other ? html : "")),
                        200, "OK", "Content-Type: text/html");
                await Load(Listing);
                var captured = await Read();
                Check(captured != null && captured.Files.Contains(Raw), "Named portal dialog package was missed");
                await web.CoreWebView2.ExecuteScriptAsync("document.querySelector('[role=dialog]').remove()");
                Check((await Read())!.Files.Contains(Raw), "Modal closing lost known package names");

                html = Document(true, unrelated: true);
                await Load(Other);
                Check(!(await Read())!.Files.Contains(Raw), "Foreign dialog or previous listing was matched");

                // A popup inherits its creation-time product, not the opener's later page.
                using var child = new BrowserWindow(root, root, "about:blank");
                await child.Prepare(web.CoreWebView2.Environment);
                typeof(BrowserWindow).GetField("openerProduct", Private)!.SetValue(child, Task.FromResult(captured));
                var bound = await (Task<ProductPage?>)typeof(BrowserWindow).GetMethod("CaptureDownloadProduct", Private)!
                    .Invoke(child, [Raw])!;
                Check(bound?.Url == Listing, "Popup download followed the opener's later listing");

                var matches = typeof(FabPreviewCache).GetMethod("PackageMatches", BindingFlags.Static | BindingFlags.NonPublic)!;
                bool Match(string file, string id) => (bool)matches.Invoke(null, [file, id])!;
                foreach (var name in new[] { Raw, "rock_xlpgfgm_gltf_raw.zip", "rock_xlpgfgm_ue_high.zip", "rock_xlpgfgm_exr_raw.zip" })
                    Check(Match(name, "xlpgfgm"), "Valid package variant missed: " + name);
                foreach (var id in new[] { "raw", "gltf", "forest", "unrelated" })
                    Check(!Match(Raw, id), "Filename token mistaken for asset ID: " + id);
                Check(!Match("rock_unrelated_raw.zip", "xlpgfgm"), "Different asset matched");
                Console.WriteLine("PASS: portal packages, modal closure, cross-listing isolation, popup binding and package IDs");
            }
            catch (Exception e) { Console.Error.WriteLine(e); Environment.ExitCode = 1; }
            finally { window.Close(); }
        };
        Application.Run(window);
        // WebView2 may retain profile files briefly; the OS temp cleanup can reclaim them.
    }
}
