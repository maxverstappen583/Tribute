#!/usr/bin/env python3
"""
tribute_bot.py
Single-file Flask + Discord tribute app.

Features:
 - Serves a gentle tribute page at "/" (uses PORT env on hosts like Render)
 - Provides /raw/thanks and /raw/glory text endpoints
 - Runs a Discord bot (if DISCORD_TOKEN is set) with:
     - Slash command: /chikatto
     - Prefix command: !chikatto
     - Slash command: /start    (shows info + link to web page if BASE_URL set)
 - All configuration via environment (.env) with safe defaults.

Usage (local):
  1) pip install -r requirements.txt
  2) create a .env with DISCORD_TOKEN (and optionally set other variables)
  3) python tribute_bot.py

Recommended env vars (example at bottom of this file)
"""

import os
import threading
import datetime
import html as _html
from dotenv import load_dotenv

# --- web ---
from flask import Flask, Response

# --- discord ---
import discord
from discord.ext import commands

load_dotenv()

# ===== CONFIG (env or defaults) =====
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")            # REQUIRED for the bot to run
GUILD_ID = os.getenv("GUILD_ID")                      # optional: set to your server ID for instant slash sync
BASE_URL = os.getenv("BASE_URL", "")                  # optional: public URL of the web page (helpful in /start)
FRIEND_NAME = os.getenv("FRIEND_NAME", "chikatto")
YOUR_NAME = os.getenv("YOUR_NAME", "Aadi")
START_YEAR = os.getenv("START_YEAR", "2023")
END_YEAR = os.getenv("END_YEAR", "2025")
EMBED_IMAGE_URL = os.getenv(
    "EMBED_IMAGE_URL",
    "https://i.postimg.cc/5y8PXNB6/9eee9a20dd4cdb333012e10346820c04.png"
)
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", os.getenv("RENDER_PORT", "5000")))  # free override for Render (RENDER_PORT sometimes set)
DEBUG = os.getenv("DEBUG", "0") == "1"

# ===== Helper: build exact-200-word texts =====
def _make_200_words(parts, pad_phrase):
    """Join `parts`, append a small closing, then pad/trim to exactly 200 words."""
    base = "".join(parts).strip()
    base += " I will keep you in my stories and in the quiet corners of my days."
    words = base.split()
    # pad
    while len(words) < 200:
        words += pad_phrase.split()
    # trim
    if len(words) > 200:
        words = words[:200]
    return " ".join(words)

# thank-you text parts
_thanks_parts = [
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
THANKS_TEXT = _make_200_words(_thanks_parts, "I remember you.")

# glorify text parts
_glory_parts = [
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
GLORY_TEXT = _make_200_words(_glory_parts, "You mattered.")

# ===== Flask web app (simple, self-contained) =====
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
    thanks_html = _html.escape(THANKS_TEXT).replace("\n", "<br>")
    glory_html = _html.escape(GLORY_TEXT).replace("\n", "<br>")
    page = (HTML_TEMPLATE
            .replace("%%IMAGE_URL%%", _html.escape(EMBED_IMAGE_URL))
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

# ===== Discord bot: both slash + prefix commands =====
def start_discord_bot():
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN not found — skipping Discord bot startup.")
        return

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    def build_tribute_embed():
        """Create a single embed containing both 200-word texts."""
        title = f"🌹 Remembering {FRIEND_NAME} ({START_YEAR} – {END_YEAR})"
        description = (
            "**Thank you**\n\n"
            + THANKS_TEXT
            + "\n\n**Remembering & Glorifying**\n\n"
            + GLORY_TEXT
        )
        embed = discord.Embed(
            title=title,
            description=description,
            color=0xD4AF37,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_image(url=EMBED_IMAGE_URL)
        embed.set_footer(text=f"— {YOUR_NAME} • {START_YEAR}-{END_YEAR}")
        return embed

    # Slash command: /chikatto
    @bot.tree.command(name="chikatto", description=f"Tribute to {FRIEND_NAME}")
    async def _chikatto(interaction: discord.Interaction):
        embed = build_tribute_embed()
        try:
            await interaction.response.send_message(embed=embed)
        except Exception:
            # fallback if initial response fails
            try:
                await interaction.followup.send(embed=embed)
            except Exception as e:
                print("Failed to send /chikatto embed:", e)

    # Prefix command: !chikatto
    @bot.command(name="chikatto")
    async def chikatto_prefix(ctx: commands.Context):
        embed = build_tribute_embed()
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            print("Failed to send !chikatto embed:", e)

    # Slash command: /start (quick info)
    @bot.tree.command(name="start", description="Show tribute bot info & link")
    async def _start(interaction: discord.Interaction):
        desc = (
            f"Tribute bot ready. Use `/chikatto` or `!chikatto` to post the tribute for **{FRIEND_NAME}**.\n\n"
        )
        if BASE_URL:
            desc += f"Open the tribute page: {BASE_URL}\n\n"
        desc += "If you manage this bot, set environment variables (DISCORD_TOKEN, FRIEND_NAME, etc.) in your host."
        embed = discord.Embed(title="🌟 Tribute Bot Ready", description=desc, color=0x8AB4F8, timestamp=datetime.datetime.utcnow())
        embed.set_footer(text=f"— {YOUR_NAME}")
        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as e:
                print("Failed to send /start reply:", e)

    @bot.event
    async def on_ready():
        print(f"Discord bot logged in as {bot.user} (id: {bot.user.id})")
        # Try to sync commands. If GUILD_ID set, sync to that guild for instant availability.
        try:
            if GUILD_ID:
                guild_obj = discord.Object(id=int(GUILD_ID))
                bot.tree.copy_global_to(guild=guild_obj)
                await bot.tree.sync(guild=guild_obj)
                print(f"Synced slash commands to guild {GUILD_ID}")
            else:
                await bot.tree.sync()
                print("Synced global slash commands (may take up to 1 hour to appear globally).")
        except Exception as e:
            print("Slash command sync warning:", e)

    # Run bot (blocking)
    bot.run(DISCORD_TOKEN)

# ===== Main: run Flask in a background thread, optionally run Discord bot =====
def run_flask():
    # When running in a thread, disable reloader to avoid double-starting
    web_app.run(host=HOST, port=PORT, debug=DEBUG, use_reloader=False)

if __name__ == "__main__":
    print(f"Starting tribute web server at http://{HOST}:{PORT}  (friend: {FRIEND_NAME})")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    if DISCORD_TOKEN:
        print("Discord token present — starting the Discord bot (slash + prefix commands).")
        start_discord_bot()
    else:
        print("No DISCORD_TOKEN found — bot disabled. Only the web page is running.")
        try:
            # Keep running while Flask thread serves
            while True:
                threading.Event().wait(3600)
        except KeyboardInterrupt:
            print("Shutting down.")
