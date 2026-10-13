namespace Demo;

/// <summary>Reads the nearest .env into the environment; real variables win.</summary>
internal static class Dotenv
{
    public static void Load()
    {
        var dir = new DirectoryInfo(Directory.GetCurrentDirectory());
        for (; dir is not null; dir = dir.Parent)
        {
            var file = Path.Combine(dir.FullName, ".env");
            if (File.Exists(file))
            {
                Read(file);
                return;
            }
        }
    }

    private static void Read(string file)
    {
        foreach (var line in File.ReadAllLines(file))
        {
            var eq = line.IndexOf('=', StringComparison.Ordinal);
            if (string.IsNullOrWhiteSpace(line) || line.StartsWith('#') || eq < 0)
            {
                continue;
            }

            var key = line[..eq].Trim();
            var value = line[(eq + 1)..].Trim().Trim('"', '\'');
            if (Environment.GetEnvironmentVariable(key) is null && value.Length > 0)
            {
                Environment.SetEnvironmentVariable(key, value);
            }
        }
    }
}
