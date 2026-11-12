using System.Diagnostics;
using System.Runtime.InteropServices;
using Microsoft.Web.WebView2.Core;

namespace ATBridge.FabBrowser;

static class ShellTheme
{
    public static readonly Color Background = Color.FromArgb(32, 32, 32);
    public static readonly Color Panel = Color.FromArgb(42, 42, 42);
    public static readonly Color Muted = Color.FromArgb(199, 199, 199);
    public static readonly Color Accent = Color.FromArgb(54, 94, 131);
    public static Button Button(string text, Action action, bool primary = false)
    {
        var button = new ShellButton { Text = text, AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink, MinimumSize = new Size(36, 34),
            FlatStyle = FlatStyle.Flat, BackColor = primary ? Accent : Color.FromArgb(52, 52, 52),
            ForeColor = Color.WhiteSmoke, Padding = new Padding(8, 2, 8, 2), Margin = new Padding(4),
            UseVisualStyleBackColor = false, AccessibleName = text };
        button.FlatAppearance.BorderColor = Color.FromArgb(87, 87, 87);
        button.Click += (_, _) => action();
        return button;
    }
}

sealed class ShellButton : Button
{
    public ShellButton() => SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer, true);
    protected override void OnPaint(PaintEventArgs e)
    {
        var hovered = Enabled && ClientRectangle.Contains(PointToClient(Cursor.Position));
        using var fill = new SolidBrush(hovered ? ControlPaint.Light(BackColor, .12f) : BackColor);
        e.Graphics.FillRectangle(fill, ClientRectangle);
        using var border = new Pen(Focused ? Color.FromArgb(157, 201, 240) : FlatAppearance.BorderColor);
        e.Graphics.DrawRectangle(border, 0, 0, Width - 1, Height - 1);
        TextRenderer.DrawText(e.Graphics, Text, Font, ClientRectangle, Enabled ? ForeColor : Color.FromArgb(165, 165, 165),
            TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis);
        if (Focused && ShowFocusCues) ControlPaint.DrawFocusRectangle(e.Graphics, Rectangle.Inflate(ClientRectangle, -4, -4), ForeColor, BackColor);
    }
    protected override void OnMouseEnter(EventArgs e) { base.OnMouseEnter(e); Invalidate(); }
    protected override void OnMouseLeave(EventArgs e) { base.OnMouseLeave(e); Invalidate(); }
    protected override void OnEnabledChanged(EventArgs e) { base.OnEnabledChanged(e); Invalidate(); }
}

sealed class ShellMenuColors : ProfessionalColorTable
{
    public override Color ToolStripDropDownBackground => ShellTheme.Panel;
    public override Color MenuBorder => Color.FromArgb(87, 87, 87);
    public override Color MenuItemSelected => ShellTheme.Accent;
    public override Color MenuItemBorder => Color.FromArgb(114, 155, 193);
    public override Color MenuItemSelectedGradientBegin => ShellTheme.Accent;
    public override Color MenuItemSelectedGradientEnd => ShellTheme.Accent;
    public override Color SeparatorDark => Color.FromArgb(87, 87, 87);
    public override Color SeparatorLight => ShellTheme.Panel;
}

sealed partial class BrowserWindow
{
    readonly Panel workspace = new() { Dock = DockStyle.Fill };
    readonly Panel sidebar = new() { Visible = false, BackColor = ShellTheme.Panel };
    readonly Panel errorPanel = new() { Dock = DockStyle.Fill, Visible = false, BackColor = ShellTheme.Background };
    readonly Label errorTitle = new() { AutoSize = true };
    readonly Label errorDetail = new() { AutoSize = false, Height = 100 };
    readonly FlowLayoutPanel errorContent = new() { AutoSize = true, FlowDirection = FlowDirection.TopDown, WrapContents = false };
    readonly Label taskSummary = new() { Dock = DockStyle.Top, Height = 32, Text = L.T("本次窗口的下载任务"), ForeColor = ShellTheme.Muted };
    readonly ToolTip hints = new() { AutoPopDelay = 15000 };
    readonly System.Windows.Forms.Timer toastTimer = new() { Interval = 7000 };
    Button back = null!, forward = null!, refresh = null!, home = null!, tasks = null!;
    Button retryPage = null!;
    Label empty = null!;
    bool loading, openedDownloads, shellReady, initializing;
    int? ownerPid;
    DateTime? ownerStarted;
    static string IdleMessage => L.T("在 Fab 下载 ZIP → 返回 Blender → 选择资产并导入");
    int Px(int value) => (int)Math.Round(value * DeviceDpi / 96.0);

