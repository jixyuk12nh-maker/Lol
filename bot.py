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
        """입장 로그 전송 (discord.py 2.6.0 Components V2)"""
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
            
            # Components V2 - View 생성
            view = JoinLogView(member)
            
            # 임베드 생성
            embed = discord.Embed(
                title="👋 새 멤버 입장!",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.set_author(
                name=f"{member.name}#{member.discriminator}",
                icon_url=member.display_avatar.url
            )
            
            # 유저 정보 (이름, ID, 멘션)
            embed.add_field(
                name="📛 이름",
                value=f"**{member.name}**",
                inline=True
            )
            embed.add_field(
                name="🆔 ID",
                value=f"`{member.id}`",
                inline=True
            )
            embed.add_field(
                name="👤 멘션",
                value=member.mention,
                inline=True
            )
            
            # 추가 정보
            embed.add_field(
                name="📅 계정 생성일",
                value=member.created_at.strftime("%Y년 %m월 %d일 %H:%M"),
                inline=True
            )
            embed.add_field(
                name="🤖 봇 여부",
                value="✅ 봇" if member.bot else "❌ 일반 유저",
                inline=True
            )
            embed.add_field(
                name="👥 총 멤버 수",
                value=f"{member.guild.member_count}명",
                inline=True
            )
            
            embed.set_footer(
                text=f"입장 시간",
                icon_url=member.guild.icon.url if member.guild.icon else None
            )
            
            # 로그 메시지 전송
            await log_channel.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"❌ 입장 로그 전송 실패: {e}")

# Components V2 - View 클래스
class JoinLogView(View):
    """입장 로그용 Components V2 View"""
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
                ),
                discord.SelectOption(
                    label="맞춤 환영",
                    value="custom",
                    description="맞춤 환영 메시지 작성",
                    emoji="✏️"
                )
            ],
            custom_id=f"welcome_select_{member.id}"
        )
        self.add_item(welcome_select)
        
        # 정보 보기 버튼 (새로운 버튼)
        self.add_item(
            Button(
                label="상세 정보",
                style=discord.ButtonStyle.secondary,
                emoji="📊",
                custom_id=f"detail_info_{member.id}"
            )
        )

