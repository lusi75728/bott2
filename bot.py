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

# 유저 데이터 초기화 공통 함수
def init_user(data, user_id):
    if user_id not in data or not isinstance(data[user_id], dict):
        data[user_id] = {
            "money": 0, "wins": 0, "losses": 0,
            "last_daily": "", "last_reward": "", "last_emergency": ""
        }
    if "last_emergency" not in data[user_id]:
        data[user_id]["last_emergency"] = ""
    if "last_reward" not in data[user_id]:
        data[user_id]["last_reward"] = ""
    return data

# 👑 봇 소유자 전용 돈 추가 명령어
@bot.tree.command(name="돈추가", description="[봇 소유자 전용] 특정 유저에게 돈을 추가합니다.")
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
    embed.description = f"👤 **대상 유저 : {유저.mention}**\n\n> 💰 **지급된 금액 : +{금액:,}머니**\n\n🔹 **최종 잔액 : {data[target_id]['money']:,}머니**"
    await interaction.followup.send(embed=embed)

# 1. /돈 (잔액 확인)
@bot.tree.command(name="돈", description="현재 가지고 있는 잔액을 확인합니다.")
async def check_money(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    init_user(data, user_id)
    money = data[user_id].get("money", 0)
    
    embed = discord.Embed(title="👛 잔액 확인", color=0x3498db)
    embed.description = f"👤 **유저 : {interaction.user.mention}**\n\n🔹 **현재 잔액 : {money:,}머니**"
    await interaction.response.send_message(embed=embed)

# 2. /출석체크 (하루 한 번, 오전 12시 초기화)
@bot.tree.command(name="출석체크", description="하루에 한 번 출석체크를 하고 10,000머니를 받습니다. (오전 12시 초기화)")
async def daily(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    data = load_data()
    init_user(data, user_id)
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    if data[user_id].get("last_daily") == today_str:
        embed = discord.Embed(title="도박에 실패했어요", color=0xe74c3c)
        embed.description = f"📆 **오늘의 출석체크를 이미 완료하셨습니다!**\n\n> ⏱️ **초기화 : 오전 12시(자정) 이후에 다시 시도해 주세요.**\n\n🔹 **잔액 : {data[user_id]['money']:,}머니**"
        await interaction.followup.send(embed=embed)
        return
        
    data[user_id]["money"] += 10000
    data[user_id]["last_daily"] = today_str
    save_data(data)
    
    embed = discord.Embed(title="출석체크에 성공했어요 🎉", color=0x3498db)
    embed.description = f"📆 **출석 보상이 안전하게 지급되었습니다!**\n\n> 💵 **결과 : +10,000머니**\n\n🔹 **잔액 : {data[user_id]['money']:,}머니**"
    await interaction.followup.send(embed=embed)

# 3. /보상금 (3시간 마다 30,000머니 - 쿨타임 버그 완벽 수정)
@bot.tree.command(name="보상금", description="3시간마다 30,000머니의 보상금을 받습니다.")
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
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                
                embed = discord.Embed(title="보상금 수령에 실패했어요", color=0xe74c3c)
                embed.description = f"⏱️ **아직 보상금을 신청할 수 있는 시간이 아닙니다!**\n\n> ⏳ **대기 시간 : {hours}시간 {minutes}분 {seconds}초 후 가능**\n\n🔹 **잔액 : {data[user_id]['money']:,}머니**"
                await interaction.followup.send(embed=embed)
                return
        except ValueError:
            # 시간 파싱 오류 발생 시 예외 안전 처리
            data[user_id]["last_reward"] = ""
            
    data[user_id]["money"] += 30000
    data[user_id]["last_reward"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    
    embed = discord.Embed(title="보상금 수령에 성공했어요 🎉", color=0x3498db)
    embed.description = f"🎁 **3시간 정기 보상금이 정상 지급되었습니다!**\n\n> 💵 **결과 : +30,000머니**\n\n🔹 **잔액 : {data[user_id]['money']:,}머니**"
    await interaction.followup.send(embed=embed)

# 🏥 /재난지원금 (3시간 마다 10만 ~ 40만 랜덤 지급)
@bot.tree.command(name="재난지원금", description="3시간마다 한 번씩 100,000 ~ 400,000머니를 랜덤으로 받습니다.")
async def emergency_money(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    data = load_data()
    init_user(data, user_id)
        
    now = datetime.now()
    last_emergency_str = data[user_id].get("last_emergency", "")
    
    if last_emergency_str:
        try:
            last_emergency_time = datetime.strptime(last_emergency_str, "%Y-%m-%d %H:%M:%S")
            next_emergency_time = last_emergency_time + timedelta(hours=3)
            if now < next_emergency_time:
                remaining = next_emergency_time - now
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                
                embed = discord.Embed(title="재난지원금 수령에 실패했어요", color=0xe74c3c)
                embed.description = f"⏱️ **재난지원금은 3시간마다 한 번씩만 신청할 수 있습니다!**\n\n> ⏳ **대기 시간 : {hours}시간 {minutes}분 {seconds}초 후 가능**\n\n🔹 **잔액 : {data[user_id]['money']:,}머니**"
                await interaction.followup.send(embed=embed)
                return
        except ValueError:
            data[user_id]["last_emergency"] = ""
            
    rand_money = random.randint(100000, 400000)
    data[user_id]["money"] += rand_money
    data[user_id]["last_emergency"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    
    embed = discord.Embed(title="🏥 재난지원금 수령에 성공했어요 🎉", color=0x3498db)
    embed.description = f"💖 **정부 지원 파산 구제금이 안전하게 지급되었습니다!**\n\n> 💵 **결과 : +{rand_money:,}머니 (랜덤 보상)**\n\n🔹 **잔액 : {data[user_id]['money']:,}머니**"
    await interaction.followup.send(embed=embed)

# 💸 송금 기능 명령어
@bot.tree.command(name="송금", description="다른 유저에게 내 머니를 송금합니다.")
@app_commands.describe(유저="머니를 보낼 대상을 선택하세요.", 금액="보낼 금액을 숫자로 입력하세요.")
async def send_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    await interaction.response.defer()
    
    from_id = str(interaction.user.id)
    to_id = str(유저.id)
    
    if from_id == to_id:
        embed = discord.Embed(title="❌ 송금 실패", description="자기 자신에게는 송금할 수 없습니다.", color=0xe74c3c)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
        
    if 금액 <= 0:
        embed = discord.Embed(title="❌ 송금 실패", description="송금할 금액은 0보다 커야 합니다.", color=0xe74c3c)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
        
    data = load_data()
    init_user(data, from_id)
    init_user(data, to_id)
        
    if data[from_id]["money"] < 금액:
        embed = discord.Embed(title="❌ 송금 실패", description=f"보유 잔액이 부족합니다.\n현재 보유량: **{data[from_id]['money']:,}머니**", color=0xe74c3c)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
        
    data[from_id]["money"] -= 금액
    data[to_id]["money"] += 금액
    save_data(data)
    
    embed = discord.Embed(title="💸 송금 성공", color=0x2ecc71)
    embed.description = f"👤 **{interaction.user.mention} ➡️ {유저.mention}**\n\n> 💵 **보낸 금액 : {금액:,}머니**\n\n🔹 **내 남은 잔액 : {data[from_id]['money']:,}머니**"
    await interaction.followup.send(embed=embed)

# 🔘 [결과 확인] 버튼 및 도박 연산 처리를 담당하는 컴포넌트 클래스
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
        init_user(data, self.user_id)

        # 결과 확인 시점에 보유 잔액 재실행 검증 (동기화 보장)
        if data[self.user_id]["money"] < self.배팅액:
            await interaction.response.send_message("❌ 보유한 금액이 베팅액보다 부족하여 결과를 확인할 수 없습니다!", ephemeral=True)
            return

        dice = random.randint(1, 100)
        
        # 승리 시: 배팅액 * 수익 배율만큼 돈 추가 증가
        if dice <= self.random_probability:
            net_profit = self.배팅액 * self.win_multiplier
            data[self.user_id]["money"] += net_profit
            data[self.user_id]["wins"] += 1
            save_data(data)
            
            embed = discord.Embed(title="도박에 성공했어요", color=0x3498db)
            embed.description = f"🎰 **승리 확률 : {self.random_probability}%**\n\n> 🎯 **결과 : +{net_profit:,}머니**\n\n🔹 **잔액 : {data[self.user_id]['money']:,}머니 | 현재 모드 : {self.모드이름}**"
            
        # 패배 시: 배팅액 * 손실 배율만큼 돈 차감 (마이너스 차감 완벽 반영)
        else:
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
    init_user(data, user_id)
    
    if data[user_id].get("money", 0) < 0:
        embed = discord.Embed(
            title="❌ 도박 제한", 
            description=f"현재 잔액이 마이너스(**{data[user_id]['money']:,}머니**) 상태입니다.\n\n🔹 **재난지원금이나 보상금으로 돈을 모아 양수(+)를 만든 후 다시 시도해 주세요!**", 
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if data[user_id].get("money", 0) < 배팅액:
        embed = discord.Embed(
            title="도박에 실패했어요",
            description=f"❌ **배팅 금액이 보유 잔액보다 많습니다.**\n\n> 💸 **배팅 시도액 : {배팅액:,}머니**\n\n🔹 **잔액 : {data[user_id]['money']:,}머니**",
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
    embed.description = f"🎰 **승리 확률 : {view.random_probability}%**\n\n> 🎯 **결과 : 버튼을 눌러 확인**\n\n🔹 **현재 모드 : {모드이름}**"
    
    await interaction.response.send_message(embed=embed, view=view)

# 5. /랭킹
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

if TOKEN: 
    bot.run(TOKEN)