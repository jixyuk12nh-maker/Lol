import os
import json
import logging
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# 기본 설정
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "bot_data.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("InfoBot")


# ============================================================
# 데이터
# ============================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "log_channels": {}
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "log_channels" not in data:
            data["log_channels"] = {}

        return data

    except Exception as e:
        logger.error(f"데이터 불러오기 실패: {e}")

        return {
            "log_channels": {}
        }


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )

    except Exception as e:
        logger.error(f"데이터 저장 실패: {e}")


data = load_data()


# ============================================================
# Components V2 카드
# ============================================================

class TextCardView(discord.ui.LayoutView):
    """
    Components V2

    LayoutView
    └── Container
        ├── TextDisplay
        ├── Separator
        ├── TextDisplay
        └── TextDisplay
    """

    def __init__(
        self,
        title: str,
        content: str,
        footer: Optional[str] = None
    ):
        super().__init__(timeout=None)

        container = discord.ui.Container()

        # 제목
        container.add_item(
            discord.ui.TextDisplay(
                f"# {title}"
            )
        )

        # 구분선
        container.add_item(
            discord.ui.Separator()
        )

        # 내용
        container.add_item(
            discord.ui.TextDisplay(
                content
            )
        )

        # 푸터
        if footer:
            container.add_item(
                discord.ui.Separator()
            )

            container.add_item(
                discord.ui.TextDisplay(
                    f"*{footer}*"
                )
            )

        self.add_item(container)


# ============================================================
# 맞춤 환영 Modal
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
# 입장 로그 버튼 / 드롭다운
# ============================================================

