import os
import json
import re
from datetime import datetime

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

DATA_FILE = "bot_data.json"


# ============================================================
# 데이터
# ============================================================

DEFAULT_DATA = {
    "guilds": {}
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA.copy()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "guilds" not in data:
            data["guilds"] = {}

        return data

    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return DEFAULT_DATA.copy()


data = load_data()


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
        print(f"❌ 데이터 저장 실패: {e}")


def get_guild_data(guild_id):
    guild_id = str(guild_id)

    if guild_id not in data["guilds"]:
        data["guilds"][guild_id] = {
            "join_log_channel": None,

            "ticket": {
                "role_id": None,
                "panel_channel_id": None,
                "panel_message_id": None,

                "title": "🎫 문의하기",
                "description": "문의하실 항목을 선택해주세요.",

                "close_button": "🔒 티켓 닫기",
                "delete_button": "🗑️ 티켓 삭제",

                "types": [
                    {
                        "name": "구매 문의",
                        "emoji": "🛒",
                        "description": "구매와 관련된 문의"
                    },
                    {
                        "name": "결제 문의",
                        "emoji": "💳",
                        "description": "결제와 관련된 문의"
                    },
                    {
                        "name": "오류 문의",
                        "emoji": "🛠️",
                        "description": "오류와 관련된 문의"
                    },
                    {
                        "name": "기타 문의",
                        "emoji": "❓",
                        "description": "기타 문의"
                    }
                ]
            }
        }

        save_data()

    return data["guilds"][guild_id]


# ============================================================
# 관리자 확인
# ============================================================

def is_admin(interaction: discord.Interaction):

    if interaction.guild is None:
        return False

    if interaction.user.guild_permissions.administrator:
        return True

    return False


async def admin_only(interaction: discord.Interaction):

    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ 관리자만 사용할 수 있습니다.",
            ephemeral=True
        )
        return False

    return True


# ============================================================
# 서버 정보 채널
# ============================================================

async def update_info_channels(guild):

    if guild is None:
        return

    total = guild.member_count or 0

    bots = sum(
        1 for member in guild.members
        if member.bot
    )

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


async def create_or_update_channel(
    guild,
    channel_type,
    name
):

    for channel in guild.channels:

        if not isinstance(
            channel,
            discord.VoiceChannel
        ):
            continue

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
                        f"{channel_type} 이름 변경 권한 없음"
                    )

                except discord.HTTPException as e:
                    print(
                        f"❌ {guild.name}: "
                        f"업데이트 실패: {e}"
                    )

            return channel

    overwrites = {
        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=True,
                connect=False
            )
    }

    if guild.me:

        overwrites[guild.me] = \
            discord.PermissionOverwrite(
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
# Components V2 유틸
# ============================================================

def make_layout(*items):

    view = discord.ui.LayoutView(
        timeout=None
    )

    for item in items:
        view.add_item(item)

    return view


def make_container(*items):

    return discord.ui.Container(
        *items
    )


# ============================================================
# /임베드
# ============================================================

@tree.command(
    name="임베드",
    description="Components V2 메시지를 생성합니다"
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

    if 제목:
        text = f"# {제목}\n\n{내용}"
    else:
        text = 내용

    try:

        container = discord.ui.Container(
            discord.ui.TextDisplay(text)
        )

        view = discord.ui.LayoutView(
            timeout=None
        )

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

        print(
            f"❌ 임베드 오류: {e}"
        )

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ 메시지를 생성하는 중 오류가 발생했습니다.",
                ephemeral=True
            )


# ============================================================
# /서버정보
# ============================================================

@tree.command(
    name="서버정보",
    description="서버 정보를 표시합니다"
)
async def server_info(
    interaction: discord.Interaction
):

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

    owner_text = (
        owner.mention
        if owner
        else "알 수 없음"
    )

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

        view = discord.ui.LayoutView(
            timeout=None
        )

        view.add_item(container)

        await interaction.response.send_message(
            view=view
        )

    except Exception as e:

        print(
            f"❌ 서버 정보 오류: {e}"
        )

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ 서버 정보를 표시하는 중 오류가 발생했습니다.",
                ephemeral=True
            )


