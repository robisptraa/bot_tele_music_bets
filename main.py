from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import yt_dlp
import asyncio
import os
import subprocess
import tempfile
import sys
from pyrogram import idle

# ===============================
# KREDENSIAL BOT
# ===============================
API_ID = 24222790
API_HASH = "7aaac582a1338b9054b09814d46c3520"
BOT_TOKEN = "8415124423:AAGXO4masGwOXQitRazpNFmfiYWdI4EdgdI"

app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
search_results = {}
playing_process = {} 

# ===============================
# UTILITY FUNCTIONS
# ===============================
async def run_in_executor(func, *args):
    return await asyncio.to_thread(func, *args)

def yt_search_sync(query, max_results=5):
    ydl_opts = {'format': 'bestaudio', 'quiet': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            entries = info.get('entries', [])
            return [{'title': e.get('title','Unknown'), 'url': e.get('webpage_url','')} for e in entries if e]
    except Exception as e:
        print(f"[ERROR] Saat mencari: {e}")
        return []

def download_audio(url):
    """Download audio ke file sementara"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'outtmpl': temp_file.name
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return temp_file.name
    except Exception as e:
        print(f"[ERROR] Saat download audio: {e}")
        return None

async def play_audio(chat_id, file_path):
    """Gunakan ffmpeg untuk memutar audio di voice chat"""
    if chat_id in playing_process:
        try: playing_process[chat_id].terminate()
        except: pass

    cmd = [
        "ffmpeg",
        "-i", file_path,
        "-f", "s16le",
        "-ar", "48000",
        "-ac", "2",
        "pipe:1"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    playing_process[chat_id] = proc
    print(f"▶️ Memutar audio di chat {chat_id}")

# ===============================
# HANDLER DEBUGGING
# ===============================
@app.on_raw_update()
async def raw_update_handler(client, update, users, chats):
    if update and hasattr(update, 'message'):
        try:
            update_text = update.message.text
            print(f"📡 UPDATE DITERIMA: Tipe: Message | Teks: {update_text[:30] if update_text else 'Non-Text'}")
        except Exception:
             print("📡 UPDATE DITERIMA: Tipe: Message (Tidak bisa mengambil teks)")
    elif update:
        print(f"📡 UPDATE DITERIMA: Tipe: {type(update).__name__}")


# ===============================
# HANDLER BOT
# ===============================
@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    print(f"✅ Handler START dipanggil oleh {message.from_user.id} di chat {message.chat.id}") 
    
    await message.reply(
        "🎵 **Selamat datang di ObetsMusicBot!**\n\n"
        "📝 Perintah:\n"
        "• /search <judul lagu> - Cari lagu\n"
        "• /stop - Hentikan musik\n"
        "• /ping - Cek status bot\n\n"
        "⚠️ Bot hanya bisa digunakan di grup dengan voice chat aktif!"
        "⚠️ Bot hanya bisa digunakan pada chat voice chat aktif!"
    )

@app.on_message(filters.command("search"))
async def search_handler(client: Client, message: Message):
    chat_id = message.chat.id
    query = " ".join(message.command[1:])
    
    if not query:
        await message.reply("❌ maaf Tolong tuliskan judul lagu dong setelah /search")
        return

    msg = await message.reply("🔍 Mencari lagu dulu dungs...")
    results = await run_in_executor(yt_search_sync, query, 5)
    
    if not results:
        await msg.edit("😢 Lagu nya ga ada nih.")
        return

    search_results[chat_id] = results
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {r['title'][:50]}", callback_data=f"play_{i}")]
        for i, r in enumerate(results)
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await msg.edit("🎤 Pilih lagunya dong:", reply_markup=markup)

@app.on_callback_query()
async def callback_query_handler(client: Client, cq):
    data = cq.data
    chat_id = cq.message.chat.id
    print(f"✅ Callback Query code Diterima: {data}")

    await cq.answer()

    if not data.startswith("play_"):
        return

    idx = int(data.split("_")[1])
    if chat_id not in search_results:
        await cq.message.edit_text("⚠️ Hasil pencarian kedaluwarsa, silakan /search ulang.")
        return

    song = search_results[chat_id][idx]
    await cq.message.edit_text(f"⏳ Memproses **{song['title']}**...")

    audio_file = await run_in_executor(download_audio, song['url'])
    if not audio_file:
        await cq.message.edit_text("❌ Gagal mendapatkan audio.")
        return

    await run_in_executor(play_audio, chat_id, audio_file)
    await cq.message.edit_text(f"▶️ Memutar: **{song['title']}**")

@app.on_message(filters.command("stop"))
async def stop_handler(client: Client, message: Message):
    chat_id = message.chat.id
    print(f"✅ Handler STOP dipanggil di chat {chat_id}")
    if chat_id in playing_process:
        try:
            playing_process[chat_id].terminate()
            del playing_process[chat_id]
            await message.reply("⏹️ Musik dihentikan.")
        except Exception as e:
            await message.reply(f"⚠️ Gagal menghentikan audio: {e}")
    else:
        await message.reply("⚠️ Tidak ada musik yang sedang diputar.")

@app.on_message(filters.command("ping"))
async def ping_handler(client: Client, message: Message):
    print(f"✅ Handler PING dipanggil oleh {message.from_user.id} di chat {message.chat.id}")
    await message.reply("🏓 Pong! Bot aktif.")

# ===============================
# MAIN
# ===============================
async def main():
    try:
        await app.start()
        me = await app.get_me()
        print(f"✅ mas BOT BERHASIL TERHUBUNG: Sebagai @{me.username}")
        print("🎵 Bot siap nya digunakan mas obi! Menunggu pesan...")
        await idle()
        await app.stop()
    except Exception as e:
        print(f"❌ KONEKSI GAGAL SAAT START: Pastikan API ID/HASH dan Token benar. Error: {e}")
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⚠️ Bot dihentikan oleh pemake")