# Components V2 - 이벤트 핸들러
@bot.event
async def on_interaction(interaction: discord.Interaction):
    """인터랙션 이벤트 처리 (discord.py 2.6.0)"""
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
        
        # 권한 체크
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
                
                embed = discord.Embed(
                    title="✅ 역할 부여 완료",
                    description=f"{member.mention}님에게 **{default_role.name}** 역할을 부여했습니다!",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
                
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
            # Modal 사용 (discord.py 2.6.0 새로운 기능)
            modal = WelcomeModal(member)
            await interaction.response.send_modal(modal)
            return
        
        welcome_messages = {
            "default": f"👋 {member.mention}님, 서버에 오신 것을 환영합니다! 즐거운 시간 보내세요!",
            "warm": f"❤️ {member.mention}님, 따뜻하게 환영합니다! 함께 즐거운 시간을 만들어봐요~",
            "official": f"📜 {member.mention}님, 공식적으로 환영합니다! 서버 규칙을 확인하시고 즐거운 활동 되세요!"
        }
        
        embed = discord.Embed(
            title="👋 환영합니다!",
            description=welcome_messages.get(selected, "👋 환영합니다!"),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{member.name}님 입장을 환영합니다!")
        
        await interaction.response.send_message(embed=embed)
    
    # 상세 정보 처리
    elif custom_id.startswith("detail_info_"):
        member_id = int(custom_id.split("_")[2])
        member = interaction.guild.get_member(member_id)
        
        if not member:
            await interaction.response.send_message(
                "❌ 멤버를 찾을 수 없습니다.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📊 {member.name} 상세 정보",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # 상세 정보 추가
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=False)
        embed.add_field(name="📛 이름", value=member.name, inline=True)
        embed.add_field(name="🏷️ 디스크리미네이터", value=f"#{member.discriminator}", inline=True)
        embed.add_field(name="👤 멘션", value=member.mention, inline=True)
        embed.add_field(name="📅 가입일", value=member.joined_at.strftime("%Y년 %m월 %d일") if member.joined_at else "알 수 없음", inline=True)
        embed.add_field(name="📅 계정 생성일", value=member.created_at.strftime("%Y년 %m월 %d일"), inline=True)
        embed.add_field(name="🎨 역할", value=f"{len(member.roles)}개", inline=True)
        embed.add_field(name="🤖 봇", value="✅" if member.bot else "❌", inline=True)
        embed.add_field(name="🔊 음성 채널", value=member.voice.channel.name if member.voice and member.voice.channel else "없음", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Modal 클래스 (discord.py 2.6.0)
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
        embed = discord.Embed(
            title="👋 맞춤 환영 메시지",
            description=self.message_input.value,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"{self.member.name}님 입장을 맞춤으로 환영합니다!")
        
        await interaction.response.send_message(embed=embed)

# 명령어 정의
@bot.tree.command(name="임베드", description="임베드 메시지를 생성합니다")
@app_commands.describe(내용="표시할 내용", 제목="제목 (선택)")
async def embed_command(interaction: discord.Interaction, 내용: str, 제목: Optional[str] = None):
    try:
        embed = discord.Embed(
            title=제목 or "📝 메시지",
            description=내용,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"요청자: {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"❌ 임베드 생성 오류: {e}")
        await interaction.response.send_message(
            "❌ 메시지를 생성하는 중 오류가 발생했습니다.",
            ephemeral=True
        )

@bot.tree.command(name="서버정보", description="서버의 기본 정보를 표시합니다")
async def server_info(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("❌ 서버에서만 사용할 수 있습니다.", ephemeral=True)
        return
    
    try:
        await interaction.guild.chunk()
        guild = interaction.guild
        total = guild.member_count or 0
        bots = sum(1 for member in guild.members if member.bot)
        humans = total - bots
        
        embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.green())
        embed.add_field(name="👤 Humans", value=humans, inline=True)
        embed.add_field(name="🤖 Bots", value=bots, inline=True)
        embed.add_field(name="👥 Total", value=total, inline=True)
        embed.add_field(name="📅 생성일", value=guild.created_at.strftime("%Y년 %m월 %d일"), inline=True)
        embed.add_field(name="👑 서버장", value=guild.owner.mention if guild.owner else "알 수 없음", inline=True)
        embed.add_field(name="📌 채널 수", value=len(guild.channels), inline=True)
        embed.set_footer(text=f"요청자: {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"❌ 서버 정보 오류: {e}")
        await interaction.response.send_message("❌ 서버 정보를 표시하는 중 오류가 발생했습니다.", ephemeral=True)

@bot.tree.command(name="정보채널", description="서버 정보 채널을 생성하거나 업데이트합니다")
async def info_channel(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("❌ 서버에서만 사용할 수 있습니다.", ephemeral=True)
        return
    
    await interaction.response.send_message("🔄 서버 정보 채널을 업데이트하는 중...", ephemeral=True)
    
    try:
        await bot.update_info_channels(interaction.guild)
        await interaction.edit_original_response(content="✅ 서버 정보 채널이 업데이트되었습니다!")
    except Exception as e:
        logger.error(f"❌ 정보 채널 업데이트 오류: {e}")
        await interaction.edit_original_response(content="❌ 정보 채널 업데이트 중 오류가 발생했습니다.")

@bot.tree.command(name="핑", description="봇의 응답 속도를 확인합니다")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 퐁! 응답 속도: {latency}ms", ephemeral=True)

@bot.tree.command(name="로그채널", description="입장 로그 채널을 설정합니다")
@app_commands.describe(채널="로그를 보낼 채널")
async def set_log_channel(interaction: discord.Interaction, 채널: discord.TextChannel):
    if not interaction.guild:
        await interaction.response.send_message("❌ 서버에서만 사용할 수 있습니다.", ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ 채널 관리 권한이 필요합니다.", ephemeral=True)
        return
    
    try:
        bot.log_channel_id = 채널.id
        await interaction.response.send_message(
            f"✅ 입장 로그 채널이 {채널.mention}(으)로 설정되었습니다!",
            ephemeral=True
        )
    except Exception as e:
        logger.error(f"❌ 로그 채널 설정 오류: {e}")
        await interaction.response.send_message("❌ 로그 채널 설정 중 오류가 발생했습니다.", ephemeral=True)

# 이벤트 핸들러
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
        await bot.update_info_channels(member.guild)
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
async def on_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ 이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
    else:
        logger.error(f"❌ 명령어 에러: {error}")
        await interaction.response.send_message("❌ 명령어 실행 중 오류가 발생했습니다.", ephemeral=True)

# 실행
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
