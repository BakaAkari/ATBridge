using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO.Compression;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace ATBridge.FabBrowser;

sealed record ProductPage(string Url, string Title, string ImageUrl, string[] Files);

sealed class FabPreviewCache
{
    readonly string downloads;
    readonly string root;
    readonly SemaphoreSlim gate = new(1, 1);
    readonly Dictionary<string, (long size, DateTime modified, string? id)> knownIds = new();
    static readonly HttpClient http = new(new HttpClientHandler { AllowAutoRedirect = false, UseCookies = false })
        { Timeout = TimeSpan.FromSeconds(15) };
    const long MaxImage = 8 * 1024 * 1024;
    const long MaxCache = 256 * 1024 * 1024;
    public string DirectoryPath => root;

    public (string title, string? image)? ReadPresentation(ProductPage page, string zipPath)
    {
        if (!ValidPage(page)) return null;
        try
        {
            var id = AssetId(new FileInfo(zipPath));
            if (id == null || !page.Files.Any(file => PackageMatches(file, id))) return null;
            EnsureManagedDirectories();
            var image = new FileInfo(Path.Combine(root, "images", Hash(page.ImageUrl) + ".png"));
            return (page.Title, image.Exists && Plain(image) && image.Length <= MaxImage ? image.FullName : null);
        }
        catch (Exception error) when (error is IOException or InvalidDataException or UnauthorizedAccessException)
        {
            // A user may move a finished ZIP while its card remains in this window.
            // One stale record must not prevent other completed cards refreshing.
            return null;
        }
    }

