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
    def __init__(self, user_id, 배팅액, win_multiplier, lose_multiplier, 모드이름):
        super().__init__(timeout=60.0)
        self.user_id = str(user_id)
        self.배팅액 = 배팅액
        self.win_multiplier = win_multiplier
        self.lose_multiplier = lose_multiplier
        self.모드이름 = 모드이름
        self.random_probability = random.randint(1, 100)

    @discord.ui.button(label="👀 결과 확인하기", style=discord.ButtonStyle.primary)
    async def check_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ 본인의 도박 결과만 확인할 수 있습니다!", ephemeral=True)
            return

        data = load_data()
        if self.user_id not in data or not isinstance(data[self.user_id], dict):
            data[self.user_id] = {"money": 0, "last_daily": "", "last_reward": "", "wins": 0, "losses": 0}

        if "wins" not in data[self.user_id]: data[self.user_id]["wins"] = 0
        if "losses" not in data[self.user_id]: data[self.user_id]["losses"] = 0

        dice = random.randint(1, 100)
        
        # 승리 조건 연산
        if dice <= self.random_probability:
            # ⭐ [버그 수정 핵심] 랜덤 보너스 수식을 없애고 배팅액 * 레버러지 배율로 순수익을 명확하게 고정!
            net_profit = self.배팅액 * self.win_multiplier
                
            data[self.user_id]["money"] += net_profit
            data[self.user_id]["wins"] += 1
            save_data(data)
            
            embed = discord.Embed(title="도박에 성공했어요", color=0x3498db)
            embed.description = f"🎰 **승리 확률 : {self.random_probability}%**\n\n> 🎯 **결과 : +{net_profit:,}머니**\n\n🔹 **잔액 : {data[self.user_id]['money']:,}머니 | 현재 모드 : {self.모드이름}**"
            
        else:
            # 패배 조건 연산
            net_loss = self.배팅액 * self.lose_multiplier
            data[self.user_id]["money"] -= net_loss
            data[self.user_id]["losses"] += 1
            save_data(data)
            
            embed = discord.Embed(title="도박에 실패했어요", color=0xe74c3c)
            embed.description = f"🎰 **승리 확률 : {self.random_probability}%**\n\n> 🎯 **결과 : -{net_loss:,}머니**\n\n🔹 **잔액 : {data[self.user_id]['money']:,}머니 | 현재 모드 : {self.모드이름}**"

        self.clear_items() 
        await interaction.response.edit_message(embed=embed, view=self)


# 4. /도박 
@bot.tree.command(name="도박", description="판마다 랜덤 승률이 결정되어 도박을 진행합니다. 버튼을 눌러 결과를 확인하세요!")
@app_commands.describe(
    배팅액="베팅할 금액을 숫자로 입력해주세요.",
    레버러지="레버러지 단계를 선택하세요 (없으면 손실 1배, 1~3단계는 손실 배수 증가)"
)
@app_commands.choices(레버러지=[
    app_commands.Choice(name="없음 (수익 배율 1배 / 손실 1배)", value=0),
    app_commands.Choice(name="1단계 (수익 배율 3배 / 손실 3배)", value=1),
    app_commands.Choice(name="2단계 (수익 배율 6배 / 손실 6배)", value=2),
    app_commands.Choice(name="3단계 (수익 배율 8배 / 손실 8배)", value=3)
])
async def gamble(interaction: discord.Interaction, 배팅액: int, 레버러지: app_commands.Choice[int]):
    user_id = str(interaction.user.id)
    data = load_data()
    
    if user_id not in data or not isinstance(data[user_id], dict):
        data[user_id] = {"money": 0, "last_daily": "", "last_reward": "", "wins": 0, "losses": 0}
        
    if data[user_id].get("money", 0) < 0:
        embed = discord.Embed(
            title="❌ 도박 제한", 
            description=f"현재 잔액이 마이너스(**{data[user_id]['money']:,}머니**) 상태입니다.\n출석체크나 보상금으로 돈을 모아 양수(+)를 만든 후 다시 시도해 주세요!", 
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if 배팅액 <= 0:
        embed = discord.Embed(title="❌ 오류", description="0원 이하의 금액은 베팅할 수 없습니다.", color=0xe74c3c)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    lev_val = 레버러지.value
    win_multiplier_bonus = {0: 1, 1: 3, 2: 6, 3: 8}[lev_val]
    lose_multiplier = {0: 1, 1: 3, 2: 6, 3: 8}[lev_val]
    모드이름 = {0: "일반 모드", 1: "레버러지 1단계", 2: "레버러지 2단계", 3: "레버러지 3단계"}[lev_val]
    
    view = GambleView(interaction.user.id, 배팅액, win_multiplier_bonus, lose_multiplier, 모드이름)
    
    embed = discord.Embed(title="도박 진행 중", color=0x3498db)
    embed.description = f"🎰 **승리 확률 : {view.random_probability}%**\n\n> 🎯 **결과 : 버튼을 눌러 확인**"
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.event
async def on_ready(): await bot.tree.sync(); print(f'{bot.user.name} 가동 중')
bot.run(TOKEN)