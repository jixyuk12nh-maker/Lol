import os
import discord
from discord import app_commands
from discord.ui import View, Button, Select, TextInput, Modal
import logging
from typing import Optional
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# Components V2 - 텍스트 카드 UI
# ============================================================

class TextCardView(View):
    """텍스트 카드 UI (Components V2)"""
    def __init__(self, title: str, content: str, footer: Optional[str] = None):
        super().__init__(timeout=None)
        
        # 카드 스타일의 텍스트 표시 (Components V2 방식)
        text = f"# {title}\n\n{content}"
        if footer:
            text += f"\n\n---\n*{footer}*"
        
        # TextDisplay 컴포넌트 생성 (올바른 방식)
        text_display = discord.ui.TextDisplay(
            text=text,
            style=discord.TextStyle.paragraph
        )
        
        # Container에 TextDisplay 추가
        container = discord.ui.Container(text_display)
        
        # LayoutView 생성 및 Container 추가
        layout_view = discord.ui.LayoutView()
        layout_view.add_item(container)
        
        # 메인 View에 LayoutView 추가
        self.add_item(layout_view)

# ============================================================
# Components V2 - 입장 로그 버튼 뷰
# ============================================================

class JoinLogView(View):
    """입장 로그용 버튼 뷰"""
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member
        
        # 프로필 보기 버튼
        self.add_item(
            Button(
                label="프로필 보기",
                style=discord.ButtonStyle.primary,
                emoji="👤",
                url=f"https://discord.com/users/{member.id}"
            )
        )
        
        # 역할 부여 버튼
        self.add_item(
            Button(
                label="기본 역할 부여",
                style=discord.ButtonStyle.success,
                emoji="🎖️",
                custom_id=f"give_role_{member.id}"
            )
        )
        
        # 환영 메시지 선택
        welcome_select = Select(
            placeholder="환영 메시지 선택",
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
                    description="공식적인 환영 메시지",
                    emoji="📜"
                )
            ],
            custom_id=f"welcome_select_{member.id}"
        )
        self.add_item(welcome_select)

# ============================================================
# Modal 클래스
# ============================================================

