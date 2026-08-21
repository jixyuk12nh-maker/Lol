import os
import json
import re
import discord

from discord import app_commands
from discord.ext import commands


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

def load_data():

    if not os.path.exists(DATA_FILE):
        return {
            "guilds": {}
        }

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception as e:

        print(
            f"❌ 데이터 로드 실패: {e}"
        )

        return {
            "guilds": {}
        }


data = load_data()


def save_data():

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )

    except Exception as e:

        print(
            f"❌ 데이터 저장 실패: {e}"
        )


def get_guild_data(guild_id):

    guild_id = str(guild_id)

    if guild_id not in data["guilds"]:

        data["guilds"][guild_id] = {
            "join_log_channel": None,

            "ticket": {
                "configured": False,

                "panel_channel_id": None,
                "panel_message_id": None,

                "support_role_id": None,

                "title": "🎫 문의하기",

                "description":
                    "문의하실 항목을 선택해주세요.",

                "close_label":
                    "티켓 닫기",

                "delete_label":
                    "티켓 삭제",

                "archive_on_close": True,

                # 처음에는 항목 없음
                "types": []
            }
        }

        save_data()

    guild_data = data["guilds"][guild_id]

    guild_data.setdefault(
        "join_log_channel",
        None
    )

    ticket = guild_data.setdefault(
        "ticket",
        {}
    )

    ticket.setdefault(
        "configured",
        False
    )

    ticket.setdefault(
        "panel_channel_id",
        None
    )

    ticket.setdefault(
        "panel_message_id",
        None
    )

    ticket.setdefault(
        "support_role_id",
        None
    )

    ticket.setdefault(
        "title",
        "🎫 문의하기"
    )

    ticket.setdefault(
        "description",
        "문의하실 항목을 선택해주세요."
    )

    ticket.setdefault(
        "close_label",
        "티켓 닫기"
    )

    ticket.setdefault(
        "delete_label",
        "티켓 삭제"
    )

    ticket.setdefault(
        "archive_on_close",
        True
    )

    ticket.setdefault(
        "types",
        []
    )

    return guild_data


# ============================================================
# 관리자 확인
# ============================================================

def is_admin(interaction):

    return (
        interaction.guild is not None
        and interaction.user.guild_permissions.administrator
    )


async def require_admin(interaction):

    if not is_admin(interaction):

        await interaction.response.send_message(
            "❌ 관리자만 사용할 수 있습니다.",
            ephemeral=True
        )

        return False

    return True


# ============================================================
# Components V2
# ============================================================

def make_v2_view(*items):

    view = discord.ui.LayoutView(
        timeout=None
    )

    for item in items:
        view.add_item(item)

    return view


# ============================================================
# 안전한 채널 이름
# ============================================================

def safe_channel_name(text):

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9가-힣_-]+",
        "-",
        text
    )

    text = text.strip("-")

    if not text:
        text = "ticket"

    return text[:80]


# ============================================================
# 서버 정보 채널
# ============================================================

async def update_info_channels(guild):

    if guild is None:
        return

    total = guild.member_count or 0

    bots = sum(
        1
        for member in guild.members
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
                        f"❌ 채널 업데이트 실패: {e}"
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

        overwrites[guild.me] = (
            discord.PermissionOverwrite(
                view_channel=True,
                connect=True
            )
        )

    try:

        return await guild.create_voice_channel(
            name=name,
            overwrites=overwrites,
            reason="서버 정보 채널 생성"
        )

    except Exception as e:

        print(
            f"❌ 정보 채널 생성 실패: {e}"
        )

        return None


# ============================================================
# /임베드
# ============================================================

@tree.command(
    name="임베드",
    description="Components V2 메시지를 생성합니다"
)
@app_commands.describe(
    내용="표시할 내용",
    제목="제목"
)
async def embed_command(
    interaction,
    내용: str,
    제목: str = None
):

    if 제목:

        text = (
            f"# {제목}\n\n"
            f"{내용}"
        )

    else:

        text = 내용

    try:

        container = discord.ui.Container(
            discord.ui.TextDisplay(text)
        )

        view = make_v2_view(
            container
        )

        await interaction.channel.send(
            view=view
        )

        await interaction.response.send_message(
            "✅ 메시지가 생성되었습니다.",
            ephemeral=True
        )

    except Exception as e:

        print(
            f"❌ 임베드 오류: {e}"
        )

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ 메시지를 생성할 수 없습니다.",
                ephemeral=True
            )