# ============================================================
# /정보채널
# ============================================================

@tree.command(
    name="정보채널",
    description="서버 정보 채널을 생성하거나 업데이트합니다"
)
async def info_channel(
    interaction: discord.Interaction
):

    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ 서버에서만 사용할 수 있습니다.",
            ephemeral=True
        )

        return

    if not await admin_only(interaction):
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
            f"❌ 정보 채널 오류: {e}"
        )

        await interaction.edit_original_response(
            content="❌ 정보 채널 업데이트 중 오류가 발생했습니다."
        )


# ============================================================
# 입장 로그
# ============================================================

@tree.command(
    name="입장로그",
    description="현재 채널을 입장 로그 채널로 설정합니다"
)
async def join_log(
    interaction: discord.Interaction
):

    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ 서버에서만 사용할 수 있습니다.",
            ephemeral=True
        )

        return

    if not await admin_only(interaction):
        return

    guild_data = get_guild_data(
        interaction.guild.id
    )

    guild_data["join_log_channel"] = \
        interaction.channel.id

    save_data()

    await interaction.response.send_message(
        "✅ 이 채널이 입장 로그 채널로 설정되었습니다.",
        ephemeral=True
    )


# ============================================================
# 입장 로그 전송
# ============================================================

async def send_join_log(member):

    guild_data = get_guild_data(
        member.guild.id
    )

    channel_id = \
        guild_data.get("join_log_channel")

    if not channel_id:
        return

    channel = member.guild.get_channel(
        channel_id
    )

    if channel is None:
        return

    bot_text = (
        "🤖 봇"
        if member.bot
        else "❌ 일반 유저"
    )

    created = member.created_at.strftime(
        "%Y년 %m월 %d일 %H:%M"
    )

    total = member.guild.member_count or 0

    text = (
        f"📛 이름: {member}\n"
        f"🆔 ID: `{member.id}`\n"
        f"👤 멘션: {member.mention}\n\n"
        f"📅 계정 생성일: {created}\n"
        f"🤖 봇 여부: {bot_text}\n"
        f"👥 총 멤버 수: {total}명"
    )

    try:

        container = discord.ui.Container(
            discord.ui.TextDisplay(text)
        )

        view = discord.ui.LayoutView(
            timeout=None
        )

        view.add_item(container)

        await channel.send(
            view=view
        )

    except Exception as e:

        print(
            f"❌ 입장 로그 전송 실패: {e}"
        )


# ============================================================
# 티켓 패널 생성
# ============================================================

def build_ticket_panel(guild):

    guild_data = get_guild_data(
        guild.id
    )

    ticket = guild_data["ticket"]

    container = discord.ui.Container()

    container.add_item(
        discord.ui.TextDisplay(
            f"# {ticket['title']}"
        )
    )

    container.add_item(
        discord.ui.TextDisplay(
            ticket["description"]
        )
    )

    # --------------------------------------------------------
    # 드롭다운
    # --------------------------------------------------------

    options = []

    for index, item in enumerate(
        ticket["types"]
    ):

        options.append(
            discord.SelectOption(
                label=item["name"][:100],
                description=item["description"][:100],
                emoji=item["emoji"],
                value=str(index)
            )
        )

    if not options:

        options.append(
            discord.SelectOption(
                label="문의 유형 없음",
                description="관리자가 티켓 유형을 추가해주세요.",
                value="none"
            )
        )

    select = TicketTypeSelect(
        guild.id,
        options=options
    )

    row = discord.ui.ActionRow(
        select
    )

    container.add_item(row)

    view = discord.ui.LayoutView(
        timeout=None
    )

    view.add_item(container)

    return view


# ============================================================
# 티켓 드롭다운
# ============================================================

