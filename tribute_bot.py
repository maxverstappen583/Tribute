import os
from threading import Thread
from flask import Flask, render_template_string, request
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from dotenv import load_dotenv

# --- Environment ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
BASE_URL = os.getenv("BASE_URL", "").strip()
PORT = int(os.getenv("PORT", 5000))

# --- Flask app setup ---
app = Flask(__name__)

# --- Visitor counter (simple file-based) ---
counter_file = "counter.txt"

def get_and_increment_counter():
    # Create file if it doesn't exist
    if not os.path.exists(counter_file):
        with open(counter_file, "w") as f:
            f.write("0")
    # Read, increment, write
    with open(counter_file, "r+") as f:
        content = f.read().strip()
        count = int(content) if content.isdigit() else 0
        count += 1
        f.seek(0)
        f.write(str(count))
        f.truncate()
    return count

def get_current_counter():
    if not os.path.exists(counter_file):
        return 0
    with open(counter_file, "r") as f:
        content = f.read().strip()
        return int(content) if content.isdigit() else 0

# --- Tribute text (personalized: Max -> Chikatto) ---
sad_tribute_text = (
    "Today, we remember not just the person Chikatto was, but the light he brought into every life he touched. "
    "His laughter, his kindness, and his unwavering spirit will forever echo in our hearts. "
    "The world feels quieter without him, yet his presence lingers in the memories we hold dear. "
    "Though the pain of his absence is heavy, I, Max, find comfort in knowing that his story lives on in each of us. "
    "This page stands as a testament to the love, respect, and gratitude we feel — a small offering to honor a life that meant so much. "
    "Rest peacefully, Chikatto. You will never be forgotten."
)

