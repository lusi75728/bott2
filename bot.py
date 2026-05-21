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
            with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def init_user(data, user_id):
    if user_id not in data or not isinstance(data[user_id], dict):
        data[user_id] = {"money": 0, "wins": 0, "losses": 0, "last_daily": "", "last_reward": "", "last_emergency": "", "last_loan": ""}
    # 필요한 키가 없을 경우 초기화
    defaults = {"money": 0, "wins": 0, "losses": 0, "last_daily": "", "last_reward": "", "last_emergency": "", "last_loan": ""}
    for k, v in defaults.items():
        if k not in data[user_id]: data[user_id][k] = v
    return data

# --- 명령어들 ---

@bot.tree.command(name="돈추가", description="[봇 소유자 전용] 특정 유저에게 돈을 추가합니다.")
async def add_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    app_info = await bot.application_info()
    if interaction.user.id != app_info.owner.id:
        embed = discord.Embed(title="❌ 권한 없음", description="이 명령어는 봇 소유자만 사용할 수 있습니다.", color=0xe74c3c)
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    data = load_data(); init_user(data, str(유저.id))
    data[str(유저.id)]["money"] += 금액
    save_data(data)
    
    embed = discord.Embed(title="👑 관리자 권한 지급 완료", color=0xf1c40f)
    embed.add_field(name="대상 유저", value=유저.mention, inline=True)
    embed.add_field(name="지급된 금액", value=f"+{금액:,}머니", inline=True)
    embed.add_field(name="최종 잔액", value=f"**{data[str(유저.id)]['money']:,}머니**", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="지갑", description="현재 보유 금액과 도박 승률을 확인합니다.")
async def check_wallet(interaction: discord.Interaction):
    data = load_data(); init_user(data, str(interaction.user.id))
    u = data[str(interaction.user.id)]
    total_games = u['wins'] + u['losses']
    win_rate = (u['wins'] / total_games * 100) if total_games > 0 else 0
    
    embed = discord.Embed(title="👛 내 지갑 확인", color=0x3498db)
    embed.add_field(name="유저", value=interaction.user.mention, inline=False)
    embed.add_field(name="💰 보유 금액", value=f"**{u['money']:,} 머니**", inline=True)
    embed.add_field(name="📊 도박 전적", value=f"{total_games}전 {u['wins']}승 {u['losses']}패", inline=True)
    embed.add_field(name="🎯 현재 승률", value=f"**{win_rate:.1f}%**", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="출석체크", description="하루에 한 번 10,000머니를 받습니다.")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id); data = load_data(); init_user(data, user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    if data[user_id]["last_daily"] == today:
        embed = discord.Embed(title="❌ 출석체크 실패", description="이미 오늘의 출석체크를 완료하셨습니다!", color=0xe74c3c)
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    data[user_id]["money"] += 10000; data[user_id]["last_daily"] = today; save_data(data)
    embed = discord.Embed(title="💵 출석체크 완료", description=f"{interaction.user.mention}님, 출석 보상 **10,000머니**가 지급되었습니다!", color=0x2ecc71)
    embed.add_field(name="현재 잔액", value=f"{data[user_id]['money']:,}머니")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="보상금", description="3시간마다 30,000머니를 받습니다.")
async def reward(interaction: discord.Interaction):
    user_id = str(interaction.user.id); data = load_data(); init_user(data, user_id)
    now = datetime.now(); last_str = data[user_id].get("last_reward", "")
    
    if last_str:
        last_time = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
        if last_time + timedelta(hours=3) > now:
            remaining = (last_time + timedelta(hours=3)) - now
            h, m = divmod(int(remaining.total_seconds()), 3600)
            m, s = divmod(m, 60)
            embed = discord.Embed(title="⏱️ 보상금 대기", description=f"**{h}시간 {m}분 {s}초** 후에 다시 받으실 수 있습니다.", color=0xf1c40f)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            
    data[user_id]["money"] += 30000; data[user_id]["last_reward"] = now.strftime("%Y-%m-%d %H:%M:%S"); save_data(data)
    embed = discord.Embed(title="🎁 보상금 수령 완료", description=f"{interaction.user.mention}님, 보상금 **30,000머니**가 지급되었습니다!", color=0x2ecc71)
    embed.add_field(name="현재 잔액", value=f"{data[user_id]['money']:,}머니")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="대출", description="잔액이 -500만 이하일 때 빚을 청산하고 20만원을 지원받습니다.")