class TicketTypeSelect(
    discord.ui.Select
):

    def __init__(
        self,
        guild_id,
        options
    ):

        self.guild_id = guild_id

        super().__init__(
            placeholder="티켓 유형을 선택하세요",
            options=options,
            custom_id=f"ticket_select:{guild_id}"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if self.values[0] == "none":

            await interaction.response.send_message(
                "❌ 등록된 티켓 유형이 없습니다.",
                ephemeral=True
            )

            return

        guild_data = get_guild_data(
            interaction.guild.id
        )

        types = \
            guild_data["ticket"]["types"]

        index = int(self.values[0])

        if index >= len(types):

            await interaction.response.send_message(
                "❌ 해당 티켓 유형이 존재하지 않습니다.",
                ephemeral=True
            )

            return

        ticket_type = types[index]

        await create_ticket(
            interaction,
            ticket_type
        )


# ============================================================
# 티켓 생성
# ============================================================

async def create_ticket(
    interaction,
    ticket_type
):

    guild = interaction.guild
    member = interaction.user

    guild_data = get_guild_data(
        guild.id
    )

    ticket_config = \
        guild_data["ticket"]

    # --------------------------------------------------------
    # 기존 티켓 확인
    # --------------------------------------------------------

    for channel in guild.text_channels:

        if channel.topic == f"ticket_owner:{member.id}":

            await interaction.response.send_message(
                f"❌ 이미 열려있는 티켓이 있습니다.\n{channel.mention}",
                ephemeral=True
            )

            return

    # --------------------------------------------------------
    # 역할
    # --------------------------------------------------------

    role_id = \
        ticket_config.get("role_id")

    support_role = None

    if role_id:

        support_role = guild.get_role(
            role_id
        )

    # --------------------------------------------------------
    # 권한
    # --------------------------------------------------------

    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        member:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )
    }

    if support_role:

        overwrites[support_role] = \
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            )

    if guild.me:

        overwrites[guild.me] = \
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )

    # --------------------------------------------------------
    # 채널 이름
    # --------------------------------------------------------

    safe_name = re.sub(
        r"[^a-zA-Z0-9가-힣_-]",
        "",
        member.display_name
    ).lower()

    safe_name = safe_name[:20]

    if not safe_name:
        safe_name = "user"

    channel_name = f"ticket-{safe_name}"

    # --------------------------------------------------------
    # 티켓 채널 생성
    # --------------------------------------------------------

    try:

        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            topic=f"ticket_owner:{member.id}",
            reason="티켓 생성"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ 채널을 생성할 권한이 없습니다.",
            ephemeral=True
        )

        return

    except discord.HTTPException as e:

        print(
            f"❌ 티켓 생성 실패: {e}"
        )

        await interaction.response.send_message(
            "❌ 티켓을 생성하지 못했습니다.",
            ephemeral=True
        )

        return

    # --------------------------------------------------------
    # 티켓 UI
    # --------------------------------------------------------

    text = (
        f"# {ticket_type['emoji']} {ticket_type['name']}\n\n"
        f"👤 문의자: {member.mention}\n\n"
        f"문의 내용을 남겨주세요."
    )

    container = discord.ui.Container()

    container.add_item(
        discord.ui.TextDisplay(text)
    )

    action_row = discord.ui.ActionRow()

    action_row.add_item(
        TicketCloseButton(
            guild.id,
            ticket_config["close_button"]
        )
    )

    action_row.add_item(
        TicketDeleteButton(
            guild.id,
            ticket_config["delete_button"]
        )
    )

    container.add_item(
        action_row
    )

    view = discord.ui.LayoutView(
        timeout=None
    )

    view.add_item(container)

    try:

        await channel.send(
            view=view
        )

        await interaction.response.send_message(
            f"✅ 티켓이 생성되었습니다.\n{channel.mention}",
            ephemeral=True
        )

    except Exception as e:

        print(
            f"❌ 티켓 메시지 오류: {e}"
        )

        await interaction.response.send_message(
            f"✅ 티켓이 생성되었습니다.\n{channel.mention}",
            ephemeral=True
        )


# ============================================================
# 티켓 권한 확인
# ============================================================

def can_manage_ticket(
    interaction
):

    if interaction.guild is None:
        return False

    guild_data = get_guild_data(
        interaction.guild.id
    )

    role_id = \
        guild_data["ticket"].get(
            "role_id"
        )

    if interaction.user.guild_permissions.administrator:
        return True

    if role_id:

        role = interaction.guild.get_role(
            role_id
        )

        if role and role in interaction.user.roles:
            return True

    return False


