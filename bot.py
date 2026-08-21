import os
import discord
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


# ============================================================
# 서버 정보 채널
# ============================================================

async def update_info_channels(guild):
    """채널 이름으로 서버 정보 표시"""

    total = guild.member_count or 0
    bots = sum(1 for m in guild.members if m.bot)
    humans = total - bots

    humans_name = f"・Humans: {humans}"
    bots_name = f"・Bots: {bots}"
    members_name = f"・Members: {total}"

    await create_or_update_channel(guild, humans_name)
    await create_or_update_channel(guild, bots_name)
    await create_or_update_channel(guild, members_name)


async def create_or_update_channel(guild, name):
    """채널 생성 또는 이름 업데이트"""

    if len(name) > 100:
        name = name[:97] + "..."

    # 이름이 정확히 같은 채널이 있는지 확인
    for channel in guild.channels:
        if (
            channel.name == name
            and isinstance(channel, discord.VoiceChannel)
        ):
            return channel

    # 기존 Humans/Bots/Members 채널 찾기
    for channel in guild.channels:
        if isinstance(channel, discord.VoiceChannel):

            if "Humans" in channel.name and "Humans" in name:
                await channel.edit(name=name)
                return channel

            if "Bots" in channel.name and "Bots" in name:
                await channel.edit(name=name)
                return channel

            if "Members" in channel.name and "Members" in name:
                await channel.edit(name=name)
                return channel

    # 새 음성 채널 생성
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            connect=False
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            connect=True
        )
    }

    channel = await guild.create_voice_channel(
        name,
        overwrites=overwrites,
        reason="서버 정보 채널 생성"
    )

    return channel


# ============================================================
# Components V2 텍스트 UI
# ============================================================

@tree.command(
    name="ui",
    description="Components V2 텍스트 카드를 생성합니다"
)
@app_commands.describe(
    내용="카드에 표시할 내용",
    제목="카드 제목 (선택)"
)
async def ui_command(
    interaction: discord.Interaction,
    내용: str,
    제목: str = None
):
    """Components V2 텍스트 카드"""

    if 제목:
        text = f"# {제목}\n\n{내용}"
    else:
        text = 내용

    container = discord.ui.Container(
        discord.ui.TextDisplay(text)
    )

    view = discord.ui.LayoutView()
    view.add_item(container)

    await interaction.channel.send(
        view=view
    )

    await interaction.response.send_message(
        "✅ UI가 전송되었습니다!",
        ephemeral=True
    )


# ============================================================
# 서버 정보 Components V2
# ============================================================

@tree.command(
    name="서버정보",
    description="서버 정보를 Components V2 카드로 표시합니다"
)
async def server_info(interaction: discord.Interaction):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ 서버에서만 사용할 수 있습니다.",
            ephemeral=True
        )
        return

    total = guild.member_count or 0
    bots = sum(1 for m in guild.members if m.bot)
    humans = total - bots

    owner = guild.owner

    if owner:
        owner_text = owner.mention
    else:
        owner_text = "알 수 없음"

    created_at = guild.created_at.strftime(
        "%Y년 %m월 %d일"
    )

    text = (
        f"# 📊 {guild.name} 서버 정보\n\n"
        f"👤 **Humans:** {humans}\n"
        f"🤖 **Bots:** {bots}\n"
        f"👥 **Members:** {total}\n\n"
        f"📅 **생성일:** {created_at}\n"
        f"👑 **서버장:** {owner_text}\n"
        f"📌 **채널 수:** {len(guild.channels)}\n"
        f"🎨 **역할 수:** {len(guild.roles)}"
    )

    container = discord.ui.Container(
        discord.ui.TextDisplay(text)
    )

    view = discord.ui.LayoutView()
    view.add_item(container)

    await interaction.response.send_message(
        view=view
    )


# ============================================================
# 정보 채널 명령어
# ============================================================

@tree.command(
    name="정보채널",
    description="서버 정보 채널을 생성/업데이트합니다"
)
async def info_channel(interaction: discord.Interaction):

    await interaction.response.send_message(
        "🔄 처리 중...",
        ephemeral=True
    )

    try:
        await update_info_channels(interaction.guild)

        await interaction.edit_original_response(
            content="✅ 정보 채널이 업데이트되었습니다!"
        )

    except Exception as e:
        print(f"정보 채널 오류: {e}")

        await interaction.edit_original_response(
            content="❌ 정보 채널 업데이트 중 오류가 발생했습니다."
        )


# ============================================================
# 핑
# ============================================================

@tree.command(
    name="핑",
    description="봇의 응답 속도를 확인합니다"
)
async def ping(interaction: discord.Interaction):

    latency = round(bot.latency * 1000)

    await interaction.response.send_message(
        f"🏓 퐁! 응답 속도: {latency}ms",
        ephemeral=True
    )


# ============================================================
# 봇 준비
# ============================================================

@bot.event
async def on_ready():

    print(f"✅ {bot.user} 실행됨")

    try:
        await tree.sync()
        print("✅ 명령어 동기화 완료")
    except Exception as e:
        print(f"❌ 명령어 동기화 실패: {e}")

    for guild in bot.guilds:

        try:
            await update_info_channels(guild)
            print(
                f"✅ {guild.name} 서버 정보 채널 준비 완료"
            )

        except Exception as e:
            print(
                f"❌ {guild.name} 정보 채널 오류: {e}"
            )

    print(
        f"📊 총 {len(bot.guilds)}개 서버 연결됨"
    )


# ============================================================
# 멤버 입장
# ============================================================

@bot.event
async def on_member_join(member):

    try:
        await update_info_channels(member.guild)
    except Exception as e:
        print(f"❌ 멤버 입장 처리 오류: {e}")


# ============================================================
# 멤버 퇴장
# ============================================================

@bot.event
async def on_member_remove(member):

    try:
        await update_info_channels(member.guild)
    except Exception as e:
        print(f"❌ 멤버 퇴장 처리 오류: {e}")


# ============================================================
# 서버 입장
# ============================================================

@bot.event
async def on_guild_join(guild):

    try:
        await update_info_channels(guild)

        print(
            f"✅ {guild.name} 서버에 입장했고 "
            f"정보 채널을 생성했습니다!"
        )

    except Exception as e:
        print(f"❌ 서버 입장 처리 오류: {e}")


# ============================================================
# 에러 처리
# ============================================================

@bot.event
async def on_error(event, *args, **kwargs):

    print(f"❌ 에러 발생: {event}")


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    token = os.getenv("DISCORD_TOKEN")

    if not token:
        print("❌ DISCORD_TOKEN 환경변수가 없습니다!")
        exit(1)

    try:

        bot.run(token)

    except discord.errors.LoginFailure:

        print(
            "❌ 잘못된 토큰입니다. "
            "환경변수를 확인해주세요."
        )

    except Exception as e:

        print(f"❌ 오류 발생: {e}")
