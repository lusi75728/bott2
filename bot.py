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

# ----------------- 공통 함수 -----------------
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
    await interaction.followup.send(f"{유저.display_name} 님께 {금액:,}원을 지급했습니다.")

@bot.tree.command(name="지갑", description="내 정보를 확인합니다.")
async def check_wallet(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    u = data[uid]
    win_rate = (u["wins"] / (u["wins"] + u["losses"]) * 100) if (u["wins"] + u["losses"]) > 0 else 0
    embed = discord.Embed(title="👛 내 지갑", color=0x3498db)
    embed.add_field(name="보유 금액", value=f"{u['money']:,}원")
    embed.add_field(name="승률", value=f"{win_rate:.1f}% ({u['wins']}승 {u['losses']}패)")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="출석체크", description="하루에 한 번 10,000원 지급.")
async def daily(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    today = datetime.now().strftime("%Y-%m-%d")
    if data[uid].get("last_daily") == today:
        return await interaction.followup.send("오늘은 이미 출석하셨습니다.", ephemeral=True)
    data[uid]["money"] += 10000
    data[uid]["last_daily"] = today
    save_data(data)
    await interaction.followup.send("출석체크 완료! 10,000원이 지급되었습니다.")

@bot.tree.command(name="보상금", description="3시간마다 50,000원 지급.")
async def reward(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    last = data[uid].get("last_reward", "")
    if last and datetime.now() < datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=3):
        return await interaction.followup.send("아직 보상금을 받을 수 없습니다.", ephemeral=True)
    data[uid]["money"] += 50000
    data[uid]["last_reward"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    await interaction.followup.send("보상금 50,000원이 지급되었습니다.")

@bot.tree.command(name="랭킹", description="서버 유저 돈 랭킹 확인.")
async def leader_board(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    rank = sorted([(k, v["money"]) for k, v in data.items()], key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 서버 부자 순위", color=0xf1c40f)
    for i, (uid, money) in enumerate(rank, 1):
        embed.add_field(name=f"{i}등", value=f"<@{uid}>: {money:,}원", inline=False)
    await interaction.followup.send(embed=embed)



@bot.tree.command(name="도박", description="배팅하고 결과를 확인합니다.")
@app_commands.describe(배팅액="금액", 레버러지="단계 선택")
@app_commands.choices(레버러지=[
    app_commands.Choice(name="일반 (1배)", value=1),
    app_commands.Choice(name="1단계 (3배)", value=3),
    app_commands.Choice(name="2단계 (6배)", value=6),
    app_commands.Choice(name="3단계 (8배)", value=8)
])
async def gamble(interaction: discord.Interaction, 배팅액: int, 레버러지: app_commands.Choice[int]):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    if data[uid]["money"] < 0:
        return await interaction.followup.send("마이너스 잔액입니다! 대출이나 지원금을 받으세요.", ephemeral=True)
    view = GambleView(uid, 배팅액, 레버러지.value)
    await interaction.followup.send("버튼을 눌러 도박 결과를 확인하세요!", view=view)

class GambleView(discord.ui.View):
    def __init__(self, uid, bet, mult):
        super().__init__(timeout=60)
        self.uid, self.bet, self.mult = uid, bet, mult
    @discord.ui.button(label="결과 확인", style=discord.ButtonStyle.primary)
    async def btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        dice = random.randint(1, 100)
        if dice > 50:
            data[self.uid]["money"] += (self.bet * self.mult)
            data[self.uid]["wins"] += 1
            res = f"승리! +{self.bet * self.mult:,}원"
        else:
            data[self.uid]["money"] -= (self.bet * self.mult)
            data[self.uid]["losses"] += 1
            res = f"패배! -{self.bet * self.mult:,}원"
        save_data(data)
        await interaction.response.edit_message(content=f"결과: {res} | 잔액: {data[self.uid]['money']:,}원", view=None)

@bot.tree.command(name="대출", description="잔액이 -500,000원 이하일 때 가능. (24시간 쿨타임)")
async def loan(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    
    if data[uid]["money"] > -500000:
        return await interaction.followup.send("대상자가 아닙니다. 잔액이 -500,000원 이하일 때 가능합니다.", ephemeral=True)
    
    now = datetime.now()
    last = data[uid].get("last_loan", "")
    if last:
        if now < datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=24):
            return await interaction.followup.send("❌ 24시간에 한 번만 대출 가능합니다.", ephemeral=True)
            
    data[uid]["money"] = 200000
    data[uid]["last_loan"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    await interaction.followup.send("✅ 대출 완료! 200,000원이 지급되었습니다.")

@bot.tree.command(name="재난지원금", description="잔액 -10,000원 이하일 때 랜덤 지원. (12시간 쿨타임)")
async def support(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    
    if data[uid]["money"] > -10000:
        return await interaction.followup.send("대상자가 아닙니다. 잔액이 -10,000원 이하일 때 가능합니다.", ephemeral=True)
    
    now = datetime.now()
    last = data[uid].get("last_support", "")
    if last:
        if now < datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=12):
            return await interaction.followup.send("❌ 12시간에 한 번만 받을 수 있습니다.", ephemeral=True)
            
    amount = random.randint(100000, 400000)
    data[uid]["money"] += amount
    data[uid]["last_support"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    await interaction.followup.send(f"🎁 지원금 {amount:,}원이 지급되었습니다.")

if TOKEN: bot.run(TOKEN)