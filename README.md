# Media-to-IA

A Python tool to download media (YouTube playlists, videos, and more) and archive them on the Internet Archive.

## 🎯 Features

- Download media from various sources (primary focus: YouTube playlists)
- Automatically upload to Internet Archive
- Track completed uploads in `completed.json`
- Clean up local files after successful upload
- Resume capability for interrupted uploads
- Support for multiple media types

## 📋 Requirements

- Python 3.6+
- `yt-dlp` for media downloading
- `internetarchive` Python library
- Internet Archive account

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/Dhdhmdhdhddh/Media-to-IA.git
cd Media-to-IA
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Internet Archive credentials:
```bash
ia configure
```

## 📖 Usage

### Basic Usage

```bash
python downloader.py "<MEDIA_URL>"
```

### Advanced Usage

```bash
python downloader.py "<MEDIA_URL>" [custom_name] [max_mb]
```

### Parameters

- **`<MEDIA_URL>`** (required): URL of media to download
  - YouTube playlist: `https://www.youtube.com/playlist?list=PLxxxxxx`
  - YouTube video: `https://www.youtube.com/watch?v=xxxxx`
  - Other supported formats via yt-dlp
- **`[custom_name]`** (optional): Custom name for the Internet Archive collection
  - Default: Auto-generated from media title
- **`[max_mb]`** (optional): Maximum file size limit in MB
  - Default: No limit

### Examples

```bash
# Download YouTube playlist with default settings
python downloader.py "https://www.youtube.com/playlist?list=PLxxxxxx"

# Download with custom collection name
python downloader.py "https://www.youtube.com/playlist?list=PLxxxxxx" "My Collection"

# Download with size limit (500 MB max)
python downloader.py "https://www.youtube.com/playlist?list=PLxxxxxx" "My Collection" 500

# Download other media types
python downloader.py "https://www.youtube.com/watch?v=xxxxx" "Single Video"
```

## 🔄 How It Works

1. **Download Phase**: Media is downloaded from the specified source using yt-dlp
2. **Upload Phase**: Downloaded files are uploaded to Internet Archive
3. **Tracking**: Upload information is stored in `completed.json` for future reference
4. **Cleanup**: Local files are automatically deleted after successful upload

## 📊 Output

- Console output with upload statistics
- Direct link to the collection on archive.org
- Entry in `completed.json` with metadata

## 📁 Project Structure

```
Media-to-IA/
├── downloader.py       # Main script
├── requirements.txt    # Python dependencies
├── completed.json      # Tracking file (auto-generated)
└── README.md          # This file
```

## ⚙️ Configuration

Internet Archive credentials are stored via `ia configure`. Ensure your account has proper permissions to upload content.

## 📝 Notes

- Media files are deleted locally after successful upload
- Check `completed.json` to see upload history
- Ensure the media source is publicly accessible for downloading
- Supports any media type that yt-dlp can handle

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## ⚠️ Disclaimer

Only download and archive content you have the right to distribute. Respect copyright laws and the terms of service of media platforms.