# ============================================================
# 티켓 닫기 버튼
# ============================================================

class TicketCloseButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id,
        label
    ):

        self.guild_id = guild_id

        super().__init__(
            label=label[:80],
            emoji="🔒",
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket_close:{guild_id}"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        channel = interaction.channel

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            return

        owner_id = None

        if channel.topic:

            match = re.match(
                r"ticket_owner:(\d+)",
                channel.topic
            )

            if match:
                owner_id = int(
                    match.group(1)
                )

        if (
            interaction.user.id != owner_id
            and not can_manage_ticket(interaction)
        ):

            await interaction.response.send_message(
                "❌ 이 티켓을 닫을 권한이 없습니다.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🔒 티켓을 닫았습니다."
        )

        if owner_id:

            member = interaction.guild.get_member(
                owner_id
            )

            if member:

                await channel.set_permissions(
                    member,
                    view_channel=False,
                    send_messages=False
                )


# ============================================================
# 티켓 삭제 버튼
# ============================================================

class TicketDeleteButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id,
        label
    ):

        self.guild_id = guild_id

        super().__init__(
            label=label[:80],
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id=f"ticket_delete:{guild_id}"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if not can_manage_ticket(
            interaction
        ):

            await interaction.response.send_message(
                "❌ 관리자 또는 설정된 역할만 삭제할 수 있습니다.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🗑️ 티켓을 삭제합니다..."
        )

        try:

            await interaction.channel.delete(
                reason=f"티켓 삭제 - {interaction.user}"
            )

        except discord.Forbidden:

            print(
                "❌ 티켓 삭제 권한 없음"
            )

        except discord.HTTPException as e:

            print(
                f"❌ 티켓 삭제 실패: {e}"
            )


# ============================================================
# 티켓 설정 UI
# ============================================================

class TicketSettingsView(
    discord.ui.LayoutView
):

    def __init__(
        self,
        guild_id
    ):

        super().__init__(
            timeout=180
        )

        self.guild_id = guild_id

        guild_data = get_guild_data(
            guild_id
        )

        ticket = guild_data["ticket"]

        text = (
            "# 🎫 티켓 설정\n\n"
            f"📌 제목: **{ticket['title']}**\n"
            f"📝 설명: **{ticket['description']}**\n\n"
            f"👮 티켓 담당 역할: "
            f"{self.get_role_text(guild_id)}\n\n"
            f"🔒 닫기 버튼: **{ticket['close_button']}**\n"
            f"🗑️ 삭제 버튼: **{ticket['delete_button']}**\n\n"
            f"📋 티켓 유형: **{len(ticket['types'])}개**"
        )

        container = discord.ui.Container()

        container.add_item(
            discord.ui.TextDisplay(text)
        )

        row1 = discord.ui.ActionRow()

        row1.add_item(
            TicketRoleButton(guild_id)
        )

        row1.add_item(
            TicketTitleButton(guild_id)
        )

        row1.add_item(
            TicketDescriptionButton(guild_id)
        )

        row2 = discord.ui.ActionRow()

        row2.add_item(
            TicketAddTypeButton(guild_id)
        )

        row2.add_item(
            TicketRemoveTypeButton(guild_id)
        )

        row2.add_item(
            TicketButtonNameButton(guild_id)
        )

        row3 = discord.ui.ActionRow()

        row3.add_item(
            TicketPanelCreateButton(guild_id)
        )

        container.add_item(row1)
        container.add_item(row2)
        container.add_item(row3)

        self.add_item(container)

    @staticmethod
    def get_role_text(guild_id):

        guild = bot.get_guild(
            guild_id
        )

        if guild is None:
            return "설정되지 않음"

        role_id = get_guild_data(
            guild_id
        )["ticket"].get("role_id")

        if not role_id:
            return "설정되지 않음"

        role = guild.get_role(
            role_id
        )

        return (
            role.mention
            if role
            else "삭제된 역할"
        )


# ============================================================
# 설정 버튼 - 역할
# ============================================================

class TicketRoleButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="역할 설정",
            emoji="👮",
            style=discord.ButtonStyle.primary,
            custom_id=f"ticket_setting_role:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_message(
            "사용할 역할을 선택해주세요.",
            view=RoleSettingView(
                self.guild_id
            ),
            ephemeral=True
        )


