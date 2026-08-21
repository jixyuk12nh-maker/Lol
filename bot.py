import os
import json
import re
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

DEFAULT_TICKET_TYPES = [
    {
        "name": "구매 문의",
        "emoji": "🛒",
        "description": "구매 관련 문의"
    },
    {
        "name": "결제 문의",
        "emoji": "💳",
        "description": "결제 관련 문의"
    },
    {
        "name": "오류 문의",
        "emoji": "🛠️",
        "description": "오류 관련 문의"
    },
    {
        "name": "기타 문의",
        "emoji": "❓",
        "description": "기타 문의"
    }
]


def load_data():

    if not os.path.exists(DATA_FILE):
        return {"guilds": {}}

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if "guilds" not in data:
            data["guilds"] = {}

        return data

    except Exception as e:

        print(
            f"❌ 데이터 로드 실패: {e}"
        )

        return {"guilds": {}}


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

                "panel_channel_id": None,
                "panel_message_id": None,

                "support_role_id": None,

                "title": "🎫 문의하기",

                "description":
                    "문의하실 항목을 선택해주세요.",

                "close_label":
                    "🔒 티켓 닫기",

                "delete_label":
                    "🗑️ 티켓 삭제",

                # 닫으면 사용자에게만 숨김
                # True = 보관
                # False = 삭제
                "archive_on_close": True,

                "types":
                    DEFAULT_TICKET_TYPES.copy()
            }
        }

        save_data()

    ticket = data["guilds"][guild_id]["ticket"]

    # 기존 데이터에 없는 값 자동 보충
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
        "🔒 티켓 닫기"
    )

    ticket.setdefault(
        "delete_label",
        "🗑️ 티켓 삭제"
    )

    ticket.setdefault(
        "archive_on_close",
        True
    )

    ticket.setdefault(
        "types",
        DEFAULT_TICKET_TYPES.copy()
    )

    return data["guilds"][guild_id]


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

