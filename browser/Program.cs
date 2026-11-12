using System.Diagnostics;
using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace ATBridge.FabBrowser;

static class Program
{
    internal const string MegascansUrl = "https://www.fab.com/sellers/Quixel";
    [STAThread]
    static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        try
        {
            string? Read(string flag)
            {
                var index = Array.IndexOf(args, flag);
                return index >= 0 && index + 1 < args.Length ? args[index + 1] : null;
            }
            L.Configure(Read("--language"));
            var profile = Read("--profile") ?? Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ATBridge", "FabBrowser");
            var downloads = Read("--downloads") ?? Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
            var probe = Read("--probe-url");
            if (probe != null && (!Uri.TryCreate(probe, UriKind.Absolute, out var uri)
                                  || uri.Scheme != "http" || uri.Host != "127.0.0.1"))
                throw new ArgumentException("Probe URL must be an IPv4 loopback HTTP fixture.");
            Application.Run(new BrowserWindow(Path.GetFullPath(profile), Path.GetFullPath(downloads),
                probe ?? InitialPage(Read("--url")), Read("--probe-report"), probe != null,
                blenderPid: int.TryParse(Read("--blender-pid"), out var pid) ? pid : null));
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "ATBridge browser startup failed");
            Environment.ExitCode = 1;
        }
    }

    static string InitialPage(string? value)
    {
        if (value == null) return MegascansUrl;
        if (Uri.TryCreate(value, UriKind.Absolute, out var uri) && uri.Scheme == "https" &&
            (uri.Host == "www.fab.com" || uri.Host == "fab.com") && uri.IsDefaultPort && string.IsNullOrEmpty(uri.UserInfo))
            return uri.ToString();
        throw new ArgumentException("Initial page must be an official Fab HTTPS URL");
    }
}

sealed partial class BrowserWindow : Form
{
    readonly WebView2 web = new() { Dock = DockStyle.Fill };
    readonly Label address = new() { AutoEllipsis = true, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft };
    readonly ToolStripStatusLabel status = new() { Spring = true, TextAlign = ContentAlignment.MiddleLeft };
    readonly string profile, downloads, initialUrl;
    readonly string? probeReport;
    readonly bool probe;
    readonly BrowserWindow probeOwner;
    readonly FabPreviewCache previewCache;
    readonly System.Windows.Forms.Timer previewTimer = new() { Interval = 4000 };
    bool cachingPreview;
    readonly HashSet<CoreWebView2DownloadOperation> active = new();
    readonly HashSet<CoreWebView2DownloadOperation> allActive = new();
    readonly FlowLayoutPanel downloadList = new() { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown,
        WrapContents = false, AutoScroll = true, Padding = new Padding(10) };
    CoreWebView2Environment? environment;
    bool pageLoaded, pageClosePending;
    ulong currentNavigation;