class RoleSettingView(
    discord.ui.View
):

    def __init__(
        self,
        guild_id
    ):

        super().__init__(
            timeout=120
        )

        self.guild_id = guild_id

        self.add_item(
            RoleSelectSetting(
                guild_id
            )
        )


class RoleSelectSetting(
    discord.ui.RoleSelect
):

    def __init__(
        self,
        guild_id
    ):

        self.guild_id = guild_id

        super().__init__(
            placeholder="티켓을 볼 역할 선택",
            min_values=1,
            max_values=1
        )

    async def callback(
        self,
        interaction
    ):

        role = self.values[0]

        guild_data = get_guild_data(
            self.guild_id
        )

        guild_data["ticket"]["role_id"] = \
            role.id

        save_data()

        await interaction.response.send_message(
            f"✅ 티켓 담당 역할을 {role.mention}으로 설정했습니다.",
            ephemeral=True
        )


# ============================================================
# 설정 버튼 - 제목
# ============================================================

class TicketTitleButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id
    ):

        self.guild_id = guild_id

        super().__init__(
            label="제목 변경",
            emoji="📝",
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket_setting_title:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            TicketTitleModal(
                self.guild_id
            )
        )


class TicketTitleModal(
    discord.ui.Modal,
    title="티켓 제목 변경"
):

    title_input = discord.ui.TextInput(
        label="티켓 패널 제목",
        placeholder="예: 🎫 문의하기",
        max_length=100
    )

    def __init__(
        self,
        guild_id
    ):

        super().__init__()

        self.guild_id = guild_id

    async def on_submit(
        self,
        interaction
    ):

        guild_data = get_guild_data(
            self.guild_id
        )

        guild_data["ticket"]["title"] = \
            str(self.title_input.value)

        save_data()

        await interaction.response.send_message(
            "✅ 티켓 제목이 변경되었습니다.",
            ephemeral=True
        )


# ============================================================
# 설정 버튼 - 설명
# ============================================================

class TicketDescriptionButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id
    ):

        self.guild_id = guild_id

        super().__init__(
            label="설명 변경",
            emoji="📄",
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket_setting_description:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            TicketDescriptionModal(
                self.guild_id
            )
        )


class TicketDescriptionModal(
    discord.ui.Modal,
    title="티켓 설명 변경"
):

    description_input = discord.ui.TextInput(
        label="티켓 패널 설명",
        placeholder="문의하실 항목을 선택해주세요.",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    def __init__(
        self,
        guild_id
    ):

        super().__init__()

        self.guild_id = guild_id

    async def on_submit(
        self,
        interaction
    ):

        guild_data = get_guild_data(
            self.guild_id
        )

        guild_data["ticket"]["description"] = \
            str(self.description_input.value)

        save_data()

        await interaction.response.send_message(
            "✅ 티켓 설명이 변경되었습니다.",
            ephemeral=True
        )


# ============================================================
# 티켓 유형 추가
# ============================================================

class TicketAddTypeButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id
    ):

        self.guild_id = guild_id

        super().__init__(
            label="유형 추가",
            emoji="➕",
            style=discord.ButtonStyle.success,
            custom_id=f"ticket_setting_add:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            TicketAddTypeModal(
                self.guild_id
            )
        )


class TicketAddTypeModal(
    discord.ui.Modal,
    title="티켓 유형 추가"
):

    name_input = discord.ui.TextInput(
        label="유형 이름",
        placeholder="예: 환불 문의",
        max_length=80
    )

    emoji_input = discord.ui.TextInput(
        label="이모지",
        placeholder="예: 💰",
        max_length=10
    )

    description_input = discord.ui.TextInput(
        label="설명",
        placeholder="환불과 관련된 문의",
        max_length=100
    )

    def __init__(
        self,
        guild_id
    ):

        super().__init__()

        self.guild_id = guild_id

    async def on_submit(
        self,
        interaction
    ):

        guild_data = get_guild_data(
            self.guild_id
        )

        types = \
            guild_data["ticket"]["types"]

        if len(types) >= 25:

            await interaction.response.send_message(
                "❌ 티켓 유형은 최대 25개까지 설정할 수 있습니다.",
                ephemeral=True
            )

            return

        types.append(
            {
                "name": str(
                    self.name_input.value
                ),
                "emoji": str(
                    self.emoji_input.value
                ),
                "description": str(
                    self.description_input.value
                )
            }
        )

        save_data()

        await interaction.response.send_message(
            "✅ 티켓 유형이 추가되었습니다.\n"
            "패널을 다시 생성하면 적용됩니다.",
            ephemeral=True
        )