# ============================================================
# /서버정보
# ============================================================

@tree.command(
    name="서버정보",
    description="서버 정보를 표시합니다"
)
async def server_info(interaction):

    guild = interaction.guild

    if guild is None:

        await interaction.response.send_message(
            "❌ 서버에서만 사용할 수 있습니다.",
            ephemeral=True
        )

        return

    total = guild.member_count or 0

    bots = sum(
        1
        for member in guild.members
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

    container = discord.ui.Container(
        discord.ui.TextDisplay(text)
    )

    await interaction.response.send_message(
        view=make_v2_view(container)
    )


# ============================================================
# /정보채널
# ============================================================

@tree.command(
    name="정보채널",
    description="Members/Humans/Bots 채널을 생성합니다"
)
async def info_channel(interaction):

    if not await require_admin(interaction):
        return

    await interaction.response.send_message(
        "🔄 업데이트 중...",
        ephemeral=True
    )

    try:

        await update_info_channels(
            interaction.guild
        )

        await interaction.edit_original_response(
            content="✅ 정보 채널이 업데이트되었습니다."
        )

    except Exception as e:

        print(
            f"❌ 정보 채널 오류: {e}"
        )

        await interaction.edit_original_response(
            content="❌ 업데이트 실패"
        )


# ============================================================
# /핑
# ============================================================

@tree.command(
    name="핑",
    description="봇 핑을 확인합니다"
)
async def ping(interaction):

    latency = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 퐁! `{latency}ms`",
        ephemeral=True
    )


# ============================================================
# /입장로그
# ============================================================

@tree.command(
    name="입장로그",
    description="현재 채널을 입장 로그 채널로 설정합니다"
)
async def join_log(interaction):

    if not await require_admin(interaction):
        return

    guild_data = get_guild_data(
        interaction.guild.id
    )

    guild_data[
        "join_log_channel"
    ] = interaction.channel.id

    save_data()

    await interaction.response.send_message(
        "✅ 현재 채널을 입장 로그 채널로 설정했습니다.",
        ephemeral=True
    )


# ============================================================
# 입장 로그
# ============================================================

async def send_join_log(member):

    guild_data = get_guild_data(
        member.guild.id
    )

    channel_id = guild_data.get(
        "join_log_channel"
    )

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

    text = (
        f"📛 이름: {member}\n"
        f"🆔 ID: `{member.id}`\n"
        f"👤 멘션: {member.mention}\n\n"
        f"📅 계정 생성일: "
        f"{member.created_at:%Y년 %m월 %d일 %H:%M}\n"
        f"🤖 봇 여부: {bot_text}\n"
        f"👥 총 멤버 수: "
        f"{member.guild.member_count or 0}명"
    )

    try:

        container = discord.ui.Container(
            discord.ui.TextDisplay(text)
        )

        await channel.send(
            view=make_v2_view(
                container
            )
        )

    except Exception as e:

        print(
            f"❌ 입장 로그 오류: {e}"
        )


# ============================================================
# 티켓 설정 상태 텍스트
# ============================================================