class WelcomeModal(Modal):
    """맞춤 환영 메시지 작성을 위한 Modal"""
    def __init__(self, member: discord.Member):
        super().__init__(title="✏️ 맞춤 환영 메시지 작성")
        self.member = member
        
        self.message_input = TextInput(
            label="환영 메시지",
            placeholder=f"{member.mention}님을 환영하는 메시지를 작성해주세요...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.message_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        content = self.message_input.value
        view = TextCardView("👋 맞춤 환영 메시지", content, f"{self.member.name}님 입장을 환영합니다!")
        await interaction.response.send_message(view=view)

# ============================================================
# 봇 클래스
# ============================================================

class InfoBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.messages = True
        
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.log_channel_id = None
        
    async def setup_hook(self):
        await self.tree.sync()
        logger.info("✅ 명령어 동기화 완료")
        
    async def update_info_channels(self, guild: discord.Guild):
        """서버 정보 채널 업데이트"""
        if not guild:
            return
            
        if not guild.me.guild_permissions.manage_channels:
            logger.warning(f"❌ {guild.name}: 채널 관리 권한 없음")
            return
            
        try:
            await guild.chunk()
            
            total = guild.member_count or 0
            bots = sum(1 for member in guild.members if member.bot)
            humans = total - bots
            
            channels_data = {
                "Members": f"・Members: {total}",
                "Humans": f"・Humans: {humans}",
                "Bots": f"・Bots: {bots}"
            }
            
            for channel_type, name in channels_data.items():
                await self._create_or_update_channel(guild, channel_type, name)
                
        except Exception as e:
            logger.error(f"❌ 정보 채널 업데이트 실패: {e}")
            
    async def _create_or_update_channel(self, guild: discord.Guild, channel_type: str, name: str):
        """채널 생성 또는 업데이트"""
        for channel in guild.voice_channels:
            if channel_type.lower() in channel.name.lower():
                if channel.name != name:
                    try:
                        await channel.edit(name=name)
                        logger.info(f"✅ {guild.name}: {name} 업데이트 완료")
                    except Exception as e:
                        logger.error(f"❌ 채널 업데이트 실패: {e}")
                return
                
        try:
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
            
            await guild.create_voice_channel(
                name=name,
                overwrites=overwrites,
                reason="서버 정보 채널 생성"
            )
            logger.info(f"✅ {guild.name}: {name} 생성 완료")
            
        except Exception as e:
            logger.error(f"❌ 채널 생성 실패: {e}")
    
    async def send_join_log(self, member: discord.Member):
        """입장 로그 전송 (Components V2 텍스트 카드)"""
        try:
            # 로그 채널 찾기
            log_channel = None
            if self.log_channel_id:
                log_channel = member.guild.get_channel(self.log_channel_id)
            
            if not log_channel:
                for channel in member.guild.text_channels:
                    if '입장-로그' in channel.name or 'join-log' in channel.name:
                        log_channel = channel
                        self.log_channel_id = channel.id
                        break
            
            if not log_channel:
                overwrites = {
                    member.guild.default_role: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=False
                    ),
                    member.guild.me: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True
                    )
                }
                
                log_channel = await member.guild.create_text_channel(
                    '📥-입장-로그',
                    overwrites=overwrites,
                    reason="입장 로그 채널 생성"
                )
                self.log_channel_id = log_channel.id
            
            # 텍스트 카드 내용 구성
            content = (
                f"**📛 이름:** {member.name}\n"
                f"**🆔 ID:** `{member.id}`\n"
                f"**👤 멘션:** {member.mention}\n\n"
                f"**📅 계정 생성일:** {member.created_at.strftime('%Y년 %m월 %d일 %H:%M')}\n"
                f"**🤖 봇 여부:** {'✅ 봇' if member.bot else '❌ 일반 유저'}\n"
                f"**👥 총 멤버 수:** {member.guild.member_count}명"
            )
            
            title = f"👋 새 멤버 입장! - {member.name}"
            footer = f"입장 시간: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}"
            
            # 텍스트 카드 전송
            text_card = TextCardView(title, content, footer)
            await log_channel.send(view=text_card)
            
            # 버튼 뷰 전송
            button_view = JoinLogView(member)
            await log_channel.send(view=button_view)
            
        except Exception as e:
            logger.error(f"❌ 입장 로그 전송 실패: {e}")

# ============================================================
# 봇 인스턴스 생성 (이벤트 등록보다 먼저)
# ============================================================

bot = InfoBot()

# ============================================================
# 이벤트 핸들러
# ============================================================

@bot.event
async def on_ready():
    logger.info(f"✅ {bot.user} 실행됨 (discord.py {discord.__version__})")
    logger.info(f"📊 총 {len(bot.guilds)}개 서버 연결됨")
    
    for guild in bot.guilds:
        try:
            await bot.update_info_channels(guild)
            logger.info(f"✅ {guild.name} 정보 채널 준비 완료")
        except Exception as e:
            logger.error(f"❌ {guild.name} 정보 채널 오류: {e}")

@bot.event
async def on_member_join(member: discord.Member):
    try:
        # 정보 채널 업데이트
        await bot.update_info_channels(member.guild)
        
        # 입장 로그 전송
        await bot.send_join_log(member)
        
        logger.info(f"👤 {member} 입장 - {member.guild.name} 정보 업데이트 완료")
    except Exception as e:
        logger.error(f"❌ 멤버 입장 처리 오류: {e}")

@bot.event
async def on_member_remove(member: discord.Member):
    try:
        await bot.update_info_channels(member.guild)
        logger.info(f"👋 {member} 퇴장 - {member.guild.name} 정보 업데이트")
    except Exception as e:
        logger.error(f"❌ 멤버 퇴장 처리 오류: {e}")

