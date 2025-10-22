import discord
from discord.ext import commands
import os
import json

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

# ==============================
# CONFIG STORAGE
# ==============================
CONFIG_FILE = "config.json"

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "main_server_id": None,
            "update_channel_id": None,
            "linked_channels": [],
            "role_links": {}
        }, f, indent=4)

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ==============================
# READY EVENT
# ==============================
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online in {len(bot.guilds)} servers!")


# ==============================
# SLASH COMMANDS FOR SETUP
# ==============================
@bot.tree.command(name="setmain", description="Set the main server & update channel")
async def setmain(interaction: discord.Interaction, channel: discord.TextChannel):
    cfg = load_config()
    cfg["main_server_id"] = channel.guild.id
    cfg["update_channel_id"] = channel.id
    save_config(cfg)
    await interaction.response.send_message(f"✅ Main update channel set to {channel.mention}", ephemeral=True)


@bot.tree.command(name="linkchannel", description="Link a channel to receive main updates")
async def linkchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    cfg = load_config()
    if channel.id not in cfg["linked_channels"]:
        cfg["linked_channels"].append(channel.id)
        save_config(cfg)
        await interaction.response.send_message(f"✅ Linked {channel.mention} to updates.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ This channel is already linked.", ephemeral=True)


@bot.tree.command(name="linkrole", description="Link one role to auto-give another.")
async def linkrole(interaction: discord.Interaction, base_role: discord.Role, linked_role: discord.Role):
    cfg = load_config()
    role_links = cfg.get("role_links", {})
    if str(base_role.id) not in role_links:
        role_links[str(base_role.id)] = []
    role_links[str(base_role.id)].append(linked_role.id)
    cfg["role_links"] = role_links
    save_config(cfg)
    await interaction.response.send_message(
        f"✅ When someone gets {base_role.name}, they also get {linked_role.name}.",
        ephemeral=True
    )


# ==============================
# 1️⃣ AUTO CROSS-POST UPDATES
# ==============================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    cfg = load_config()
    main_channel = cfg.get("update_channel_id")

    if main_channel and message.channel.id == main_channel:
        for linked_id in cfg["linked_channels"]:
            ch = bot.get_channel(linked_id)
            if ch:
                await ch.send(f"{message.content}")

    await bot.process_commands(message)


# ==============================
# 2️⃣ ROLE LINKING
# ==============================
@bot.event
async def on_member_update(before, after):
    cfg = load_config()
    role_links = cfg.get("role_links", {})

    added_roles = [r for r in after.roles if r not in before.roles]
    for role in added_roles:
        if str(role.id) in role_links:
            for linked_id in role_links[str(role.id)]:
                linked_role = after.guild.get_role(linked_id)
                if linked_role and linked_role not in after.roles:
                    await after.add_roles(linked_role)


# ==============================
# 3️⃣ USERNAME SYNC
# ==============================
@bot.event
async def on_user_update(before, after):
    if before.name != after.name:
        for guild in bot.guilds:
            member = guild.get_member(after.id)
            if member:
                try:
                    await member.edit(nick=after.name)
                except:
                    pass


# ==============================
# RUN
# ==============================
@bot.event
async def on_guild_join(guild):
    await bot.tree.sync(guild=guild)

@bot.event
async def on_connect():
    await bot.tree.sync()

bot.run(os.getenv("DISCORD_TOKEN"))