def ticket_settings_text(guild):

    ticket = get_guild_data(
        guild.id
    )["ticket"]

    types = ticket["types"]

    role_id = ticket.get(
        "support_role_id"
    )

    role = guild.get_role(
        role_id
    ) if role_id else None

    role_text = (
        role.mention
        if role
        else "❌ 설정되지 않음"
    )

    channel_id = ticket.get(
        "panel_channel_id"
    )

    channel = guild.get_channel(
        channel_id
    ) if channel_id else None

    channel_text = (
        channel.mention
        if channel
        else "❌ 설정되지 않음"
    )

    if types:

        type_lines = []

        for i, item in enumerate(
            types,
            1
        ):

            emoji = item.get(
                "emoji",
                ""
            )

            type_lines.append(
                f"{i}. {emoji} **{item['name']}**"
            )

        type_text = "\n".join(
            type_lines
        )

    else:

        type_text = (
            "❌ 등록된 티켓 항목이 없습니다."
        )

    archive_text = (
        "🟢 켜짐"
        if ticket["archive_on_close"]
        else "🔴 꺼짐"
    )

    return (
        f"# ⚙️ 티켓 설정\n\n"
        f"**티켓 제목**\n"
        f"`{ticket['title']}`\n\n"
        f"**티켓 설명**\n"
        f"{ticket['description']}\n\n"
        f"**담당 역할**\n"
        f"{role_text}\n\n"
        f"**패널 채널**\n"
        f"{channel_text}\n\n"
        f"**닫을 때 보관**\n"
        f"{archive_text}\n\n"
        f"**티켓 항목**\n"
        f"{type_text}"
    )


# ============================================================
# 티켓 설정 Modal
# ============================================================

