import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# 설정
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

DATA_FILE = "bot_data.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("InfoBot")


# ============================================================
# 데이터 관리
# ============================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "log_channels": {}
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "log_channels": {}
        }


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


data = load_data()


# ============================================================
# Components V2 - 텍스트 카드
# ============================================================

class TextCardView(discord.ui.LayoutView):
    """
    Discord Components V2 카드

    LayoutView
    └── Container
        ├── TextDisplay
        ├── Separator
        └── TextDisplay
    """

    def __init__(
        self,
        title: str,
        content: str,
        footer: Optional[str] = None
    ):
        super().__init__(timeout=None)

        children = []

        # 제목
        children.append(
            discord.ui.TextDisplay(
                f"# {title}"
            )
        )

        # 구분선
        children.append(
            discord.ui.Separator()
        )

        # 본문
        children.append(
            discord.ui.TextDisplay(
                content
            )
        )

        # 푸터
        if footer:
            children.append(
                discord.ui.Separator()
            )

            children.append(
                discord.ui.TextDisplay(
                    f"*{footer}*"
                )
            )

        # Container
        container = discord.ui.Container(
            *children
        )

        self.add_item(container)


# ============================================================
# 입장 로그 Components V2
# ============================================================

class JoinLogView(discord.ui.LayoutView):

    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)

        self.member_id = member.id

        container = discord.ui.Container()

        # ----------------------------------------------------
        # 버튼 ActionRow
        # ----------------------------------------------------

        action_row = discord.ui.ActionRow()

        profile_button = discord.ui.Button(
            label="프로필 보기",
            style=discord.ButtonStyle.link,
            emoji="👤",
            url=f"https://discord.com/users/{member.id}"
        )

        role_button = discord.ui.Button(
            label="기본 역할 부여",
            style=discord.ButtonStyle.success,
            emoji="🎖️",
            custom_id=f"give_role:{member.id}"
        )

        action_row.add_item(profile_button)
        action_row.add_item(role_button)

        container.add_item(action_row)

        # ----------------------------------------------------
        # 환영 메시지 Select
        # ----------------------------------------------------

        select = discord.ui.Select(
            placeholder="환영 메시지 선택",
            custom_id=f"welcome_select:{member.id}",
            options=[
                discord.SelectOption(
                    label="기본 환영",
                    value="default",
                    description="기본 환영 메시지를 보냅니다.",
                    emoji="👋"
                ),
                discord.SelectOption(
                    label="따뜻한 환영",
                    value="warm",
                    description="따뜻한 환영 메시지를 보냅니다.",
                    emoji="❤️"
                ),
                discord.SelectOption(
                    label="공식 환영",
                    value="official",
                    description="공식 환영 메시지를 보냅니다.",
                    emoji="📜"
                ),
                discord.SelectOption(
                    label="맞춤 환영",
                    value="custom",
                    description="직접 환영 메시지를 작성합니다.",
                    emoji="✏️"
                )
            ]
        )

        select.callback = self.welcome_callback

        select_row = discord.ui.ActionRow()
        select_row.add_item(select)

        container.add_item(select_row)

        self.add_item(container)

    async def welcome_callback(
        self,
        interaction: discord.Interaction
    ):

        if not interaction.guild:
            return

        member = interaction.guild.get_member(self.member_id)

        if not member:
            await interaction.response.send_message(
                "❌ 멤버를 찾을 수 없습니다.",
                ephemeral=True
            )
            return

        selected = interaction.data.get("values", [None])[0]

        if selected == "custom":
            await interaction.response.send_modal(
                WelcomeModal(member)
            )
            return

        messages = {
            "default":
                f"👋 {member.mention}님, 서버에 오신 것을 환영합니다!",

            "warm":
                f"❤️ {member.mention}님, 따뜻하게 환영합니다!\n"
                f"함께 즐거운 시간을 보내봐요!",

            "official":
                f"📜 {member.mention}님, 서버 입장을 환영합니다.\n"
                f"서버 규칙을 확인하시고 즐거운 활동 부탁드립니다."
        }

        content = messages.get(
            selected,
            f"👋 {member.mention}님을 환영합니다!"
        )

        view = TextCardView(
            "👋 환영합니다!",
            content,
            f"{member.name}님 입장을 환영합니다."
        )

        await interaction.response.send_message(
            view=view
        )


