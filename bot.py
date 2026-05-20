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

# 봇 기본 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

DATA_FILE = "money.json"

# 안전한 데이터 로드/저장 함수
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
    print(f'{bot.user.name} 버튼 클릭형 도박봇 가동 시작!')
    try:
        synced = await bot.tree.sync()
        print(f"동기화 완료: {len(synced)}개의 슬래시 명령어 등록됨.")
    except Exception as e:
        print(f"동기화 중 오류 발생: {e}")

def init_user(data, user_id):
    if user_id not in data or not isinstance(data[user_id], dict):
        data[user_id] = {
            "money": 0, "wins": 0, "losses": 0, 
            "last_daily": "", "last_reward": "", 
            "last_loan": "", "last_support": ""
        }
    return data

# ----------------- 명령어들 -----------------

# 👑 봇 소유자 전용 돈 추가 명령어
@bot.tree.command(name="돈추가", description="[관리자] 특정 유저에게 돈을 추가합니다.")
@app_commands.describe(유저="돈을 지급할 유저를 선택하세요.", 금액="지급할 금액을 숫자로 입력하세요.")
async def add_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    await interaction.response.defer()
    app_info = await bot.application_info()
    if interaction.user.id != app_info.owner.id:
        embed = discord.Embed(title="❌ 권한 없음", description="이 명령어는 봇 소유자만 사용할 수 있습니다.", color=0xe74c3c)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    if 금액 <= 0:
        embed = discord.Embed(title="❌ 오류", description="0원 이하의 금액은 추가할 수 없습니다.", color=0xe74c3c)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    target_id = str(유저.id)
    data = load_data()
    init_user(data, target_id)
        
    data[target_id]["money"] += 금액
    save_data(data)
    
    embed = discord.Embed(title="👑 관리자 권한 지급 완료", color=0xf1c40f)
    embed.description = f"👤 **대상 유저 : {유저.mention}**\n\n> 💰 **지급된 금액 : +{금액:,}머니**\n\n🔷 **최종 잔액 : {data[target_id]['money']:,}머니**"
    await interaction.followup.send(embed=embed)

