import os
import json
import glob
import time
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from yt_dlp import YoutubeDL
import threading
import sys
import requests
from PIL import Image  

CURRENT_VERSION = "0.0.5"
LICENSE_KEY = "LICENSE-001"

UPDATE_CHECK_URL = "https://raw.githubusercontent.com/ThoCon199/MakeByThoCon/main/tool_update.json"
SYSTEM_STATUS_URL = "https://raw.githubusercontent.com/ThoCon199/MakeByThoCon/main/system_status.json"
LICENSE_DB_URL = "https://raw.githubusercontent.com/ThoCon199/MakeByThoCon/main/license_db.json"

DOWNLOAD_LOG = "downloaded_videos.json"
LAST_CHANNEL_FILE = "last_channel.txt"

# Đường dẫn công cụ Deno và FFmpeg
FFMPEG_DIR = r"C:\ffmpeg\bin"
DENO_PATH = r"C:\ffmpeg\bin\deno.exe"

def check_system_and_license():
    try:
        import time

        cache = f"?t={int(time.time())}"

        r = requests.get(SYSTEM_STATUS_URL + cache, timeout=5)
        system_data = r.json()

        if system_data.get("disable_all"):
            messagebox.showerror(
                "Thông báo",
                system_data.get("message", "Tool đã bị vô hiệu hóa.")
            )
            sys.exit()

        if system_data.get("force_update"):

            latest = system_data.get("latest_version")

            if latest != CURRENT_VERSION:
                messagebox.showerror(
                    "Cập nhật bắt buộc",
                    f"Phiên bản mới: {latest}\nVui lòng cập nhật tool."
                )
                sys.exit()

        r2 = requests.get(LICENSE_DB_URL + cache, timeout=5)
        license_db = r2.json()

        if LICENSE_KEY not in license_db:
            messagebox.showerror("License lỗi", "License không tồn tại.")
            sys.exit()

        if not license_db[LICENSE_KEY].get("active", False):
            messagebox.showerror(
                "License bị thu hồi",
                license_db[LICENSE_KEY].get("note", "Liên hệ admin.")
            )
            sys.exit()

    except Exception as e:
        messagebox.showerror(
            "Lỗi xác minh",
            f"Không thể xác minh license.\n{e}"
        )
        sys.exit()


def auto_update():
    try:
        import time

        cache = f"?t={int(time.time())}"

        r = requests.get(UPDATE_CHECK_URL + cache, timeout=5)
        data = r.json()

        latest = data.get("latest_version")

        if latest != CURRENT_VERSION:

            messagebox.showinfo(
                "Update",
                data.get("message", "Updating...")
            )

            new_code = requests.get(data["update_url"]).text

            current_file = sys.argv[0]

            with open(current_file, "w", encoding="utf-8") as f:
                f.write(new_code)

            messagebox.showinfo(
                "Update",
                "Đã cập nhật xong. Tool sẽ khởi động lại."
            )

            os.execv(sys.executable, ['python'] + sys.argv)

    except Exception as e:
        print("Update check failed:", e)


def send_channel_to_gsheet(channel_url):
    form_url = "https://docs.google.com/forms/u/0/d/e/1FAIpQLSe7qd0SQ7euJwylcQw6_1nB60rM49OVNJxr0RJIh1VRzKEwjg/formResponse"

    data = {
        "entry.465162591": channel_url
    }

    try:
        requests.post(form_url, data=data)
    except:
        pass


def get_base_ydl_opts():
    """Hàm cấu hình chung cho yt-dlp"""
    return {
        'ffmpeg_location': FFMPEG_DIR,
        'ignoreerrors': True,
        'no_warnings': True,
    }


