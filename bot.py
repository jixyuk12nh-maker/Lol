import os
import discord
from discord import app_commands

# ============================================================
# 기본 설정
# ============================================================

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
    """서버의 Members / Humans / Bots 채널을 생성 및 업데이트"""

    if guild is None:
        return

    total = guild.member_count or 0

    # 캐시된 멤버 기준
    bots = sum(1 for member in guild.members if member.bot)
    humans = total - bots

    channels = {
        "Members": f"・Members: {total}",
        "Humans": f"・Humans: {humans}",
        "Bots": f"・Bots: {bots}"
    }

    for channel_type, channel_name in channels.items():
        await create_or_update_channel(
            guild,
            channel_type,
            channel_name
        )


async def create_or_update_channel(guild, channel_type, name):
    """정보용 음성 채널 생성 또는 이름 업데이트"""

    # 기존 해당 채널 찾기
    for channel in guild.channels:

        if not isinstance(channel, discord.VoiceChannel):
            continue

        # 기존 이름에서 종류 확인
        if channel_type.lower() in channel.name.lower():

            if channel.name != name:
                try:
                    await channel.edit(
                        name=name,
                        reason="서버 정보 채널 업데이트"
                    )
                except discord.Forbidden:
                    print(
                        f"❌ {guild.name}: "
                        f"{channel_type} 채널 이름 변경 권한 없음"
                    )
                except discord.HTTPException as e:
                    print(
                        f"❌ {guild.name}: "
                        f"{channel_type} 채널 업데이트 실패: {e}"
                    )

            return channel

    # 권한 설정
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            connect=False
        )
    }

    # 봇 권한
    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            connect=True
        )

    try:
        channel = await guild.create_voice_channel(
            name=name,
            overwrites=overwrites,
            reason="서버 정보 채널 생성"
        )

        print(
            f"✅ {guild.name}: "
            f"{name} 생성 완료"
        )

        return channel

    except discord.Forbidden:
        print(
            f"❌ {guild.name}: "
            f"{name} 생성 권한 없음"
        )

    except discord.HTTPException as e:
        print(
            f"❌ {guild.name}: "
            f"{name} 생성 실패: {e}"
        )

    return None


# ============================================================
# 청소 명령어 (추가됨)
# ============================================================

@tree.command(
    name="청소",
    description="지정된 개수만큼 메시지를 삭제합니다"
)
@app_commands.describe(
    갯수="삭제할 메시지 개수 (1~100)"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_command(
    interaction: discord.Interaction,
    갯수: int
):
    """현재 채널에서 메시지를 삭제합니다"""

    # 갯수 제한 확인
    if 갯수 < 1:
        await interaction.response.send_message(
            "❌ 1개 이상의 메시지를 삭제해야 합니다.",
            ephemeral=True
        )
        return

    if 갯수 > 100:
        await interaction.response.send_message(
            "❌ 한 번에 최대 100개까지만 삭제할 수 있습니다.",
            ephemeral=True
        )
        return

    # 현재 채널
    target_channel = interaction.channel

    # 봇 권한 확인
    permissions = target_channel.permissions_for(interaction.guild.me)

    if not permissions.read_message_history:
        await interaction.response.send_message(
            "❌ 메시지 기록을 읽을 권한이 없습니다.",
            ephemeral=True
        )
        return

    if not permissions.manage_messages:
        await interaction.response.send_message(
            "❌ 메시지를 관리할 권한이 없습니다.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"🔄 {갯수}개의 메시지를 삭제하는 중...",
        ephemeral=True
    )

    try:
        # 메시지 삭제
        deleted = await target_channel.purge(
            limit=갯수,
            check=None,
            bulk=True
        )

        if deleted:
            await interaction.edit_original_response(
                content=f"✅ {len(deleted)}개의 메시지를 삭제했습니다."
            )
        else:
            await interaction.edit_original_response(
                content="❌ 삭제할 메시지가 없습니다."
            )

    except discord.Forbidden:
        await interaction.edit_original_response(
            content="❌ 메시지를 삭제할 권한이 없습니다."
        )

    except discord.HTTPException as e:
        await interaction.edit_original_response(
            content=f"❌ 메시지 삭제 중 오류가 발생했습니다: {e}"
        )


# ============================================================
# 청소 명령어 에러 처리 (추가됨)
# ============================================================

@clear_command.error
async def clear_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ 이 명령어를 사용하려면 `메시지 관리` 권한이 필요합니다.",
            ephemeral=True
        )
        return

    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏰ 잠시 후 다시 시도해주세요. (남은 시간: {round(error.retry_after)}초)",
            ephemeral=True
        )
        return

    # 기타 오류
    print(f"❌ 청소 명령어 오류: {error}")
    
    if not interaction.response.is_done():
        await interaction.response.send_message(
            "❌ 명령어 실행 중 오류가 발생했습니다.",
            ephemeral=True
        )


# ============================================================
# 임베드 / 텍스트 카드
# ============================================================

