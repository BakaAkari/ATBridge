using System.Diagnostics;

namespace ATBridge.FabBrowser;

sealed class DownloadCard : FlowLayoutPanel
{
    readonly Label title = new() { AutoSize = true, MaximumSize = new Size(280, 0) };
    readonly Label filename = new() { AutoSize = true, ForeColor = ShellTheme.Muted };
    readonly Label detail = new() { AutoSize = true, ForeColor = ShellTheme.Muted };
    readonly Label explanation = new() { AutoSize = true, Visible = false, ForeColor = ShellTheme.Muted };
    readonly PictureBox picture = new() { SizeMode = PictureBoxSizeMode.Zoom, Height = 112, Visible = false };
    readonly Label previewCaption = new() { AutoSize = true, Visible = false, ForeColor = ShellTheme.Muted,
        Text = L.T("商品图暂不可用 · 不影响导入") };
    readonly ProgressBar progress = new DownloadProgress { Height = 6, Style = ProgressBarStyle.Marquee };
    readonly FlowLayoutPanel actions = new() { AutoSize = true, WrapContents = true };
    readonly Button action;
    readonly Button info = null!;
    readonly Action cancel;
    readonly string path;
    Action source;
    readonly Action<string> notify;
    bool completed;
    public bool Terminal { get; private set; }
    public bool Completed => completed;
    public string ArchivePath => path;
    public event EventHandler? Terminated;

    public DownloadCard(string name, string path, Action cancel, Action source, Action<string> notify)
    {
        this.cancel = cancel; this.path = path; this.source = source; this.notify = notify;
        AutoSize = true; AutoSizeMode = AutoSizeMode.GrowAndShrink;
        FlowDirection = FlowDirection.TopDown; WrapContents = false;
        Padding = new Padding(10, 14, 10, 16); Margin = new Padding(0, 0, 0, 10);
        BackColor = Color.FromArgb(48, 48, 48); ForeColor = Color.WhiteSmoke;
        Width = 300; MinimumSize = new Size(200, 0);
        title.Font = new Font(L.IsChinese ? "Microsoft YaHei UI" : "Segoe UI", 9F, FontStyle.Bold);
        title.Text = Path.GetFileNameWithoutExtension(name).Replace('_', ' ');
        filename.Text = name; filename.Visible = false;
        explanation.Text = path;
        action = ShellTheme.Button(L.T("取消下载"), Act);
        var origin = ShellTheme.Button(L.T("商品页"), () => this.source());
        info = ShellTheme.Button(L.T("详情"), () =>
        {
            explanation.Visible = !explanation.Visible; filename.Visible = explanation.Visible;
            info.Text = explanation.Visible ? L.T("收起详情") : L.T("详情");
        });
        actions.Controls.Add(action); actions.Controls.Add(origin); actions.Controls.Add(info);
        Controls.Add(picture); Controls.Add(title); Controls.Add(progress); Controls.Add(detail); Controls.Add(previewCaption);
        Controls.Add(actions); Controls.Add(filename); Controls.Add(explanation);
        SizeChanged += (_, _) => FitContents();
        SetProgress(0, 0); FitContents();
    }

    void FitContents()
    {
        var width = Math.Max(140, ClientSize.Width - Padding.Horizontal - 8);
        foreach (var label in new[] { title, filename, detail, explanation, previewCaption }) label.MaximumSize = new Size(width, 0);
        picture.Width = progress.Width = width;
        actions.MaximumSize = new Size(width, 0);
    }

    void Act()
    {
        try
        {
            if (!Terminal) cancel();
            else if (completed)
            {
                if (!File.Exists(path)) { notify(L.T("ZIP 已被移动或删除，请检查下载目录。")); return; }
                Process.Start(new ProcessStartInfo("explorer.exe", "/select,\"" + path + "\"") { UseShellExecute = true });
            }
            else source();
        }
        catch (Exception error) { notify(L.T("操作未完成：") + error.Message); }
    }

    public void SetProgress(long received, long total)
    {
        if (Terminal || IsDisposed) return;
        if (total > 0)
        {
            progress.Style = ProgressBarStyle.Continuous;
            progress.Value = (int)Math.Clamp(received * 100.0 / total, 0, 100);
            detail.Text = L.F("下载中 · {0}%\n{1:F1} / {2:F1} MiB", progress.Value, received / 1048576.0, total / 1048576.0);
        }
        else detail.Text = L.F("下载中 · 已接收 {0:F1} MiB", received / 1048576.0);
    }

    public void Finish(bool success, string message, string details)
    {
        if (IsDisposed || Terminal) return;
        Terminal = true; completed = success;
        previewCaption.Visible = success;
        progress.Style = ProgressBarStyle.Continuous; progress.Value = success ? 100 : 0;
        progress.Visible = false;
        detail.ForeColor = success ? Color.FromArgb(169, 217, 178) : Color.FromArgb(255, 178, 167);
        detail.Text = success ? message + L.T("\n回到 Blender，选择资产并导入。") : message + L.T("\nZIP 未完成保存，可回商品页重新下载。");
        explanation.Text = details + "\n\n" + path;
        action.Text = success ? L.T("显示文件") : L.T("重新打开商品页");
        Terminated?.Invoke(this, EventArgs.Empty);
    }

    public void SetProduct(string name, string? imagePath)
    {
        if (IsDisposed) return;
        title.Text = name;
        if (imagePath == null) return;
        try
        {
            using var source = Image.FromFile(imagePath);
            var image = new Bitmap(source);
            var previous = picture.Image; picture.Image = image; previous?.Dispose();
            picture.Visible = true;
            previewCaption.Text = L.T("Fab 商品图");
        }
        catch (Exception error) when (error is IOException or ArgumentException or OutOfMemoryException) { }
    }

    public void SetSource(Action navigate) => source = navigate;

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            picture.Image?.Dispose(); picture.Image = null;
        }
        base.Dispose(disposing);
    }
}

sealed class DownloadProgress : ProgressBar
{
    readonly System.Windows.Forms.Timer pulse = new() { Interval = 80 };
    int offset;
    public DownloadProgress()
    {
        SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer, true);
        pulse.Tick += (_, _) => { offset = (offset + 5) % 140; Invalidate(); };
    }
    protected override void OnVisibleChanged(EventArgs e)
    {
        base.OnVisibleChanged(e);
        if (Visible) pulse.Start(); else pulse.Stop();
    }
    protected override void OnPaint(PaintEventArgs e)
    {
        e.Graphics.Clear(Color.FromArgb(80, 80, 80));
        using var fill = new SolidBrush(Color.FromArgb(149, 189, 223));
        if (Style == ProgressBarStyle.Marquee)
            e.Graphics.FillRectangle(fill, (offset - 40) * Width / 100, 0, Width * .4f, Height);
        else e.Graphics.FillRectangle(fill, 0, 0, Width * Value / (float)Math.Max(1, Maximum), Height);
    }
    protected override void Dispose(bool disposing)
    {
        if (disposing) pulse.Dispose();
        base.Dispose(disposing);
    }
}