def load_downloaded():
    if os.path.exists(DOWNLOAD_LOG):
        try:
            with open(DOWNLOAD_LOG, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_downloaded(video_ids):
    with open(DOWNLOAD_LOG, "w", encoding="utf-8") as f:
        json.dump(video_ids, f, indent=2)


def ensure_output_folders():
    folders = [
        "output/video",
        "output/thumb",
        "output/tiêu đề",
        "output/mô tả",
        "output/video_tags",
        "output/channel_info",
        "output/json"
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)


def safe_filename(name):
    return "".join(c for c in name if c.isalnum() or c in " _-").strip()


def download_file(url, save_path):
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False


def download_channel_info(channel_url, log_callback):
    log_callback("📡 Đang lấy thông tin kênh...")

    ydl_opts = {
        **get_base_ydl_opts(),
        'quiet': True,
        'extract_flat': True,
        'dump_single_json': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        if not info:
            log_callback("⚠️ Không lấy được thông tin kênh.")
            return

        ensure_output_folders()

        channel_name = (
            info.get("channel")
            or info.get("uploader")
            or info.get("title")
            or "unknown_channel"
        )

        safe_name = safe_filename(channel_name)
        description = info.get("description", "")
        tags = info.get("tags", [])

        # Avatar
        avatar_url = None
        thumbnails = info.get("thumbnails", [])
        if thumbnails:
            avatar_url = thumbnails[-1].get("url")

        # Banner
        banner_url = None
        banner_candidates = info.get("banners") or info.get("channel_banners") or []
        if banner_candidates:
            banner_url = banner_candidates[-1].get("url")

        # Lưu description
        with open(f"output/channel_info/{safe_name}_description.txt", "w", encoding="utf-8") as f:
            f.write(description)

        # Lưu tags
        if tags:
            with open(f"output/channel_info/{safe_name}_tags.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(tags))

        # Lưu raw json
        with open(f"output/channel_info/{safe_name}_full.json", "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        if avatar_url and download_file(avatar_url, f"output/channel_info/{safe_name}_avatar.jpg"):
            log_callback("✅ Đã tải avatar kênh")

        if banner_url and download_file(banner_url, f"output/channel_info/{safe_name}_banner.jpg"):
            log_callback("✅ Đã tải banner kênh")

        log_callback("✅ Đã lưu thông tin kênh")


def download_video(video_url, log_callback, download_format):
    temp_outtmpl = '%(id)s.%(ext)s'

    ydl_opts = {
        **get_base_ydl_opts(),
        'outtmpl': temp_outtmpl,
        'writethumbnail': True,
        'quiet': False,
        'extractor_args': {'youtube': {'player_client': ['android']}},
    }

    if download_format == 'mp4':
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
        })
    else:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        if not info:
            raise Exception("Không thể trích xuất thông tin video.")

        video_id = info.get('id')
        title = info.get('title', '')
        description = info.get('description', '')
        video_tags = info.get('tags', [])

        upload_date_raw = info.get('upload_date')
        if upload_date_raw:
            upload_date = datetime.strptime(upload_date_raw, "%Y%m%d")
            date_prefix = upload_date.strftime("%Y%m%d")
        else:
            date_prefix = "unknown_date"

        ensure_output_folders()

        # Dời file sau khi tải hoàn tất
        for file in glob.glob(f"{video_id}.*"):
            ext = file.split('.')[-1].lower()

            if ext in ['mp4', 'webm', 'mkv', 'mp3']:
                new_name = f"{date_prefix}_{video_id}.{ext}"
                target = os.path.join("output/video", new_name)
                try:
                    os.replace(file, target)
                except Exception:
                    pass

            elif ext in ['jpg', 'png', 'webp', 'jpeg']:
                new_name = f"{date_prefix}_{video_id}.jpg"
                target = os.path.join("output/thumb", new_name)
                try:
                    with Image.open(file) as img:
                        rgb_img = img.convert('RGB')
                        rgb_img.save(target, 'JPEG')
                    if os.path.exists(file):
                        os.remove(file)
                except Exception:
                    fallback_name = f"{date_prefix}_{video_id}.{ext}"
                    target_fallback = os.path.join("output/thumb", fallback_name)
                    try:
                        os.replace(file, target_fallback)
                    except Exception:
                        pass

            elif ext == "json":
                new_name = f"{date_prefix}_{video_id}.{ext}"
                target = os.path.join("output/json", new_name)
                try:
                    os.replace(file, target)
                except Exception:
                    pass

        # Title
        title_file = f"{date_prefix}_{video_id}.txt"
        with open(os.path.join("output/tiêu đề", title_file), "w", encoding="utf-8") as f:
            f.write(title)

        # Description
        with open(os.path.join("output/mô tả", title_file), "w", encoding="utf-8") as f:
            f.write(description)

        # Tags
        if video_tags:
            with open(os.path.join("output/video_tags", title_file), "w", encoding="utf-8") as f:
                f.write("\n".join(video_tags))

        log_callback(f"✅ Tải xong: {title}")
        return video_id


def fetch_video_list(channel_url, mode, log_callback):
    sort_map = {'newest': 'date', 'oldest': 'date'}

    ydl_opts = {
        **get_base_ydl_opts(),
        'quiet': True,
        'extract_flat': True,
        'dump_single_json': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        log_callback("📥 Đang lấy danh sách video...")

        target_url = f"{channel_url.rstrip('/')}/videos"
        info = ydl.extract_info(target_url, download=False)
        entries = info.get("entries", []) if info else []

        if mode == "oldest":
            entries.reverse()

        return entries, len(entries)


def start_download():
    def log(msg):
        root.after(0, lambda: log_box.insert(tk.END, msg + "\n"))
        root.after(0, lambda: log_box.see(tk.END))

    def update_status(text):
        root.after(0, lambda: status_label.config(text=text))

    channel_url = url_entry.get().strip()

    if not channel_url:
        messagebox.showerror("Lỗi", "Vui lòng dán link kênh YouTube.")
        return

    send_channel_to_gsheet(channel_url)

    mode = mode_var.get()
    download_format = format_var.get()

    try:
        limit = int(limit_entry.get().strip())
        if limit <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Lỗi", "Số lượng video phải là số nguyên dương.")
        return

    try:
        with open(LAST_CHANNEL_FILE, "w", encoding="utf-8") as f:
            f.write(channel_url)
    except Exception:
        pass

    log(f"\n🔗 Kênh: {channel_url}")
    log(f"⚙️ Chế độ: {mode}")
    log(f"🎯 Số lượng: {limit}")
    log(f"📁 Định dạng: {download_format}\n")

    downloaded = load_downloaded()

    try:
        download_channel_info(channel_url, log)
        entries, total = fetch_video_list(channel_url, mode, log)

        # 1. Đếm tổng số video ĐÃ TẢI của nguồn này (bao gồm cả các lần trước)
        # Tìm các video của kênh này đã có trong danh sách 'downloaded'
        already_downloaded_count = sum(1 for entry in entries if entry.get("id") in downloaded)

        # Cập nhật Label màu xanh ngay khi lấy xong danh sách: (Tổng đã tải / Tổng video của kênh)
        update_status(f"🔢 Đã tải: {already_downloaded_count} / {total} video")

        current_session_count = 0  # Số video tải thành công trong LẦN CHẠY NÀY

        for entry in entries:
            # Dừng nếu đã tải đủ số lượng yêu cầu của lần này
            if current_session_count >= limit:
                break

            vid = entry.get("id")
            if not vid:
                continue

            video_url = f"https://www.youtube.com/watch?v={vid}"

            # Bỏ qua video đã tải ở các lần trước
            if vid in downloaded:
                continue

            # 2. Đếm lượt tải hiện tại của LẦN CHẠY NÀY (chạy từ 1 đến limit)
            run_index = current_session_count + 1
            
            # Log màu đen: Hiện tiến trình yêu cầu của lần chạy này (ví dụ: 1/15, 2/15)
            log(f"⬇️ ({run_index}/{limit}) Đang tải: {entry.get('title', vid)}")

            try:
                vid_id = download_video(video_url, log, download_format)
                if vid_id:
                    downloaded.append(vid_id)
                    save_downloaded(downloaded)
                    
                    current_session_count += 1
                    already_downloaded_count += 1
                    
                    # Cập nhật Label màu xanh: Tăng dần số tổng video đã tải của kênh (ví dụ: 16/300)
                    update_status(f"🔢 Đã tải: {already_downloaded_count} / {total} video")
                    
                time.sleep(2)
            except Exception as e:
                log(f"❌ Lỗi tải {vid}: {e}")

        log(f"\n✅ Đã tải thành công {current_session_count} video. Hoàn tất!")

    except Exception as e:
        root.after(0, lambda: messagebox.showerror("Lỗi", f"Không thể lấy danh sách: {e}"))

def on_start_click():
    threading.Thread(target=start_download, daemon=True).start()


check_system_and_license()
auto_update()


root = tk.Tk()
root.title("YouTube Channel Downloader")
root.geometry("600x620")
root.resizable(False, False)

status_label = tk.Label(root, text="🔢 Đã tải: 0 / 0 video", fg="blue")
status_label.pack(pady=(5, 5))

tk.Label(root, text="🔗 Dán link kênh YouTube:").pack(pady=(5, 2))

url_entry = tk.Entry(root, width=70)
url_entry.pack(pady=(0, 10))

try:
    with open(LAST_CHANNEL_FILE, "r", encoding="utf-8") as f:
        url_entry.insert(0, f.read().strip())
except Exception:
        pass

tk.Label(root, text="📌 Chọn chế độ tải:").pack()

mode_var = tk.StringVar(value="newest")
frm = tk.Frame(root)
frm.pack()
tk.Radiobutton(frm, text="Mới nhất", variable=mode_var, value="newest").grid(row=0, column=0, padx=10)
tk.Radiobutton(frm, text="Cũ nhất", variable=mode_var, value="oldest").grid(row=0, column=1, padx=10)

tk.Label(root, text="🎵 Chọn định dạng tải:").pack(pady=(10, 2))

format_var = tk.StringVar(value="mp4")
frm_format = tk.Frame(root)
frm_format.pack()
tk.Radiobutton(frm_format, text="MP4 (video)", variable=format_var, value="mp4").grid(row=0, column=0, padx=10)
tk.Radiobutton(frm_format, text="MP3 (âm thanh)", variable=format_var, value="mp3").grid(row=0, column=1, padx=10)

tk.Label(root, text="🔢 Số lượng video muốn tải:").pack(pady=(10, 2))

limit_entry = tk.Entry(root, width=10)
limit_entry.insert(0, "1000")
limit_entry.pack(pady=(0, 10))

tk.Button(
    root,
    text="▶️ Bắt đầu tải",
    command=on_start_click,
    bg="#4CAF50",
    fg="white",
    width=20
).pack(pady=15)

log_box = tk.Text(root, height=15, width=80)
log_box.pack(padx=10, pady=10)

root.mainloop()