# ============================================================
# 티켓 유형 삭제
# ============================================================

class TicketRemoveTypeButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id
    ):

        self.guild_id = guild_id

        super().__init__(
            label="유형 삭제",
            emoji="➖",
            style=discord.ButtonStyle.danger,
            custom_id=f"ticket_setting_remove:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        guild_data = get_guild_data(
            self.guild_id
        )

        types = \
            guild_data["ticket"]["types"]

        if not types:

            await interaction.response.send_message(
                "❌ 삭제할 유형이 없습니다.",
                ephemeral=True
            )

            return

        options = []

        for index, item in enumerate(types):

            options.append(
                discord.SelectOption(
                    label=item["name"][:100],
                    emoji=item["emoji"],
                    value=str(index)
                )
            )

        view = discord.ui.View(
            timeout=120
        )

        view.add_item(
            TicketRemoveSelect(
                self.guild_id,
                options
            )
        )

        await interaction.response.send_message(
            "삭제할 티켓 유형을 선택해주세요.",
            view=view,
            ephemeral=True
        )


class TicketRemoveSelect(
    discord.ui.Select
):

    def __init__(
        self,
        guild_id,
        options
    ):

        self.guild_id = guild_id

        super().__init__(
            placeholder="삭제할 유형 선택",
            options=options
        )

    async def callback(
        self,
        interaction
    ):

        index = int(
            self.values[0]
        )

        guild_data = get_guild_data(
            self.guild_id
        )

        types = \
            guild_data["ticket"]["types"]

        if index >= len(types):

            await interaction.response.send_message(
                "❌ 해당 유형을 찾을 수 없습니다.",
                ephemeral=True
            )

            return

        removed = types.pop(index)

        save_data()

        await interaction.response.send_message(
            f"✅ `{removed['name']}` 유형을 삭제했습니다.",
            ephemeral=True
        )


# ============================================================
# 버튼 이름 변경
# ============================================================

class TicketButtonNameButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id
    ):

        self.guild_id = guild_id

        super().__init__(
            label="버튼 이름 변경",
            emoji="🔘",
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket_setting_buttons:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            TicketButtonNameModal(
                self.guild_id
            )
        )


class TicketButtonNameModal(
    discord.ui.Modal,
    title="티켓 버튼 이름 변경"
):

    close_input = discord.ui.TextInput(
        label="닫기 버튼 이름",
        placeholder="예: 🔒 티켓 닫기",
        max_length=80
    )

    delete_input = discord.ui.TextInput(
        label="삭제 버튼 이름",
        placeholder="예: 🗑️ 티켓 삭제",
        max_length=80
    )

    def __init__(
        self,
        guild_id
    ):

        super().__init__()

        self.guild_id = guild_id

    async def on_submit(
        self,
        interaction
    ):

        guild_data = get_guild_data(
            self.guild_id
        )

        ticket = guild_data["ticket"]

        ticket["close_button"] = \
            str(self.close_input.value)

        ticket["delete_button"] = \
            str(self.delete_input.value)

        save_data()

        await interaction.response.send_message(
            "✅ 티켓 버튼 이름이 변경되었습니다.\n"
            "새 티켓부터 적용됩니다.",
            ephemeral=True
        )


# ============================================================
# 패널 생성
# ============================================================

class TicketPanelCreateButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id
    ):

        self.guild_id = guild_id

        super().__init__(
            label="티켓 패널 생성/업데이트",
            emoji="🎫",
            style=discord.ButtonStyle.success,
            custom_id=f"ticket_panel_create:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        guild = interaction.guild

        if guild is None:
            return

        if not is_admin(interaction):

            await interaction.response.send_message(
                "❌ 관리자만 사용할 수 있습니다.",
                ephemeral=True
            )

            return

        await send_or_update_ticket_panel(
            guild,
            interaction.channel
        )

        await interaction.response.send_message(
            "✅ 티켓 패널을 업데이트했습니다.",
            ephemeral=True
        )


async def send_or_update_ticket_panel(
    guild,
    channel
):

    guild_data = get_guild_data(
        guild.id
    )

    ticket = guild_data["ticket"]

    view = build_ticket_panel(
        guild
    )

    # 기존 패널 확인
    channel_id = \
        ticket.get("panel_channel_id")

    message_id = \
        ticket.get("panel_message_id")

    if (
        channel_id == channel.id
        and message_id
    ):

        try:

            old_channel = guild.get_channel(
                channel_id
            )

            if old_channel:

                message = await old_channel.fetch_message(
                    message_id
                )

                await message.edit(
                    view=view
                )

                return message

        except (
            discord.NotFound,
            discord.HTTPException
        ):
            pass

    message = await channel.send(
        view=view
    )

    ticket["panel_channel_id"] = \
        channel.id

    ticket["panel_message_id"] = \
        message.id

    save_data()

    return message


# ============================================================
# /티켓
# ============================================================

@tree.command(
    name="티켓",
    description="Components V2 티켓 패널을 생성합니다"
)
async def ticket_command(
    interaction: discord.Interaction
):

    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ 서버에서만 사용할 수 있습니다.",
            ephemeral=True
        )

        return

    if not await admin_only(interaction):
        return

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        await send_or_update_ticket_panel(
            interaction.guild,
            interaction.channel
        )

        await interaction.followup.send(
            "✅ 티켓 패널을 생성했습니다.",
            ephemeral=True
        )

    except Exception as e:

        print(
            f"❌ 티켓 패널 생성 실패: {e}"
        )

        await interaction.followup.send(
            "❌ 티켓 패널을 생성하지 못했습니다.",
            ephemeral=True
        )


# ============================================================
# /티켓설정
# ============================================================

@tree.command(
    name="티켓설정",
    description="Components V2 티켓 설정 패널을 엽니다"
)
async def ticket_settings(
    interaction: discord.Interaction
):

    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ 서버에서만 사용할 수 있습니다.",
            ephemeral=True
        )

        return

    if not await admin_only(interaction):
        return

    view = TicketSettingsView(
        interaction.guild.id
    )

    await interaction.response.send_message(
        view=view,
        ephemeral=True
    )


# ============================================================
# /핑
# ============================================================

@tree.command(
    name="핑",
    description="봇의 응답 속도를 확인합니다"
)
async def ping(
    interaction: discord.Interaction
):

    latency = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 퐁! 응답 속도: {latency}ms",
        ephemeral=True
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

        await send_join_log(
            member
        )

        print(
            f"👤 {member} 입장 - "
            f"{member.guild.name}"
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
            f"{member.guild.name}"
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

        get_guild_data(
            guild.id
        )

        await update_info_channels(
            guild
        )

        print(
            f"✅ {guild.name} 서버 입장"
        )

    except Exception as e:

        print(
            f"❌ 서버 입장 처리 오류: {e}"
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

    # --------------------------------------------------------
    # 기존 서버 데이터 생성
    # --------------------------------------------------------

    for guild in bot.guilds:

        get_guild_data(
            guild.id
        )

        try:

            await update_info_channels(
                guild
            )

        except Exception as e:

            print(
                f"❌ {guild.name} 정보 채널 오류: {e}"
            )

    print(
        f"📊 총 {len(bot.guilds)}개 서버 연결됨"
    )


# ============================================================
# 이벤트 오류
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

        raise SystemExit(1)

    try:

        bot.run(token)

    except discord.errors.LoginFailure:

        print(
            "❌ 잘못된 토큰입니다."
        )

    except Exception as e:

        print(
            f"❌ 오류 발생: {e}"
            )
