import discord
from discord.ext import commands
from utils import get_db


class SkillEquipSelect(discord.ui.Select):
    def __init__(self, db_path, player_skills, bot_cog):
        self.db_path = db_path
        self.bot_cog = bot_cog
        options = []
        for s in player_skills:
            s_id, s_name, s_element, s_mult, s_cost = s
            options.append(
                discord.SelectOption(
                    label=f"[{s_element}] {s_name}",
                    description=f"Sát thương x{s_mult} | Phí: {s_cost} Thể lực",
                    value=str(s_id),
                )
            )

        super().__init__(
            placeholder="Chọn tối đa 4 Công Pháp để mang theo...",
            min_values=1,
            max_values=min(4, len(options)),
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_ids = [int(v) for v in self.values]
        user_id = str(interaction.user.id)

        async with get_db(self.db_path) as db:
            await db.execute(
                "DELETE FROM player_equipped_skills WHERE user_id = ?", (user_id,)
            )
            insert_data = [
                (user_id, idx + 1, sid) for idx, sid in enumerate(selected_ids)
            ]
            await db.executemany(
                "INSERT INTO player_equipped_skills (user_id, slot, skill_id) VALUES (?, ?, ?)",
                insert_data,
            )
            await db.commit()

        await interaction.response.send_message(
            f"✅ Đã mang theo {len(selected_ids)} công pháp vào trận!", ephemeral=True
        )


class SkillView(discord.ui.View):
    def __init__(self, db_path, player_skills, bot_cog):
        super().__init__(timeout=60)
        self.add_item(SkillEquipSelect(db_path, player_skills, bot_cog))


class CongPhap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    @commands.command(name="hoc", aliases=["doc", "learn"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hoc_cong_phap(self, ctx):
        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            # Tìm danh sách bí kíp trong túi
            cursor = await db.execute(
                """
                SELECT i.item_id, im.ten_vat_pham, im.mo_ta 
                FROM inventory i JOIN item_master im ON i.item_id = im.item_id 
                WHERE i.user_id = ? AND im.loai_vat_pham = 'skill_book' AND i.so_luong > 0
            """,
                (user_id,),
            )
            books = await cursor.fetchall()

            if not books:
                return await ctx.send(
                    "❌ Ngài không có quyển Bí Kíp Công Pháp nào trong túi đồ cả!"
                )

            # Check xem học được skill nào
            learned_any = False
            learned_names = []
            for item_id, ten_vp, mo_ta in books:
                # Trích xuất skill_id từ item_id (VD: 201 -> Skill 1)
                skill_id = item_id - 200

                # Check nếu đã học
                c2 = await db.execute(
                    "SELECT 1 FROM player_skills WHERE user_id = ? AND skill_id = ?",
                    (user_id, skill_id),
                )
                has_learned = await c2.fetchone()

                if not has_learned:
                    # Trừ 1 cuốn
                    await db.execute(
                        "UPDATE inventory SET so_luong = so_luong - 1 WHERE user_id = ? AND item_id = ?",
                        (user_id, item_id),
                    )
                    # Insert skill
                    await db.execute(
                        "INSERT INTO player_skills (user_id, skill_id, level) VALUES (?, ?, 1)",
                        (user_id, skill_id),
                    )
                    learned_any = True

                    # Fetch skill name
                    c3 = await db.execute(
                        "SELECT name FROM skills_master WHERE skill_id = ?", (skill_id,)
                    )
                    s_r = await c3.fetchone()
                    s_name = s_r[0] if s_r else f"Công pháp #{skill_id}"
                    learned_names.append(s_name)

            await db.execute("DELETE FROM inventory WHERE so_luong <= 0")
            await db.commit()

        if learned_any:
            msg = f"✨ **ĐỘT PHÁ CẢNH GIỚI VÕ HỌC!** {ctx.author.mention} vừa lĩnh ngộ thành công:\n"
            msg += "\n".join([f"📜 **{name}**" for name in learned_names])
            await ctx.send(msg)
        else:
            await ctx.send(
                "⚠️ Đạo hữu đã lĩnh ngộ hết những bí kíp trong túi rồi, không học được gì mới."
            )

    @commands.command(name="congphap", aliases=["skills", "kynang"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def xem_cong_phap(self, ctx):
        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT ps.skill_id, sm.name, sm.element, sm.base_multiplier, sm.stamina_cost 
                FROM player_skills ps JOIN skills_master sm ON ps.skill_id = sm.skill_id 
                WHERE ps.user_id = ?
            """,
                (user_id,),
            )
            skills = await cursor.fetchall()

            c2 = await db.execute(
                """
                SELECT sm.name FROM player_equipped_skills eq JOIN skills_master sm ON eq.skill_id = sm.skill_id 
                WHERE eq.user_id = ? ORDER BY eq.slot ASC
            """,
                (user_id,),
            )
            equipped = await c2.fetchall()

        if not skills:
            return await ctx.send(
                "❌ Đạo hữu chưa lĩnh ngộ bất kỳ công pháp nào. Hãy săn boss tìm bí kíp!"
            )

        # Hiển thị
        embed = discord.Embed(
            title=f"📜 CÔNG PHÁP BẢN MỆNH CỦA {ctx.author.name}",
            color=discord.Color.blue(),
        )
        eq_txt = ", ".join([r[0] for r in equipped]) if equipped else "Chưa trang bị"
        embed.add_field(
            name="⚔️ Đang dùng",
            value=f"**{eq_txt}**\n*(Chỉ mang theo được tối đa 4 kĩ năng vào trận)*",
            inline=False,
        )

        skills_txt = ""
        for s in skills:
            s_id, s_name, s_element, s_mult, s_cost = s
            skills_txt += (
                f"🔸 **[{s_element}] {s_name}** | ST: x{s_mult} | Phí: {s_cost} TL\n"
            )

        embed.add_field(name="📚 Đã học", value=skills_txt, inline=False)

        view = SkillView(self.db_path, skills, self)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(CongPhap(bot))