# ============================================================
# Modal
# ============================================================

class WelcomeModal(discord.ui.Modal):

    def __init__(self, member: discord.Member):
        super().__init__(
            title="✏️ 맞춤 환영 메시지"
        )

        self.member = member

        self.message_input = discord.ui.TextInput(
            label="환영 메시지",
            placeholder=(
                f"{member.name}님에게 보낼 환영 메시지를 입력하세요."
            ),
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=1,
            max_length=1000
        )

        self.add_item(self.message_input)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        content = self.message_input.value

        view = TextCardView(
            "👋 맞춤 환영 메시지",
            content,
            f"{self.member.name}님 입장을 환영합니다!"
        )

        await interaction.response.send_message(
            view=view
        )


# ============================================================
# 봇
# ============================================================

class InfoBot(commands.Bot):

    def __init__(self):

        intents = discord.Intents.default()

        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):

        await self.tree.sync()

        logger.info(
            "✅ Slash Command 동기화 완료"
        )

    # ========================================================
    # 정보 채널
    # ========================================================

    async def update_info_channels(
        self,
        guild: discord.Guild
    ):

        if not guild:
            return

        me = guild.me

        if not me:
            return

        if not me.guild_permissions.manage_channels:

            logger.warning(
                f"❌ {guild.name}: 채널 관리 권한 없음"
            )

            return

        try:

            await guild.chunk()

            total = guild.member_count or 0

            bots = sum(
                1
                for member in guild.members
                if member.bot
            )

            humans = total - bots

            channels = {
                "Members":
                    f"・Members: {total}",

                "Humans":
                    f"・Humans: {humans}",

                "Bots":
                    f"・Bots: {bots}"
            }

            for channel_type, name in channels.items():

                await self.create_or_update_info_channel(
                    guild,
                    channel_type,
                    name
                )

        except Exception as e:

            logger.error(
                f"❌ 정보 채널 업데이트 실패: {e}"
            )

    async def create_or_update_info_channel(
        self,
        guild: discord.Guild,
        channel_type: str,
        name: str
    ):

        for channel in guild.voice_channels:

            if channel_type.lower() in channel.name.lower():

                if channel.name != name:

                    try:

                        await channel.edit(
                            name=name,
                            reason="서버 정보 채널 업데이트"
                        )

                    except Exception as e:

                        logger.error(
                            f"❌ 채널 이름 변경 실패: {e}"
                        )

                return

        try:

            overwrites = {

                guild.default_role:
                    discord.PermissionOverwrite(
                        view_channel=True,
                        connect=False
                    ),

                guild.me:
                    discord.PermissionOverwrite(
                        view_channel=True,
                        connect=True,
                        manage_channels=True
                    )
            }

            await guild.create_voice_channel(
                name=name,
                overwrites=overwrites,
                reason="서버 정보 채널 생성"
            )

            logger.info(
                f"✅ {guild.name}: {name} 생성"
            )

        except Exception as e:

            logger.error(
                f"❌ 정보 채널 생성 실패: {e}"
            )

    # ========================================================
    # 입장 로그 채널
    # ========================================================

    async def get_log_channel(
        self,
        guild: discord.Guild
    ):

        guild_id = str(guild.id)

        channel_id = data["log_channels"].get(
            guild_id
        )

        if channel_id:

            channel = guild.get_channel(
                int(channel_id)
            )

            if isinstance(
                channel,
                discord.TextChannel
            ):

                return channel

        # 기존 채널 검색
        for channel in guild.text_channels:

            if (
                "입장-로그" in channel.name
                or "join-log" in channel.name
                or "join_log" in channel.name
            ):

                data["log_channels"][guild_id] = channel.id
                save_data(data)

                return channel

        # 채널 생성
        if not guild.me.guild_permissions.manage_channels:

            logger.warning(
                f"❌ {guild.name}: 채널 관리 권한 없음"
            )

            return None

        # @everyone에게 숨김
        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            guild.me:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_messages=True
                )
        }

        # 관리자 역할들은 볼 수 있게
        for role in guild.roles:

            if role.permissions.administrator:

                overwrites[role] = (
                    discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=False
                    )
                )

        channel = await guild.create_text_channel(
            "📥-입장-로그",
            overwrites=overwrites,
            reason="관리자 전용 입장 로그 채널 생성"
        )

        data["log_channels"][guild_id] = channel.id
        save_data(data)

        return channel

    # ========================================================
    # 입장 로그
    # ========================================================

    async def send_join_log(
        self,
        member: discord.Member
    ):

        try:

            channel = await self.get_log_channel(
                member.guild
            )

            if not channel:
                return

            created_at = member.created_at.strftime(
                "%Y년 %m월 %d일 %H:%M"
            )

            joined_at = datetime.now().strftime(
                "%Y년 %m월 %d일 %H:%M:%S"
            )

            total_members = (
                member.guild.member_count or 0
            )

            content = (
                f"📛 **이름:** {member.name}\n"
                f"🆔 **ID:** `{member.id}`\n"
                f"👤 **멘션:** {member.mention}\n\n"
                f"📅 **계정 생성일:** {created_at}\n"
                f"🤖 **봇 여부:** "
                f"{'✅ 봇' if member.bot else '❌ 일반 유저'}\n"
                f"👥 **총 멤버 수:** {total_members}명"
            )

            card = TextCardView(
                f"👋 새 멤버 입장! - {member.name}",
                content,
                f"입장 시간: {joined_at}"
            )

            await channel.send(
                view=card
            )

            controls = JoinLogView(member)

            await channel.send(
                view=controls
            )

            logger.info(
                f"👤 {member} 입장 - {member.guild.name}"
            )

        except Exception as e:

            logger.error(
                f"❌ 입장 로그 전송 실패: {e}"
            )


