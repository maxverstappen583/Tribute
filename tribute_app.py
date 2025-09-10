#!/usr/bin/env python3
"""
tribute_bot.py
Single-file Flask + Discord app that:
 - Serves a tribute web page at /
 - Exposes /raw/thanks and /raw/glory plaintext endpoints
 - If DISCORD_TOKEN is provided in .env, runs a Discord bot with a /chikatto slash command
Usage:
  1) Create .env (example below)
  2) pip install -r requirements.txt
  3) python tribute_bot.py
"""

import os
import threading
import html as _html
import datetime
from dotenv import load_dotenv

# web
from flask import Flask, Response

# discord
import discord
from discord.ext import commands

load_dotenv()

# ===== ENV / CONFIG =====
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")  # REQUIRED for bot; if missing, bot won't start
GUILD_ID = os.getenv("GUILD_ID")            # optional (put guild/server id for instant command sync)
FRIEND_NAME = os.getenv("FRIEND_NAME", "chikatto")
YOUR_NAME = os.getenv("YOUR_NAME", "Max")
START_YEAR = os.getenv("START_YEAR", "2023")
END_YEAR = os.getenv("END_YEAR", "2025")
# default to the image link you provided
EMBED_IMAGE_URL = os.getenv("EMBED_IMAGE_URL", "https://i.postimg.cc/5y8PXNB6/9eee9a20dd4cdb333012e10346820c04.png")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "0") == "1"

# ===== Build two 200-word texts (guaranteed 200 words) =====
def _make_200_words(parts, pad_phrase):
    base = "".join(parts).strip()
    # small closing to help flow
    base += " I will keep you in my stories and in the quiet corners of my days."
    words = base.split()
    while len(words) < 200:
        words += pad_phrase.split()
    if len(words) > 200:
        words = words[:200]
    return " ".join(words)

thanks_parts = [
    "I want to thank you for being my friend in ways that feel too deep for simple sentences. ",
    "You arrived quietly and stayed through ordinary days and the storms, giving steadiness when I needed it most. ",
    "You listened like few ever do — patient, ready with a joke, a memory, a steady hand. ",
    "Your kindness was never loud; it was honest and constant. ",
    "You showed me how small moments could be sacred: the way you laughed at dumb jokes, the late-night messages that turned into safety, the silent understanding when words failed. ",
    "You trusted me with parts of yourself and made me feel seen. ",
    "Even in nothingness, your presence felt like home. ",
    "Those two years we shared — the risky plans, the quiet coffees, the terrible songs we both loved — shaped better parts of who I am. ",
    "I am thankful for every conversation, every shared silence, and every silly dare. ",
    "I will carry your kindness forward by being kinder to others, remembering the softness you taught me. ",
    "Goodbyes are wrong for what we had; instead I will say thank you for being my friend. ",
    "Thank you, chikatto, for everything you gave — for being ordinary and extraordinary all at once. ",
    "I miss you deeply and I will honor you in small, steady ways. "
]
THANKS_TEXT = _make_200_words(thanks_parts, "I remember you.")

glory_parts = [
    "You shone with a quiet brilliance that did not need an audience. ",
    "Your laugh was a comet that warmed the room, and your courage often hid behind gentle words. ",
    "You moved through life with a stubborn tenderness that made ordinary days feel elevated. ",
    "People who met you left with a lighter heart and a memory that kept returning like a favorite refrain. ",
    "Your choices spoke of loyalty; your actions wrote kindness into places others overlooked. ",
    "In your presence, small victories felt sacred and risks felt less lonely. ",
    "You carried both mischief and wisdom, sometimes in the same glance, and you taught others how to balance softness with grit. ",
    "To glorify you is to point to how you made people better — more open, more brave, more willing to try. ",
    "Your name will live in the echoes of laughter you started and the quiet courage you inspired. ",
    "Even now, the way you loved and fought for what mattered feels like a map for the rest of us. ",
    "You were a bright, restless light that never failed to move hearts. ",
    "Your story will be told in small rituals, in the songs we pick, in the promises we keep. ",
    "Rest in the honor you earned every day just by being yourself. "
]
GLORY_TEXT = _make_200_words(glory_parts, "You mattered.")

