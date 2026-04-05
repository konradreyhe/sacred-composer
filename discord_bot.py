"""Sacred Composer Discord Bot — Generate and share compositions via slash commands.

Setup:
  1. Create a bot at https://discord.com/developers/applications
  2. Enable the "bot" scope and "applications.commands" scope
  3. Invite the bot to your server with the generated OAuth2 URL
  4. pip install discord.py
  5. Run:  DISCORD_TOKEN=your-token-here python discord_bot.py

The bot registers five slash commands:
  /compose      — Generate a composition with full control over parameters
  /consciousness — Quick preset for a mental state (meditation, focus, etc.)
  /random       — Surprise composition with random parameters
  /patterns     — List all available pattern generators
  /remix        — Fork a previously shared composition with a new seed
"""

import discord
from discord import app_commands
import logging
import os
import sys
import tempfile
import random
import traceback

_log = logging.getLogger(__name__)

# Allow importing sacred_composer from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sacred_composer import CompositionBuilder, render_wav
from sacred_composer.constants import SCALES, NOTE_NAMES

# ---------------------------------------------------------------------------
# Client setup
# ---------------------------------------------------------------------------
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# In-memory store: message_id -> composition parameters (for /remix)
_composition_log: dict[int, dict] = {}

# Available keys for autocomplete
AVAILABLE_KEYS = [f"{note}_{scale}" for note in NOTE_NAMES for scale in SCALES]

# All pattern names the builder supports
PATTERN_NAMES = list(CompositionBuilder.PATTERN_GENERATORS.keys())

