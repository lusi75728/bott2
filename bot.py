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

# --- 기본 함수들 ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def init_user(data, user_id):
    if user_id not in data or not isinstance(data[user_id], dict):
        data[user_id] = {"money": 0, "wins": 0, "losses": 0, "last_daily": "", "last_reward": "", "last_emergency": ""}
    for k in ["money", "wins", "losses", "last_daily", "last_reward", "last_emergency"]:
        if k not in data[user_id]: data[user_id][k] = 0 if k in ["money", "wins", "losses"] else ""
    return data

# --- 명령어들 (이미지 스타일 임베드 적용) ---

@bot.tree.command(name="돈추가", description="[관리자] 특정 유저에게 돈을 추가합니다.")
async def add_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    app_info = await bot.application_info()
    if interaction.user.id != app_info.owner.id: return await interaction.response.send_message("❌ 권한이 없습니다.", ephemeral=True)
    data = load_data(); init_user(data, str(유저.id))
    data[str(유저.id)]["money"] += 금액
    save_data(data)
    embed = discord.Embed(title="👑 관리자 지급 완료", color=0xf1c40f)
    embed.add_field(name="대상 유저", value=유저.mention, inline=True)
    embed.add_field(name="지급 금액", value=f"+{금액:,}머니", inline=True)
    embed.add_field(name="최종 잔액", value=f"{data[str(유저.id)]['money']:,}머니", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="지갑", description="내 보유 잔액과 전적을 확인합니다.")
async def check_wallet(interaction: discord.Interaction):
    data = load_data(); init_user(data, str(interaction.user.id))
    u = data[str(interaction.user.id)]
    embed = discord.Embed(title="👛 내 지갑 정보", color=0x3498db)
    embed.add_field(name="💰 보유 금액", value=f"{u['money']:,}머니", inline=False)
    embed.add_field(name="📊 도박 전적", value=f"{u['wins']}승 {u['losses']}패", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="출석체크", description="하루 한 번 10,000머니를 받습니다.")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id); data = load_data(); init_user(data, user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    if data[user_id]["last_daily"] == today:
        embed = discord.Embed(title="🚨 출석체크 오류", description="이미 오늘 출석하셨습니다.", color=0xe74c3c)
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    data[user_id]["money"] += 10000; data[user_id]["last_daily"] = today; save_data(data)
    embed = discord.Embed(title="💵 출석체크 완료", color=0x2ecc71)
    embed.add_field(name="보상", value="+10,000머니", inline=True)
    embed.add_field(name="현재 잔액", value=f"{data[user_id]['money']:,}머니", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="보상금", description="3시간마다 30,000머니를 받습니다.")
async def reward(interaction: discord.Interaction):
    user_id = str(interaction.user.id); data = load_data(); init_user(data, user_id)
    now = datetime.now(); last = data[user_id].get("last_reward", "")
    if last and datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=3) > now:
        embed = discord.Embed(title="🚨 보상금 대기 중", description="3시간마다 수령 가능합니다.", color=0xe74c3c)
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    data[user_id]["money"] += 30000; data[user_id]["last_reward"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_data(data)
    embed = discord.Embed(title="🎁 보상금 수령 완료", color=0x2ecc71)
    embed.add_field(name="보상", value="+30,000머니", inline=True)
    embed.add_field(name="현재 잔액", value=f"{data[user_id]['money']:,}머니", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="재난지원금", description="3시간마다 랜덤 지급")
async def emergency_money(interaction: discord.Interaction):
    user_id = str(interaction.user.id); data = load_data(); init_user(data, user_id)
    now = datetime.now(); last = data[user_id].get("last_emergency", "")
    if last and datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=3) > now:
        embed = discord.Embed(title="🚨 재난지원금 대기 중", description="3시간마다 수령 가능합니다.", color=0xe74c3c)
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    amt = random.randint(100000, 400000); data[user_id]["money"] += amt; data[user_id]["last_emergency"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_data(data)
    embed = discord.Embed(title="🏥 재난지원금 수령 완료", color=0x3498db)
    embed.add_field(name="획득 금액", value=f"+{amt:,}머니", inline=True)
    embed.add_field(name="현재 잔액", value=f"{data[user_id]['money']:,}머니", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="송금", description="다른 유저에게 머니를 송금합니다.")
async def send_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    await interaction.response.defer()
    f_id, t_id = str(interaction.user.id), str(유저.id)
    data = load_data(); init_user(data, f_id); init_user(data, t_id)
    if data[f_id]["money"] < 금액 or 금액 <= 0:
        embed = discord.Embed(title="❌ 송금 실패", description="잔액이 부족하거나 금액이 올바르지 않습니다.", color=0xe74c3c)
        return await interaction.followup.send(embed=embed, ephemeral=True)
    data[f_id]["money"] -= 금액; data[t_id]["money"] += 금액; save_data(data)
    embed = discord.Embed(title="💸 송금 성공", color=0x2ecc71)
    embed.add_field(name="송금 대상", value=유저.mention, inline=True)
    embed.add_field(name="송금 금액", value=f"{금액:,}머니", inline=True)
    embed.add_field(name="나의 잔액", value=f"{data[f_id]['money']:,}머니", inline=False)
    await interaction.followup.send(embed=embed)

class GambleView(discord.ui.View):
    def __init__(self, user_id, 배팅액):
        super().__init__(timeout=60); self.user_id, self.배팅액 = str(user_id), 배팅액
    @discord.ui.button(label="결과 확인하기", style=discord.ButtonStyle.primary)
    async def check_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id: return
        data = load_data(); init_user(data, self.user_id)
        win = random.randint(1, 100) <= 50
        if win: data[self.user_id]["money"] += self.배팅액; data[self.user_id]["wins"] += 1; title, color = "🎉 도박 성공", 0x3498db
        else: data[self.user_id]["money"] -= self.배팅액; data[self.user_id]["losses"] += 1; title, color = "💥 도박 실패", 0xe74c3c
        save_data(data)
        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="결과", value=f"{self.배팅액:,}머니 {'획득' if win else '손실'}", inline=False)
        embed.add_field(name="현재 잔액", value=f"{data[self.user_id]['money']:,}머니", inline=False)
        self.clear_items(); await interaction.response.edit_message(embed=embed, view=self)

@bot.tree.command(name="도박", description="배팅액을 걸고 도박을 합니다.")
async def gamble(interaction: discord.Interaction, 배팅액: int):
    data = load_data(); init_user(data, str(interaction.user.id))
    if data[str(interaction.user.id)]["money"] < 배팅액:
        embed = discord.Embed(title="❌ 도박 실패", description="잔액이 부족합니다.", color=0xe74c3c)
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    await interaction.response.send_message("🎰 **도박을 시작합니다.** 버튼을 눌러주세요.", view=GambleView(interaction.user.id, 배팅액))

@bot.tree.command(name="랭킹", description="서버 부자 순위 Top 10")
async def leader_board(interaction: discord.Interaction):
    data = load_data()
    rank = sorted([(k, v['money']) for k, v in data.items()], key=lambda x: x[1], reverse=True)[:10]
    desc = "\n".join([f"**{i+1}등** : <@{uid}> - **{m:,}머니**" for i, (uid, m) in enumerate(rank)])
    embed = discord.Embed(title="🏆 서버 랭킹 (Top 10)", description=desc, color=0xf1c40f)
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'{bot.user.name} 봇이 가동되었습니다.')

bot.run(TOKEN)