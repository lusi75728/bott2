import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

DATA_FILE = "money.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@bot.event
async def on_ready():
    print(f'{bot.user.name} 봇 가동 시작!')
    await bot.tree.sync()

def init_user(data, user_id):
    if user_id not in data:
        data[user_id] = {
            "money": 0, "wins": 0, "losses": 0, 
            "last_daily": "", "last_reward": "", 
            "last_loan": "", "last_support": ""
        }
    return data

# ----------------- 명령어들 -----------------

@bot.tree.command(name="돈추가", description="[관리자] 특정 유저에게 돈을 추가합니다.")
async def add_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    await interaction.response.defer()
    app_info = await bot.application_info()
    if interaction.user.id != app_info.owner.id:
        return await interaction.followup.send("권한이 없습니다.", ephemeral=True)
    data = load_data()
    uid = str(유저.id)
    init_user(data, uid)
    data[uid]["money"] += 금액
    save_data(data)
    embed = discord.Embed(title="✅ 지급 완료", description=f"{유저.mention} 님께 {금액:,}원을 지급했습니다.", color=0x2ecc71)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="지갑", description="내 정보를 확인합니다.")
async def check_wallet(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    u = data[uid]
    win_rate = (u["wins"] / (u["wins"] + u["losses"]) * 100) if (u["wins"] + u["losses"]) > 0 else 0
    embed = discord.Embed(title="👛 내 지갑 정보", color=0x3498db)
    embed.add_field(name="💰 보유 금액", value=f"{u['money']:,}원", inline=False)
    embed.add_field(name="📊 전적", value=f"{u['wins']}승 {u['losses']}패 (승률: {win_rate:.1f}%)", inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="출석체크", description="하루에 한 번 10,000원 지급.")
async def daily(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    today = datetime.now().strftime("%Y-%m-%d")
    if data[uid].get("last_daily") == today:
        embed = discord.Embed(title="❌ 출석체크 실패", description="오늘은 이미 출석하셨습니다.", color=0xe74c3c)
        return await interaction.followup.send(embed=embed)
    data[uid]["money"] += 10000
    data[uid]["last_daily"] = today
    save_data(data)
    embed = discord.Embed(title="✅ 출석 완료", description="10,000원이 지급되었습니다!", color=0x2ecc71)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="보상금", description="3시간마다 50,000원 지급.")
async def reward(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    last = data[uid].get("last_reward", "")
    if last and datetime.now() < datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=3):
        embed = discord.Embed(title="⏱️ 대기 중", description="3시간마다 받을 수 있습니다.", color=0xf1c40f)
        return await interaction.followup.send(embed=embed)
    data[uid]["money"] += 50000
    data[uid]["last_reward"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    embed = discord.Embed(title="🎁 보상금 지급", description="50,000원이 지급되었습니다!", color=0x2ecc71)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="대출", description="잔액이 -500,000원 이하일 때 가능. (24시간 쿨타임)")
async def loan(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    if data[uid]["money"] > -500000:
        embed = discord.Embed(title="❌ 대출 불가", description="잔액이 -500,000원 이하일 때만 가능합니다.", color=0xe74c3c)
        return await interaction.followup.send(embed=embed)
    
    now = datetime.now()
    last = data[uid].get("last_loan", "")
    if last and now < datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=24):
        embed = discord.Embed(title="⏱️ 쿨타임", description="24시간에 한 번만 가능합니다.", color=0xf1c40f)
        return await interaction.followup.send(embed=embed)
            
    data[uid]["money"] = 200000
    data[uid]["last_loan"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    embed = discord.Embed(title="✅ 대출 승인", description="모든 빚이 청산되고 200,000원이 지급되었습니다.", color=0x2ecc71)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="재난지원금", description="잔액 -10,000원 이하일 때 랜덤 지원. (12시간 쿨타임)")
async def support(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    if data[uid]["money"] > -10000:
        embed = discord.Embed(title="❌ 지원 불가", description="잔액이 -10,000원 이하일 때 가능합니다.", color=0xe74c3c)
        return await interaction.followup.send(embed=embed)
    
    now = datetime.now()
    last = data[uid].get("last_support", "")
    if last and now < datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=12):
        embed = discord.Embed(title="⏱️ 쿨타임", description="12시간에 한 번만 받을 수 있습니다.", color=0xf1c40f)
        return await interaction.followup.send(embed=embed)
            
    amount = random.randint(100000, 400000)
    data[uid]["money"] += amount
    data[uid]["last_support"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    embed = discord.Embed(title="🎁 지원금 지급", description=f"{amount:,}원이 지급되었습니다!", color=0x2ecc71)
    await interaction.followup.send(embed=embed)

if TOKEN: bot.run(TOKEN)