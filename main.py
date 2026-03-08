import discord
import os
import requests
from discord import Option
from dotenv import load_dotenv

load_dotenv()

# 設定
TOKEN = os.getenv('DISCORD_TOKEN')
HYPIXEL_API_KEY = os.getenv('HYPIXEL_API_KEY')
REGISTERED_ROLE_ID = 1480040046433276065

intents = discord.Intents.default()
intents.members = True
bot = discord.Bot(intents=intents)

# --- 共通処理：プレイヤー情報を一括取得 ---
def get_player_info(mcid):
    # 1. Mojang API
    mojang = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{mcid}")
    if mojang.status_code != 200: return None, "MCIDが見つかりません。"
    m_data = mojang.json()
    uuid, name = m_data["id"], m_data["name"]

    # 2. Hypixel API
    headers = {"API-Key": HYPIXEL_API_KEY}
    hypixel = requests.get(f"https://api.hypixel.net/v2/player?uuid={uuid}", headers=headers).json()
    if not hypixel.get("success"): return None, "Hypixel APIエラーです。"
    
    p_data = hypixel.get("player")
    if not p_data: return None, "Hypixel未ログインのプレイヤーです。"

    # 3. Discord連携確認
    link = p_data.get("socialMedia", {}).get("links", {}).get("DISCORD")
    if not link: return None, "Hypixel側でDiscordが連携されていません。"

    return {"uuid": uuid, "name": name, "linked_discord": link}, None

# --- 共通処理：ロール付与と名前変更 ---
async def apply_registration(ctx, mc_name):
    role = ctx.guild.get_role(REGISTERED_ROLE_ID)
    msg = f"✅ 登録完了！ `{mc_name}` さん、ようこそ。"
    
    try:
        if ctx.author.display_name != mc_name:
            await ctx.author.edit(nick=mc_name)
    except discord.Forbidden:
        msg += "\n(※権限によりニックネームは変更できませんでした)"
    
    await ctx.author.add_roles(role)
    return msg

# --- コマンド ---
@bot.event
async def on_ready():
    print(f"Logged in: {bot.user}")

@bot.slash_command(description="Hypixel連携でサーバーに登録します")
async def register(ctx, mcid: str):
    await ctx.defer()
    role = ctx.guild.get_role(REGISTERED_ROLE_ID)
    
    if role in ctx.author.roles:
        return await ctx.respond("すでに登録済みです。名前変更は `/rename` を使ってください。")

    info, error = get_player_info(mcid)
    if error: return await ctx.respond(f"❌ {error}")

    if info["linked_discord"].lower() != ctx.author.name.lower():
        return await ctx.respond(f"❌ 不一致: Hypixel側は `{info['linked_discord']}` です。")

    result = await apply_registration(ctx, info["name"])
    await ctx.respond(result)

@bot.slash_command(description="MCIDを変更した際に名前を更新します")
async def rename(ctx, new_mcid: str):
    await ctx.defer()
    role = ctx.guild.get_role(REGISTERED_ROLE_ID)

    if role not in ctx.author.roles:
        return await ctx.respond("先に `/register` で登録してください。")

    if ctx.author.display_name.lower() == new_mcid.lower():
        return await ctx.respond("現在の登録名と同じです。変更の必要はありません。")

    info, error = get_player_info(new_mcid)
    if error: return await ctx.respond(f"❌ {error}")

    if info["linked_discord"].lower() != ctx.author.name.lower():
        return await ctx.respond(f"❌ 不一致: 新MCIDの連携先が `{info['linked_discord']}` です。")

    result = await apply_registration(ctx, info["name"])
    await ctx.respond(f"🔄 更新成功！\n{result}")

bot.run(TOKEN)