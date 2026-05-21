import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os
import threading
from flask import Flask
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 렌더용 웹 서버 (포트 오류 방지)
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"
def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# .env 로드 (로컬용)
load_dotenv()

# 데이터 및 봇 설정
DATA_FILE = "money.json"
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 유틸 함수 ---
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

# --- 명령어 영역 ---
# [여기에 기존 송금, 도박, 돈추가 등의 함수들을 그대로 넣어주세요]
@bot.tree.command(name="돈추가", description="[관리자] 유저에게 돈을 추가합니다.")
async def add_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    data = load_data(); u = get_user_data(data, 유저.id)
    u["money"] += 금액; save_data(data)
    await interaction.response.send_message(f"💰 {유저.display_name}님에게 {금액:,}머니가 지급되었습니다. (잔액: {u['money']:,}머니)")

@bot.tree.command(name="지갑", description="내 정보를 확인합니다.")
async def check_wallet(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    total = u['wins'] + u['losses']; rate = (u['wins'] / total * 100) if total > 0 else 0
    await interaction.response.send_message(f"👛 **{interaction.user.display_name}님의 지갑**\n💰 잔액: {u['money']:,}머니\n📊 전적: {total}전 {u['wins']}승 {u['losses']}패 ({rate:.1f}%)")

@bot.tree.command(name="출석체크", description="1일 1회 10,000머니 지급")
async def daily(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    if u["last_daily"] == today: return await interaction.response.send_message("❌ 오늘은 이미 출석하셨습니다.", ephemeral=True)
    u["money"] += 10000; u["last_daily"] = today; save_data(data)
    await interaction.response.send_message(f"💵 출석체크 완료! 10,000머니가 지급되었습니다. (잔액: {u['money']:,}머니)")

@bot.tree.command(name="보상금", description="3시간마다 30,000머니 지급")
async def reward(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    if u["last_reward"] and datetime.strptime(u["last_reward"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=3) > datetime.now():
        return await interaction.response.send_message("🚨 3시간마다 수령 가능합니다.", ephemeral=True)
    u["money"] += 30000; u["last_reward"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); save_data(data)
    await interaction.response.send_message(f"🎁 보상금 30,000머니 수령 완료! (잔액: {u['money']:,}머니)")

@bot.tree.command(name="재난지원금", description="-10,000 이하일 때 6시간마다 랜덤 지급")
async def emergency_money(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    if u["money"] > -10000: return await interaction.response.send_message("❌ 잔액이 -10,000 미만일 때만 가능합니다.", ephemeral=True)
    if u["last_emergency"] and datetime.strptime(u["last_emergency"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=6) > datetime.now():
        return await interaction.response.send_message("🚨 6시간 대기 필요", ephemeral=True)
    amt = random.randint(100000, 400000); u["money"] += amt; u["last_emergency"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); save_data(data)
    await interaction.response.send_message(f"🏥 재난지원금 {amt:,}머니가 지급되었습니다. (잔액: {u['money']:,}머니)")

@bot.tree.command(name="대출", description="-5,000,000 이하일 때 200,000 지급")
async def loan(interaction: discord.Interaction):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    if u["money"] > -5000000: return await interaction.response.send_message("❌ 잔액 -5,000,000 미만일 때만 가능합니다.", ephemeral=True)
    if u["last_loan"] and datetime.strptime(u["last_loan"], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24) > datetime.now():
        return await interaction.response.send_message("🚨 24시간마다 가능합니다.", ephemeral=True)
    u["money"] = 200000; u["last_loan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); save_data(data)
    await interaction.response.send_message("🏦 대출(구제)로 200,000머니가 지급되었습니다.")

@bot.tree.command(name="송금", description="다른 유저에게 돈을 보냅니다.")
async def send_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    data = load_data(); u_f = get_user_data(data, interaction.user.id); u_t = get_user_data(data, 유저.id)
    if u_f["money"] < 금액 or 금액 <= 0: return await interaction.response.send_message("❌ 잔액이 부족합니다.", ephemeral=True)
    u_f["money"] -= 금액; u_t["money"] += 금액; save_data(data)
    
    embed = discord.Embed(title="송금 완료", color=0x2ecc71)
    embed.add_field(name="💸 송금 금액", value=f"{금액:,}머니", inline=False)
    embed.add_field(name="👤 송금자", value=f"{interaction.user.mention}\n잔액: {u_f['money']:,}머니", inline=True)
    embed.add_field(name="📥 받은 사람", value=f"{유저.mention}\n잔액: {u_t['money']:,}머니", inline=True)
    embed.set_footer(text="⚠ 현금 거래 적발 시 이용 정지 조치가 이루어집니다. | 현재 모드 : 일반 모드")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="랭킹", description="서버 돈 랭킹 확인")
async def leader_board(interaction: discord.Interaction):
    data = load_data(); ranking = sorted([(uid, info.get("money", 0)) for uid, info in data.items() if isinstance(info, dict)], key=lambda x: x[1], reverse=True)[:10]
    desc = "\n".join([f"{i+1}. <@{uid}> : {m:,}머니" for i, (uid, m) in enumerate(ranking)])
    await interaction.response.send_message(f"🏆 **서버 돈 랭킹 (Top 10)**\n\n{desc}")

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
            profit = self.배팅액 * self.win_mul; u["money"] += profit; u["wins"] += 1; msg = f"성공! +{profit:,}머니"
        else:
            loss = self.배팅액 * self.win_mul; u["money"] -= loss; u["losses"] += 1; msg = f"실패... -{loss:,}머니"
        save_data(data); self.clear_items(); await interaction.response.edit_message(content=f"🎰 결과: {msg}\n잔액: {u['money']:,}머니", view=self)

@bot.tree.command(name="도박", description="배팅액과 레버러지를 설정해 도박합니다.")
@app_commands.choices(레버리지=[app_commands.Choice(name="1배", value=1), app_commands.Choice(name="3배", value=3), app_commands.Choice(name="6배", value=6), app_commands.Choice(name="8배", value=8)])
async def gamble(interaction: discord.Interaction, 배팅액: int, 레버리지: app_commands.Choice[int]):
    data = load_data(); u = get_user_data(data, interaction.user.id)
    if u["money"] < 배팅액: return await interaction.response.send_message("❌ 잔액 부족", ephemeral=True)
    view = GambleView(interaction.user.id, 배팅액, 레버리지.value, 레버리지.name)
    await interaction.response.send_message(f"🎰 도박 시작! 배팅액: {배팅액:,} (레버리지 {레버리지.name})", view=view)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'{bot.user.name} 가동 시작!')

# 렌더 실행부
if __name__ == "__main__":
    # 웹 서버 시작
    threading.Thread(target=run_web, daemon=True).start()
    
    # 토큰 로드 (환경 변수 확인)
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        print("경고: BOT_TOKEN을 찾을 수 없습니다. 환경 변수를 확인하세요.")
    else:
        bot.run(TOKEN)