    public BrowserWindow(string profile, string downloads, string initialUrl, string? probeReport = null,
        bool probe = false, BrowserWindow? probeOwner = null, int? blenderPid = null)
    {
        this.profile = profile; this.downloads = downloads; this.initialUrl = initialUrl;
        this.probeReport = probeReport; this.probe = probe;
        this.probeOwner = probeOwner ?? this;
        previewCache = new FabPreviewCache(downloads);
        BuildShell(blenderPid);
        Shown += async (_, _) =>
        {
            if (environment != null) return; // Popup was initialized before being shown.
            await LoadInitial();
        };
        FormClosing += (_, e) =>
        {
            var pending = this.probeOwner == this ? allActive : active;
            if (!probe && pending.Count > 0 && MessageBox.Show(this,
                L.T("还有资产正在下载。关闭窗口将取消这些下载，确定关闭？"), L.T("下载尚未完成"),
                MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
            { e.Cancel = true; return; }
            pageClosePending = false; // A user/owner close cancels, unlike a webpage's close request.
            foreach (var operation in pending.ToArray()) operation.Cancel();
        };
        previewTimer.Tick += async (_, _) => await CacheCurrentProduct(false);
        if (!probe && probeOwner == null) previewTimer.Start();
        FormClosed += (_, _) => { previewTimer.Stop(); previewTimer.Dispose(); toastTimer.Dispose(); hints.Dispose(); web.Dispose(); };
    }

    public async Task Prepare(CoreWebView2Environment? shared = null)
    {
        environment = shared ?? await CoreWebView2Environment.CreateAsync(userDataFolder: profile);
        await web.EnsureCoreWebView2Async(environment);
        web.KeyDown += (_, e) =>
        {
            var key = e.KeyData;
            if (key == (Keys.Alt | Keys.Left) || key == (Keys.Alt | Keys.Right) ||
                key == (Keys.Control | Keys.R) || key == (Keys.Control | Keys.J) ||
                key == Keys.F5 || (key == Keys.Escape && loading))
            {
                e.Handled = true;
                // WebView blocks its browser process during accelerator callbacks.
                BeginInvoke(new Action(() => { if (!IsDisposed) HandleShortcut(key); }));
            }
        };
        // No native objects, file access API, or Blender commands exposed to any webpage.
        web.CoreWebView2.Settings.AreHostObjectsAllowed = false;
        web.CoreWebView2.Settings.IsWebMessageEnabled = false;
        web.CoreWebView2.Settings.IsPasswordAutosaveEnabled = false;
        web.CoreWebView2.WindowCloseRequested += (_, _) =>
        {
            if (active.Count == 0) Close();
            else
            {
                pageClosePending = true;
                status.Text = L.T("网页请求关闭窗口；等待 ZIP 下载完成。");
            }
        };
        web.CoreWebView2.SourceChanged += (_, _) => UpdateNavigation();
        web.CoreWebView2.HistoryChanged += (_, _) => UpdateNavigation();
        web.CoreWebView2.NavigationStarting += (_, e) =>
        {
            if (!AllowedNavigation(e.Uri)) { e.Cancel = true; Notify(L.T("仅允许 HTTPS 网页。")); return; }
            currentNavigation = e.NavigationId;
            loading = true; HidePageError(); UpdateNavigation();
        };
        web.CoreWebView2.NavigationCompleted += (_, e) =>
        {
            if (e.NavigationId != currentNavigation) return;
            loading = false; UpdateNavigation();
            if (!e.IsSuccess)
            {
                if (e.WebErrorStatus != CoreWebView2WebErrorStatus.OperationCanceled)
                    ShowPageError(L.T("页面未能打开"), L.T("请检查网络连接，再重新加载。技术信息：") + e.WebErrorStatus);
                return;
            }
            HidePageError(); pageLoaded = true;
        };
        web.CoreWebView2.NewWindowRequested += async (_, e) =>
        {
            e.Handled = true;
            if (!AllowedNavigation(e.Uri)) return;
            using var deferral = e.GetDeferral();
            var child = new BrowserWindow(profile, downloads, "about:blank", probeReport, probe, probeOwner);
            try
            {
                // The opener and popup share the same environment, including official login state.
                await child.Prepare(environment);
                e.NewWindow = child.web.CoreWebView2;
                child.Show(this);
            }
            catch (Exception)
            {
                child.Dispose(); status.Text = L.T("无法打开新窗口，请使用普通浏览器完成操作。");
            }
        };
        web.CoreWebView2.DownloadStarting += OnDownload;
        UpdateNavigation();
    }

    bool AllowedNavigation(string url) => url == "about:blank" ||
        (Uri.TryCreate(url, UriKind.Absolute, out var uri) &&
         (uri.Scheme == "https" || (probe && uri.Scheme == "http" && uri.Host == "127.0.0.1")));

    void OnDownload(object? sender, CoreWebView2DownloadStartingEventArgs e)
    {
        try
        {
            var name = Path.GetFileName(e.ResultFilePath);
            if (!name.EndsWith(".zip", StringComparison.OrdinalIgnoreCase))
            {
                e.Cancel = true; status.Text = L.T("请选择 ZIP 格式的资产包。"); return;
            }
            foreach (var character in Path.GetInvalidFileNameChars()) name = name.Replace(character, '_');
            // A unique containing directory also prevents duplicate downloads overwriting one another.
            var directory = Path.Combine(downloads, "ATBridge", Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(directory);
            var finalPath = Path.Combine(directory, name);
            var partialPath = finalPath + ".partial";
            e.ResultFilePath = partialPath;
            e.Handled = true;
            var operation = e.DownloadOperation;
            // Capture the product at download start, before the user navigates elsewhere.
            var product = probe ? Task.FromResult<ProductPage?>(null) : probeOwner.ReadProductPage();
            active.Add(operation);
            probeOwner.allActive.Add(operation);
            var card = probeOwner.AddDownload(name, operation, finalPath, web.Source?.ToString() ?? Program.MegascansUrl);
            if (!probe) _ = probeOwner.AttachProductSource(product, card);
            probeOwner.Notify(L.T("已开始下载 · ") + name);
            operation.StateChanged += (_, _) =>
            {
                if (operation.State == CoreWebView2DownloadState.InProgress) return;
                active.Remove(operation);
                probeOwner.allActive.Remove(operation);
                if (operation.State == CoreWebView2DownloadState.Interrupted)
                {
                    var reason = operation.InterruptReason.ToString();
                    var message = reason == "UserCanceled" ? L.T("已取消") : L.T("下载中断");
                    card.Finish(false, message, reason);
                    probeOwner.Notify(message + " · " + name);
                    if (probe) FinishProbe(false, "download interrupted");
                    CloseAfterDownloads();
                    return;
                }
                try
                {
                    File.Move(partialPath, finalPath);
                    card.Finish(true, L.T("ZIP 已保存"), L.T("回到 Blender，选择资产后导入到场景。"));
                    probeOwner.Notify(L.T("ZIP 已保存 · 返回 Blender 选择资产并导入"));
                    if (!probe) _ = probeOwner.CacheDownloadedProduct(product, card, finalPath);
                    if (probe)
                    {
                        var passed = pageLoaded && !web.CoreWebView2.Settings.AreHostObjectsAllowed
                            && !web.CoreWebView2.Settings.IsWebMessageEnabled;
                        if (pageClosePending && probeOwner != this)
                            FormClosed += (_, _) => probeOwner.FinishProbe(passed, finalPath);
                        else FinishProbe(passed, finalPath);
                    }
                }
                catch (Exception error)
                {
                    status.Text = L.T("保存失败：") + error.Message;
                    card.Finish(false, L.T("保存失败"), error.Message);
                    probeOwner.Notify(L.T("ZIP 保存失败，请查看下载详情。"));
                    if (probe) FinishProbe(false, "save failed");
                }
                CloseAfterDownloads();
            };
        }
        catch (Exception error)
        {
            e.Cancel = true; status.Text = L.T("无法开始下载：") + error.Message;
            if (probe) FinishProbe(false, "download initialization failed");
        }
    }

    async Task<ProductPage?> ReadProductPage()
    {
        try
        {
            if (IsDisposed || web.CoreWebView2 == null) return null;
            var json = await web.CoreWebView2.ExecuteScriptAsync("""
                (() => {
                  if (location.protocol !== 'https:' || !['www.fab.com','fab.com'].includes(location.hostname) ||
                      !/^\/listings\/[0-9a-f-]{36}$/i.test(location.pathname)) return null;
                  const main = document.querySelector('main');
                  if (!main) return null;
                  const title = (main.querySelector('h1')?.textContent || document.querySelector('meta[property="og:title"]')?.content || '').trim();
                  if (!title || !document.title.includes(title)) return null;
                  const image = [...main.querySelectorAll('img')].find(x =>
                    (x.currentSrc || x.src).startsWith('https://media.fab.com/image_previews/gallery_images/') &&
                    x.alt.includes(title));
                  if (!image) return null;
                  const files = [...new Set((main.innerText.match(/[a-zA-Z0-9_.()-]+\.zip\b/g) || []))].slice(0,500);
                  return {Url:location.origin+location.pathname,Title:title,ImageUrl:image.currentSrc||image.src,Files:files};
                })()
                """).WaitAsync(TimeSpan.FromSeconds(3));
            return JsonSerializer.Deserialize<ProductPage>(json);
        }
        catch (Exception) { return null; }
    }

    async Task CacheDownloadedProduct(Task<ProductPage?> product, DownloadCard card, string path)
    {
        try
        {
            var page = await product;
            if (page != null)
            {
                await previewCache.StoreAsync(page);
                var presentation = await Task.Run(() => previewCache.ReadPresentation(page, path));
                if (!IsDisposed && !card.IsDisposed && presentation != null)
                    card.SetProduct(presentation.Value.title, presentation.Value.image);
            }
        }
        catch (Exception error) { Debug.WriteLine("Product image cache: " + error.Message); }
    }

    async Task AttachProductSource(Task<ProductPage?> product, DownloadCard card)
    {
        var page = await product;
        if (!IsDisposed && !card.IsDisposed && page != null && FabPreviewCache.ValidPage(page))
            card.SetSource(() => Navigate(page.Url));
    }

    async Task CacheCurrentProduct(bool explicitRequest)
    {
        if (cachingPreview || probe || IsDisposed) return;
        cachingPreview = true;
        try
        {
            var page = await ReadProductPage();
            var count = page == null ? 0 : await previewCache.StoreAsync(page);
            if (count > 0 && page != null && !IsDisposed)
            {
                foreach (var card in downloadList.Controls.OfType<DownloadCard>().Where(c => c.Completed).ToArray())
                {
                    var presentation = await Task.Run(() => previewCache.ReadPresentation(page, card.ArchivePath));
                    if (!card.IsDisposed && presentation != null)
                        card.SetProduct(presentation.Value.title, presentation.Value.image);
                }
            }
            if (explicitRequest && !IsDisposed)
                status.Text = count > 0 ? L.T("商品图已缓存；Blender 将自动显示预览。") :
                    L.T("请打开已下载资产的商品页；若未关联，请展开下载列表后再缓存商品图。");
        }
        catch (Exception error)
        {
            if (explicitRequest && !IsDisposed) status.Text = L.T("商品图缓存失败，不影响 ZIP 导入：") + error.Message;
        }
        finally { cachingPreview = false; }
    }

    void CloseAfterDownloads()
    {
        if (pageClosePending && active.Count == 0 && !IsDisposed)
            BeginInvoke(new Action(Close));
    }

    void FinishProbe(bool passed, string result)
    {
        if (probeOwner != this) { probeOwner.FinishProbe(passed, result); return; }
        if (probeReport != null)
            File.WriteAllText(probeReport, JsonSerializer.Serialize(new { passed, result,
                runtime = environment?.BrowserVersionString }));
        Environment.ExitCode = passed ? 0 : 1;
        BeginInvoke(new Action(Close));
    }
}
