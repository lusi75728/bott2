import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

# .env 파일에 적힌 토큰 불러오기
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
    if target_id not in data or not isinstance(data[target_id], dict):
        data[target_id] = {"money": 0, "last_daily": "", "last_reward": "", "wins": 0, "losses": 0}
        
    data[target_id]["money"] += 금액
    save_data(data)
    
    embed = discord.Embed(title="👑 관리자 권한 지급 완료", color=0xf1c40f)
    embed.add_field(name="대상 유저", value=유저.mention, inline=True)
    embed.add_field(name="지급된 금액", value=f"+{금액:,}머니", inline=True)
    embed.add_field(name="최종 잔액", value=f"**{data[target_id]['money']:,}머니**", inline=False)
    await interaction.followup.send(embed=embed)

# 1. /지갑 
@bot.tree.command(name="지갑", description="현재 보유 금액과 도박 승률을 확인합니다.")
async def check_wallet(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    
    if user_id not in data or not isinstance(data[user_id], dict):
        data[user_id] = {"money": 0, "last_daily": "", "last_reward": "", "wins": 0, "losses": 0}
        
    money = data[user_id].get("money", 0)
    wins = data[user_id].get("wins", 0)
    losses = data[user_id].get("losses", 0)
    total_games = wins + losses
    
    win_rate = 0.0
    if total_games > 0:
        win_rate = (wins / total_games) * 100
        
    embed = discord.Embed(title="👛 내 지갑 확인", color=0x3498db)
    embed.add_field(name="유저", value=interaction.user.mention, inline=False)
    embed.add_field(name="💰 보유 금액", value=f"**{money:,} 머니**", inline=True)
    embed.add_field(name="📊 도박 전적", value=f"{total_games}전 {wins}승 {losses}패", inline=True)
    embed.add_field(name="🎯 현재 승률", value=f"**{win_rate:.1f}%**", inline=True)
    
    await interaction.response.send_message(embed=embed)

# 2. /출석체크
@bot.tree.command(name="출석체크", description="하루에 한 번 출석체크를 하고 10,000머니를 받습니다. (오전 12시 초기화)")
async def daily(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id not in data or not isinstance(data[user_id], dict):
        data[user_id] = {"money": 0, "last_daily": "", "last_reward": "", "wins": 0, "losses": 0}
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    if data[user_id].get("last_daily") == today_str:
        embed = discord.Embed(title="❌ 출석체크 실패", description="이미 오늘의 출석체크를 완료하셨습니다!\n오전 12시(자정) 이후에 다시 시도해 주세요.", color=0xe74c3c)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
        
    data[user_id]["money"] = int(data[user_id].get("money", 0)) + 10000
    data[user_id]["last_daily"] = today_str
    save_data(data)
    
    embed = discord.Embed(title="💵 출석체크 완료", description=f"{interaction.user.mention}님, 출석 보상 **10,000머니**이 지급되었습니다!", color=0x2ecc71)
    embed.add_field(name="현재 잔액", value=f"{data[user_id]['money']:,}머니")
    await interaction.followup.send(embed=embed)

# 3. /보상금
@bot.tree.command(name="보상금", description="3시간마다 30,000머니의 보상금을 받습니다.")
async def reward(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    data = load_data()
    if user_id not in data or not isinstance(data[user_id], dict):
        data[user_id] = {"money": 0, "last_daily": "", "last_reward": "", "wins": 0, "losses": 0}
        
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
                embed = discord.Embed(title="⏱️ 보상금 대기", description=f"아직 보상금을 받을 수 없습니다.\n**{hours}시간 {minutes}분 {seconds}초** 후에 다시 받으실 수 있습니다.", color=0xf1c40f)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        except:
            pass
            
    data[user_id]["money"] = int(data[user_id].get("money", 0)) + 30000
    data[user_id]["last_reward"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    
    embed = discord.Embed(title="🎁 보상금 수령 완료", description=f"{interaction.user.mention}님, 3시간 보상금 **30,000머니**이 지급되었습니다!", color=0x2ecc71)
    embed.add_field(name="현재 잔액", value=f"{data[user_id]['money']:,}머니")
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
    
    if from_id not in data or not isinstance(data[from_id], dict):
        data[from_id] = {"money": 0, "last_daily": "", "last_reward": "", "wins": 0, "losses": 0}
    if to_id not in data or not isinstance(data[to_id], dict):
        data[to_id] = {"money": 0, "last_daily": "", "last_reward": "", "wins": 0, "losses": 0}
        
    if data[from_id]["money"] < 금액:
        embed = discord.Embed(title="❌ 송금 실패", description=f"보유 잔액이 부족합니다.\n현재 보유량: **{data[from_id]['money']:,}머니**", color=0xe74c3c)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
        
    data[from_id]["money"] -= 금액
    data[to_id]["money"] += 금액
    save_data(data)
    
    embed = discord.Embed(title="💸 송금 성공", color=0x2ecc71)
    embed.description = f"{interaction.user.mention}님이 {유저.mention}님에게 머니를 보냈습니다."
    embed.add_field(name="보낸 금액", value=f"{금액:,}머니", inline=True)
    embed.add_field(name="내 남은 잔액", value=f"{data[from_id]['money']:,}머니", inline=True)
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
        if self.user_id not in data or not isinstance(data[self.user_id], dict):
            data[self.user_id] = {"money": 0, "last_daily": "", "last_reward": "", "wins": 0, "losses": 0}

        if "wins" not in data[self.user_id]: data[self.user_id]["wins"] = 0
        if "losses" not in data[self.user_id]: data[self.user_id]["losses"] = 0

        dice = random.randint(1, 100)
        
        # 승리 조건 연산
        if dice <= self.random_probability:
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
else:
    print("❌ 에러: .env 파일에서 'BOT_TOKEN'을 찾을 수 없습니다.")