# ===== Flask web app =====
web_app = Flask(__name__)

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Tribute — %%FRIEND_NAME%%</title>
  <style>
    :root{ --bg1:#0f1724; --bg2:#1a2236; --gold:#d4af37; --muted:#bfc7d6 }
    body{ margin:0; font-family:Inter, system-ui, -apple-system, 'Segoe UI', Roboto, Arial; background: linear-gradient(180deg,var(--bg1),var(--bg2)); color:#eef2ff; display:flex; align-items:center; justify-content:center; min-height:100vh; }
    .wrap{ width:94%; max-width:980px; padding:28px; }
    .card{ background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(0,0,0,0.06)); border-radius:16px; padding:28px; box-shadow: 0 8px 30px rgba(2,6,23,0.6); border:1px solid rgba(255,255,255,0.03); }
    .hero{ display:flex; gap:24px; align-items:center; }
    .img{ width:200px; height:200px; border-radius:14px; overflow:hidden; flex:0 0 200px; border:6px solid rgba(212,175,55,0.92); background:#111; display:flex; align-items:center; justify-content:center; }
    .img img{ width:100%; height:100%; object-fit:cover; }
    h1{ margin:0; font-size:2.2rem; color:var(--gold); letter-spacing:0.6px; }
    .sub{ color:var(--muted); margin-top:6px; }
    .years{ color:var(--gold); font-weight:600; margin-top:6px; }
    .content{ margin-top:18px; display:grid; grid-template-columns:1fr 1fr; gap:18px; align-items:start; }
    .panel{ background:rgba(255,255,255,0.02); padding:16px; border-radius:12px; min-height:220px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.02); }
    .panel h3{ margin:0 0 8px 0; color:#ffdc80; }
    .muted{ color:var(--muted); font-size:0.95rem; white-space:pre-wrap; line-height:1.42; }
    footer{ margin-top:18px; text-align:center; color:#a8b0c6; font-size:0.95rem; }
    @media (max-width:820px){ .hero{ flex-direction:column; align-items:center; } .content{ grid-template-columns:1fr; } .img{ width:160px; height:160px; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card" role="main">
      <div class="hero">
        <div class="img" aria-hidden="true">
          <img src="%%IMAGE_URL%%" alt="Photo of %%FRIEND_NAME%%">
        </div>
        <div>
          <h1 id="title">In Loving Memory — %%FRIEND_NAME%%</h1>
          <div class="sub">Forever in our stories and quiet moments.</div>
          <div class="years">%%START%% — %%END%%</div>
        </div>
      </div>
      <div class="content">
        <div class="panel">
          <h3>Thank you</h3>
          <div class="muted">%%THANKS_HTML%%</div>
        </div>
        <div class="panel">
          <h3>Remembering & Glorifying</h3>
          <div class="muted">%%GLORY_HTML%%</div>
        </div>
      </div>
      <footer>Made with love — keep %%FRIEND_NAME%% close. — %%YOUR_NAME%%</footer>
    </div>
  </div>
</body>
</html>
"""

@web_app.route("/")
def index():
    # escape text into safe HTML with preserved line breaks
    thanks_html = _html.escape(THANKS_TEXT).replace("\n", "<br>")
    glory_html = _html.escape(GLORY_TEXT).replace("\n", "<br>")
    page = (HTML_TEMPLATE
            .replace("%%IMAGE_URL%%", EMBED_IMAGE_URL)
            .replace("%%FRIEND_NAME%%", _html.escape(FRIEND_NAME))
            .replace("%%YOUR_NAME%%", _html.escape(YOUR_NAME))
            .replace("%%START%%", _html.escape(START_YEAR))
            .replace("%%END%%", _html.escape(END_YEAR))
            .replace("%%THANKS_HTML%%", thanks_html)
            .replace("%%GLORY_HTML%%", glory_html)
           )
    return Response(page, mimetype="text/html; charset=utf-8")

@web_app.route("/raw/thanks")
def raw_thanks():
    return Response(THANKS_TEXT, mimetype="text/plain; charset=utf-8")

@web_app.route("/raw/glory")
def raw_glory():
    return Response(GLORY_TEXT, mimetype="text/plain; charset=utf-8")

# ===== Discord bot (slash command) =====
def start_discord_bot():
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN not set — skipping Discord bot startup.")
        return

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    # create slash command
    @bot.tree.command(name="chikatto", description=f"Tribute to {FRIEND_NAME}")
    async def _chikatto(interaction: discord.Interaction):
        # build embed
        embed = discord.Embed(
            title=f"In Loving Memory — {FRIEND_NAME}",
            description=f"**Thank you**\n\n{THANKS_TEXT}\n\n**Remembering & Glorifying**\n\n{GLORY_TEXT}",
            color=0xD4AF37,
            timestamp=datetime.datetime.utcnow()
        )
        # set main image and a small footer
        embed.set_image(url=EMBED_IMAGE_URL)
        embed.set_footer(text=f"— {YOUR_NAME} • {START_YEAR}-{END_YEAR}")
        # send (non-ephemeral so it shows in channel)
        try:
            await interaction.response.send_message(embed=embed)
        except Exception:
            # fallback if initial response fails
            await interaction.followup.send(embed=embed)

    @bot.event
    async def on_ready():
        print(f"Discord bot logged in as {bot.user} (id: {bot.user.id})")
        # sync commands to guild if provided for instant availability, else global sync
        try:
            if GUILD_ID:
                guild = discord.Object(id=int(GUILD_ID))
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"Synced slash commands to GUILD {GUILD_ID}")
            else:
                await bot.tree.sync()
                print("Synced global slash commands (can take up to 1 hour to appear).")
        except Exception as e:
            print("Command sync error:", e)

    # Run the bot (blocking call)
    bot.run(DISCORD_TOKEN)

# ===== Main: run Flask in a thread and optionally run Discord bot =====
def run_flask():
    # disable reloader when running in thread
    web_app.run(host=HOST, port=PORT, debug=DEBUG, use_reloader=False)

if __name__ == "__main__":
    print("Starting tribute web server at http://%s:%s" % (HOST, PORT))
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # start discord bot in main thread (blocking) if token present
    if DISCORD_TOKEN:
        print("Discord token found — starting bot. If you'd prefer only the web app, remove DISCORD_TOKEN from .env.")
        start_discord_bot()
    else:
        # keep the main thread alive while Flask runs in background
        try:
            while True:
                threading.Event().wait(3600)
        except KeyboardInterrupt:
            print("Shutting down.")