def create_v2_view(container):

    view = discord.ui.LayoutView(
        timeout=None
    )

    view.add_item(container)

    return view


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

                except Exception as e:

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

        overwrites[guild.me] = \
            discord.PermissionOverwrite(
                view_channel=True,
                connect=True
            )

    try:

        return await guild.create_voice_channel(
            name=name,
            overwrites=overwrites,
            reason="서버 정보 채널 생성"
        )

    except Exception as e:

        print(
            f"❌ 채널 생성 실패: {e}"
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

    text = (
        f"# {제목}\n\n{내용}"
        if 제목
        else 내용
    )

    container = discord.ui.Container(
        discord.ui.TextDisplay(text)
    )

    view = create_v2_view(
        container
    )

    try:

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
                "❌ 메시지를 생성하지 못했습니다.",
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

    text = (
        f"# 📊 {guild.name}\n\n"
        f"👤 **Humans:** {humans}\n"
        f"🤖 **Bots:** {bots}\n"
        f"👥 **Members:** {total}\n\n"
        f"📅 **생성일:** "
        f"{guild.created_at:%Y년 %m월 %d일}\n"
        f"👑 **서버장:** {owner_text}\n"
        f"📌 **채널 수:** {len(guild.channels)}\n"
        f"🎨 **역할 수:** {len(guild.roles)}"
    )

    container = discord.ui.Container(
        discord.ui.TextDisplay(text)
    )

    await interaction.response.send_message(
        view=create_v2_view(container)
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

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        await update_info_channels(
            interaction.guild
        )

        await interaction.followup.send(
            "✅ 정보 채널이 업데이트되었습니다.",
            ephemeral=True
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ 오류: {e}",
            ephemeral=True
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
        "✅ 현재 채널이 입장 로그 채널로 설정되었습니다.",
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

    container = discord.ui.Container(
        discord.ui.TextDisplay(text)
    )

    try:

        await channel.send(
            view=create_v2_view(container)
        )

    except Exception as e:

        print(
            f"❌ 입장 로그 오류: {e}"
        )


# ============================================================
# 티켓 패널
# ============================================================

class TicketSelect(
    discord.ui.Select
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        guild_data = get_guild_data(
            guild_id
        )

        types = guild_data[
            "ticket"
        ]["types"]

        options = []

        for index, ticket_type in enumerate(types):

            try:

                option = discord.SelectOption(
                    label=ticket_type["name"][:100],
                    description=ticket_type[
                        "description"
                    ][:100],
                    emoji=ticket_type["emoji"],
                    value=str(index)
                )

                options.append(option)

            except Exception:

                # 잘못된 이모지 때문에 패널 전체가
                # 깨지는 것을 방지
                options.append(
                    discord.SelectOption(
                        label=ticket_type["name"][:100],
                        description=ticket_type[
                            "description"
                        ][:100],
                        value=str(index)
                    )
                )

        if not options:

            options.append(
                discord.SelectOption(
                    label="티켓 유형 없음",
                    description="관리자가 유형을 추가해주세요.",
                    value="none"
                )
            )

        super().__init__(
            placeholder="문의 유형을 선택하세요",
            options=options,
            min_values=1,
            max_values=1,
            custom_id=f"ticket_select:{guild_id}"
        )

    async def callback(self, interaction):

        if self.values[0] == "none":

            await interaction.response.send_message(
                "❌ 등록된 티켓 유형이 없습니다.",
                ephemeral=True
            )

            return

        index = int(
            self.values[0]
        )

        guild_data = get_guild_data(
            interaction.guild.id
        )

        types = guild_data[
            "ticket"
        ]["types"]

        if index >= len(types):

            await interaction.response.send_message(
                "❌ 해당 티켓 유형을 찾을 수 없습니다.",
                ephemeral=True
            )

            return

        await create_ticket(
            interaction,
            types[index]
        )


class TicketPanelView(
    discord.ui.LayoutView
):

    def __init__(self, guild_id):

        super().__init__(
            timeout=None
        )

        guild_data = get_guild_data(
            guild_id
        )

        ticket = guild_data[
            "ticket"
        ]

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

        row = discord.ui.ActionRow()

        row.add_item(
            TicketSelect(guild_id)
        )

        container.add_item(
            row
        )

        self.add_item(
            container
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

    ticket = guild_data[
        "ticket"
    ]

    # 이미 열린 티켓 확인
    for channel in guild.text_channels:

        if not channel.topic:
            continue

        if channel.topic.startswith(
            f"ticket_owner:{member.id}"
        ):

            await interaction.response.send_message(
                f"❌ 이미 티켓이 있습니다.\n{channel.mention}",
                ephemeral=True
            )

            return

    support_role = None

    role_id = ticket.get(
        "support_role_id"
    )

    if role_id:

        support_role = guild.get_role(
            role_id
        )

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

        overwrites[
            support_role
        ] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True
        )

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

    safe_name = re.sub(
        r"[^a-zA-Z0-9가-힣_-]",
        "",
        member.display_name
    )[:20]

    if not safe_name:
        safe_name = "user"

    channel_name = (
        f"ticket-{safe_name}"
    )

    try:

        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            topic=(
                f"ticket_owner:{member.id}"
                f"|status:open"
            ),
            reason="티켓 생성"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ 채널 생성 권한이 없습니다.",
            ephemeral=True
        )

        return

    text = (
        f"# {ticket_type['emoji']} "
        f"{ticket_type['name']}\n\n"
        f"👤 문의자: {member.mention}\n\n"
        f"문의 내용을 남겨주세요."
    )

    container = discord.ui.Container()

    container.add_item(
        discord.ui.TextDisplay(text)
    )

    row = discord.ui.ActionRow()

    row.add_item(
        TicketCloseButton(
            guild.id,
            ticket["close_label"]
        )
    )

    row.add_item(
        TicketDeleteButton(
            guild.id,
            ticket["delete_label"]
        )
    )

    container.add_item(
        row
    )

    try:

        await channel.send(
            view=create_v2_view(
                container
            )
        )

        await interaction.response.send_message(
            f"✅ 티켓이 생성되었습니다.\n{channel.mention}",
            ephemeral=True
        )

    except Exception as e:

        print(
            f"❌ 티켓 UI 오류: {e}"
        )

        await interaction.response.send_message(
            f"❌ 티켓 UI 생성 실패: `{e}`",
            ephemeral=True
        )


# ============================================================
# 티켓 사용자 / 관리자 확인
# ============================================================

def get_ticket_owner(channel):

    if not channel.topic:
        return None

    match = re.search(
        r"ticket_owner:(\d+)",
        channel.topic
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


def is_ticket_staff(interaction):

    if interaction.guild is None:
        return False

    if interaction.user.guild_permissions.administrator:
        return True

    guild_data = get_guild_data(
        interaction.guild.id
    )

    role_id = guild_data[
        "ticket"
    ].get(
        "support_role_id"
    )

    if not role_id:
        return False

    role = interaction.guild.get_role(
        role_id
    )

    return role in interaction.user.roles if role else False


# ============================================================
# 티켓 닫기
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

    async def callback(self, interaction):

        channel = interaction.channel

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            return

        owner_id = get_ticket_owner(
            channel
        )

        if (
            interaction.user.id != owner_id
            and not is_ticket_staff(interaction)
        ):

            await interaction.response.send_message(
                "❌ 이 티켓을 닫을 권한이 없습니다.",
                ephemeral=True
            )

            return

        guild_data = get_guild_data(
            interaction.guild.id
        )

        archive = guild_data[
            "ticket"
        ].get(
            "archive_on_close",
            True
        )

        # ====================================================
        # 보관 ON
        # ====================================================

        if archive:

            if owner_id:

                owner = interaction.guild.get_member(
                    owner_id
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
                            f"❌ 사용자 권한 제거 실패: {e}"
                        )

            try:

                await channel.edit(
                    name=(
                        f"closed-{channel.name}"
                        if not channel.name.startswith("closed-")
                        else channel.name
                    ),
                    topic=(
                        f"ticket_owner:{owner_id}"
                        f"|status:closed"
                    )
                )

            except Exception:
                pass

            await interaction.response.send_message(
                "🔒 티켓이 닫혔습니다.\n"
                "관리자에게는 계속 표시됩니다.",
            )

        # ====================================================
        # 보관 OFF
        # ====================================================

        else:

            await interaction.response.send_message(
                "🗑️ 티켓을 닫고 삭제합니다."
            )

            await channel.delete(
                reason="티켓 닫기 - 보관 OFF"
            )


# ============================================================
# 티켓 삭제
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

    async def callback(self, interaction):

        if not is_ticket_staff(
            interaction
        ):

            await interaction.response.send_message(
                "❌ 관리자 또는 설정된 티켓 역할만 삭제할 수 있습니다.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🗑️ 티켓을 삭제합니다."
        )

        try:

            await interaction.channel.delete(
                reason=f"티켓 삭제 - {interaction.user}"
            )

        except Exception as e:

            print(
                f"❌ 티켓 삭제 실패: {e}"
            )


# ============================================================
# 티켓 설정 UI
# ============================================================

class TicketSettingsView(
    discord.ui.LayoutView
):

    def __init__(self, guild_id):

        super().__init__(
            timeout=300
        )

        self.guild_id = guild_id

        guild = bot.get_guild(
            guild_id
        )

        guild_data = get_guild_data(
            guild_id
        )

        ticket = guild_data[
            "ticket"
        ]

        role_id = ticket.get(
            "support_role_id"
        )

        role = (
            guild.get_role(role_id)
            if guild and role_id
            else None
        )

        role_text = (
            role.mention
            if role
            else "❌ 설정 안 됨"
        )

        archive_text = (
            "🟢 켜짐 — 닫으면 관리자에게 보관"
            if ticket["archive_on_close"]
            else "🔴 꺼짐 — 닫으면 티켓 삭제"
        )

        types_text = ""

        for i, item in enumerate(
            ticket["types"],
            start=1
        ):

            types_text += (
                f"{i}. {item['emoji']} "
                f"**{item['name']}**\n"
                f"   └ {item['description']}\n"
            )

        if not types_text:
            types_text = "❌ 없음"

        text = (
            "# 🎫 티켓 설정\n\n"

            "## 현재 설정\n"
            f"📌 제목: `{ticket['title']}`\n"
            f"📝 설명: `{ticket['description']}`\n"
            f"👮 담당 역할: {role_text}\n"
            f"📦 닫기 후 보관: {archive_text}\n"
            f"🔒 닫기 버튼: `{ticket['close_label']}`\n"
            f"🗑️ 삭제 버튼: `{ticket['delete_label']}`\n\n"

            "## 📋 드롭다운 항목\n"
            f"{types_text}\n"

            "아래 버튼으로 설정을 변경하면 "
            "**이 UI의 현재 설정도 바로 갱신됩니다.**"
        )

        container = discord.ui.Container()

        container.add_item(
            discord.ui.TextDisplay(text)
        )

        # ----------------------------------------------------
        # 1행
        # ----------------------------------------------------

        row1 = discord.ui.ActionRow()

        row1.add_item(
            TicketRoleButton(
                guild_id
            )
        )

        row1.add_item(
            TicketTitleButton(
                guild_id
            )
        )

        row1.add_item(
            TicketDescriptionButton(
                guild_id
            )
        )

        # ----------------------------------------------------
        # 2행
        # ----------------------------------------------------

        row2 = discord.ui.ActionRow()

        row2.add_item(
            TicketAddTypeButton(
                guild_id
            )
        )

        row2.add_item(
            TicketRemoveTypeButton(
                guild_id
            )
        )

        row2.add_item(
            TicketButtonNameButton(
                guild_id
            )
        )

        # ----------------------------------------------------
        # 3행
        # ----------------------------------------------------

        row3 = discord.ui.ActionRow()

        row3.add_item(
            TicketArchiveButton(
                guild_id
            )
        )

        row3.add_item(
            TicketPanelButton(
                guild_id
            )
        )

        # UI 아래쪽에 버튼 배치
        container.add_item(row1)
        container.add_item(row2)
        container.add_item(row3)

        self.add_item(
            container
        )


async def refresh_settings_ui(
    interaction
):

    if interaction.message is None:
        return

    try:

        await interaction.response.edit_message(
            content=None,
            embed=None,
            embeds=[],
            attachments=[],
            view=TicketSettingsView(
                interaction.guild.id
            )
        )

    except Exception as e:

        print(
            f"❌ 설정 UI 갱신 실패: {e}"
        )


# ============================================================
# 역할 설정
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
            custom_id=f"ticket_role:{guild_id}"
        )

    async def callback(self, interaction):

        await interaction.response.send_message(
            "아래에서 티켓을 볼 역할을 선택하세요.",
            view=TicketRoleView(
                self.guild_id
            ),
            ephemeral=True
        )


class TicketRoleView(
    discord.ui.View
):

    def __init__(self, guild_id):

        super().__init__(
            timeout=120
        )

        self.add_item(
            TicketRoleSelect(
                guild_id
            )
        )


class TicketRoleSelect(
    discord.ui.RoleSelect
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            placeholder="티켓 담당 역할 선택",
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction):

        role = self.values[0]

        guild_data = get_guild_data(
            self.guild_id
        )

        guild_data[
            "ticket"
        ][
            "support_role_id"
        ] = role.id

        save_data()

        await interaction.response.send_message(
            f"✅ 담당 역할을 {role.mention}으로 설정했습니다.",
            ephemeral=True
        )


# ============================================================
# 제목 변경
# ============================================================

class TicketTitleButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="제목 변경",
            emoji="📝",
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket_title:{guild_id}"
        )

    async def callback(self, interaction):

        await interaction.response.send_modal(
            TicketTitleModal(
                self.guild_id
            )
        )


class TicketTitleModal(
    discord.ui.Modal,
    title="티켓 제목 변경"
):

    value = discord.ui.TextInput(
        label="제목",
        placeholder="예: 🎫 고객센터",
        max_length=100
    )

    def __init__(self, guild_id):

        super().__init__()

        self.guild_id = guild_id

    async def on_submit(self, interaction):

        guild_data = get_guild_data(
            self.guild_id
        )

        guild_data[
            "ticket"
        ]["title"] = str(
            self.value.value
        )

        save_data()

        # 기존 패널 즉시 업데이트
        await update_ticket_panel(
            interaction.guild
        )

        await interaction.response.send_message(
            "✅ 제목을 변경하고 패널도 업데이트했습니다.",
            ephemeral=True
        )


# ============================================================
# 설명 변경
# ============================================================

class TicketDescriptionButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="설명 변경",
            emoji="📄",
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket_description:{guild_id}"
        )

    async def callback(self, interaction):

        await interaction.response.send_modal(
            TicketDescriptionModal(
                self.guild_id
            )
        )


class TicketDescriptionModal(
    discord.ui.Modal,
    title="티켓 설명 변경"
):

    value = discord.ui.TextInput(
        label="설명",
        placeholder="문의하실 항목을 선택해주세요.",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    def __init__(self, guild_id):

        super().__init__()

        self.guild_id = guild_id

    async def on_submit(self, interaction):

        guild_data = get_guild_data(
            self.guild_id
        )

        guild_data[
            "ticket"
        ]["description"] = str(
            self.value.value
        )

        save_data()

        await update_ticket_panel(
            interaction.guild
        )

        await interaction.response.send_message(
            "✅ 설명을 변경하고 패널도 업데이트했습니다.",
            ephemeral=True
        )


# ============================================================
# 티켓 유형 추가
# ============================================================

class TicketAddTypeButton(
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

    async def callback(self, interaction):

        await interaction.response.send_modal(
            TicketAddTypeModal(
                self.guild_id
            )
        )


class TicketAddTypeModal(
    discord.ui.Modal,
    title="드롭다운 항목 추가"
):

    name = discord.ui.TextInput(
        label="항목 이름",
        placeholder="예: 환불 문의",
        max_length=80
    )

    emoji = discord.ui.TextInput(
        label="이모지",
        placeholder="예: 💰",
        max_length=20
    )

    description = discord.ui.TextInput(
        label="설명",
        placeholder="환불 관련 문의",
        max_length=100
    )

    def __init__(self, guild_id):

        super().__init__()

        self.guild_id = guild_id

    async def on_submit(self, interaction):

        guild_data = get_guild_data(
            self.guild_id
        )

        types = guild_data[
            "ticket"
        ]["types"]

        if len(types) >= 25:

            await interaction.response.send_message(
                "❌ Discord 드롭다운은 최대 25개 항목까지 가능합니다.",
                ephemeral=True
            )

            return

        emoji = str(
            self.emoji.value
        ).strip()

        # 커스텀 이모지는 그대로 받을 수 있도록
        # 문자열 형태로 저장
        types.append(
            {
                "name": str(
                    self.name.value
                ),
                "emoji": emoji,
                "description": str(
                    self.description.value
                )
            }
        )

        save_data()

        await update_ticket_panel(
            interaction.guild
        )

        await interaction.response.send_message(
            "✅ 드롭다운 항목을 추가하고 패널을 즉시 업데이트했습니다.",
            ephemeral=True
        )


# ============================================================
# 항목 삭제
# ============================================================

class TicketRemoveTypeButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="항목 삭제",
            emoji="➖",
            style=discord.ButtonStyle.danger,
            custom_id=f"ticket_remove:{guild_id}"
        )

    async def callback(self, interaction):

        guild_data = get_guild_data(
            self.guild_id
        )

        types = guild_data[
            "ticket"
        ]["types"]

        if not types:

            await interaction.response.send_message(
                "❌ 삭제할 항목이 없습니다.",
                ephemeral=True
            )

            return

        options = []

        for index, item in enumerate(types):

            try:

                options.append(
                    discord.SelectOption(
                        label=item["name"][:100],
                        description=item[
                            "description"
                        ][:100],
                        emoji=item["emoji"],
                        value=str(index)
                    )
                )

            except Exception:

                options.append(
                    discord.SelectOption(
                        label=item["name"][:100],
                        description=item[
                            "description"
                        ][:100],
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
            "삭제할 항목을 선택하세요.",
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
            placeholder="삭제할 항목 선택",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction):

        index = int(
            self.values[0]
        )

        guild_data = get_guild_data(
            self.guild_id
        )

        types = guild_data[
            "ticket"
        ]["types"]

        if index >= len(types):

            await interaction.response.send_message(
                "❌ 항목을 찾을 수 없습니다.",
                ephemeral=True
            )

            return

        removed = types.pop(index)

        save_data()

        await update_ticket_panel(
            interaction.guild
        )

        await interaction.response.send_message(
            f"✅ `{removed['name']}` 항목을 삭제했습니다.",
            ephemeral=True
        )


# ============================================================
# 버튼 이름 변경
# ============================================================

class TicketButtonNameButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="버튼 이름",
            emoji="🔘",
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket_buttons:{guild_id}"
        )

    async def callback(self, interaction):

        await interaction.response.send_modal(
            TicketButtonNameModal(
                self.guild_id
            )
        )


class TicketButtonNameModal(
    discord.ui.Modal,
    title="티켓 버튼 이름 변경"
):

    close_name = discord.ui.TextInput(
        label="닫기 버튼",
        placeholder="예: 🔒 문의 종료",
        max_length=80
    )

    delete_name = discord.ui.TextInput(
        label="삭제 버튼",
        placeholder="예: 🗑️ 채널 삭제",
        max_length=80
    )

    def __init__(self, guild_id):

        super().__init__()

        self.guild_id = guild_id

    async def on_submit(self, interaction):

        guild_data = get_guild_data(
            self.guild_id
        )

        ticket = guild_data[
            "ticket"
        ]

        ticket[
            "close_label"
        ] = str(
            self.close_name.value
        )

        ticket[
            "delete_label"
        ] = str(
            self.delete_name.value
        )

        save_data()

        await interaction.response.send_message(
            "✅ 버튼 이름을 변경했습니다.\n"
            "새로 생성되는 티켓부터 적용됩니다.",
            ephemeral=True
        )


# ============================================================
# 보관 ON/OFF
# ============================================================

class TicketArchiveButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="보관 ON/OFF",
            emoji="📦",
            style=discord.ButtonStyle.primary,
            custom_id=f"ticket_archive:{guild_id}"
        )

    async def callback(self, interaction):

        guild_data = get_guild_data(
            self.guild_id
        )

        ticket = guild_data[
            "ticket"
        ]

        ticket[
            "archive_on_close"
        ] = not ticket[
            "archive_on_close"
        ]

        save_data()

        await refresh_settings_ui(
            interaction
        )


# ============================================================
# 패널 생성 버튼
# ============================================================

class TicketPanelButton(
    discord.ui.Button
):

    def __init__(self, guild_id):

        self.guild_id = guild_id

        super().__init__(
            label="패널 업데이트",
            emoji="🎫",
            style=discord.ButtonStyle.success,
            custom_id=f"ticket_panel:{guild_id}"
        )

    async def callback(self, interaction):

        await update_ticket_panel(
            interaction.guild
        )

        await refresh_settings_ui(
            interaction
        )


# ============================================================
# 티켓 패널 업데이트
# ============================================================

async def update_ticket_panel(guild):

    guild_data = get_guild_data(
        guild.id
    )

    ticket = guild_data[
        "ticket"
    ]

    channel_id = ticket.get(
        "panel_channel_id"
    )

    message_id = ticket.get(
        "panel_message_id"
    )

    if not channel_id or not message_id:
        return False

    channel = guild.get_channel(
        channel_id
    )

    if channel is None:
        return False

    try:

        message = await channel.fetch_message(
            message_id
        )

        await message.edit(
            content=None,
            embed=None,
            embeds=[],
            attachments=[],
            view=TicketPanelView(
                guild.id
            )
        )

        return True

    except Exception as e:

        print(
            f"❌ 티켓 패널 업데이트 실패: {e}"
        )

        return False


# ============================================================
# /티켓
# ============================================================

@tree.command(
    name="티켓",
    description="현재 채널에 티켓 패널을 생성합니다"
)
async def ticket_command(interaction):

    if not await require_admin(interaction):
        return

    guild = interaction.guild

    guild_data = get_guild_data(
        guild.id
    )

    ticket = guild_data[
        "ticket"
    ]

    # 새 패널 생성
    try:

        message = await interaction.channel.send(
            view=TicketPanelView(
                guild.id
            )
        )

        ticket[
            "panel_channel_id"
        ] = interaction.channel.id

        ticket[
            "panel_message_id"
        ] = message.id

        save_data()

        await interaction.response.send_message(
            "✅ 티켓 패널을 생성했습니다.",
            ephemeral=True
        )

    except Exception as e:

        print(
            f"❌ 티켓 패널 생성 오류: {e}"
        )

        await interaction.response.send_message(
            f"❌ 티켓 패널 생성 실패: `{e}`",
            ephemeral=True
        )


# ============================================================
# /티켓설정
# ============================================================

@tree.command(
    name="티켓설정",
    description="티켓 Components V2 설정 UI를 엽니다"
)
async def ticket_settings(interaction):

    if not await require_admin(interaction):
        return

    await interaction.response.send_message(
        view=TicketSettingsView(
            interaction.guild.id
        ),
        ephemeral=True
    )


# ============================================================
# 이벤트
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


@bot.event
async def on_guild_join(guild):

    get_guild_data(
        guild.id
    )

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

    # 서버 데이터 준비
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
                f"❌ {guild.name}: {e}"
            )

    print(
        f"📊 총 {len(bot.guilds)}개 서버 연결됨"
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