    void BuildShell(int? blenderPid)
    {
        Text = probeOwner == this ? "ATBridge · Megascans" : L.T("ATBridge · 网页窗口");
        AutoScaleMode = AutoScaleMode.Dpi;
        Font = new Font(L.IsChinese ? "Microsoft YaHei UI" : "Segoe UI", 9F);
        BackColor = ShellTheme.Background; ForeColor = Color.WhiteSmoke;
        Size = new Size(1280, 860); MinimumSize = new Size(900, 640);
        StartPosition = FormStartPosition.CenterScreen;
        CaptureBlender(blenderPid);

        var navigation = new TableLayoutPanel { Dock = DockStyle.Top, Height = 64,
            Padding = new Padding(10, 8, 10, 8), ColumnCount = 7, RowCount = 1 };
        for (var i = 0; i < 7; i++) navigation.ColumnStyles.Add(
            new ColumnStyle(i == 4 ? SizeType.Percent : SizeType.AutoSize, i == 4 ? 100 : 0));
        back = ShellTheme.Button("←", () => { if (web.CoreWebView2?.CanGoBack == true) web.CoreWebView2.GoBack(); });
        forward = ShellTheme.Button("→", () => { if (web.CoreWebView2?.CanGoForward == true) web.CoreWebView2.GoForward(); });
        refresh = ShellTheme.Button(L.T("刷新"), ReloadOrStop);
        home = ShellTheme.Button("Megascans", () => Navigate(Program.MegascansUrl));
        tasks = ShellTheme.Button(L.T("下载"), () => probeOwner.ToggleDownloads());
        var more = ShellTheme.Button(L.T("更多 ···"), () => { });
        var menu = new ContextMenuStrip { BackColor = ShellTheme.Panel, ForeColor = ForeColor,
            ShowImageMargin = false, Font = Font, Renderer = new ToolStripProfessionalRenderer(new ShellMenuColors()) };
        menu.Items.Add(L.T("复制完整网址"), null, (_, _) => CopyAddress());
        menu.Items.Add(L.T("打开下载目录"), null, (_, _) => OpenFolder(downloads));
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add(L.T("补齐当前商品图"), null, async (_, _) => await probeOwner.CacheCurrentProduct(true));
        menu.Items.Add(L.T("打开商品图缓存"), null, (_, _) => OpenFolder(previewCache.DirectoryPath));
        menu.Items.Add(L.T("返回 Blender"), null, (_, _) => probeOwner.ReturnToBlender());
        more.Click += (_, _) => menu.Show(more, new Point(0, more.Height));
        more.Disposed += (_, _) => menu.Dispose();
        address.Margin = new Padding(14, 0, 10, 0); address.Cursor = Cursors.Hand;
        address.ForeColor = ShellTheme.Muted; address.Text = L.T("正在准备浏览器…");
        address.AccessibleName = L.T("当前网页地址，点击复制");
        address.Click += (_, _) => CopyAddress();
        var controls = new Control[] { back, forward, refresh, home, address, tasks, more };
        for (var i = 0; i < controls.Length; i++) navigation.Controls.Add(controls[i], i, 0);
        hints.SetToolTip(back, L.T("后退 · Alt+←")); hints.SetToolTip(forward, L.T("前进 · Alt+→"));
        hints.SetToolTip(refresh, L.T("刷新 · Ctrl+R；加载中可停止"));
        back.AccessibleName = L.T("后退"); forward.AccessibleName = L.T("前进");

        var heading = new TableLayoutPanel { Dock = DockStyle.Top, Height = 56, ColumnCount = 2, Padding = new Padding(12, 5, 10, 5) };
        heading.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        heading.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        heading.Controls.Add(new Label { Text = L.T("下载"), AutoSize = true, Font = new Font(Font, FontStyle.Bold), Anchor = AnchorStyles.Left });
        heading.Controls.Add(ShellTheme.Button(L.T("收起"), ToggleDownloads));
        taskSummary.Padding = new Padding(16, 0, 0, 0);
        var bottom = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 142, Padding = new Padding(10),
            FlowDirection = FlowDirection.TopDown, WrapContents = false };
        var returnButton = ShellTheme.Button(L.T("返回 Blender"), ReturnToBlender, true);
        returnButton.Width = 304;
        bottom.Controls.Add(returnButton);
        bottom.Controls.Add(new Label { Text = L.T("只切换窗口，不会自动导入。"), AutoSize = true, ForeColor = ShellTheme.Muted, Margin = new Padding(6, 4, 0, 4) });
        var management = new FlowLayoutPanel { AutoSize = true, WrapContents = false };
        management.Controls.Add(ShellTheme.Button(L.T("下载目录"), () => OpenFolder(downloads)));
        management.Controls.Add(ShellTheme.Button(L.T("清除已结束记录"), ClearFinished));
        bottom.Controls.Add(management);
        downloadList.BackColor = ShellTheme.Panel;
        sidebar.Controls.Add(downloadList); sidebar.Controls.Add(bottom);
        sidebar.Controls.Add(taskSummary); sidebar.Controls.Add(heading);
        ResetEmpty();
        downloadList.ClientSizeChanged += (_, _) => SizeCards();