@bot.event
async def on_guild_join(guild: discord.Guild):
    try:
        await bot.update_info_channels(guild)
        logger.info(f"✅ {guild.name} 서버에 입장했습니다.")
    except Exception as e:
        logger.error(f"❌ 서버 입장 처리 오류: {e}")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """인터랙션 이벤트 처리"""
    if not interaction.type == discord.InteractionType.component:
        return
    
    custom_id = interaction.data.get("custom_id", "")
    
    # 역할 부여 처리
    if custom_id.startswith("give_role_"):
        member_id = int(custom_id.split("_")[2])
        member = interaction.guild.get_member(member_id)
        
        if not member:
            await interaction.response.send_message(
                "❌ 멤버를 찾을 수 없습니다.",
                ephemeral=True
            )
            return
        
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ 역할을 부여할 권한이 없습니다.",
                ephemeral=True
            )
            return
        
        # 기본 역할 찾기
        default_role = None
        for role in interaction.guild.roles:
            if role.name == "멤버" or role.name == "Member" or role.position == 1:
                default_role = role
                break
        
        if not default_role:
            default_role = interaction.guild.roles[-1] if len(interaction.guild.roles) > 1 else None
        
        if default_role and default_role != interaction.guild.default_role:
            try:
                await member.add_roles(default_role, reason="입장 시 기본 역할 부여")
                
                content = f"✅ {member.mention}님에게 **{default_role.name}** 역할을 부여했습니다!"
                view = TextCardView("✅ 역할 부여 완료", content)
                await interaction.response.send_message(view=view)
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ 역할 부여 실패: {e}",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "❌ 부여할 기본 역할이 없습니다.",
                ephemeral=True
            )
    
    # 환영 메시지 선택 처리
    elif custom_id.startswith("welcome_select_"):
        member_id = int(custom_id.split("_")[2])
        member = interaction.guild.get_member(member_id)
        
        if not member:
            await interaction.response.send_message(
                "❌ 멤버를 찾을 수 없습니다.",
                ephemeral=True
            )
            return
        
        selected = interaction.data.get("values", [])[0] if interaction.data.get("values") else None
        
        if selected == "custom":
            modal = WelcomeModal(member)
            await interaction.response.send_modal(modal)
            return
        
        welcome_messages = {
            "default": f"👋 {member.mention}님, 서버에 오신 것을 환영합니다! 즐거운 시간 보내세요!",
            "warm": f"❤️ {member.mention}님, 따뜻하게 환영합니다! 함께 즐거운 시간을 만들어봐요~",
            "official": f"📜 {member.mention}님, 공식적으로 환영합니다! 서버 규칙을 확인하시고 즐거운 활동 되세요!"
        }
        
        content = welcome_messages.get(selected, "👋 환영합니다!")
        view = TextCardView("👋 환영합니다!", content, f"{member.name}님 입장을 환영합니다!")
        await interaction.response.send_message(view=view)

@bot.event
async def on_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ 이 명령어를 사용할 권한이 없습니다.",
            ephemeral=True
        )
    else:
        logger.error(f"❌ 명령어 에러: {error}")
        await interaction.response.send_message(
            "❌ 명령어 실행 중 오류가 발생했습니다.",
            ephemeral=True
        )

# ============================================================
# 명령어 정의
# ============================================================

@bot.tree.command(
    name="임베드",
    description="텍스트 카드 형태의 메시지를 생성합니다"
)
@app_commands.describe(
    내용="표시할 내용",
    제목="카드 제목 (선택)"
)
async def embed_command(
    interaction: discord.Interaction,
    내용: str,
    제목: Optional[str] = None
):
    """텍스트 카드 메시지 생성"""
    try:
        title = 제목 or "📝 메시지"
        footer = f"요청자: {interaction.user.display_name}"
        
        view = TextCardView(title, 내용, footer)
        await interaction.response.send_message(view=view)
        
    except Exception as e:
        logger.error(f"❌ 임베드 생성 오류: {e}")
        await interaction.response.send_message(
            "❌ 메시지를 생성하는 중 오류가 발생했습니다.",
            ephemeral=True
        )

