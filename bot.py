import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 봇 설정
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

# --- 통일된 임베드 함수 (알로항봇 스타일) ---
def get_embed(title, description, color):
    return discord.Embed(title=title, description=description, color=color)

# --- 명령어들 ---

@bot.tree.command(name="정보확인", description="다른 유저의 잔액과 승률을 확인합니다.")
@app_commands.describe(유저="확인할 유저를 선택하세요.")
async def check_info(interaction: discord.Interaction, 유저: discord.Member):
    data = load_data()
    user_id = str(유저.id)
    
    if user_id not in data:
        await interaction.response.send_message(f"{유저.display_name} 님은 아직 데이터를 가지고 있지 않습니다.", ephemeral=True)
        return

    u_data = data[user_id]
    wins = u_data.get("wins", 0)
    losses = u_data.get("losses", 0)
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    embed = discord.Embed(title=f"📊 {유저.display_name} 님 정보", color=0x2ecc71)
    embed.add_field(name="💰 잔액", value=f"{u_data.get('money', 0):,} 머니")
    embed.add_field(name="🎯 승률", value=f"{win_rate:.1f}% ({total}전 {wins}승 {losses}패)")
    await interaction.response.send_message(embed=embed)
@bot.tree.command(name="돈추가", description="[관리자] 유저에게 돈을 추가합니다.")
async def add_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    data = load_data(); u = get_user_data(data, 유저.id)
    u["money"] += 금액; save_data(data)
    desc = f"💰 **지급 금액 : +{금액:,}머니**\n\n🔹 **잔액 : {u['money']:,}머니**"
    await interaction.response.send_message(embed=get_embed("👑 관리자 권한 지급", desc, 0xf1c40f))