# --- Flask route: tribute page ---
@app.route("/")
def tribute_page():
    visitor_number = get_and_increment_counter()
    open_section = request.args.get("open", "")  # accepts q1, q2, q3 for auto-expand
    return render_template_string(f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>In Loving Memory of Chikatto</title>
        <style>
            :root {{
                --bg: #0d0d0d;
                --panel: #1a1a1a;
                --panel-2: #141414;
                --accent: #ff6f61;
                --header: #2b0000;
                --text: #f5f5f5;
                --muted: #aaaaaa;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', system-ui, -apple-system, Roboto, Arial, sans-serif;
                text-align: center;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
            }}
            header {{
                background-color: var(--header);
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.5);
                position: sticky;
                top: 0;
                z-index: 1;
            }}
            h1 {{
                color: var(--accent);
                margin: 0;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            .pfp {{
                border-radius: 50%;
                margin: 20px auto 10px;
                border: 4px solid var(--accent);
                width: 180px;
                height: 180px;
                object-fit: cover;
                display: block;
            }}
            .intro {{
                max-width: 760px;
                margin: 0 auto 10px;
                line-height: 1.6;
                padding: 0 16px;
            }}
            /* Candle */
            .candle {{
                position: relative;
                width: 44px;
                height: 112px;
                background: rgba(255,255,255,0.12);
                margin: 10px auto 8px;
                border-radius: 10px;
                box-shadow: inset 0 0 10px rgba(255,255,255,0.08);
            }}
            .flame {{
                position: absolute;
                top: -34px;
                left: 50%;
                width: 22px;
                height: 32px;
                background: radial-gradient(circle, #ffec85 0%, #ffae34 60%, rgba(255,174,52,0) 100%);
                border-radius: 50%;
                transform: translateX(-50%);
                animation: flicker 1.6s infinite ease-in-out;
                filter: drop-shadow(0 0 10px rgba(255, 170, 60, 0.6))
                        drop-shadow(0 0 18px rgba(255, 220, 150, 0.4));
            }}
            @keyframes flicker {{
                0%   {{ transform: translateX(-50%) scale(1);   opacity: 1;   }}
                35%  {{ transform: translateX(-50%) scale(1.06); opacity: 0.9; }}
                60%  {{ transform: translateX(-50%) scale(0.98); opacity: 1;   }}
                100% {{ transform: translateX(-50%) scale(1.03); opacity: 0.92;}}
            }}
            .section {{
                max-width: 760px;
                margin: 6px auto 24px;
                text-align: left;
                padding: 0 16px;
            }}
            .question {{
                background-color: var(--panel);
                padding: 14px 16px;
                margin: 12px 0 0;
                border-radius: 10px;
                cursor: pointer;
                font-weight: 600;
                color: var(--accent);
                transition: background 0.3s, transform 0.15s;
                user-select: none;
            }}
            .question:hover {{ background-color: #261010; }}
            .question:active {{ transform: scale(0.995); }}
            .answer {{
                max-height: 0;
                overflow: hidden;
                opacity: 0;
                padding: 0 16px;
                background-color: var(--panel-2);
                border-left: 3px solid var(--accent);
                margin: 0 0 12px;
                border-radius: 0 0 10px 10px;
                line-height: 1.65;
                transition: max-height 0.6s ease, opacity 0.6s ease, padding 0.6s ease;
            }}
            .answer.show {{
                max-height: 540px; /* big enough for full text */
                opacity: 1;
                padding: 12px 16px 14px;
            }}
            footer {{
                margin: 26px 0 30px;
                font-size: 0.95em;
                color: var(--muted);
                padding: 0 16px;
            }}
            .count {{
                color: var(--accent);
                font-weight: 700;
            }}
        </style>
        <script>
            function toggleAnswer(id) {{
                const ans = document.getElementById(id);
                if (ans) ans.classList.toggle("show");
            }}
            window.addEventListener("load", function() {{
                const open = "{open_section}";
                if (open) {{
                    const ans = document.getElementById(open);
                    if (ans) ans.classList.add("show");
                    const q = open === "q1" ? "what-was-he-like" : (open === "q2" ? "memories" : (open === "q3" ? "legacy" : null));
                    if (q) {{
                        const el = document.getElementById(q);
                        if (el) el.scrollIntoView({{ behavior: "smooth", block: "center" }});
                    }}
                }}
            }});
        </script>
    </head>
    <body>
        <header>
            <h1>In Loving Memory of Chikatto</h1>
        </header>

        <img
            class="pfp"
            src="https://i.postimg.cc/5y8PXNB6/9eee9a20dd4cdb333012e10346820c04.png"
            alt="Chikatto"
        />

        <div class="candle" title="A candle lit in remembrance">
            <div class="flame"></div>
        </div>

        <div class="intro">{sad_tribute_text}</div>

        <div class="section">
            <div id="what-was-he-like" class="question" onclick="toggleAnswer('q1')">🌟 What was he like?</div>
            <div class="answer" id="q1">
                Chikatto was warm, genuine, and endlessly kind. He had a way of making everyone feel seen and valued,
                and his laughter could light up even the darkest days.
            </div>

            <div id="memories" class="question" onclick="toggleAnswer('q2')">📖 A cherished memory</div>
            <div class="answer" id="q2">
                I, Max, will never forget the late-night talks we shared — conversations that wandered from silly jokes
                to deep reflections about life, always leaving me feeling lighter and inspired.
            </div>

            <div id="legacy" class="question" onclick="toggleAnswer('q3')">💫 His legacy</div>
            <div class="answer" id="q3">
                Chikatto’s legacy is one of compassion, resilience, and joy. His influence lives on in the kindness we
                show to others and the courage we find in ourselves.
            </div>
        </div>

        <footer>
            You are the <span class="count">{visitor_number}</span> person to see this and light a candle.<br/>
            With love, Max — Forever in our hearts
        </footer>
    </body>
    </html>
    """)

# --- Discord bot setup ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Dynamic view so buttons only show if BASE_URL is configured
def make_tribute_view():
    if not BASE_URL:
        return None
    view = View()
    view.add_item(Button(label="Full Tribute", url=BASE_URL))
    # Link to auto-open Q&A answers on arrival
    view.add_item(Button(label="What was he like?", url=f"{BASE_URL}?open=q1"))
    view.add_item(Button(label="Memories", url=f"{BASE_URL}?open=q2"))
    view.add_item(Button(label="Legacy", url=f"{BASE_URL}?open=q3"))
    return view

@bot.event
async def on_ready():
    try:
        synced = await tree.sync()
        print(f"Logged in as {bot.user} — synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Slash command sync error: {e}")

# Prefix: !chikatto
@bot.command(name="chikatto")
async def chikatto_prefix(ctx):
    await ctx.send("✨ Chikatto Chika Chika ✨")

# Slash: /chikatto
@tree.command(name="chikatto", description="Chikatto Chika Chika")
async def chikatto_slash(interaction: discord.Interaction):
    await interaction.response.send_message("✨ Chikatto Chika Chika ✨")

# Slash: /start (shows info and link if available)
@tree.command(name="start", description="Show tribute info and the web link (if configured)")
async def start_slash(interaction: discord.Interaction):
    if BASE_URL:
        await interaction.response.send_message(
            f"Welcome to the tribute bot. View the tribute page here: {BASE_URL}"
        )
    else:
        await interaction.response.send_message(
            "Welcome to the tribute bot. Set BASE_URL to share the web tribute link."
        )

# Shared embed builder
def build_tribute_embed():
    count = get_current_counter()
    embed = discord.Embed(
        title="In Loving Memory of Chikatto",
        description=f"{sad_tribute_text}\n\n🕯️ **{count} people** have visited and lit a candle.",
        color=discord.Color.dark_red()
    )
    embed.set_thumbnail(url="https://i.postimg.cc/5y8PXNB6/9eee9a20dd4cdb333012e10346820c04.png")
    embed.add_field(name="From", value="Max", inline=True)
    embed.add_field(name="To", value="Chikatto", inline=True)
    embed.set_footer(text="Forever in our hearts")
    return embed

# Prefix: !tribute
@bot.command(name="tribute")
async def tribute_prefix(ctx):
    embed = build_tribute_embed()
    view = make_tribute_view()
    if view:
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send(embed=embed)

# Slash: /tribute
@tree.command(name="tribute", description="Share a heartfelt tribute for Chikatto")
async def tribute_slash(interaction: discord.Interaction):
    embed = build_tribute_embed()
    view = make_tribute_view()
    if view:
        await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed)

# --- Run web + bot ---
if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is required. Set it in .env or your environment.")
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT)).start()
    bot.run(TOKEN)