class TicketBasicModal(
    discord.ui.Modal,
    title="티켓 기본 설정"
):

    title_input = discord.ui.TextInput(
        label="티켓 제목",
        placeholder="예: 🎫 문의하기",
        max_length=100
    )

    description_input = discord.ui.TextInput(
        label="티켓 설명",
        placeholder="문의하실 항목을 선택해주세요.",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    close_input = discord.ui.TextInput(
        label="닫기 버튼 이름",
        placeholder="티켓 닫기",
        max_length=80
    )

    delete_input = discord.ui.TextInput(
        label="삭제 버튼 이름",
        placeholder="티켓 삭제",
        max_length=80
    )

    def __init__(self, guild_id):

        super().__init__()

        self.guild_id = guild_id

        ticket = get_guild_data(
            guild_id
        )["ticket"]

        self.title_input.default = ticket[
            "title"
        ]

        self.description_input.default = ticket[
            "description"
        ]

        self.close_input.default = ticket[
            "close_label"
        ]

        self.delete_input.default = ticket[
            "delete_label"
        ]

    async def on_submit(
        self,
        interaction
    ):

        ticket = get_guild_data(
            self.guild_id
        )["ticket"]

        ticket["title"] = str(
            self.title_input.value
        )

        ticket["description"] = str(
            self.description_input.value
        )

        ticket["close_label"] = str(
            self.close_input.value
        )

        ticket["delete_label"] = str(
            self.delete_input.value
        )

        save_data()

        await interaction.response.edit_message(
            content=ticket_settings_text(
                interaction.guild
            ),
            view=TicketSettingsView(
                self.guild_id
            )
        )


# ============================================================
# 티켓 항목 추가 Modal
# ============================================================

class AddTicketTypeModal(
    discord.ui.Modal,
    title="티켓 항목 추가"
):

    name_input = discord.ui.TextInput(
        label="항목 이름",
        placeholder="예: 구매 문의",
        max_length=80
    )

    emoji_input = discord.ui.TextInput(
        label="이모지",
        placeholder="예: 🛒",
        required=False,
        max_length=100
    )

    description_input = discord.ui.TextInput(
        label="설명",
        placeholder="예: 구매 관련 문의",
        max_length=100
    )

    def __init__(self, guild_id):

        super().__init__()

        self.guild_id = guild_id

    async def on_submit(
        self,
        interaction
    ):

        guild_data = get_guild_data(
            self.guild_id
        )

        types = guild_data[
            "ticket"
        ]["types"]

        if len(types) >= 25:

            await interaction.response.send_message(
                "❌ 드롭다운에는 최대 25개까지 추가할 수 있습니다.",
                ephemeral=True
            )

            return

        types.append({
            "name": str(
                self.name_input.value
            ),
            "emoji": str(
                self.emoji_input.value
            ),
            "description": str(
                self.description_input.value
            )
        })

        save_data()

        await interaction.response.edit_message(
            content=ticket_settings_text(
                interaction.guild
            ),
            view=TicketSettingsView(
                self.guild_id
            )
        )


# ============================================================
# 티켓 항목 수정 Modal
# ============================================================

class EditTicketTypeModal(
    discord.ui.Modal,
    title="티켓 항목 수정"
):

    name_input = discord.ui.TextInput(
        label="항목 이름",
        max_length=80
    )

    emoji_input = discord.ui.TextInput(
        label="이모지",
        required=False,
        max_length=100
    )

    description_input = discord.ui.TextInput(
        label="설명",
        max_length=100
    )

    def __init__(
        self,
        guild_id,
        index
    ):

        super().__init__()

        self.guild_id = guild_id
        self.index = index

        item = get_guild_data(
            guild_id
        )["ticket"]["types"][index]

        self.name_input.default = item[
            "name"
        ]

        self.emoji_input.default = item.get(
            "emoji",
            ""
        )

        self.description_input.default = item[
            "description"
        ]

    async def on_submit(
        self,
        interaction
    ):

        item = get_guild_data(
            self.guild_id
        )["ticket"]["types"][self.index]

        item["name"] = str(
            self.name_input.value
        )

        item["emoji"] = str(
            self.emoji_input.value
        )

        item["description"] = str(
            self.description_input.value
        )

        save_data()

        await interaction.response.edit_message(
            content=ticket_settings_text(
                interaction.guild
            ),
            view=TicketSettingsView(
                self.guild_id
            )
        )


# ============================================================
# 티켓 항목 선택
# ============================================================

class TicketEditSelect(
    discord.ui.Select
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        ticket = get_guild_data(
            guild_id
        )["ticket"]

        options = []

        for index, item in enumerate(
            ticket["types"]
        ):

            kwargs = {
                "label": item["name"][:100],
                "description": item["description"][:100],
                "value": str(index)
            }

            emoji = item.get(
                "emoji",
                ""
            )

            if emoji:
                kwargs["emoji"] = emoji

            options.append(
                discord.SelectOption(
                    **kwargs
                )
            )

        if not options:

            options.append(
                discord.SelectOption(
                    label="등록된 항목 없음",
                    value="none"
                )
            )

        super().__init__(
            placeholder="수정할 티켓 항목 선택",
            options=options,
            custom_id=f"ticket_edit:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        if not await require_admin(interaction):
            return

        value = self.values[0]

        if value == "none":

            await interaction.response.send_message(
                "❌ 먼저 티켓 항목을 추가해주세요.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            EditTicketTypeModal(
                self.guild_id,
                int(value)
            )
        )


# ============================================================
# 티켓 항목 삭제 Select
# ============================================================

class TicketDeleteSelect(
    discord.ui.Select
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        ticket = get_guild_data(
            guild_id
        )["ticket"]

        options = []

        for index, item in enumerate(
            ticket["types"]
        ):

            kwargs = {
                "label": item["name"][:100],
                "value": str(index)
            }

            emoji = item.get(
                "emoji",
                ""
            )

            if emoji:
                kwargs["emoji"] = emoji

            options.append(
                discord.SelectOption(
                    **kwargs
                )
            )

        if not options:

            options.append(
                discord.SelectOption(
                    label="등록된 항목 없음",
                    value="none"
                )
            )

        super().__init__(
            placeholder="삭제할 티켓 항목 선택",
            options=options,
            custom_id=f"ticket_delete:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        if not await require_admin(interaction):
            return

        value = self.values[0]

        if value == "none":

            await interaction.response.send_message(
                "❌ 삭제할 항목이 없습니다.",
                ephemeral=True
            )

            return

        ticket = get_guild_data(
            self.guild_id
        )["ticket"]

        removed = ticket["types"].pop(
            int(value)
        )

        save_data()

        await interaction.response.edit_message(
            content=ticket_settings_text(
                interaction.guild
            ),
            view=TicketSettingsView(
                self.guild_id
            )
        )

        print(
            f"🗑️ 티켓 항목 삭제: "
            f"{removed['name']}"
        )


# ============================================================
# 담당 역할 설정
# ============================================================

class SupportRoleSelect(
    discord.ui.RoleSelect
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            placeholder="티켓 담당 역할 선택",
            min_values=1,
            max_values=1,
            custom_id=f"ticket_role:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        if not await require_admin(interaction):
            return

        role = self.values[0]

        ticket = get_guild_data(
            self.guild_id
        )["ticket"]

        ticket["support_role_id"] = role.id

        save_data()

        await interaction.response.edit_message(
            content=ticket_settings_text(
                interaction.guild
            ),
            view=TicketSettingsView(
                self.guild_id
            )
        )


# ============================================================
# 패널 채널 설정
# ============================================================

class PanelChannelSelect(
    discord.ui.ChannelSelect
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            placeholder="티켓 패널을 보낼 채널 선택",
            channel_types=[
                discord.ChannelType.text
            ],
            min_values=1,
            max_values=1,
            custom_id=f"ticket_channel:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        if not await require_admin(interaction):
            return

        channel = self.values[0]

        ticket = get_guild_data(
            self.guild_id
        )["ticket"]

        ticket["panel_channel_id"] = channel.id

        save_data()

        await interaction.response.edit_message(
            content=ticket_settings_text(
                interaction.guild
            ),
            view=TicketSettingsView(
                self.guild_id
            )
        )


# ============================================================
# 보관 ON/OFF
# ============================================================

class ArchiveToggle(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        ticket = get_guild_data(
            guild_id
        )["ticket"]

        enabled = ticket[
            "archive_on_close"
        ]

        super().__init__(
            label=(
                "보관: ON"
                if enabled
                else "보관: OFF"
            ),
            style=(
                discord.ButtonStyle.success
                if enabled
                else discord.ButtonStyle.secondary
            ),
            custom_id=f"ticket_archive:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        if not await require_admin(interaction):
            return

        ticket = get_guild_data(
            self.guild_id
        )["ticket"]

        ticket["archive_on_close"] = not ticket[
            "archive_on_close"
        ]

        save_data()

        await interaction.response.edit_message(
            content=ticket_settings_text(
                interaction.guild
            ),
            view=TicketSettingsView(
                self.guild_id
            )
        )


# ============================================================
# 기본 설정 버튼
# ============================================================

class TicketBasicButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="기본 설정",
            emoji="⚙️",
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket_basic:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        if not await require_admin(interaction):
            return

        await interaction.response.send_modal(
            TicketBasicModal(
                self.guild_id
            )
        )


# ============================================================
# 항목 추가 버튼
# ============================================================

class AddTypeButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="항목 추가",
            emoji="➕",
            style=discord.ButtonStyle.success,
            custom_id=f"ticket_add:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        if not await require_admin(interaction):
            return

        await interaction.response.send_modal(
            AddTicketTypeModal(
                self.guild_id
            )
        )


# ============================================================
# 항목 수정 버튼
# ============================================================

class EditTypeButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="항목 수정",
            emoji="✏️",
            style=discord.ButtonStyle.primary,
            custom_id=f"ticket_edit_button:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        if not await require_admin(interaction):
            return

        ticket = get_guild_data(
            self.guild_id
        )["ticket"]

        if not ticket["types"]:

            await interaction.response.send_message(
                "❌ 수정할 티켓 항목이 없습니다.",
                ephemeral=True
            )

            return

        await interaction.response.edit_message(
            content=ticket_settings_text(
                interaction.guild
            ),
            view=TicketEditView(
                self.guild_id
            )
        )


# ============================================================
# 항목 삭제 버튼
# ============================================================

class DeleteTypeButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="항목 삭제",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id=f"ticket_delete_button:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        if not await require_admin(interaction):
            return

        ticket = get_guild_data(
            self.guild_id
        )["ticket"]

        if not ticket["types"]:

            await interaction.response.send_message(
                "❌ 삭제할 티켓 항목이 없습니다.",
                ephemeral=True
            )

            return

        await interaction.response.edit_message(
            content=ticket_settings_text(
                interaction.guild
            ),
            view=TicketDeleteView(
                self.guild_id
            )
        )


# ============================================================
# 패널 적용
# ============================================================

class ApplyPanelButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="패널 적용",
            emoji="📤",
            style=discord.ButtonStyle.success,
            custom_id=f"ticket_apply:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        if not await require_admin(interaction):
            return

        guild = interaction.guild

        ticket = get_guild_data(
            guild.id
        )["ticket"]

        if not ticket["types"]:

            await interaction.response.send_message(
                "❌ 먼저 티켓 항목을 하나 이상 추가해주세요.",
                ephemeral=True
            )

            return

        if not ticket["support_role_id"]:

            await interaction.response.send_message(
                "❌ 먼저 담당 역할을 설정해주세요.",
                ephemeral=True
            )

            return

        if not ticket["panel_channel_id"]:

            await interaction.response.send_message(
                "❌ 먼저 패널 채널을 설정해주세요.",
                ephemeral=True
            )

            return

        channel = guild.get_channel(
            ticket["panel_channel_id"]
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ 패널 채널을 찾을 수 없습니다.",
                ephemeral=True
            )

            return

        ticket["configured"] = True

        save_data()

        await channel.send(
            view=TicketPanelView(
                guild.id
            )
        )

        await interaction.response.send_message(
            f"✅ <#{channel.id}>에 티켓 패널을 생성했습니다.",
            ephemeral=True
        )


# ============================================================
# 설정 UI
# ============================================================

class TicketSettingsView(
    discord.ui.LayoutView
):

    def __init__(self, guild_id):

        super().__init__(
            timeout=None
        )

        self.guild_id = guild_id

        container = discord.ui.Container(

            discord.ui.TextDisplay(
                ticket_settings_text(
                    bot.get_guild(
                        guild_id
                    )
                )
            ),

            discord.ui.Separator(),

            discord.ui.ActionRow(
                AddTypeButton(
                    guild_id
                ),
                EditTypeButton(
                    guild_id
                ),
                DeleteTypeButton(
                    guild_id
                )
            ),

            discord.ui.ActionRow(
                TicketBasicButton(
                    guild_id
                ),
                ArchiveToggle(
                    guild_id
                ),
                ApplyPanelButton(
                    guild_id
                )
            ),

            discord.ui.Separator(),

            discord.ui.TextDisplay(
                "👤 **담당 역할 설정**"
            ),

            discord.ui.ActionRow(
                SupportRoleSelect(
                    guild_id
                )
            ),

            discord.ui.TextDisplay(
                "📌 **패널 채널 설정**"
            ),

            discord.ui.ActionRow(
                PanelChannelSelect(
                    guild_id
                )
            )
        )

        self.add_item(
            container
        )


# ============================================================
# 항목 수정 UI
# ============================================================

class TicketEditView(
    discord.ui.LayoutView
):

    def __init__(self, guild_id):

        super().__init__(
            timeout=None
        )

        container = discord.ui.Container(

            discord.ui.TextDisplay(
                "# ✏️ 티켓 항목 수정\n\n"
                "수정할 항목을 선택하세요."
            ),

            discord.ui.Separator(),

            discord.ui.ActionRow(
                TicketEditSelect(
                    guild_id
                )
            )
        )

        self.add_item(
            container
        )


# ============================================================
# 항목 삭제 UI
# ============================================================

class TicketDeleteView(
    discord.ui.LayoutView
):

    def __init__(self, guild_id):

        super().__init__(
            timeout=None
        )

        container = discord.ui.Container(

            discord.ui.TextDisplay(
                "# 🗑️ 티켓 항목 삭제\n\n"
                "삭제할 항목을 선택하세요."
            ),

            discord.ui.Separator(),

            discord.ui.ActionRow(
                TicketDeleteSelect(
                    guild_id
                )
            )
        )

        self.add_item(
            container
        )


# ============================================================
# /티켓
# ============================================================

@tree.command(
    name="티켓",
    description="티켓 시스템을 설정합니다"
)
async def ticket_command(interaction):

    if not await require_admin(interaction):
        return

    guild_data = get_guild_data(
        interaction.guild.id
    )

    ticket = guild_data[
        "ticket"
    ]

    # 설정 UI만 열림
    container = discord.ui.Container(
        discord.ui.TextDisplay(
            ticket_settings_text(
                interaction.guild
            )
        )
    )

    await interaction.response.send_message(
        view=TicketSettingsView(
            interaction.guild.id
        ),
        ephemeral=True
    )


# ============================================================
# 실제 티켓 패널 드롭다운
# ============================================================

class TicketPanelSelect(
    discord.ui.Select
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        ticket = get_guild_data(
            guild_id
        )["ticket"]

        options = []

        for index, item in enumerate(
            ticket["types"]
        ):

            kwargs = {
                "label": item["name"][:100],
                "description": item["description"][:100],
                "value": str(index)
            }

            emoji = item.get(
                "emoji",
                ""
            )

            if emoji:
                kwargs["emoji"] = emoji

            options.append(
                discord.SelectOption(
                    **kwargs
                )
            )

        super().__init__(
            placeholder="문의할 항목을 선택하세요",
            options=options,
            custom_id=f"ticket_panel:{guild_id}"
        )

    async def callback(
        self,
        interaction
    ):

        guild = interaction.guild

        ticket = get_guild_data(
            guild.id
        )["ticket"]

        index = int(
            self.values[0]
        )

        item = ticket[
            "types"
        ][index]

        # 이미 열린 티켓 확인
        existing = None

        for channel in guild.text_channels:

            if (
                channel.topic
                and f"ticket_user:{interaction.user.id}"
                in channel.topic
            ):

                existing = channel
                break

        if existing:

            await interaction.response.send_message(
                f"❌ 이미 열린 티켓이 있습니다.\n{existing.mention}",
                ephemeral=True
            )

            return

        support_role = guild.get_role(
            ticket["support_role_id"]
        )

        if support_role is None:

            await interaction.response.send_message(
                "❌ 담당 역할이 삭제되었습니다. 관리자가 설정을 다시 해주세요.",
                ephemeral=True
            )

            return

        # ====================================================
        # 티켓 권한
        # ====================================================

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            interaction.user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                ),

            support_role:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )
        }

        if guild.me:

            overwrites[
                guild.me
            ] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )

        # 관리자 역할은 기본적으로 관리자 권한으로 접근
        for role in guild.roles:

            if role.permissions.administrator:

                overwrites[
                    role
                ] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    manage_messages=True
                )

        channel_name = (
            f"ticket-{safe_channel_name(item['name'])}-"
            f"{interaction.user.name}"
        )

        channel_name = channel_name[
            :100
        ]

        try:

            channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic=(
                    f"ticket_user:{interaction.user.id}"
                    f"|type:{index}"
                    f"|closed:false"
                ),
                reason="티켓 생성"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ 채널 생성 권한이 없습니다.",
                ephemeral=True
            )

            return

        except Exception as e:

            print(
                f"❌ 티켓 생성 오류: {e}"
            )

            await interaction.response.send_message(
                "❌ 티켓을 생성하지 못했습니다.",
                ephemeral=True
            )

            return

        # ====================================================
        # 티켓 카드
        # ====================================================

        text = (
            f"# {item.get('emoji', '🎫')} "
            f"{item['name']}\n\n"
            f"{item['description']}\n\n"
            f"👤 생성자: {interaction.user.mention}\n"
            f"👥 담당 역할: {support_role.mention}"
        )

        container = discord.ui.Container(
            discord.ui.TextDisplay(text),

            discord.ui.Separator(),

            discord.ui.ActionRow(
                CloseTicketButton(
                    guild.id,
                    interaction.user.id,
                    ticket["close_label"]
                ),
                DeleteTicketButton(
                    guild.id,
                    interaction.user.id,
                    ticket["delete_label"]
                )
            )
        )

        await channel.send(
            view=make_v2_view(
                container
            )
        )

        await interaction.response.send_message(
            f"✅ 티켓이 생성되었습니다.\n{channel.mention}",
            ephemeral=True
        )


# ============================================================
# 실제 티켓 패널
# ============================================================

class TicketPanelView(
    discord.ui.LayoutView
):

    def __init__(self, guild_id):

        super().__init__(
            timeout=None
        )

        ticket = get_guild_data(
            guild_id
        )["ticket"]

        container = discord.ui.Container(

            discord.ui.TextDisplay(
                f"# {ticket['title']}\n\n"
                f"{ticket['description']}"
            ),

            discord.ui.Separator(),

            discord.ui.ActionRow(
                TicketPanelSelect(
                    guild_id
                )
            )
        )

        self.add_item(
            container
        )


# ============================================================
# 티켓 닫기
# ============================================================

class CloseTicketButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id,
        owner_id,
        label
    ):

        self.guild_id = guild_id
        self.owner_id = owner_id

        super().__init__(
            label=label[:80],
            emoji="🔒",
            style=discord.ButtonStyle.secondary,
            custom_id=(
                f"ticket_close:"
                f"{guild_id}:"
                f"{owner_id}"
            )
        )

    async def callback(
        self,
        interaction
    ):

        channel = interaction.channel

        # 관리자라면 사용자 권한을 건드리지 않고
        # 티켓을 닫는 것도 가능
        if interaction.user.id != self.owner_id:

            if not interaction.user.guild_permissions.administrator:

                await interaction.response.send_message(
                    "❌ 티켓 생성자만 닫을 수 있습니다.",
                    ephemeral=True
                )

                return

        guild_data = get_guild_data(
            interaction.guild.id
        )

        ticket = guild_data[
            "ticket"
        ]

        owner = interaction.guild.get_member(
            self.owner_id
        )

        if owner:

            try:

                await channel.set_permissions(
                    owner,
                    view_channel=False,
                    send_messages=False,
                    read_message_history=False
                )

            except Exception as e:

                print(
                    f"❌ 티켓 사용자 권한 제거 실패: {e}"
                )

        # topic 변경
        try:

            old_topic = channel.topic or ""

            old_topic = re.sub(
                r"\|closed:(true|false)",
                "",
                old_topic
            )

            await channel.edit(
                topic=(
                    old_topic
                    + "|closed:true"
                ),
                reason="티켓 닫기"
            )

        except Exception:
            pass

        if ticket["archive_on_close"]:

            try:

                await channel.edit(
                    name=f"closed-{channel.name}"[:100],
                    reason="티켓 보관"
                )

            except Exception:
                pass

            await interaction.response.send_message(
                "🔒 티켓이 닫혔습니다.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "🗑️ 티켓을 삭제하는 중...",
                ephemeral=True
            )

            try:

                await channel.delete(
                    reason="티켓 닫기 - 자동 삭제"
                )

            except Exception as e:

                print(
                    f"❌ 티켓 삭제 실패: {e}"
                )


# ============================================================
# 티켓 삭제
# ============================================================

class DeleteTicketButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id,
        owner_id,
        label
    ):

        self.guild_id = guild_id
        self.owner_id = owner_id

        super().__init__(
            label=label[:80],
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id=(
                f"ticket_delete:"
                f"{guild_id}:"
                f"{owner_id}"
            )
        )

    async def callback(
        self,
        interaction
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ 관리자만 티켓을 삭제할 수 있습니다.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🗑️ 티켓을 삭제합니다...",
            ephemeral=True
        )

        try:

            await interaction.channel.delete(
                reason="관리자 티켓 삭제"
            )

        except Exception as e:

            print(
                f"❌ 티켓 삭제 오류: {e}"
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

    except Exception as e:

        print(
            f"❌ 입장 처리 오류: {e}"
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

    except Exception as e:

        print(
            f"❌ 퇴장 처리 오류: {e}"
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

    # ========================================================
    # 정보 채널 업데이트
    # ========================================================

    for guild in bot.guilds:

        try:

            await update_info_channels(
                guild
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
# 에러
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