# 1. /지갑 (잔액 확인 및 전적)
@bot.tree.command(name="지갑", description="현재 가지고 있는 잔액과 도박 전적을 확인합니다.")
async def check_wallet(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    data = load_data()
    init_user(data, user_id)
    u = data[user_id]
    win_rate = (u["wins"] / (u["wins"] + u["losses"]) * 100) if (u["wins"] + u["losses"]) > 0 else 0
    
    embed = discord.Embed(title="👛 잔액 확인", color=0x3498db)
    embed.description = f"👤 **유저 : {interaction.user.mention}**\n\n🎰 **전적 정보 : {u['wins']}승 {u['losses']}패 (승률: {win_rate:.1f}%)**\n\n🔷 **현재 잔액 : {u['money']:,}머니**"
    await interaction.followup.send(embed=embed)

# 2. /출석체크 (하루 한 번, 오전 12시 초기화)
@bot.tree.command(name="출석체크", description="하루에 한 번 출석체크를 하고 10,000머니를 받습니다.")
async def daily(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    data = load_data()
    init_user(data, user_id)
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    if data[user_id].get("last_daily") == today_str:
        embed = discord.Embed(title="출석체크에 실패했어요", color=0xe74c3c)
        embed.description = f"📆 **오늘의 출석체크를 이미 완료하셨습니다!**\n\n> ⏱️ **초기화 : 오전 12시(자정) 이후에 다시 시도해 주세요.**\n\n🔷 **잔액 : {data[user_id]['money']:,}머니**"
        await interaction.followup.send(embed=embed)
        return
        
    data[user_id]["money"] += 10000
    data[user_id]["last_daily"] = today_str
    save_data(data)
    
    embed = discord.Embed(title="출석체크에 성공했어요 🎉", color=0x3498db)
    embed.description = f"📆 **출석 보상이 안전하게 지급되었습니다!**\n\n> 💵 **결과 : +10,000머니**\n\n🔷 **잔액 : {data[user_id]['money']:,}머니**"
    await interaction.followup.send(embed=embed)

# 3. /보상금 (3시간 마다 50,000머니)
@bot.tree.command(name="보상금", description="3시간마다 50,000머니의 보상금을 받습니다.")
async def reward(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    data = load_data()
    init_user(data, user_id)
        
    now = datetime.now()
    last_reward_str = data[user_id].get("last_reward", "")
    if last_reward_str:
        try:
            last_reward_time = datetime.strptime(last_reward_str, "%Y-%m-%d %H:%M:%S")
            next_reward_time = last_reward_time + timedelta(hours=3)
            if now < next_reward_time:
                remaining = next_reward_time - now
                minutes, seconds = divmod(remaining.seconds, 60)
                hours, minutes = divmod(minutes, 60)
                
                embed = discord.Embed(title="보상금 수령에 실패했어요", color=0xe74c3c)
                embed.description = f"⏱️ **아직 보상금을 신청할 수 있는 시간이 아닙니다!**\n\n> ⏳ **대기 시간 : {hours}시간 {minutes}분 {seconds}초 후 가능**\n\n🔷 **잔액 : {data[user_id]['money']:,}머니**"
                await interaction.followup.send(embed=embed)
                return
        except:
            pass
            
    data[user_id]["money"] += 50000
    data[user_id]["last_reward"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    
    embed = discord.Embed(title="보상금 수령에 성공했어요 🎉", color=0x3498db)
    embed.description = f"🎁 **3시간 정기 보상금이 정상 지급되었습니다!**\n\n> 💵 **결과 : +50,000머니**\n\n🔷 **잔액 : {data[user_id]['money']:,}머니**"
    await interaction.followup.send(embed=embed)

# 🔘 [결과 확인] 버튼 및 도박 연산 컴포넌트 클래스
class GambleView(discord.ui.View):
    def __init__(self, user_id, 배팅액, win_multiplier, lose_multiplier, 모드이름):
        super().__init__(timeout=60.0)
        self.user_id = str(user_id)
        self.배팅액 = 배팅액
        self.win_multiplier = win_multiplier
        self.lose_multiplier = lose_multiplier
        self.모드이름 = 모드이름
        self.random_probability = random.randint(1, 100) # 1~100 사이 랜덤 승률

    @discord.ui.button(label="👀 결과 확인하기", style=discord.ButtonStyle.primary)
    async def check_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ 본인의 도박 결과만 확인할 수 있습니다!", ephemeral=True)
            return

        data = load_data()
        init_user(data, self.user_id)

        if data[self.user_id]["money"] < self.배팅액:
            await interaction.response.send_message("❌ 버튼을 누르는 사이에 잔액이 부족해졌습니다!", ephemeral=True)
            return

        dice = random.randint(1, 100)
        
        # 승리 조건 연산
        if dice <= self.random_probability:
            total_payout = int(self.배팅액 * (100 / self.random_probability) * self.win_multiplier)
            net_profit = total_payout - self.배팅액
            if net_profit < 0:
                net_profit = 0
                
            data[self.user_id]["money"] += net_profit
            data[self.user_id]["wins"] += 1
            save_data(data)
            
            # 성공 시 알로항 스타일 레이아웃 (파란색 바)
            embed = discord.Embed(title="도박에 성공했어요", color=0x3498db)
            embed.description = f"🎰 **승리 확률 : {self.random_probability}%**\n\n> 🎯 **결과 : +{net_profit:,}머니**\n\n🔷 **잔액 : {data[self.user_id]['money']:,}머니 | 현재 모드 : {self.모드이름}**"
            
        else:
            # 패배 조건 연산
            net_loss = self.배팅액 * self.lose_multiplier
            data[self.user_id]["money"] -= net_loss
            data[self.user_id]["losses"] += 1
            save_data(data)
            
            # 실패 시 알로항 스타일 레이아웃 (빨간색 바)
            embed = discord.Embed(title="도박에 실패했어요", color=0xe74c3c)
            embed.description = f"🎰 **승리 확률 : {self.random_probability}%**\n\n> 🎯 **결과 : -{net_loss:,}머니**\n\n🔷 **잔액 : {data[self.user_id]['money']:,}머니 | 현재 모드 : {self.모드이름}**"

        self.clear_items() 
        await interaction.response.edit_message(embed=embed, view=self)

# 4. /도박 (버튼식 인터페이스)
@bot.tree.command(name="도박", description="판마다 랜덤 승률이 결정되어 도박을 진행합니다. 버튼을 눌러 결과를 확인하세요!")
@app_commands.describe(
    배팅액="베팅할 금액을 숫자로 입력해주세요.",
    레버러지="레버러지 단계를 선택하세요 (없으면 손실 1배, 1~3단계는 손실 배수 증가)"
)
@app_commands.choices(레버러지=[
    app_commands.Choice(name="없음 (수익 배율 적용 / 손실 1배)", value=0),
    app_commands.Choice(name="1단계 (수익 배율 x3 / 손실 3배)", value=1),
    app_commands.Choice(name="2단계 (수익 배율 x6 / 손실 6배)", value=2),
    app_commands.Choice(name="3단계 (수익 배율 x8 / 손실 8배)", value=3)
])
async def gamble(interaction: discord.Interaction, 배팅액: int, 레버러지: app_commands.Choice[int]):
    uid = str(interaction.user.id)
    data = load_data()
    init_user(data, uid)

    if 배팅액 <= 0:
        embed = discord.Embed(title="❌ 오류", description="0원 이하의 금액은 베팅할 수 없습니다.", color=0xe74c3c)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if data[uid]["money"] < 배팅액:
        embed = discord.Embed(title="도박에 실패했어요", color=0xe74c3c)
        embed.description = f"❌ **잔액이 부족합니다.**\n\n> 💸 **보유 중인 돈보다 많이 배팅할 수 없습니다.**\n\n🔷 **잔액 : {data[uid]['money']:,}머니**"
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    lev_val = 레버러지.value
    win_multiplier_bonus = {0: 1, 1: 3, 2: 6, 3: 8}[lev_val]
    lose_multiplier = {0: 1, 1: 3, 2: 6, 3: 8}[lev_val]
    모드이름 = {0: "일반 모드", 1: "레버러지 1단계", 2: "레버러지 2단계", 3: "레버러지 3단계"}[lev_val]
    
    view = GambleView(interaction.user.id, 배팅액, win_multiplier_bonus, lose_multiplier, 모드이름)
    
    embed = discord.Embed(title="도박 진행 중", color=0x3498db)
    embed.description = f"🎰 **승리 확률 : {view.random_probability}%**\n\n> 🎯 **결과 : 버튼을 눌러 확인**\n\n🔷 **배팅 모드 : {모드이름}**"
    
    await interaction.response.send_message(embed=embed, view=view)

# 5. /대출 (잔액 -500,000원 이하, 24시간 쿨타임)
@bot.tree.command(name="대출", description="잔액이 -500,000원 이하일 때 가능. (24시간 쿨타임)")
async def loan(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    
    if data[uid]["money"] > -500000:
        embed = discord.Embed(title="대출에 실패했어요", color=0xe74c3c)
        embed.description = f"❌ **대출 조건을 만족하지 못했습니다.**\n\n> 💸 **조건 : 잔액이 -500,000머니 이하일 때만 가능**\n\n🔷 **잔액 : {data[uid]['money']:,}머니**"
        return await interaction.followup.send(embed=embed)
    
    now = datetime.now()
    last = data[uid].get("last_loan", "")
    if last and now < datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=24):
        embed = discord.Embed(title="대출에 실패했어요", color=0xe74c3c)
        embed.description = f"⏱️ **대출 쿨타임이 아직 지나지 않았습니다.**\n\n> ⏳ **제한 : 24시간에 한 번만 신청 가능**\n\n🔷 **잔액 : {data[uid]['money']:,}머니**"
        return await interaction.followup.send(embed=embed)
            
    data[uid]["money"] = 200000
    data[uid]["last_loan"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    
    embed = discord.Embed(title="대출 승인 완료 ✨", color=0x2ecc71)
    embed.description = f"💸 **모든 빚이 청산되고 지원금이 충전되었습니다!**\n\n> 🎯 **결과 : 200,000머니로 초기화**\n\n🔷 **잔액 : {data[uid]['money']:,}머니**"
    await interaction.followup.send(embed=embed)

# 6. /재난지원금 (잔액 -10,000원 이하, 12시간 쿨타임)
@bot.tree.command(name="재난지원금", description="잔액 -10,000원 이하일 때 랜덤 지원. (12시간 쿨타임)")
async def support(interaction: discord.Interaction):
    await interaction.response.defer()
    data = load_data()
    uid = str(interaction.user.id)
    init_user(data, uid)
    
    if data[uid]["money"] > -10000:
        embed = discord.Embed(title="지원금 신청에 실패했어요", color=0xe74c3c)
        embed.description = f"❌ **재난지원금 대상자가 아닙니다.**\n\n> 💸 **조건 : 잔액이 -10,000머니 이하일 때만 신청 가능**\n\n🔷 **잔액 : {data[uid]['money']:,}머니**"
        return await interaction.followup.send(embed=embed)
    
    now = datetime.now()
    last = data[uid].get("last_support", "")
    if last and now < datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=12):
        embed = discord.Embed(title="지원금 신청에 실패했어요", color=0xe74c3c)
        embed.description = f"⏱️ **재난지원금 쿨타임이 아직 지나지 않았습니다.**\n\n> ⏳ **제한 : 12시간에 한 번만 신청 가능**\n\n🔷 **잔액 : {data[uid]['money']:,}머니**"
        return await interaction.followup.send(embed=embed)
            
    amount = random.randint(100000, 400000)
    data[uid]["money"] += amount
    data[uid]["last_support"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    
    embed = discord.Embed(title="재난지원금 수령 완료 🎁", color=0x2ecc71)
    embed.description = f"✨ **구호 목적의 재난지원금이 안전하게 지급되었습니다!**\n\n> 🎯 **결과 : +{amount:,}머니**\n\n🔷 **잔액 : {data[uid]['money']:,}머니**"
    await interaction.followup.send(embed=embed)

# 7. /랭킹
@bot.tree.command(name="랭킹", description="서버 유저들의 돈 랭킹을 확인합니다.")
async def leader_board(interaction: discord.Interaction):
    data = load_data()
    ranking = []
    for user_id, user_info in data.items():
        if isinstance(user_info, dict):
            ranking.append((user_id, user_info.get("money", 0)))
        
    ranking.sort(key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title="🏆 서버 돈 랭킹 (Top 10)", color=0xf1c40f)
    if not ranking:
        embed.description = "아직 등록된 유저 데이터가 없습니다."
    else:
        description_text = ""
        for index, (u_id, u_money) in enumerate(ranking[:10], start=1):
            user_mention = f"<@{u_id}>"
            medal = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"**{index}등**"
            description_text += f"{medal} {user_mention} ➡️ **{u_money:,}머니**\n"
        embed.description = description_text
        
    await interaction.response.send_message(embed=embed)

if TOKEN: bot.run(TOKEN)