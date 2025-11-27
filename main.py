import os
import asyncio
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import DocumentAttributeVideo
from moviepy.editor import VideoFileClip

# ==============================
# CONFIG
# ==============================
API_ID = 22821829          # ganti
API_HASH = "c276aee836576d14cf89a1b96b94be65"    # ganti
SESSION = "bot_session"

CHANNEL_ID = -1002946957408   # channel source
TARGET_CHANNEL = "https://t.me/+RVVnazOHU2UzZTRh"  # channel tujuan

START = 2300
END = 5000

PARALLEL_LIMIT = 5      # jumlah paralel download/compress/upload
COMPRESS_LIMIT_MB = 500 # compress jika > 500MB

# ==============================
client = TelegramClient(SESSION, API_ID, API_HASH)

sem = asyncio.Semaphore(PARALLEL_LIMIT)


# ======================================================
# UTIL: get file size
# ======================================================
def get_size_mb(path):
    return os.path.getsize(path) / (1024 * 1024)


# ======================================================
# COMPRESS VIDEO
# ======================================================
async def compress_video(input_file, output_file):
    print(f"[COMPRESS] Mulai compress: {input_file}")

    clip = VideoFileClip(input_file)
    clip.write_videofile(
        output_file,
        codec="libx264",
        audio_codec="aac",
        bitrate="1200k"  # bisa dinaik/turunkan
    )
    clip.close()

    print(f"[COMPRESS] Selesai compress → {output_file}")


# ======================================================
# PROCESS EACH MEDIA
# ======================================================
async def process_media(message):
    async with sem:
        try:
            if not message.media:
                print(f"[SKIP] ID {message.id} tidak ada media.")
                return

            print(f"[DOWNLOAD] ID {message.id}")

            file_path = await message.download_media()
            size_mb = get_size_mb(file_path)

            print(f"[INFO] ID {message.id} - Size: {size_mb:.2f} MB")

            # ======================================
            # COMPRESS jika > 500MB
            # ======================================
            final_path = file_path
            if size_mb > COMPRESS_LIMIT_MB:
                print(f"[COMPRESS] ID {message.id} > 500MB → compressing...")
                compressed = file_path.replace(".", "_compressed.")
                await compress_video(file_path, compressed)
                final_path = compressed

            # ======================================
            # UPLOAD
            # ======================================
            try:
                print(f"[UPLOAD] ID {message.id}")
                await client.send_file(
                    TARGET_CHANNEL,
                    final_path,
                    caption=f"ID {message.id}"
                )
                print(f"[DONE] ID {message.id} selesai upload!")

            except FloodWaitError as e:
                print(f"[FLOOD WAIT] Menunggu {e.seconds} detik...")
                await asyncio.sleep(e.seconds)
                await client.send_file(
                    TARGET_CHANNEL,
                    final_path,
                    caption=f"ID {message.id}"
                )

            # Bersihkan file
            try:
                os.remove(file_path)
                if file_path != final_path:
                    os.remove(final_path)
            except:
                pass

        except Exception as e:
            print(f"[ERROR] ID {message.id} → {e}")


# ======================================================
# AUTO PROCESS RANGE
# ======================================================
async def start_range():
    channel = await client.get_entity(CHANNEL_ID)

    tasks = []

    for msg_id in range(START, END + 1):
        try:
            msg = await client.get_messages(channel, ids=msg_id)
            if not msg:
                print(f"[NOT FOUND] {msg_id}")
                continue

            tasks.append(asyncio.create_task(process_media(msg)))

        except Exception as e:
            print(f"[ERROR] Tidak bisa ambil {msg_id}: {e}")

    # Jalankan paralel
    await asyncio.gather(*tasks)
    print("\n=== SELESAI SEMUA RANGE ===")


# ======================================================
# MAIN
# ======================================================
async def main():
    await client.start()
    print("BOT PARAREL RUNNING...")

    await start_range()

    print("Semua proses selesai!")
    await client.run_until_disconnected()


client.loop.run_until_complete(main())
