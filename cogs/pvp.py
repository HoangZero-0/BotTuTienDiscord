import discord
from discord.ext import commands
from utils import get_db, update_player_stats
import random
import asyncio

class PvPBattleView(discord.ui.View):
    def __init__(self, db_path, p1_data, p2_data, bot_cog):
        super().__init__(timeout=60.0) # 60 giây ngâm lượt là xử thua
        self.db_path = db_path
        self.bot_cog = bot_cog
        
        self.p1 = p1_data
        self.p2 = p2_data
        
        # Random lượt đi đầu tiên
        self.current_turn = random.choice([self.p1['user_id'], self.p2['user_id']])
        self.turn_count = 1
        self.log_text = f"🎲 Lãnh chúa vận mệnh chọn **{'Người Thách Đấu' if self.current_turn == self.p1['user_id'] else 'Người Bị Thách'}** đi trước!"

        # Create Buttons (Generic for both)
        for i in range(1, 5):
            btn = discord.ui.Button(label=f"Tuyệt Kỹ {i}", style=discord.ButtonStyle.primary, row=0 if i<=2 else 1, custom_id=f"skill_{i}")
            btn.callback = self.make_attack_callback(i)
            self.add_item(btn)
            
        btn_atk = discord.ui.Button(label="⚔️ Đánh Thường", style=discord.ButtonStyle.secondary, row=2, custom_id="skill_0")
        btn_atk.callback = self.make_attack_callback(0)
        self.add_item(btn_atk)
        
        btn_surrender = discord.ui.Button(label="🏳️ Nhận thua", style=discord.ButtonStyle.danger, row=2, custom_id="action_surrender")
        btn_surrender.callback = self.surrender_callback
        self.add_item(btn_surrender)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user_id = str(interaction.user.id)
        if user_id not in (self.p1['user_id'], self.p2['user_id']):
            await interaction.response.send_message("❌ Ngươi là kẻ đứng xem, không được xen vào trận tỷ thí!", ephemeral=True)
            return False
        return True

    def get_player(self, user_id):
        return self.p1 if self.p1['user_id'] == user_id else self.p2

    def get_opponent(self, user_id):
        return self.p2 if self.p1['user_id'] == user_id else self.p1

    async def on_timeout(self):
        loser = self.get_player(self.current_turn)
        winner = self.get_opponent(self.current_turn)
        self.log_text = f"⏳ Thời gian trôi qua, {loser['name']} dường như đứng im chịu chết. Xử thua do bỏ AFK!"
        await self.end_battle(None, winner, loser)

    def make_attack_callback(self, slot):
        async def callback(interaction: discord.Interaction):
            user_id = str(interaction.user.id)
            if user_id != self.current_turn:
                return await interaction.response.send_message("⏳ Phải chờ đối phương ra chiêu mới đến lượt của ngươi!", ephemeral=True)
            
            attacker = self.get_player(user_id)
            defender = self.get_opponent(user_id)
            
            # Identify skill
            if slot == 0:
                s_name, s_cost, s_mult = "Kiếm Lực Nguyên Sinh", 1, 1.0
            else:
                skill = attacker['skills'].get(slot)
                if not skill:
                    return await interaction.response.send_message("⚠️ Ngươi chưa trang bị công pháp ở khe cắm này!", ephemeral=True)
                s_name, s_element, s_mult, s_cost = skill
                
            if attacker['tl'] < s_cost:
                return await interaction.response.send_message(f"⚠️ Không đủ {s_cost} Thể lực, không thể ra đòn!", ephemeral=True)
                
            attacker['tl'] -= s_cost
            
            # Calculate Damage
            ratio = attacker['cp'] / max(1, defender['cp'])
            # Base = 12-25% Máu của Nạn Nhân
            base_dmg = defender['max_hp'] * random.uniform(0.12, 0.25)
            # Khống chế damage bạo kích / phế vật tối đa
            bounded_ratio = min(5.0, max(0.1, ratio)) 
            
            dmg = int(base_dmg * bounded_ratio * s_mult)
            if dmg <= 0: dmg = 1
            
            defender['hp'] -= dmg
            if defender['hp'] < 0: defender['hp'] = 0
            
            # Log
            self.log_text = f"💥 [Lượt {self.turn_count}] **{attacker['name']}** xuất ra `{s_name}`, sát thương cuồn cuộn giáng **{dmg:,}** điểm lên đối diện!"
            self.turn_count += 1
            
            if defender['hp'] <= 0:
                await self.end_battle(interaction, attacker, defender)
            else:
                self.current_turn = defender['user_id']
                await self.update_ui(interaction)
                
        return callback

    async def surrender_callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id != self.current_turn:
            return await interaction.response.send_message("Chỉ có thể xin thua khi tới lượt của mình!", ephemeral=True)
            
        loser = self.get_player(user_id)
        winner = self.get_opponent(user_id)
        
        self.log_text = f"🏳️ [Lượt {self.turn_count}] **{loser['name']}** cảm thấy hoảng sợ và tự phế võ công, gục xuống xin tha!"
        loser['hp'] = 0
        await self.end_battle(interaction, winner, loser)

    async def update_ui(self, interaction):
        for child in self.children:
            if child.custom_id and child.custom_id.startswith("skill_"):
                slot = int(child.custom_id.split("_")[1])
                # Show skill name if it's currently user's turn acting
                pass 
                # Chú ý: Vì 1 cục view này được nhìn bởi cả 2 user, text trên button phải trung lập!
                # Do đó label vẫn để yên "Tuyệt Kỹ 1, 2, 3..."

        embed = interaction.message.embeds[0]
        embed.clear_fields()
        
        hp1_bar = int((self.p1['hp'] / max(1, self.p1['max_hp'])) * 10)
        hp2_bar = int((self.p2['hp'] / max(1, self.p2['max_hp'])) * 10)
        
        embed.description = f"⚔️ Đang đến lượt của: **<@{self.current_turn}>**"
        embed.add_field(name="Diễn biến tỷ thí", value=self.log_text, inline=False)
        embed.add_field(name=f"🔵 {self.p1['name']}", value=f"`[{'🟦'*hp1_bar}{'⬜'*(10-hp1_bar)}]`\nHP: **{self.p1['hp']:,}/{self.p1['max_hp']:,}**\nKhí: {self.p1['tl']}", inline=True)
        embed.add_field(name=f"🔴 {self.p2['name']}", value=f"`[{'🟥'*hp2_bar}{'⬜'*(10-hp2_bar)}]`\nHP: **{self.p2['hp']:,}/{self.p2['max_hp']:,}**\nKhí: {self.p2['tl']}", inline=True)
        
        if interaction:
            await interaction.response.edit_message(embed=embed, view=self)

    async def end_battle(self, interaction, winner, loser):
        self.stop()
        for child in self.children: child.disabled = True
        
        # Tính toán cướp 5% Tu vi
        stolen_tv = int(loser['tu_vi'] * 0.05)
        if stolen_tv <= 0: stolen_tv = 0
        
        async with get_db(self.db_path) as db:
            # Update winner
            await db.execute("UPDATE players SET sinh_luc = ?, the_luc = ?, tu_vi = tu_vi + ? WHERE user_id = ?", 
                             (winner['hp'], winner['tl'], stolen_tv, winner['user_id']))
            # Update loser
            await db.execute("UPDATE players SET sinh_luc = 0, the_luc = ?, tu_vi = max(0, tu_vi - ?) WHERE user_id = ?", 
                             (loser['tl'], stolen_tv, loser['user_id']))
            await db.commit()
            
        final_log = self.log_text + f"\n\n🏆 **TỔNG KẾT** 🏆\n**{winner['name']}** Vang danh thiên hạ, cướp đoạt **{stolen_tv:,}** Tu Vi của kẻ chiến bại!\n**{loser['name']}** Trọng thương, sinh lực bằng 0."
        
        # Lấy embed hiện tại hoặc lấy từ cog truyền vao
        if interaction:
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.gold()
            embed.description = f"⚔️ TRẬN CHIẾN KẾT THÚC"
            embed.clear_fields()
            embed.add_field(name="Lịch Sử Huyết Chiến", value=final_log, inline=False)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Handle Timeout message replacing later manually logic
            pass