# ============================================================
# 봇 생성
# ============================================================

bot = InfoBot()


# ============================================================
# 이벤트
# ============================================================

@bot.event
async def on_ready():

    logger.info(
        f"✅ {bot.user} 실행됨"
    )

    logger.info(
        f"📊 연결 서버: {len(bot.guilds)}개"
    )

    for guild in bot.guilds:

        try:

            await bot.update_info_channels(
                guild
            )

        except Exception as e:

            logger.error(
                f"❌ {guild.name} 초기화 실패: {e}"
            )


@bot.event
async def on_member_join(
    member: discord.Member
):

    try:

        await bot.update_info_channels(
            member.guild
        )

        await bot.send_join_log(
            member
        )

    except Exception as e:

        logger.error(
            f"❌ 입장 처리 실패: {e}"
        )


@bot.event
async def on_member_remove(
    member: discord.Member
):

    try:

        await bot.update_info_channels(
            member.guild
        )

    except Exception as e:

        logger.error(
            f"❌ 퇴장 처리 실패: {e}"
        )


@bot.event
async def on_guild_join(
    guild: discord.Guild
):

    try:

        await bot.update_info_channels(
            guild
        )

    except Exception as e:

        logger.error(
            f"❌ 서버 입장 처리 실패: {e}"
        )


# ============================================================
# /임베드
# ============================================================

@bot.tree.command(
    name="임베드",
    description="Components V2 텍스트 카드를 생성합니다."
)
@app_commands.describe(
    내용="카드에 표시할 내용",
    제목="카드 제목"
)
async def embed_command(
    interaction: discord.Interaction,
    내용: str,
    제목: Optional[str] = None
):

    try:

        view = TextCardView(
            제목 or "📝 메시지",
            내용,
            f"요청자: {interaction.user.display_name}"
        )

        await interaction.response.send_message(
            view=view
        )

    except Exception as e:

        logger.error(
            f"❌ 임베드 오류: {e}"
        )

        await interaction.response.send_message(
            "❌ 메시지를 생성할 수 없습니다.",
            ephemeral=True
        )


# ============================================================
# /서버정보
# ============================================================