        errorTitle.Font = new Font(Font.FontFamily, 18, FontStyle.Bold);
        errorDetail.ForeColor = ShellTheme.Muted;
        retryPage = ShellTheme.Button(L.T("重新加载"), async () =>
        {
            if (web.CoreWebView2 == null) await LoadInitial();
            else { HidePageError(); web.CoreWebView2.Reload(); }
        }, true);
        var errorActions = new FlowLayoutPanel { AutoSize = true };
        errorActions.Controls.Add(retryPage);
        errorActions.Controls.Add(ShellTheme.Button(L.T("返回 Megascans"), () => Navigate(Program.MegascansUrl)));
        errorContent.Controls.Add(errorTitle); errorContent.Controls.Add(errorDetail); errorContent.Controls.Add(errorActions);
        errorPanel.Controls.Add(errorContent);
        workspace.Controls.Add(web); workspace.Controls.Add(errorPanel); workspace.Controls.Add(sidebar);
        var footer = new StatusStrip { BackColor = ShellTheme.Panel, ForeColor = ShellTheme.Muted, SizingGrip = true };
        status.Text = IdleMessage; status.AutoToolTip = false;
        footer.Items.Add(status);
        var showDownloads = new ToolStripButton(L.T("查看下载"));
        showDownloads.Click += (_, _) => probeOwner.ShowDownloads(); footer.Items.Add(showDownloads);
        Controls.Add(workspace); Controls.Add(navigation); Controls.Add(footer);
        toastTimer.Tick += (_, _) => { toastTimer.Stop(); if (!IsDisposed) status.Text = IdleMessage; };
        workspace.Resize += (_, _) => LayoutWorkspace();
        DpiChanged += (_, _) => BeginInvoke(new Action(LayoutWorkspace));
        shellReady = true; LayoutWorkspace(); UpdateNavigation();
    }

    async Task LoadInitial()
    {
        if (initializing || IsDisposed) return;
        initializing = true; retryPage.Enabled = false;
        try { await Prepare(); HidePageError(); web.CoreWebView2.Navigate(initialUrl); }
        catch (Exception error)
        {
            var (title, detail) = StartupFailure(error);
            ShowPageError(title, detail);
            if (probe) FinishProbe(false, "initialization failed");
        }
        finally { initializing = false; if (!IsDisposed) retryPage.Enabled = true; }
    }

    internal static (string title, string detail) StartupFailure(Exception error)
    {
        if (error is WebView2RuntimeNotFoundException)
            return (L.T("未找到浏览器运行时"), L.T("请安装 Microsoft Edge WebView2 Runtime，然后重新加载。"));
        if (error.HResult == unchecked((int)0x8007139F))
            return (L.T("浏览器初始化状态冲突"),
                L.T("可能有旧版窗口正在使用同一份浏览器资料。请等待下载完成，关闭其余旧版 ATBridge 浏览器，再点“重新加载”。\n不要删除登录资料。错误代码：0x8007139F"));
        if (error is UnauthorizedAccessException || error.HResult == unchecked((int)0x80070005))
            return (L.T("无法访问浏览器资料目录"), L.T("请检查当前用户对资料目录的访问权限，再重新加载。\n") + error.Message);
        return (L.T("浏览器启动失败"), L.T("WebView2 初始化未完成。请关闭旧浏览器窗口后重新加载。\n") + error.Message);
    }

    void Navigate(string url)
    {
        if (web.CoreWebView2 == null) { Notify(L.T("浏览器尚未准备好，请稍候或重新加载。")); return; }
        HidePageError(); web.CoreWebView2.Navigate(url);
    }

    void UpdateNavigation()
    {
        if (!shellReady || IsDisposed) return;
        var core = web.CoreWebView2;
        back.Enabled = core?.CanGoBack == true; forward.Enabled = core?.CanGoForward == true;
        refresh.Enabled = home.Enabled = core != null;
        refresh.Text = loading ? L.T("停止") : L.T("刷新");
        if (Uri.TryCreate(web.Source?.ToString(), UriKind.Absolute, out var url))
        {
            address.Text = url.Scheme == "https" ? url.Host +
                (ClientSize.Width >= Px(1200) ? Uri.UnescapeDataString(url.AbsolutePath) : "") : url.ToString();
            hints.SetToolTip(address, url.ToString() + L.T("\n点击复制完整网址"));
        }
    }

    void ReloadOrStop()
    {
        if (web.CoreWebView2 == null) return;
        if (loading) web.CoreWebView2.Stop(); else { HidePageError(); web.CoreWebView2.Reload(); }
    }

    protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
    {
        return HandleShortcut(keyData) || base.ProcessCmdKey(ref msg, keyData);
    }

    bool HandleShortcut(Keys keyData)
    {
        if (keyData == (Keys.Alt | Keys.Left)) { back.PerformClick(); return true; }
        if (keyData == (Keys.Alt | Keys.Right)) { forward.PerformClick(); return true; }
        if (keyData == (Keys.Control | Keys.R) || keyData == Keys.F5) { ReloadOrStop(); return true; }
        if (keyData == Keys.Escape && loading) { web.CoreWebView2?.Stop(); return true; }
        if (keyData == (Keys.Control | Keys.J)) { probeOwner.ToggleDownloads(); return true; }
        return false;
    }

    void LayoutWorkspace()
    {
        if (!shellReady) return;
        var width = Px(352);
        sidebar.SetBounds(Math.Max(0, workspace.ClientSize.Width - width), 0, width, workspace.ClientSize.Height);
        // In compact windows the drawer overlays the page rather than squeezing it.
        workspace.Padding = new Padding(0, 0, sidebar.Visible && ClientSize.Width >= Px(1200) ? width : 0, 0);
        sidebar.BringToFront();
        errorDetail.Width = Math.Max(Px(260), Math.Min(Px(620), errorPanel.ClientSize.Width - Px(64)));
        errorContent.Location = new Point(Px(32), Px(64));
        SizeCards(); UpdateNavigation();
    }

    void SizeCards()
    {
        var width = Math.Max(Px(230), downloadList.ClientSize.Width - downloadList.Padding.Horizontal - Px(24));
        foreach (Control card in downloadList.Controls)
        {
            card.MinimumSize = new Size(width, 0); card.MaximumSize = new Size(width, 0); card.Width = width;
        }
    }

    void ToggleDownloads()
    {
        sidebar.Visible = !sidebar.Visible; LayoutWorkspace();
    }
    void ShowDownloads() { sidebar.Visible = true; LayoutWorkspace(); }
    void ShowPageError(string title, string detail)
    {
        errorTitle.Text = title; errorDetail.Text = detail;
        errorPanel.Visible = true; errorPanel.BringToFront(); sidebar.BringToFront(); LayoutWorkspace();
        Notify(title);
    }
    void HidePageError() => errorPanel.Visible = false;
    void Notify(string text)
    {
        if (IsDisposed) return;
        status.Text = text; status.ToolTipText = text;
        toastTimer.Stop(); toastTimer.Start();
    }

    void ResetEmpty()
    {
        empty = new Label { Text = L.T("还没有下载任务\n\n在 Quixel 商品页选择 ZIP。下载完成后，回到 Blender 选择资产并导入。"),
            ForeColor = ShellTheme.Muted, Padding = new Padding(8), AutoSize = true };
        downloadList.Controls.Add(empty); SizeCards();
    }

    DownloadCard AddDownload(string name, CoreWebView2DownloadOperation operation, string path, string source)
    {
        if (empty.Parent != null) { downloadList.Controls.Remove(empty); empty.Dispose(); }
        var card = new DownloadCard(name, path, () => operation.Cancel(), () => Navigate(source), Notify);
        void Progress(object? sender, object args) => card.SetProgress(operation.BytesReceived,
            (long)Math.Min((ulong)long.MaxValue, operation.TotalBytesToReceive.GetValueOrDefault()));
        operation.BytesReceivedChanged += Progress;
        card.Terminated += (_, _) => operation.BytesReceivedChanged -= Progress;
        card.Disposed += (_, _) => operation.BytesReceivedChanged -= Progress;
        Progress(null, EventArgs.Empty);
        card.Terminated += (_, _) => RefreshTasks();
        downloadList.Controls.Add(card);
        if (!openedDownloads) { openedDownloads = true; ShowDownloads(); }
        RefreshTasks(); return card;
    }

    void RefreshTasks()
    {
        var cards = downloadList.Controls.OfType<DownloadCard>().ToArray();
        var ongoing = cards.Count(c => !c.Terminal);
        tasks.Text = ongoing > 0 ? L.F("下载 · {0} 进行中", ongoing) : cards.Length > 0 ? L.F("下载 · {0}", cards.Length) : L.T("下载");
        taskSummary.Text = L.F("进行中 {0}   ·   已结束 {1}", ongoing, cards.Length - ongoing);
        tasks.AccessibleDescription = taskSummary.Text;
        downloadList.SuspendLayout();
        var index = 0;
        foreach (var card in cards.OrderBy(c => c.Terminal)) downloadList.Controls.SetChildIndex(card, index++);
        downloadList.ResumeLayout(); SizeCards();
    }

    void ClearFinished()
    {
        foreach (var card in downloadList.Controls.OfType<DownloadCard>().Where(c => c.Terminal).ToArray())
        { downloadList.Controls.Remove(card); card.Dispose(); }
        if (downloadList.Controls.Count == 0) ResetEmpty();
        RefreshTasks(); Notify(L.T("已清除结束的任务记录，ZIP 文件保留。"));
    }

    void OpenFolder(string path)
    {
        try { Directory.CreateDirectory(path); Process.Start(new ProcessStartInfo(path) { UseShellExecute = true }); }
        catch (Exception error) { Notify(L.T("无法打开目录：") + error.Message); }
    }
    void CopyAddress()
    {
        try { if (web.Source != null) { Clipboard.SetText(web.Source.ToString()); Notify(L.T("已复制完整网址。")); } }
        catch (ExternalException) { Notify(L.T("剪贴板暂不可用，请重试。")); }
    }

    void CaptureBlender(int? pid)
    {
        if (pid == null) return;
        try
        {
            using var process = Process.GetProcessById(pid.Value);
            if (!process.ProcessName.Equals("blender", StringComparison.OrdinalIgnoreCase)) return;
            ownerPid = pid; ownerStarted = process.StartTime.ToUniversalTime();
        }
        catch (Exception error) when (error is ArgumentException or InvalidOperationException or System.ComponentModel.Win32Exception) { }
    }

    void ReturnToBlender()
    {
        try
        {
            if (ownerPid == null) { Notify(L.T("请从 Blender 的“浏览 Fab 资产”打开此窗口；当前没有关联的 Blender。")); return; }
            using var process = Process.GetProcessById(ownerPid.Value);
            if (process.HasExited || process.StartTime.ToUniversalTime() != ownerStarted)
                throw new InvalidOperationException();
            IntPtr target = IntPtr.Zero;
            EnumWindows((window, _) =>
            {
                GetWindowThreadProcessId(window, out var pid);
                if (pid == ownerPid && IsWindowVisible(window) && GetWindow(window, 4) == IntPtr.Zero)
                { target = window; return false; }
                return true;
            }, IntPtr.Zero);
            if (target == IntPtr.Zero) { Notify(L.T("未找到原 Blender 的可见窗口，请从任务栏返回。")); return; }
            if (IsIconic(target)) ShowWindow(target, 9);
            if (!SetForegroundWindow(target)) Notify(L.T("Windows 未允许切换焦点，请从任务栏返回 Blender。"));
        }
        catch (Exception error) when (error is ArgumentException or InvalidOperationException or System.ComponentModel.Win32Exception)
        { Notify(L.T("原 Blender 已关闭，请重新打开插件。已下载的 ZIP 仍保留。")); }
    }
    delegate bool EnumWindowCallback(IntPtr window, IntPtr parameter);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowCallback callback, IntPtr parameter);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr window, out uint pid);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")] static extern bool IsIconic(IntPtr window);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr window, int command);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr window);
    [DllImport("user32.dll")] static extern IntPtr GetWindow(IntPtr window, uint command);
}