# Consciousness state names
CONSCIOUSNESS_STATES = CompositionBuilder.available_states()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _build_and_send(
    interaction: discord.Interaction,
    *,
    key: str,
    pattern: str,
    tempo: int,
    bars: int,
    seed: int,
    title: str | None = None,
    wav_preview: bool = False,
    consciousness_state: str | None = None,
):
    """Build a composition, render files, and send them as a followup."""
    title = title or f"Sacred Composition (seed {seed})"

    if consciousness_state:
        piece = CompositionBuilder(title=title)
        piece.consciousness(consciousness_state)
    else:
        piece = CompositionBuilder(key=key, tempo=tempo, bars=bars, title=title)
        piece.form(pattern="fibonacci", n_sections=5)
        piece.melody(pattern=pattern, seed=seed)
        piece.bass(seed=seed + 100)
        piece.inner_voice(pattern="golden_spiral", seed=seed + 200)

    comp = piece.build()
    info = comp.info()

    # Render MIDI
    mid_path = os.path.join(tempfile.gettempdir(), f"sacred_{seed}.mid")
    comp.render(mid_path)
    files = [discord.File(mid_path, filename=f"sacred_{seed}.mid")]

    # Optional WAV preview (first 30 seconds)
    wav_path = None
    if wav_preview:
        try:
            wav_path = os.path.join(tempfile.gettempdir(), f"sacred_{seed}.wav")
            render_wav(comp.score, wav_path)
            # Truncate to ~30 seconds (30s * 44100 samples * 2 bytes * 1 channel + 44 header)
            max_bytes = 30 * 44100 * 2 + 44
            size = os.path.getsize(wav_path)
            if size > max_bytes:
                with open(wav_path, "r+b") as wf:
                    wf.truncate(max_bytes)
            files.append(discord.File(wav_path, filename=f"sacred_{seed}.wav"))
        except (OSError, ImportError, RuntimeError) as exc:
            _log.warning("WAV rendering skipped (best-effort): %s", exc)

    # Build embed
    embed = discord.Embed(
        title=info["title"],
        description=f"Pattern: `{pattern}` | Key: `{key}`",
        color=0x8B23FF,
    )
    embed.add_field(name="Notes", value=str(info["total_notes"]))
    embed.add_field(name="Voices", value=str(info["voices"]))
    embed.add_field(name="Duration", value=f"{info['duration_seconds']:.0f}s")
    embed.add_field(name="Tempo", value=f"{info['tempo']} BPM")
    embed.add_field(name="Bars", value=str(bars))
    embed.add_field(name="Seed", value=str(seed))
    if consciousness_state:
        embed.add_field(name="State", value=consciousness_state)
    embed.set_footer(text="Sacred Composer | Use /remix <message_id> to fork")

    msg = await interaction.followup.send(embed=embed, files=files)

    # Store parameters for /remix
    _composition_log[msg.id] = {
        "key": key, "pattern": pattern, "tempo": tempo,
        "bars": bars, "seed": seed,
        "consciousness_state": consciousness_state,
    }

    # Clean up temp files
    try:
        os.unlink(mid_path)
        if wav_path:
            os.unlink(wav_path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# /compose — Full parameter control
# ---------------------------------------------------------------------------
@tree.command(name="compose", description="Generate a Sacred Composer piece")
@app_commands.describe(
    key="Musical key (e.g. D_minor, C_major, A_dorian)",
    pattern="Melody pattern generator",
    tempo="Tempo in BPM",
    bars="Length in bars",
    seed="Random seed for reproducibility",
)
async def compose_cmd(
    interaction: discord.Interaction,
    key: str = "D_minor",
    pattern: str = "infinity_series",
    tempo: int = 72,
    bars: int = 32,
    seed: int = 42,
):
    await interaction.response.defer()
    try:
        await _build_and_send(
            interaction, key=key, pattern=pattern,
            tempo=tempo, bars=bars, seed=seed,
        )
    except Exception as exc:
        await interaction.followup.send(f"Error: {exc}")


# ---------------------------------------------------------------------------
# /consciousness — Mental state preset with WAV preview
# ---------------------------------------------------------------------------
@tree.command(name="consciousness", description="Generate music for a mental state")
@app_commands.describe(
    state="Consciousness preset (meditation, focus, deep_sleep, relaxation, flow, energy)",
    seed="Random seed for reproducibility",
)
@app_commands.choices(state=[
    app_commands.Choice(name=s, value=s) for s in CONSCIOUSNESS_STATES
])
async def consciousness_cmd(
    interaction: discord.Interaction,
    state: str = "meditation",
    seed: int = 7,
):
    await interaction.response.defer()
    try:
        # Consciousness presets define their own key/tempo/bars, but we pass
        # defaults that get overridden inside _build_and_send.
        preset = CompositionBuilder.CONSCIOUSNESS_PRESETS.get(state, {})
        await _build_and_send(
            interaction,
            key=preset.get("key", "C_minor"),
            pattern=preset.get("melody_pattern", "golden_spiral"),
            tempo=preset.get("tempo", 60),
            bars=preset.get("bars", 96),
            seed=seed,
            title=f"{state.replace('_', ' ').title()} (seed {seed})",
            wav_preview=True,
            consciousness_state=state,
        )
    except Exception as exc:
        await interaction.followup.send(f"Error: {exc}")


# ---------------------------------------------------------------------------
# /random — Surprise composition
# ---------------------------------------------------------------------------
@tree.command(name="random", description="Generate a surprise composition with random parameters")
async def random_cmd(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        seed = random.randint(1, 99999)
        rng = random.Random(seed)
        key = rng.choice(AVAILABLE_KEYS)
        pattern = rng.choice(PATTERN_NAMES)
        tempo = rng.randint(50, 140)
        bars = rng.choice([16, 32, 48, 64, 96])
        await _build_and_send(
            interaction, key=key, pattern=pattern,
            tempo=tempo, bars=bars, seed=seed,
            title=f"Random Composition (seed {seed})",
        )
    except Exception as exc:
        await interaction.followup.send(f"Error: {exc}")


# ---------------------------------------------------------------------------
# /patterns — List available pattern generators
# ---------------------------------------------------------------------------
@tree.command(name="patterns", description="List all available pattern generators")
async def patterns_cmd(interaction: discord.Interaction):
    lines = [f"`{name}`" for name in PATTERN_NAMES]
    embed = discord.Embed(
        title="Available Pattern Generators",
        description="\n".join(lines),
        color=0x8B23FF,
    )
    embed.set_footer(text=f"{len(PATTERN_NAMES)} patterns | Use with /compose pattern:<name>")
    await interaction.response.send_message(embed=embed)


# ---------------------------------------------------------------------------
# /remix — Fork a previously shared composition with a new seed
# ---------------------------------------------------------------------------
@tree.command(name="remix", description="Fork a previously shared composition with a different seed")
@app_commands.describe(
    message_id="Message ID of the composition to remix",
    seed="New random seed (leave blank for random)",
)
async def remix_cmd(
    interaction: discord.Interaction,
    message_id: str,
    seed: int | None = None,
):
    await interaction.response.defer()
    try:
        mid = int(message_id)
    except ValueError:
        await interaction.followup.send("Invalid message ID. Right-click a bot message and copy its ID.")
        return

    params = _composition_log.get(mid)
    if params is None:
        await interaction.followup.send(
            "Composition not found in this session's history. "
            "Only compositions generated since the bot started can be remixed."
        )
        return

    new_seed = seed if seed is not None else random.randint(1, 99999)
    try:
        await _build_and_send(
            interaction,
            key=params["key"],
            pattern=params["pattern"],
            tempo=params["tempo"],
            bars=params["bars"],
            seed=new_seed,
            title=f"Remix of {mid} (seed {new_seed})",
            consciousness_state=params.get("consciousness_state"),
        )
    except Exception as exc:
        await interaction.followup.send(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Bot lifecycle
# ---------------------------------------------------------------------------
@client.event
async def on_ready():
    await tree.sync()
    print(f"Sacred Composer Bot is online as {client.user}")
    print(f"  Patterns: {len(PATTERN_NAMES)}  |  States: {len(CONSCIOUSNESS_STATES)}")
    print(f"  Invite URL: https://discord.com/oauth2/authorize?client_id={client.user.id}&scope=bot+applications.commands")


# Token from environment variable — never hardcode secrets
TOKEN = os.environ.get("DISCORD_TOKEN", "")
if not TOKEN:
    print("ERROR: Set the DISCORD_TOKEN environment variable before running.")
    print("  Example:  DISCORD_TOKEN=your-token-here python discord_bot.py")
    sys.exit(1)

client.run(TOKEN)