class JoinLogView(discord.ui.LayoutView):

    def __init__(
        self,
        member: discord.Member
    ):
        super().__init__(timeout=None)

        self.member_id = member.id

        container = discord.ui.Container()

        # ----------------------------------------------------
        # 버튼
        # ----------------------------------------------------

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

        role_button.callback = self.give_role_callback

        action_row = discord.ui.ActionRow()

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
                    description="기본 환영 메시지",
                    emoji="👋"
                ),
                discord.SelectOption(
                    label="따뜻한 환영",
                    value="warm",
                    description="따뜻한 환영 메시지",
                    emoji="❤️"
                ),
                discord.SelectOption(
                    label="공식 환영",
                    value="official",
                    description="공식 환영 메시지",
                    emoji="📜"
                ),
                discord.SelectOption(
                    label="맞춤 환영",
                    value="custom",
                    description="직접 환영 메시지 작성",
                    emoji="✏️"
                )
            ]
        )

        select.callback = self.welcome_callback

        select_row = discord.ui.ActionRow()
        select_row.add_item(select)

        container.add_item(select_row)

        self.add_item(container)

    # ========================================================
    # 역할 부여
    # ========================================================

    async def give_role_callback(
        self,
        interaction: discord.Interaction
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ 서버에서만 사용할 수 있습니다.",
                ephemeral=True
            )
            return

        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ 역할 관리 권한이 없습니다.",
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(
            self.member_id
        )

        if not member:
            await interaction.response.send_message(
                "❌ 해당 멤버를 찾을 수 없습니다.",
                ephemeral=True
            )
            return

        # 기본 역할 찾기
        default_role = None

        for role in interaction.guild.roles:
            if role.name.lower() in (
                "멤버",
                "member"
            ):
                default_role = role
                break

        # 멤버 역할이 없으면 두 번째 역할 사용
        if default_role is None:

            normal_roles = [
                role
                for role in interaction.guild.roles
                if role != interaction.guild.default_role
                and not role.managed
            ]

            if normal_roles:
                default_role = normal_roles[0]

        if default_role is None:
            await interaction.response.send_message(
                "❌ 부여할 역할을 찾을 수 없습니다.",
                ephemeral=True
            )
            return

        # 봇보다 높은 역할인지 확인
        if default_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "❌ 봇보다 높거나 같은 위치의 역할은 부여할 수 없습니다.",
                ephemeral=True
            )
            return

        try:
            await member.add_roles(
                default_role,
                reason=f"입장 로그 버튼 - {interaction.user}"
            )

            view = TextCardView(
                "✅ 역할 부여 완료",
                (
                    f"{member.mention}님에게 "
                    f"**{default_role.name}** 역할을 부여했습니다."
                )
            )

            await interaction.response.send_message(
                view=view,
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ 봇에게 역할을 부여할 권한이 없습니다.",
                ephemeral=True
            )

        except Exception as e:
            logger.exception(
                f"역할 부여 실패: {e}"
            )

            await interaction.response.send_message(
                "❌ 역할 부여 중 오류가 발생했습니다.",
                ephemeral=True
            )

    # ========================================================
    # 환영 메시지
    # ========================================================

    async def welcome_callback(
        self,
        interaction: discord.Interaction
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ 서버에서만 사용할 수 있습니다.",
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(
            self.member_id
        )

        if not member:
            await interaction.response.send_message(
                "❌ 해당 멤버를 찾을 수 없습니다.",
                ephemeral=True
            )
            return

        values = interaction.data.get(
            "values",
            []
        )

        if not values:
            return

        selected = values[0]

        # 맞춤 메시지
        if selected == "custom":
            await interaction.response.send_modal(
                WelcomeModal(member)
            )
            return

        messages = {
            "default": (
                f"👋 {member.mention}님, "
                f"서버에 오신 것을 환영합니다!"
            ),

            "warm": (
                f"❤️ {member.mention}님, "
                f"따뜻하게 환영합니다!\n"
                f"함께 즐거운 시간을 만들어봐요!"
            ),

            "official": (
                f"📜 {member.mention}님, "
                f"서버 입장을 환영합니다.\n"
                f"서버 규칙을 확인하시고 즐거운 활동 부탁드립니다."
            )
        }

        content = messages.get(
            selected,
            f"👋 {member.mention}님을 환영합니다!"
        )

        view = TextCardView(
            "👋 환영합니다!",
            content,
            f"{member.name}님 입장을 환영합니다!"
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

        # 중요
        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    # ========================================================
    # 초기화
    # ========================================================

    async def setup_hook(self):

        try:
            await self.tree.sync()

            logger.info(
                "✅ Slash Command 동기화 완료"
            )

        except Exception as e:
            logger.exception(
                f"❌ Slash Command 동기화 실패: {e}"
            )

    # ========================================================
    # 정보 채널 업데이트
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
                f"❌ {guild.name}: Manage Channels 권한 없음"
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

            channel_data = {
                "Members": f"・Members: {total}",
                "Humans": f"・Humans: {humans}",
                "Bots": f"・Bots: {bots}"
            }

            for channel_type, name in channel_data.items():

                await self.create_or_update_info_channel(
                    guild,
                    channel_type,
                    name
                )

        except Exception as e:
            logger.exception(
                f"❌ 정보 채널 업데이트 실패: {e}"
            )

    # ========================================================
    # 정보 채널 생성 / 업데이트
    # ========================================================

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
                        logger.exception(
                            f"❌ 채널 업데이트 실패: {e}"
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
            logger.exception(
                f"❌ 채널 생성 실패: {e}"
            )

    # ========================================================
    # 로그 채널 가져오기
    # ========================================================

    async def get_log_channel(
        self,
        guild: discord.Guild
    ):

        guild_id = str(guild.id)

        # ----------------------------------------------------
        # 저장된 채널
        # ----------------------------------------------------

        channel_id = data["log_channels"].get(
            guild_id
        )

        if channel_id:

            try:

                channel = guild.get_channel(
                    int(channel_id)
                )

                if isinstance(
                    channel,
                    discord.TextChannel
                ):
                    return channel

            except Exception:
                pass

        # ----------------------------------------------------
        # 기존 로그 채널 검색
        # ----------------------------------------------------

        for channel in guild.text_channels:

            if (
                "입장-로그" in channel.name
                or "join-log" in channel.name
                or "join_log" in channel.name
            ):

                data["log_channels"][
                    guild_id
                ] = channel.id

                save_data()

                return channel

        # ----------------------------------------------------
        # 권한 확인
        # ----------------------------------------------------

        if not guild.me.guild_permissions.manage_channels:

            logger.error(
                f"❌ {guild.name}: Manage Channels 권한 없음"
            )

            return None

        # ----------------------------------------------------
        # 관리자 전용 채널 생성
        # ----------------------------------------------------

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

        # 관리자 권한 역할
        for role in guild.roles:

            if role.permissions.administrator:

                overwrites[role] = (
                    discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=False
                    )
                )

        try:

            channel = await guild.create_text_channel(
                "📥-입장-로그",
                overwrites=overwrites,
                reason="관리자 전용 입장 로그 채널 생성"
            )

            data["log_channels"][
                guild_id
            ] = channel.id

            save_data()

            logger.info(
                f"✅ {guild.name}: 관리자 전용 입장 로그 채널 생성"
            )

            return channel

        except discord.Forbidden:

            logger.error(
                f"❌ {guild.name}: 로그 채널 생성 권한 없음"
            )

            return None

        except Exception as e:

            logger.exception(
                f"❌ 로그 채널 생성 실패: {e}"
            )

            return None

    # ========================================================
    # 입장 로그
    # ========================================================

    async def send_join_log(
        self,
        member: discord.Member
    ):

        logger.info(
            f"📥 입장 로그 처리 시작: "
            f"{member} / {member.guild.name}"
        )

        try:

            channel = await self.get_log_channel(
                member.guild
            )

            if channel is None:

                logger.error(
                    f"❌ 로그 채널을 찾을 수 없음: "
                    f"{member.guild.name}"
                )

                return

            logger.info(
                f"📌 로그 채널: "
                f"#{channel.name} ({channel.id})"
            )

            # ------------------------------------------------
            # 멤버 정보
            # ------------------------------------------------

            created_at = member.created_at.strftime(
                "%Y년 %m월 %d일 %H:%M"
            )

            joined_at = datetime.now().strftime(
                "%Y년 %m월 %d일 %H:%M:%S"
            )

            total = member.guild.member_count or 0

            bot_text = (
                "✅ 봇"
                if member.bot
                else "❌ 일반 유저"
            )

            content = (
                f"📛 **이름:** {member.name}\n"
                f"🆔 **ID:** `{member.id}`\n"
                f"👤 **멘션:** {member.mention}\n\n"
                f"📅 **계정 생성일:** {created_at}\n"
                f"🤖 **봇 여부:** {bot_text}\n"
                f"👥 **총 멤버 수:** {total}명"
            )

            # ------------------------------------------------
            # 카드
            # ------------------------------------------------

            card = TextCardView(
                f"👋 새 멤버 입장! - {member.name}",
                content,
                f"입장 시간: {joined_at}"
            )

            await channel.send(
                view=card
            )

            # ------------------------------------------------
            # 버튼
            # ------------------------------------------------

            controls = JoinLogView(
                member
            )

            await channel.send(
                view=controls
            )

            logger.info(
                f"✅ 입장 로그 전송 성공: "
                f"{member} -> #{channel.name}"
            )

        except discord.Forbidden:

            logger.error(
                f"❌ 입장 로그 전송 권한 없음: "
                f"{member.guild.name}"
            )

        except Exception as e:

            logger.exception(
                f"❌ 입장 로그 전송 실패: {e}"
            )


# ============================================================
# 봇 생성
# ============================================================

bot = InfoBot()


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    logger.info(
        f"✅ {bot.user} 실행됨"
    )

    logger.info(
        f"📊 연결 서버: {len(bot.guilds)}개"
    )

    # 중요: Intent 확인
    logger.info(
        f"🔧 Members Intent: "
        f"{bot.intents.members}"
    )

    logger.info(
        f"🔧 Guilds Intent: "
        f"{bot.intents.guilds}"
    )

    logger.info(
        f"🔧 Message Content Intent: "
        f"{bot.intents.message_content}"
    )

    for guild in bot.guilds:

        logger.info(
            f"🏠 서버 연결됨: "
            f"{guild.name} ({guild.id})"
        )

        try:

            await bot.update_info_channels(
                guild
            )

        except Exception as e:

            logger.exception(
                f"❌ {guild.name} 초기화 실패: {e}"
            )


# ============================================================
# 멤버 입장
# ============================================================

@bot.event
async def on_member_join(
    member: discord.Member
):

    logger.info(
        f"🔥 JOIN EVENT 발생! "
        f"서버={member.guild.name} "
        f"유저={member} "
        f"ID={member.id}"
    )

    try:

        # 정보 채널 업데이트
        await bot.update_info_channels(
            member.guild
        )

        # 입장 로그
        await bot.send_join_log(
            member
        )

        logger.info(
            f"✅ 입장 처리 완료: "
            f"{member.guild.name} / {member}"
        )

    except Exception as e:

        logger.exception(
            f"❌ 멤버 입장 처리 실패: {e}"
        )


# ============================================================
# 멤버 퇴장
# ============================================================

@bot.event
async def on_member_remove(
    member: discord.Member
):

    logger.info(
        f"👋 MEMBER REMOVE: "
        f"{member} -> {member.guild.name}"
    )

    try:

        await bot.update_info_channels(
            member.guild
        )

    except Exception as e:

        logger.exception(
            f"❌ 퇴장 처리 실패: {e}"
        )


# ============================================================
# 서버 입장
# ============================================================

@bot.event
async def on_guild_join(
    guild: discord.Guild
):

    logger.info(
        f"➕ 새로운 서버 입장: "
        f"{guild.name} ({guild.id})"
    )

    try:

        await bot.update_info_channels(
            guild
        )

    except Exception as e:

        logger.exception(
            f"❌ 서버 초기화 실패: {e}"
        )


# ============================================================
# /임베드
# ============================================================

@bot.tree.command(
    name="임베드",
    description="Components V2 텍스트 카드를 생성합니다."
)
@app_commands.describe(
    내용="카드 내용",
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

        logger.exception(
            f"❌ 임베드 생성 실패: {e}"
        )

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ 메시지를 생성하는 중 오류가 발생했습니다.",
                ephemeral=True
            )


# ============================================================
# /서버정보
# ============================================================

@bot.tree.command(
    name="서버정보",
    description="서버 정보를 표시합니다."
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

        logger.exception(
            f"❌ 서버 정보 실패: {e}"
        )

        await interaction.response.send_message(
            "❌ 서버 정보를 가져오는 중 오류가 발생했습니다.",
            ephemeral=True
        )


# ============================================================
# /정보채널
# ============================================================

@bot.tree.command(
    name="정보채널",
    description="서버 정보 채널을 생성하거나 업데이트합니다."
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

        logger.exception(
            f"❌ 정보 채널 오류: {e}"
        )

        await interaction.edit_original_response(
            content="❌ 정보 채널 업데이트에 실패했습니다."
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

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ 서버에서만 사용할 수 있습니다.",
            ephemeral=True
        )

        return

    try:

        data["log_channels"][
            str(interaction.guild.id)
        ] = 채널.id

        save_data()

        view = TextCardView(
            "📥 로그 채널 설정",
            (
                f"입장 로그 채널이 "
                f"{채널.mention}으로 설정되었습니다."
            )
        )

        await interaction.response.send_message(
            view=view,
            ephemeral=True
        )

    except Exception as e:

        logger.exception(
            f"❌ 로그 채널 설정 실패: {e}"
        )

        await interaction.response.send_message(
            "❌ 로그 채널 설정에 실패했습니다.",
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
# Slash Command 에러
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    logger.exception(
        f"❌ Slash Command 오류: {error}"
    )

    if isinstance(
        error,
        app_commands.MissingPermissions
    ):

        message = (
            "❌ 이 명령어를 사용할 권한이 없습니다."
        )

    else:

        message = (
            "❌ 명령어 실행 중 오류가 발생했습니다."
        )

    try:

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

    except Exception:
        pass


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    if not TOKEN:

        logger.error(
            "❌ DISCORD_TOKEN 환경변수가 없습니다!"
        )

        raise SystemExit(1)

    logger.info(
        "🚀 InfoBot 시작 중..."
    )

    try:

        bot.run(TOKEN)

    except discord.LoginFailure:

        logger.error(
            "❌ Discord 토큰이 잘못되었습니다."
        )

    except Exception as e:

        logger.exception(
            f"❌ 봇 실행 실패: {e}"
        )
