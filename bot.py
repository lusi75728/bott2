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
            "last_daily": "", "last_reward": "", "last_emergency": ""
        }
    if "wins" not in data[user_id]: data[user_id]["wins"] = 0
    if "losses" not in data[user_id]: data[user_id]["losses"] = 0
    if "last_daily" not in data[user_id]: data[user_id]["last_daily"] = ""
    if "last_reward" not in data[user_id]: data[user_id]["last_reward"] = ""
    if "last_emergency" not in data[user_id]: data[user_id]["last_emergency"] = ""
    
    try:
        data[user_id]["money"] = int(data[user_id].get("money", 0))
    except:
        data[user_id]["money"] = 0
    return data

# --- 명령어들 ---

@bot.tree.command(name="돈추가", description="[관리자] 특정 유저에게 돈을 추가합니다.")
async def add_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    app_info = await bot.application_info()
    if interaction.user.id != app_info.owner.id:
        await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
        return
    data = load_data()
    init_user(data, str(유저.id))
    data[str(유저.id)]["money"] += 금액
    save_data(data)
    await interaction.response.send_message(f"👑 {유저.name}님께 {금액:,}머니를 지급했습니다.")

@bot.tree.command(name="지갑", description="내 잔액과 전적을 확인합니다.")
async def check_wallet(interaction: discord.Interaction):
    data = load_data()
    init_user(data, str(interaction.user.id))
    user = data[str(interaction.user.id)]
    embed = discord.Embed(title="👛 내 지갑", color=0x3498db)
    embed.add_field(name="잔액", value=f"{user['money']:,}머니")
    embed.add_field(name="전적", value=f"{user['wins']}승 {user['losses']}패")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="출석체크", description="하루 한 번 10,000머니를 받습니다.")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    init_user(data, user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    if data[user_id]["last_daily"] == today:
        await interaction.response.send_message("🚨 이미 오늘 출석했습니다.", ephemeral=True)
        return
    data[user_id]["money"] += 10000
    data[user_id]["last_daily"] = today
    save_data(data)
    embed = discord.Embed(title="💵 출석체크 완료", description=f"잔액: {data[user_id]['money']:,}머니", color=0x2ecc71)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="보상금", description="3시간마다 30,000머니를 받습니다.")
async def reward(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    init_user(data, user_id)
    now = datetime.now()
    last = data[user_id].get("last_reward", "")
    if last and datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=3) > now:
        await interaction.response.send_message("🚨 대기 시간이 남았습니다.", ephemeral=True)
        return
    data[user_id]["money"] += 30000
    data[user_id]["last_reward"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    embed = discord.Embed(title="🎁 보상금 수령", description=f"잔액: {data[user_id]['money']:,}머니", color=0x2ecc71)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="재난지원금", description="3시간마다 랜덤 지급")
async def emergency_money(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    init_user(data, user_id)
    now = datetime.now()
    last = data[user_id].get("last_emergency", "")
    if last and datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + timedelta(hours=3) > now:
        await interaction.response.send_message("🚨 대기 시간이 남았습니다.", ephemeral=True)
        return
    amt = random.randint(100000, 400000)
    data[user_id]["money"] += amt
    data[user_id]["last_emergency"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    embed = discord.Embed(title="🏥 재난지원금", description=f"+{amt:,}머니 획득! 잔액: {data[user_id]['money']:,}머니", color=0x3498db)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="송금", description="상대에게 송금합니다.")
async def send_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    await interaction.response.defer()
    f_id, t_id = str(interaction.user.id), str(유저.id)
    data = load_data()
    init_user(data, f_id); init_user(data, t_id)
    if data[f_id]["money"] < 금액:
        await interaction.followup.send("잔액이 부족합니다.")
        return
    data[f_id]["money"] -= 금액
    data[t_id]["money"] += 금액
    save_data(data)
    embed = discord.Embed(title="💸 송금 성공", color=0x2ecc71)
    embed.description = f"내 잔액: {data[f_id]['money']:,}\n상대 잔액: {data[t_id]['money']:,}"
    await interaction.followup.send(embed=embed)

class GambleView(discord.ui.View):
    def __init__(self, user_id, 배팅액, mult, mode):
        super().__init__(timeout=60)
        self.user_id, self.배팅액, self.mult, self.mode = str(user_id), 배팅액, mult, mode
    
    @discord.ui.button(label="결과 확인", style=discord.ButtonStyle.primary)
    async def check_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id: return
        data = load_data()
        init_user(data, self.user_id)
        win = random.randint(1, 100) <= 50
        amt = self.배팅액 * self.mult
        if win:
            data[self.user_id]["money"] += amt
            data[self.user_id]["wins"] += 1
            title, color = "🎉 도박 성공", 0x3498db
        else:
            data[self.user_id]["money"] -= amt
            data[self.user_id]["losses"] += 1
            title, color = "💥 도박 실패", 0xe74c3c
        save_data(data)
        embed = discord.Embed(title=title, description=f"잔액: {data[self.user_id]['money']:,}머니", color=color)
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)

@bot.tree.command(name="도박", description="도박을 시작합니다.")
async def gamble(interaction: discord.Interaction, 배팅액: int):
    data = load_data()
    init_user(data, str(interaction.user.id))
    if data[str(interaction.user.id)]["money"] < 배팅액:
        await interaction.response.send_message("잔액 부족!", ephemeral=True)
        return
    view = GambleView(interaction.user.id, 배팅액, 1, "일반")
    await interaction.response.send_message("도박 진행 중...", view=view)

@bot.tree.command(name="랭킹", description="서버 부자 순위")
async def leader_board(interaction: discord.Interaction):
    data = load_data()
    rank = sorted([(k, v['money']) for k, v in data.items()], key=lambda x: x[1], reverse=True)[:10]
    desc = "\n".join([f"{i+1}등: <@{uid}> - {m:,}머니" for i, (uid, m) in enumerate(rank)])
    await interaction.response.send_message(embed=discord.Embed(title="🏆 랭킹", description=desc))

bot.run(TOKEN)