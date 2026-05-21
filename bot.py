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

# --- 데이터 관리 ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_data(data, user_id):
    u_id = str(user_id)
    if u_id not in data or not isinstance(data[u_id], dict):
        data[u_id] = {"money": 0, "wins": 0, "losses": 0, "last_daily": "", "last_reward": "", "last_emergency": "", "last_loan": ""}
    return data[u_id]

# --- 디자인 통일된 임베드 함수 (유저, 지급/결과, 잔액) ---
def create_embed(title, user, field2_name, field2_val, current_money, color):
    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="유저", value=user.mention, inline=False)
    embed.add_field(name=field2_name, value=field2_val, inline=False)
    embed.add_field(name="🔹 현재 잔액", value=f"{current_money:,}머니", inline=False)
    return embed

# --- 명령어 ---

@bot.tree.command(name="돈추가", description="[관리자] 유저에게 돈을 추가합니다.")
async def add_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    data = load_data(); u = get_user_data(data, 유저.id)
    u["money"] += 금액; save_data(data)
    await interaction.response.send_message(embed=create_embed("👑 관리자 권한 지급", 유저, "💰 지급 금액", f"+{금액:,}머니", u["money"], 0xf1c40f))

@bot.tree.command(name="지갑", description="내 정보를 확인합니다.")
async def check_wallet(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    total = u['wins'] + u['losses']; rate = (u['wins'] / total * 100) if total > 0 else 0
    embed = discord.Embed(title="👛 내 지갑", color=0x3498db)
    embed.add_field(name="유저", value=interaction.user.mention, inline=False)
    embed.add_field(name="💰 보유 금액", value=f"{u['money']:,}머니", inline=False)
    embed.add_field(name="📊 전적 / 승률", value=f"{total}전 {u['wins']}승 {u['losses']}패 ({rate:.1f}%)", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="출석체크", description="1일 1회 10,000머니 지급")
async def daily(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    if u["last_daily"] == today: return await interaction.response.send_message("❌ 이미 출석하셨습니다.", ephemeral=True)
    u["money"] += 10000; u["last_daily"] = today; save_data(data)
    await interaction.response.send_message(embed=create_embed("💵 출석체크 완료", interaction.user, "💰 지급 금액", "+10,000머니", u["money"], 0x2ecc71))

@bot.tree.command(name="보상금", description="3시간마다 30,000머니 지급")
async def reward(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    if u["last_reward"] and datetime.strptime(u["last_reward"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=3) > datetime.now():
        return await interaction.response.send_message("🚨 3시간 대기 필요", ephemeral=True)
    u["money"] += 30000; u["last_reward"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); save_data(data)
    await interaction.response.send_message(embed=create_embed("🎁 보상금 수령", interaction.user, "💰 지급 금액", "+30,000머니", u["money"], 0x2ecc71))

@bot.tree.command(name="재난지원금", description="-10,000 이하일 때 6시간마다 랜덤 지급")
async def emergency_money(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    if u["money"] > -10000: return await interaction.response.send_message("❌ 잔액 -10,000 이하만 가능", ephemeral=True)
    if u["last_emergency"] and datetime.strptime(u["last_emergency"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=6) > datetime.now():
        return await interaction.response.send_message("🚨 6시간 대기 필요", ephemeral=True)
    amt = random.randint(100000, 400000); u["money"] += amt; u["last_emergency"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); save_data(data)
    await interaction.response.send_message(embed=create_embed("🏥 재난지원금 수령", interaction.user, "💰 지급 금액", f"+{amt:,}머니", u["money"], 0x3498db))

@bot.tree.command(name="대출", description="-5,000,000 이하일 때 빚 청산 및 200,000 지급")
async def loan(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    if u["money"] > -5000000: return await interaction.response.send_message("❌ 잔액 -5,000,000 이하만 가능", ephemeral=True)
    if u["last_loan"] and datetime.strptime(u["last_loan"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24) > datetime.now():
        return await interaction.response.send_message("🚨 24시간 대기 필요", ephemeral=True)
    u["money"] = 200000; u["last_loan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); save_data(data)
    await interaction.response.send_message(embed=create_embed("🏦 대출(구제) 완료", interaction.user, "💰 지급 금액", "+200,000머니", u["money"], 0xf1c40f))

@bot.tree.command(name="랭킹", description="서버 부자 순위 Top 10")
async def leader_board(interaction: discord.Interaction):
    data = load_data()
    rank = sorted([(k, v['money']) for k, v in data.items() if isinstance(v, dict)], key=lambda x: x[1], reverse=True)[:10]
    desc = "\n".join([f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'{i+1}등'} <@{uid}> ➡️ {m:,}머니" for i, (uid, m) in enumerate(rank)])
    embed = discord.Embed(title="🏆 서버 돈 랭킹", description=desc, color=0xf1c40f)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="송금", description="유저에게 송금")
async def send_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    await interaction.response.defer()
    data = load_data(); u_f = get_user_data(data, interaction.user.id); u_t = get_user_data(data, 유저.id)
    if u_f["money"] < 금액 or 금액 <= 0: return await interaction.followup.send("❌ 잔액 부족", ephemeral=True)
    u_f["money"] -= 금액; u_t["money"] += 금액; save_data(data)
    embed = discord.Embed(title="💸 송금 성공", color=0x2ecc71)
    embed.add_field(name="유저", value=f"{interaction.user.mention} ➡️ {유저.mention}", inline=False)
    embed.add_field(name="💰 송금액", value=f"{금액:,}머니", inline=False)
    embed.add_field(name="🔹 현재 잔액", value=f"{u_f['money']:,}머니", inline=False)
    await interaction.followup.send(embed=embed)

# 레버리지 도박 로직
class GambleView(discord.ui.View):
    def __init__(self, user_id, bet, mul, mode): super().__init__(timeout=60); self.u_id = str(user_id); self.bet = bet; self.mul = mul; self.mode = mode
    @discord.ui.button(label="👀 결과 확인", style=discord.ButtonStyle.primary)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.u_id: return
        data = load_data(); u = get_user_data(data, self.u_id)
        prob = random.randint(1, 100); win = random.randint(1, 100) <= prob
        if win:
            gain = self.bet * self.mul; u["money"] += gain; u["wins"] += 1; title, color = "도박 성공", 0x3498db
            res = f"{gain:,}머니 획득 (승률 {prob}%)"
        else:
            loss = self.bet * self.mul; u["money"] -= loss; u["losses"] += 1; title, color = "도박 실패", 0xe74c3c
            res = f"{loss:,}머니 손실 (승률 {prob}%)"
        save_data(data)
        await interaction.response.edit_message(embed=create_embed(title, interaction.user, "💰 결과", res, u["money"], color), view=None)

@bot.tree.command(name="도박", description="레버리지를 선택하여 도박합니다.")
@app_commands.choices(레버리지=[
    app_commands.Choice(name="없음(1배)", value=1), app_commands.Choice(name="1단계(3배)", value=3),
    app_commands.Choice(name="2단계(6배)", value=6), app_commands.Choice(name="3단계(8배)", value=8)
])
async def gamble(interaction: discord.Interaction, 배팅액: int, 레버리지: app_commands.Choice[int]):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    if u["money"] < 배팅액: return await interaction.response.send_message("❌ 잔액 부족", ephemeral=True)
    await interaction.response.send_message(f"🎰 **도박 시작 ({레버리지.name})**", view=GambleView(interaction.user.id, 배팅액, 레버리지.value, 레버리지.name))

@bot.event
async def on_ready(): await bot.tree.sync(); print(f'{bot.user.name} 가동 중')
bot.run(TOKEN)