@bot.tree.command(name="지갑", description="내 정보를 확인합니다.")
async def check_wallet(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    total = u['wins'] + u['losses']; rate = (u['wins'] / total * 100) if total > 0 else 0
    desc = f"💰 **보유 금액 : {u['money']:,}머니**\n\n📊 **전적 : {total}전 {u['wins']}승 {u['losses']}패 ({rate:.1f}%)**"
    await interaction.response.send_message(embed=get_embed("👛 내 지갑", desc, 0x3498db))

@bot.tree.command(name="출석체크", description="1일 1회 10,000머니 지급")
async def daily(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    if u["last_daily"] == today: return await interaction.response.send_message("❌ 이미 출석하셨습니다.", ephemeral=True)
    u["money"] += 10000; u["last_daily"] = today; save_data(data)
    desc = f"💰 **지급 금액 : +10,000머니**\n\n🔹 **잔액 : {u['money']:,}머니**"
    await interaction.response.send_message(embed=get_embed("💵 출석체크 완료", desc, 0x2ecc71))

@bot.tree.command(name="보상금", description="3시간마다 30,000머니 지급")
async def reward(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    if u["last_reward"] and datetime.strptime(u["last_reward"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=3) > datetime.now():
        return await interaction.response.send_message("🚨 3시간 대기 필요", ephemeral=True)
    u["money"] += 30000; u["last_reward"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); save_data(data)
    desc = f"💰 **지급 금액 : +30,000머니**\n\n🔹 **잔액 : {u['money']:,}머니**"
    await interaction.response.send_message(embed=get_embed("🎁 보상금 수령", desc, 0x2ecc71))

@bot.tree.command(name="재난지원금", description="잔액 -10,000원 이하일 때 랜덤 지원.")
async def support(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    if data[uid]["money"] > -10000:
        return await interaction.followup.send("대상자가 아닙니다.", ephemeral=True)
    amount = random.randint(100000, 400000)
    data[uid]["money"] += amount
    save_data(data)
    await interaction.followup.send(f"지원금 {amount:,}원이 지급되었습니다.")
    
    # 2. 6시간 쿨타임 체크
    now = datetime.now()
    if u.get("last_emergency"):
        try:
            last_time = datetime.strptime(u["last_emergency"], "%Y-%m-%d %H:%M:%S")
            if last_time + timedelta(hours=6) > now:
                remaining = (last_time + timedelta(hours=6) - now)
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                return await interaction.response.send_message(f"🚨 아직 수령할 수 없습니다. 남은 시간: {hours}시간 {minutes}분", ephemeral=True)
        except ValueError:
            pass 
            
    # 3. 100,000 ~ 400,000 랜덤 지급
    amt = random.randint(100000, 400000)
    u["money"] += amt
    u["last_emergency"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    
    desc = f"💰 **지급 금액 : +{amt:,}머니**\n\n🔹 **현재 잔액 : {u['money']:,}머니**"
    await interaction.response.send_message(embed=get_embed("🏥 재난지원금 수령", desc, 0x3498db))

@bot.tree.command(name="대출", description="-5,000,000 이하일 때 200,000 지급")
async def loan(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    if u["money"] > -5000000: return await interaction.response.send_message("❌ 잔액 -5,000,000 이하만 가능", ephemeral=True)
    if u["last_loan"] and datetime.strptime(u["last_loan"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24) > datetime.now():
        return await interaction.response.send_message("🚨 24시간 대기 필요", ephemeral=True)
    u["money"] = 200000; u["last_loan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); save_data(data)
    desc = f"💰 **지급 금액 : +200,000머니**\n\n🔹 **잔액 : {u['money']:,}머니**"
    await interaction.response.send_message(embed=get_embed("🏦 대출(구제) 완료", desc, 0xf1c40f))

@bot.tree.command(name="송금", description="다른 유저에게 돈을 보냅니다.")
async def send_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    data = load_data(); u_f = get_user_data(data, interaction.user.id); u_t = get_user_data(data, 유저.id)
    if u_f["money"] < 금액 or 금액 <= 0: return await interaction.response.send_message("❌ 잔액 부족", ephemeral=True)
    u_f["money"] -= 금액; u_t["money"] += 금액; save_data(data)
    desc = f"🎯 **송금 대상 : {유저.mention}**\n\n> 💰 **송금액 : {금액:,}머니**\n\n🔹 **잔액 : {u_f['money']:,}머니 | 현재 모드 : 일반 모드**"
    await interaction.response.send_message(embed=get_embed("💸 송금 성공", desc, 0x2ecc71))

@bot.tree.command(name="랭킹", description="서버 돈 랭킹 확인")
async def leader_board(interaction: discord.Interaction):
    data = load_data(); ranking = sorted([(uid, info.get("money", 0)) for uid, info in data.items() if isinstance(info, dict)], key=lambda x: x[1], reverse=True)[:10]
    desc = "\n".join([f"{i+1}. <@{uid}> : {m:,}머니" for i, (uid, m) in enumerate(ranking)])
    await interaction.response.send_message(embed=get_embed("🏆 서버 돈 랭킹 (Top 10)", desc, 0xf1c40f))

# --- 도박 클래스 ---
class GambleView(discord.ui.View):
    def __init__(self, user_id, 배팅액, win_mul, mode_name):
        super().__init__(timeout=60.0); self.user_id = str(user_id); self.배팅액 = 배팅액
        self.win_mul = win_mul; self.mode_name = mode_name; self.random_probability = random.randint(1, 100)

    @discord.ui.button(label="👀 결과 확인하기", style=discord.ButtonStyle.primary)
    async def check_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id: return await interaction.response.send_message("❌ 본인의 결과만 확인 가능", ephemeral=True)
        data = load_data(); u = get_user_data(data, self.user_id)
        dice = random.randint(1, 100)
        if dice <= self.random_probability:
            profit = self.배팅액 * self.win_mul; u["money"] += profit; u["wins"] += 1; title, color = "도박에 성공했어요", 0x3498db
            desc = f"🎰 **승리 확률 : {self.random_probability}%**\n\n> 🎯 **결과 : +{profit:,}머니**\n\n🔹 **잔액 : {u['money']:,}머니 | 현재 모드 : {self.mode_name}**"
        else:
            loss = self.배팅액 * self.win_mul; u["money"] -= loss; u["losses"] += 1; title, color = "도박에 실패했어요", 0xe74c3c
            desc = f"🎰 **승리 확률 : {self.random_probability}%**\n\n> 🎯 **결과 : -{loss:,}머니**\n\n🔹 **잔액 : {u['money']:,}머니 | 현재 모드 : {self.mode_name}**"
        save_data(data); self.clear_items(); await interaction.response.edit_message(embed=get_embed(title, desc, color), view=self)

@bot.tree.command(name="도박", description="배팅액과 레버러지를 설정해 도박합니다.")
@app_commands.choices(레버리지=[
    app_commands.Choice(name="일반 모드(1배)", value=1), app_commands.Choice(name="레버러지 1단계(3배)", value=3),
    app_commands.Choice(name="레버러지 2단계(6배)", value=6), app_commands.Choice(name="레버러지 3단계(8배)", value=8)
])
async def gamble(interaction: discord.Interaction, 배팅액: int, 레버리지: app_commands.Choice[int]):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    if u["money"] < 배팅액: return await interaction.response.send_message("❌ 잔액 부족", ephemeral=True)
    view = GambleView(interaction.user.id, 배팅액, 레버리지.value, 레버리지.name)
    embed = get_embed("🎰 도박 진행 중", f"🎰 **승리 확률 : {view.random_probability}%**\n\n> 🎯 **결과 : 버튼을 눌러 확인**", 0x3498db)
    await interaction.response.send_message(embed=embed, view=view)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'{bot.user.name} 가동 시작!')

load_dotenv()
if __name__ == "__main__":
    bot.run(os.getenv('BOT_TOKEN'))