@bot.tree.command(
    name="서버정보",
    description="서버의 기본 정보를 텍스트 카드로 표시합니다"
)
async def server_info(interaction: discord.Interaction):
    """서버 정보 표시"""
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
        bots = sum(1 for member in guild.members if member.bot)
        humans = total - bots
        
        content = (
            f"**👤 Humans:** {humans}\n"
            f"**🤖 Bots:** {bots}\n"
            f"**👥 Members:** {total}\n\n"
            f"**📅 생성일:** {guild.created_at.strftime('%Y년 %m월 %d일')}\n"
            f"**👑 서버장:** {guild.owner.mention if guild.owner else '알 수 없음'}\n"
            f"**📌 채널 수:** {len(guild.channels)}\n"
            f"**🎨 역할 수:** {len(guild.roles)}"
        )
        
        title = f"📊 {guild.name}"
        footer = f"요청자: {interaction.user.display_name}"
        
        view = TextCardView(title, content, footer)
        await interaction.response.send_message(view=view)
        
    except Exception as e:
        logger.error(f"❌ 서버 정보 오류: {e}")
        await interaction.response.send_message(
            "❌ 서버 정보를 표시하는 중 오류가 발생했습니다.",
            ephemeral=True
        )

@bot.tree.command(
    name="정보채널",
    description="서버 정보 채널을 생성하거나 업데이트합니다"
)
async def info_channel(interaction: discord.Interaction):
    """정보 채널 업데이트"""
    if not interaction.guild:
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
        await bot.update_info_channels(interaction.guild)
        await interaction.edit_original_response(
            content="✅ 서버 정보 채널이 업데이트되었습니다!"
        )
    except Exception as e:
        logger.error(f"❌ 정보 채널 업데이트 오류: {e}")
        await interaction.edit_original_response(
            content="❌ 정보 채널 업데이트 중 오류가 발생했습니다."
        )

@bot.tree.command(
    name="로그채널",
    description="입장 로그 채널을 설정합니다"
)
@app_commands.describe(
    채널="로그를 보낼 채널"
)
async def set_log_channel(
    interaction: discord.Interaction,
    채널: discord.TextChannel
):
    """로그 채널 설정"""
    if not interaction.guild:
        await interaction.response.send_message(
            "❌ 서버에서만 사용할 수 있습니다.",
            ephemeral=True
        )
        return
    
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "❌ 채널 관리 권한이 필요합니다.",
            ephemeral=True
        )
        return
    
    try:
        bot.log_channel_id = 채널.id
        content = f"✅ 입장 로그 채널이 {채널.mention}(으)로 설정되었습니다!"
        view = TextCardView("📥 로그 채널 설정", content)
        await interaction.response.send_message(view=view, ephemeral=True)
    except Exception as e:
        logger.error(f"❌ 로그 채널 설정 오류: {e}")
        await interaction.response.send_message(
            "❌ 로그 채널 설정 중 오류가 발생했습니다.",
            ephemeral=True
        )

@bot.tree.command(
    name="핑",
    description="봇의 응답 속도를 확인합니다"
)
async def ping(interaction: discord.Interaction):
    """핑 확인"""
    latency = round(bot.latency * 1000)
    content = f"**응답 속도:** {latency}ms"
    view = TextCardView("🏓 퐁!", content)
    await interaction.response.send_message(view=view, ephemeral=True)

# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        logger.error("❌ DISCORD_TOKEN 환경변수가 없습니다!")
        exit(1)
        
    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        logger.error("❌ 잘못된 토큰입니다. DISCORD_TOKEN을 확인해주세요.")
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