class ChallengeView(discord.ui.View):
    def __init__(self, db_path, challenger, target, bot_cog):
        super().__init__(timeout=120.0)
        self.db_path = db_path
        self.challenger = challenger
        self.target = target
        self.bot_cog = bot_cog

    @discord.ui.button(label="⚔️ Chấp nhận tỷ thí", style=discord.ButtonStyle.success)
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            return await interaction.response.send_message("❌ Người được thách đấu không phải là bạn!", ephemeral=True)
            
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(content=f"🔥 **{self.target.mention} đã CHẤP NHẬN lời thách đấu! Chiến Sự Bùng Nổ!**", view=self)
        self.stop()
        await self.bot_cog.start_pvp(interaction.message.channel, self.challenger, self.target)

    @discord.ui.button(label="🏃 Khước từ", style=discord.ButtonStyle.danger)
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            return await interaction.response.send_message("❌ Quyền từ chối thuộc về người được mời!", ephemeral=True)
            
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(content=f"💨 **{self.target.mention} cảm thấy không khỏe nên đã từ chối tỷ thí.**", view=self)
        self.stop()


class PvP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    @commands.command(name="thachdau", aliases=["pvp", "pk"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def invoke_pvp(self, ctx, target: discord.Member = None):
        if not target:
            return await ctx.send("❌ Ngài muốn thách đấu hư không sao? Hãy tag @Tên_đối_thủ vào!")
        if target == ctx.author:
            return await ctx.send("❌ Đánh bản thân thì có ích gì?")
        if target.bot:
            return await ctx.send("❌ Bot không rảnh chơi PvP với ngài, đi săn quái vật đi!")
            
        challenger_id = str(ctx.author.id)
        target_id = str(target.id)

        # Check conditions
        res_c = await update_player_stats(self.db_path, challenger_id)
        if not res_c: return await ctx.send("❌ Đạo hữu chưa tu luyện!")
        if res_c[0] < 5: return await ctx.send("⚠️ Ngài không đủ kích hoạt đan điền (Cần 5 Thể lực)!")
        if res_c[1] <= 0: return await ctx.send("💀 Người đang hấp hối không có tư cách đi xưng hùng xưng bá!")

        res_t = await update_player_stats(self.db_path, target_id)
        if not res_t: return await ctx.send("❌ Tên kia là một kẻ phàm phu tục tử, chưa từng tu chân!")
        if res_t[0] < 5: return await ctx.send("⚠️ Đối thủ không đủ Thể lực để đấu!")
        if res_t[1] <= 0: return await ctx.send("💀 Tên kia đang dưỡng thương do hết sạch Sinh Lực, tha cho hắn đi!")

        view = ChallengeView(self.db_path, ctx.author, target, self)
        await ctx.send(f"🛡️ {target.mention}, **{ctx.author.display_name}** ném chiến thư vào mặt bạn!\n⚔️ Nếu thoái thác, bạn sẽ không mất gì, nhưng nếu lên đài, kẻ gục ngã sẽ mất **5% Đạo Hạnh (Tu Vi)**! Bạn dám không?", view=view)

    async def _fetch_player_pvp_data(self, user):
        async with get_db(self.db_path) as db:
            c = await db.execute("SELECT p.tu_vi, p.luc_chien_goc, COALESCE(SUM(im.chi_so_buff), 0), p.sinh_luc, p.the_luc, p.canh_gioi_id, p.dao_hieu "
                                 "FROM players p LEFT JOIN inventory i ON p.user_id = i.user_id AND i.trang_thai = 'dang_trang_bi' "
                                 "LEFT JOIN item_master im ON i.item_id = im.item_id WHERE p.user_id = ?", (str(user.id),))
            r = await c.fetchone()
            if not r: return None
            
            tu_vi, base_cp, buff_cp, sl, tl, cg_id, dao_hieu = r
            cp = base_cp + (buff_cp or 0)
            max_sl = cg_id * 100
            dh_prefix = f"[{dao_hieu}] " if dao_hieu else ""
            
            # Fetch equipped skills
            skills = {}
            c2 = await db.execute("""
                SELECT eq.slot, sm.name, sm.element, sm.base_multiplier, sm.stamina_cost 
                FROM player_equipped_skills eq JOIN skills_master sm ON eq.skill_id = sm.skill_id 
                WHERE eq.user_id = ?
            """, (str(user.id),))
            for row in await c2.fetchall():
                skills[row[0]] = (row[1], row[2], row[3], row[4])
                
            return {
                'user_id': str(user.id),
                'name': f"{dh_prefix}{user.display_name}",
                'hp': sl,
                'max_hp': max_sl,
                'tl': tl,
                'cp': cp,
                'tu_vi': tu_vi,
                'skills': skills
            }

    async def start_pvp(self, channel, p1, p2):
        p1_data = await self._fetch_player_pvp_data(p1)
        p2_data = await self._fetch_player_pvp_data(p2)
        
        if not p1_data or not p2_data: return await channel.send("Lỗi xảy ra khi giải nén khí cơ võ giả.")

        view = PvPBattleView(self.db_path, p1_data, p2_data, self)
        
        embed = discord.Embed(title=f"⚔️ SÀN ĐẤU CỬU GIỚI: {p1_data['name']} VS {p2_data['name']}", color=discord.Color.red())
        embed.description = f"Vận sức chuẩn bị công kích! Trận đấu Bắt Đầu!"
        
        # Init View Embed Layout
        hp1_bar = int((p1_data['hp'] / max(1, p1_data['max_hp'])) * 10)
        hp2_bar = int((p2_data['hp'] / max(1, p2_data['max_hp'])) * 10)
        embed.add_field(name="Diễn biến", value=view.log_text, inline=False)
        embed.add_field(name=p1_data['name'], value=f"`[{'🟦'*hp1_bar}{'⬜'*(10-hp1_bar)}]`\nHP: {p1_data['hp']:,}\nPhí: {p1_data['tl']}", inline=True)
        embed.add_field(name=p2_data['name'], value=f"`[{'🟥'*hp2_bar}{'⬜'*(10-hp2_bar)}]`\nHP: {p2_data['hp']:,}\nPhí: {p2_data['tl']}", inline=True)
        
        msg = await channel.send(embed=embed, view=view)
        # Store message to edit later on timeout
        view.message = msg
        
        # Override on_timeout to edit message directly
        original_timeout = view.on_timeout
        async def custom_timeout():
            loser_id = view.current_turn
            winner_id = p1_data['user_id'] if loser_id == p2_data['user_id'] else p2_data['user_id']
            loser = view.get_player(loser_id)
            winner = view.get_player(winner_id)
            
            view.log_text = f"⏳ Thời gian trôi qua, **{loser['name']}** tĩnh tọa ngủ quên trên đài. Xử AFK Thua Cuộc!"
            loser['hp'] = 0
            
            stolen_tv = int(loser['tu_vi'] * 0.05) if loser['tu_vi'] else 0
            async with get_db(self.db_path) as db:
                await db.execute("UPDATE players SET sinh_luc = ?, the_luc = ?, tu_vi = tu_vi + ? WHERE user_id = ?", (winner['hp'], winner['tl'], stolen_tv, winner['user_id']))
                await db.execute("UPDATE players SET sinh_luc = 0, the_luc = ?, tu_vi = max(0, tu_vi - ?) WHERE user_id = ?", (loser['tl'], stolen_tv, loser['user_id']))
                await db.commit()
                
            for child in view.children: child.disabled = True
            e = msg.embeds[0]
            e.color = discord.Color.teal()
            e.clear_fields()
            e.description = "⚔️ TRẬN TỶ THÍ BỊ GIÁN ĐOẠN"
            e.add_field(name="Lịch Sử Huyết Chiến", value=view.log_text + f"\n\n🏆 **TỔNG KẾT**\n**{winner['name']}** hốt tay trên **{stolen_tv:,}** Tu Vi từ con gà gật gù!", inline=False)
            await msg.edit(embed=e, view=view)
            
        view.on_timeout = custom_timeout

async def setup(bot):
    await bot.add_cog(PvP(bot))