    public FabPreviewCache(string downloads, string? cacheRoot = null)
    {
        this.downloads = Path.GetFullPath(downloads);
        root = cacheRoot ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "ATBridge", "Cache", "Fab");
    }

    public static bool ValidPage(ProductPage page) =>
        Uri.TryCreate(page.Url, UriKind.Absolute, out var url) && url.Scheme == "https" &&
        (url.Host == "www.fab.com" || url.Host == "fab.com") && url.IsDefaultPort &&
        Regex.IsMatch(url.AbsolutePath, @"^/listings/[0-9a-fA-F-]{36}$") &&
        Guid.TryParse(url.Segments.Last(), out _) && string.IsNullOrEmpty(url.UserInfo) &&
        Uri.TryCreate(page.ImageUrl, UriKind.Absolute, out var image) &&
        image.Scheme == "https" && image.Host == "media.fab.com" && image.IsDefaultPort &&
        string.IsNullOrEmpty(image.UserInfo) && image.AbsolutePath.StartsWith("/image_previews/", StringComparison.Ordinal) &&
        page.Title.Length is > 0 and <= 300 && page.Files.Length <= 500;

    static string Hash(string value) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value))).ToLowerInvariant();
    static bool Plain(FileSystemInfo path) => (path.Attributes & FileAttributes.ReparsePoint) == 0;

    void EnsureManagedDirectories()
    {
        foreach (var path in new[] { root, Path.Combine(root, "images"), Path.Combine(root, "assets") })
        {
            for (var directory = new DirectoryInfo(path); directory != null; directory = directory.Parent)
                if (directory.Exists && !Plain(directory))
                    throw new IOException("Image cache paths cannot contain links");
        }
        Directory.CreateDirectory(Path.Combine(root, "images"));
        Directory.CreateDirectory(Path.Combine(root, "assets"));
    }

    static bool PackageMatches(string filename, string id)
    {
        // Fab Megascans names put the ID immediately before the quality suffix.
        // Matching arbitrary tokens would confuse IDs with 'raw', 'zip', or title words.
        var match = Regex.Match(filename, @"(?:^|_)(?<id>[a-z0-9]{6,32})_(?:raw|high|mid|medium|low)(?:_\d{1,2}k)?\.zip$",
            RegexOptions.IgnoreCase);
        return match.Success && string.Equals(match.Groups["id"].Value, id, StringComparison.OrdinalIgnoreCase);
    }

    IEnumerable<FileInfo> Packages()
    {
        var folder = new DirectoryInfo(downloads);
        if (!folder.Exists || !Plain(folder)) return Array.Empty<FileInfo>();
        var files = folder.EnumerateFiles().Where(f => f.Extension.Equals(".zip", StringComparison.OrdinalIgnoreCase) && Plain(f));
        var own = new DirectoryInfo(Path.Combine(downloads, "ATBridge"));
        if (own.Exists && Plain(own))
            files = files.Concat(own.EnumerateDirectories().Where(Plain)
                .SelectMany(d => d.EnumerateFiles()).Where(f => f.Extension.Equals(".zip", StringComparison.OrdinalIgnoreCase) && Plain(f)));
        return files.Where(f => f.Length is > 0 and <= 1073741824)
            .OrderByDescending(f => f.LastWriteTimeUtc).Take(20).ToArray();
    }

    static string? AssetId(FileInfo file)
    {
        using var stream = new FileStream(file.FullName, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
        using var archive = new ZipArchive(stream, ZipArchiveMode.Read);
        if (archive.Entries.Count > 10000) return null;
        long total = 0;
        var ids = new List<string>();
        foreach (var entry in archive.Entries.Where(e => e.FullName.EndsWith(".json", StringComparison.OrdinalIgnoreCase)))
        {
            if (entry.Length > 8 * 1024 * 1024) continue;
            total += entry.Length;
            if (total > 32 * 1024 * 1024) return null;
            try
            {
                using var input = entry.Open();
                using var document = JsonDocument.Parse(input);
                var data = document.RootElement;
                if (data.ValueKind != JsonValueKind.Object || !data.TryGetProperty("id", out var id) ||
                    id.ValueKind != JsonValueKind.String) continue;
                var text = id.GetString()!;
                if (text.Length is < 1 or > 256 || string.IsNullOrWhiteSpace(text)) continue;
                bool valid = true, hasPayload = false;
                foreach (var field in new[] { "models", "maps" })
                {
                    if (!data.TryGetProperty(field, out var list)) continue;
                    if (list.ValueKind != JsonValueKind.Array) { valid = false; break; }
                    foreach (var item in list.EnumerateArray())
                    {
                        if (item.ValueKind != JsonValueKind.Object) { valid = false; break; }
                        if (item.TryGetProperty("uri", out var uri))
                        {
                            if (uri.ValueKind != JsonValueKind.String) { valid = false; break; }
                            if (!string.IsNullOrWhiteSpace(uri.GetString())) hasPayload = true;
                        }
                    }
                }
                if (valid && hasPayload) ids.Add(text);
            }
            catch (JsonException) { }
        }
        return ids.Count == 1 ? ids[0] : null;
    }

    public async Task<int> StoreAsync(ProductPage page)
    {
        if (!ValidPage(page)) return 0;
        // Preserve captured download pages even if another product image is in flight.
        // The window already coalesces its periodic current-page requests.
        await gate.WaitAsync();
        try
        {
            // Bind only IDs explicitly present in this product's displayed package names.
            // The webpage cannot supply a destination path or command.
            var ids = await Task.Run(() =>
            {
                var found = new HashSet<string>();
                foreach (var file in Packages())
                {
                    try
                    {
                        if (!knownIds.TryGetValue(file.FullName, out var known) ||
                            known.size != file.Length || known.modified != file.LastWriteTimeUtc)
                        {
                            known = (file.Length, file.LastWriteTimeUtc, AssetId(file));
                            if (knownIds.Count >= 200) knownIds.Clear();
                            knownIds[file.FullName] = known;
                        }
                        var id = known.id;
                        if (id != null && page.Files.Any(f => PackageMatches(f, id)))
                            found.Add(id);
                    }
                    catch (Exception e) when (e is IOException or InvalidDataException or UnauthorizedAccessException) { }
                }
                return found;
            });
            if (ids.Count == 0) return 0;
            EnsureManagedDirectories();
            var filename = Hash(page.ImageUrl) + ".png";
            var imagePath = Path.Combine(root, "images", filename);
            if (File.Exists(imagePath) && !Plain(new FileInfo(imagePath)))
                throw new IOException("Image cache files cannot be links");
            if (!File.Exists(imagePath) || File.GetLastWriteTimeUtc(imagePath) < DateTime.UtcNow.AddDays(-7))
            {
                using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(20));
                using var response = await http.GetAsync(page.ImageUrl, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
                response.EnsureSuccessStatusCode();
                if (!(response.Content.Headers.ContentType?.MediaType?.StartsWith("image/", StringComparison.Ordinal) ?? false) ||
                    response.Content.Headers.ContentLength > MaxImage) return 0;
                using var network = await response.Content.ReadAsStreamAsync(deadline.Token);
                using var bytes = new MemoryStream();
                var buffer = new byte[32768];
                int count;
                while ((count = await network.ReadAsync(buffer, deadline.Token)) > 0)
                {
                    if (bytes.Length + count > MaxImage) return 0;
                    bytes.Write(buffer, 0, count);
                }
                var png = await Task.Run(() => Resize(bytes.ToArray()));
                var temporary = imagePath + "." + Guid.NewGuid().ToString("N") + ".tmp";
                try { await File.WriteAllBytesAsync(temporary, png); File.Move(temporary, imagePath, true); }
                finally { if (File.Exists(temporary)) File.Delete(temporary); }
            }
            foreach (var id in ids)
            {
                var recordPath = Path.Combine(root, "assets", Hash(id) + ".json");
                if (File.Exists(recordPath) && !Plain(new FileInfo(recordPath)))
                    throw new IOException("Image cache records cannot be links");
                var json = JsonSerializer.Serialize(new { schema = 1, asset_id = id, image = filename,
                    title = page.Title, listing_url = new Uri(page.Url).GetLeftPart(UriPartial.Path), image_url = page.ImageUrl });
                if (File.Exists(recordPath) && await File.ReadAllTextAsync(recordPath) == json) continue;
                var temporary = recordPath + "." + Guid.NewGuid().ToString("N") + ".tmp";
                try { await File.WriteAllTextAsync(temporary, json); File.Move(temporary, recordPath, true); }
                finally { if (File.Exists(temporary)) File.Delete(temporary); }
            }
            Prune();
            return ids.Count;
        }
        finally { gate.Release(); }
    }

    static byte[] Resize(byte[] data)
    {
        using var input = new MemoryStream(data);
        using var source = Image.FromStream(input, false, true);
        if (source.Width > 16384 || source.Height > 16384 || (long)source.Width * source.Height > 64000000)
            throw new InvalidDataException("Product image is too large");
        var scale = Math.Min(1.0, 512.0 / Math.Max(source.Width, source.Height));
        using var target = new Bitmap(Math.Max(1, (int)(source.Width * scale)), Math.Max(1, (int)(source.Height * scale)));
        using (var graphics = Graphics.FromImage(target))
        {
            graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
            graphics.DrawImage(source, 0, 0, target.Width, target.Height);
        }
        using var output = new MemoryStream();
        target.Save(output, ImageFormat.Png);
        return output.ToArray();
    }

    void Prune()
    {
        EnsureManagedDirectories();
        // Only managed names inside this cache; never recurse into download or asset folders.
        var images = new DirectoryInfo(Path.Combine(root, "images")).EnumerateFiles()
            .Where(f => Plain(f) && Regex.IsMatch(f.Name, @"^[a-f0-9]{64}\.png$"))
            .OrderBy(f => f.LastWriteTimeUtc).ToList();
        var total = images.Sum(f => f.Length);
        foreach (var file in images)
            if (file.LastWriteTimeUtc < DateTime.UtcNow.AddDays(-90) || total > MaxCache)
            { total -= file.Length; file.Delete(); }
        foreach (var folder in new[] { "assets", "images" })
            foreach (var temporary in new DirectoryInfo(Path.Combine(root, folder)).EnumerateFiles("*.tmp"))
                if (Plain(temporary) && Regex.IsMatch(temporary.Name, @"^[a-f0-9]{64}\.(png|json)\.[a-f0-9]{32}\.tmp$") &&
                    temporary.LastWriteTimeUtc < DateTime.UtcNow.AddDays(-1)) temporary.Delete();
        foreach (var record in new DirectoryInfo(Path.Combine(root, "assets")).EnumerateFiles("*.json"))
        {
            if (!Plain(record) || !Regex.IsMatch(record.Name, @"^[a-f0-9]{64}\.json$")) continue;
            try
            {
                using var json = JsonDocument.Parse(File.ReadAllText(record.FullName));
                var image = json.RootElement.GetProperty("image").GetString() ?? "";
                if (Regex.IsMatch(image, @"^[a-f0-9]{64}\.png$") && !File.Exists(Path.Combine(root, "images", image)))
                    record.Delete();
            }
            catch (JsonException) { }
        }
    }
}