@tree.command(
    name="임베드",
    description="임베드 메시지를 생성합니다"
)
@app_commands.describe(
    내용="표시할 내용",
    제목="제목 (선택)"
)
async def embed_command(
    interaction: discord.Interaction,
    내용: str,
    제목: str = None
):
    """텍스트 카드 메시지 생성"""

    if 제목:
        text = f"# {제목}\n\n{내용}"
    else:
        text = 내용

    try:
        container = discord.ui.Container(
            discord.ui.TextDisplay(text)
        )

        view = discord.ui.LayoutView()
        view.add_item(container)

        await interaction.channel.send(
            view=view
        )

        await interaction.response.send_message(
            "✅ 메시지가 생성되었습니다!",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ 메시지를 전송할 권한이 없습니다.",
            ephemeral=True
        )

    except Exception as e:
        print(f"❌ 임베드 생성 오류: {e}")

        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ 메시지를 생성하는 중 오류가 발생했습니다.",
                ephemeral=True
            )


# ============================================================
# 서버 정보
# ============================================================

@tree.command(
    name="서버정보",
    description="서버의 기본 정보를 표시합니다"
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
    bots = sum(
        1 for member in guild.members
        if member.bot
    )
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
        f"# 📊 {guild.name}\n\n"
        f"👤 **Humans:** {humans}\n"
        f"🤖 **Bots:** {bots}\n"
        f"👥 **Members:** {total}\n\n"
        f"📅 **생성일:** {created_at}\n"
        f"👑 **서버장:** {owner_text}\n"
        f"📌 **채널 수:** {len(guild.channels)}\n"
        f"🎨 **역할 수:** {len(guild.roles)}"
    )

    try:
        container = discord.ui.Container(
            discord.ui.TextDisplay(text)
        )

        view = discord.ui.LayoutView()
        view.add_item(container)

        await interaction.response.send_message(
            view=view
        )

    except Exception as e:
        print(f"❌ 서버 정보 오류: {e}")

        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ 서버 정보를 표시하는 중 오류가 발생했습니다.",
                ephemeral=True
            )


# ============================================================
# 정보 채널 명령어
# ============================================================

@tree.command(
    name="정보채널",
    description="서버 정보 채널을 생성하거나 업데이트합니다"
)
async def info_channel(interaction: discord.Interaction):

    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ 서버에서만 사용할 수 있습니다.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🔄 서버 정보 채널을 업데이트하는 중...",
        ephemeral=True
    )

    try:

        await update_info_channels(
            interaction.guild
        )

        await interaction.edit_original_response(
            content="✅ 서버 정보 채널이 업데이트되었습니다!"
        )

    except Exception as e:

        print(
            f"❌ 정보 채널 업데이트 오류: {e}"
        )

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

    latency = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 퐁! 응답 속도: {latency}ms",
        ephemeral=True
    )


# ============================================================
# 봇 준비
# ============================================================

@bot.event
async def on_ready():

    print(
        f"✅ {bot.user} 실행됨"
    )

    try:

        await tree.sync()

        print(
            "✅ 명령어 동기화 완료"
        )

    except Exception as e:

        print(
            f"❌ 명령어 동기화 실패: {e}"
        )

    # 모든 서버 정보 채널 업데이트
    for guild in bot.guilds:

        try:

            await update_info_channels(
                guild
            )

            print(
                f"✅ {guild.name} "
                f"정보 채널 준비 완료"
            )

        except Exception as e:

            print(
                f"❌ {guild.name} "
                f"정보 채널 오류: {e}"
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

        await update_info_channels(
            member.guild
        )

        print(
            f"👤 {member} 입장 - "
            f"{member.guild.name} 정보 업데이트"
        )

    except Exception as e:

        print(
            f"❌ 멤버 입장 처리 오류: {e}"
        )


# ============================================================
# 멤버 퇴장
# ============================================================

@bot.event
async def on_member_remove(member):

    try:

        await update_info_channels(
            member.guild
        )

        print(
            f"👋 {member} 퇴장 - "
            f"{member.guild.name} 정보 업데이트"
        )

    except Exception as e:

        print(
            f"❌ 멤버 퇴장 처리 오류: {e}"
        )


# ============================================================
# 서버 입장
# ============================================================

@bot.event
async def on_guild_join(guild):

    try:

        await update_info_channels(
            guild
        )

        print(
            f"✅ {guild.name} 서버에 입장했습니다."
        )

    except Exception as e:

        print(
            f"❌ 서버 입장 처리 오류: {e}"
        )


# ============================================================
# 에러 처리
# ============================================================

@bot.event
async def on_error(
    event,
    *args,
    **kwargs
):

    print(
        f"❌ 이벤트 오류: {event}"
    )


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    token = os.getenv(
        "DISCORD_TOKEN"
    )

    if not token:

        print(
            "❌ DISCORD_TOKEN 환경변수가 없습니다!"
        )

        exit(1)

    try:

        bot.run(token)

    except discord.errors.LoginFailure:

        print(
            "❌ 잘못된 토큰입니다. "
            "DISCORD_TOKEN을 확인해주세요."
        )

    except Exception as e:

        print(
            f"❌ 오류 발생: {e}"
        )