@bot.tree.command(
    name="서버정보",
    description="서버 정보를 Components V2 카드로 표시합니다."
)
async def server_info(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ 서버에서만 사용할 수 있습니다.",
            ephemeral=True
        )

        return

    try:

        guild = interaction.guild

        await guild.chunk()

        total = guild.member_count or 0

        bots = sum(
            1
            for member in guild.members
            if member.bot
        )

        humans = total - bots

        owner = (
            guild.owner.mention
            if guild.owner
            else "알 수 없음"
        )

        content = (
            f"👤 **Humans:** {humans}\n"
            f"🤖 **Bots:** {bots}\n"
            f"👥 **Members:** {total}\n\n"
            f"📅 **생성일:** "
            f"{guild.created_at.strftime('%Y년 %m월 %d일')}\n"
            f"👑 **서버장:** {owner}\n"
            f"📌 **채널 수:** {len(guild.channels)}\n"
            f"🎨 **역할 수:** {len(guild.roles)}"
        )

        view = TextCardView(
            f"📊 {guild.name}",
            content,
            f"요청자: {interaction.user.display_name}"
        )

        await interaction.response.send_message(
            view=view
        )

    except Exception as e:

        logger.error(
            f"❌ 서버 정보 오류: {e}"
        )

        await interaction.response.send_message(
            "❌ 서버 정보를 가져올 수 없습니다.",
            ephemeral=True
        )


# ============================================================
# /정보채널
# ============================================================

@bot.tree.command(
    name="정보채널",
    description="서버 정보 음성 채널을 생성하거나 업데이트합니다."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def info_channel(
    interaction: discord.Interaction
):

    await interaction.response.send_message(
        "🔄 서버 정보 채널을 업데이트하는 중...",
        ephemeral=True
    )

    try:

        await bot.update_info_channels(
            interaction.guild
        )

        await interaction.edit_original_response(
            content="✅ 서버 정보 채널이 업데이트되었습니다!"
        )

    except Exception as e:

        logger.error(
            f"❌ 정보 채널 오류: {e}"
        )

        await interaction.edit_original_response(
            content="❌ 정보 채널 업데이트 실패"
        )


# ============================================================
# /로그채널
# ============================================================

@bot.tree.command(
    name="로그채널",
    description="입장 로그 채널을 설정합니다."
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
@app_commands.describe(
    채널="입장 로그를 보낼 채널"
)
async def set_log_channel(
    interaction: discord.Interaction,
    채널: discord.TextChannel
):

    data["log_channels"][
        str(interaction.guild.id)
    ] = 채널.id

    save_data(data)

    view = TextCardView(
        "📥 로그 채널 설정",
        f"입장 로그 채널이 {채널.mention}으로 설정되었습니다."
    )

    await interaction.response.send_message(
        view=view,
        ephemeral=True
    )


# ============================================================
# /핑
# ============================================================

@bot.tree.command(
    name="핑",
    description="봇의 응답 속도를 확인합니다."
)
async def ping(
    interaction: discord.Interaction
):

    latency = round(
        bot.latency * 1000
    )

    view = TextCardView(
        "🏓 퐁!",
        f"**응답 속도:** `{latency}ms`"
    )

    await interaction.response.send_message(
        view=view,
        ephemeral=True
    )


# ============================================================
# 권한 오류
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    if isinstance(
        error,
        app_commands.MissingPermissions
    ):

        message = (
            "❌ 이 명령어를 사용할 권한이 없습니다."
        )

    else:

        logger.error(
            f"❌ Slash Command 오류: {error}"
        )

        message = (
            "❌ 명령어 실행 중 오류가 발생했습니다."
        )

    if interaction.response.is_done():

        await interaction.followup.send(
            message,
            ephemeral=True
        )

    else:

        await interaction.response.send_message(
            message,
            ephemeral=True
        )


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    if not TOKEN:

        logger.error(
            "❌ DISCORD_TOKEN 환경변수가 없습니다!"
        )

        raise SystemExit(1)

    try:

        bot.run(TOKEN)

    except discord.LoginFailure:

        logger.error(
            "❌ Discord 토큰이 잘못되었습니다."
        )

    except Exception as e:

        logger.error(
            f"❌ 봇 실행 오류: {e}"
        )