async def loan(interaction: discord.Interaction):
    user_id = str(interaction.user.id); data = load_data(); init_user(data, user_id)
    now = datetime.now()
    
    last_loan = data[user_id].get("last_loan", "")
    if last_loan:
        last_time = datetime.strptime(last_loan, "%Y-%m-%d %H:%M:%S")
        if last_time + timedelta(hours=24) > now:
            remaining = (last_time + timedelta(hours=24)) - now
            h, m = divmod(int(remaining.total_seconds()), 3600)
            m, s = divmod(m, 60)
            embed = discord.Embed(title="⏱️ 대출 대기", description=f"대출(구제)은 24시간마다 가능합니다.\n남은 시간: **{h}시간 {m}분**", color=0xf1c40f)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

    if data[user_id]["money"] > -5000000:
        embed = discord.Embed(title="❌ 대출 불가", description="잔액이 -5,000,000 머니 이하인 경우에만 구제받을 수 있습니다.", color=0xe74c3c)
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    data[user_id]["money"] = 200000
    data[user_id]["last_loan"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    
    embed = discord.Embed(title="🏦 대출(구제) 완료", description=f"{interaction.user.mention}님의 빚이 청산되고 지원금 **200,000머니**가 지급되었습니다.", color=0xf1c40f)
    embed.add_field(name="현재 잔액", value=f"{data[user_id]['money']:,}머니")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="송금", description="다른 유저에게 머니를 송금합니다.")
async def send_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    await interaction.response.defer()
    f_id, t_id = str(interaction.user.id), str(유저.id)
    data = load_data(); init_user(data, f_id); init_user(data, t_id)
    
    if data[f_id]["money"] < 금액 or 금액 <= 0:
        embed = discord.Embed(title="❌ 송금 실패", description="잔액이 부족하거나 잘못된 금액입니다.", color=0xe74c3c)
        return await interaction.followup.send(embed=embed, ephemeral=True)
        
    data[f_id]["money"] -= 금액; data[t_id]["money"] += 금액; save_data(data)
    embed = discord.Embed(title="💸 송금 성공", color=0x2ecc71)
    embed.description = f"{interaction.user.mention}님이 {유저.mention}님에게 머니를 보냈습니다."
    embed.add_field(name="보낸 금액", value=f"{금액:,}머니", inline=True)
    embed.add_field(name="내 남은 잔액", value=f"{data[f_id]['money']:,}머니", inline=True)
    await interaction.followup.send(embed=embed)

class GambleView(discord.ui.View):
    def __init__(self, user_id, 배팅액):
        super().__init__(timeout=60); self.user_id, self.배팅액 = str(user_id), 배팅액
    @discord.ui.button(label="👀 결과 확인하기", style=discord.ButtonStyle.primary)
    async def check_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id: 
            return await interaction.response.send_message("❌ 본인의 도박 결과만 확인할 수 있습니다!", ephemeral=True)
        data = load_data(); init_user(data, self.user_id)
        win = random.randint(1, 100) <= 50
        if win: 
            data[self.user_id]["money"] += self.배팅액; data[self.user_id]["wins"] += 1; title, color = "도박에 성공했어요", 0x3498db
        else: 
            data[self.user_id]["money"] -= self.배팅액; data[self.user_id]["losses"] += 1; title, color = "도박에 실패했어요", 0xe74c3c
        save_data(data)
        embed = discord.Embed(title=title, color=color)
        embed.description = f"🎰 **승리 확률 : 50%**\n\n> 🎯 **결과 : {self.배팅액:,}머니 {'획득' if win else '손실'}**\n\n🔹 **잔액 : {data[self.user_id]['money']:,}머니**"
        self.clear_items(); await interaction.response.edit_message(embed=embed, view=self)

@bot.tree.command(name="도박", description="배팅액을 걸고 도박을 합니다.")
async def gamble(interaction: discord.Interaction, 배팅액: int):
    data = load_data(); init_user(data, str(interaction.user.id))
    if data[str(interaction.user.id)]["money"] < 배팅액:
        embed = discord.Embed(title="❌ 도박 실패", description="잔액이 부족합니다.", color=0xe74c3c)
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    await interaction.response.send_message("🎰 **도박을 시작합니다.** 버튼을 눌러 결과를 확인하세요.", view=GambleView(interaction.user.id, 배팅액))

@bot.tree.command(name="랭킹", description="서버 부자 순위 Top 10")
async def leader_board(interaction: discord.Interaction):
    data = load_data()
    rank = sorted([(k, v['money']) for k, v in data.items() if isinstance(v, dict)], key=lambda x: x[1], reverse=True)[:10]
    desc = "\n".join([f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'**{i+1}등**'} <@{uid}> ➡️ **{m:,}머니**" for i, (uid, m) in enumerate(rank)])
    embed = discord.Embed(title="🏆 서버 돈 랭킹 (Top 10)", description=desc if desc else "데이터가 없습니다.", color=0xf1c40f)
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'{bot.user.name} 봇이 가동되었습니다.')

bot.run(TOKEN)