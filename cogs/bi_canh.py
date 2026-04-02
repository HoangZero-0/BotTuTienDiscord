import discord
from discord.ext import commands
import random
import asyncio
from utils import get_db


class BiCanh(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    # Tổng xác suất = 100%
    EVENTS = [
        ("treasure", 0.30),  # 30% - Kho báu: Nhận 1-7 vật phẩm
        ("big_fortune", 0.08),  # 8%  - Cơ Duyên Lớn: Nhận đồ xịn + Tu Vi + HP/TL
        ("trap_tv", 0.12),  # 12% - Bẫy trận: Mất % Tu Vi
        ("trap_cs", 0.10),  # 10% - Yêu khí: Mất % Lực Chiến
        ("trap_item", 0.08),  # 8%  - Cướp đoạt: Mất 1 món
        ("npc", 0.12),  # 12% - NPC: Nhận Linh Thạch
        ("empty", 0.20),  # 20% - Trống rỗng
    ]

    def _roll_event(self):
        roll = random.random()
        cumulative = 0
        for event_name, rate in self.EVENTS:
            cumulative += rate
            if roll < cumulative:
                return event_name
        return "empty"

    def _roll_grade(self, cg_id):
        rates = {
            5: 0.0001 + (cg_id * 0.0003),
            4: 0.001 + (cg_id * 0.002),
            3: 0.02 + (cg_id * 0.008),
            2: 0.15 + (cg_id * 0.025),
            1: 1.0,
        }
        for grade in [5, 4, 3, 2, 1]:
            if random.random() < rates[grade]:
                return grade
        return 1

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def bicanh(self, ctx):
        user_id = str(ctx.author.id)

        # 1. Cập nhật và lấy chỉ số (HP/TL)
        res = await update_player_stats(self.db_path, user_id)
        if not res:
            return await ctx.send("❌ Đạo hữu chưa tu luyện!")
        tl, sl, max_tl, max_sl = res

        async with get_db(self.db_path) as db:
            c = await db.execute(
                "SELECT canh_gioi_id, tu_vi, luc_chien_goc, linh_thach FROM players WHERE user_id = ?",
                (user_id,),
            )
            row = await c.fetchone()
            if not row:
                return
            cg_id, tu_vi, luc_chien, linh_thach = row

            if tl < 10:
                return await ctx.send("⚠️ Không đủ **10 Thể Lực** để thám hiểm!")
            lt_cost = max(10, int(linh_thach * 0.02 * (1 + cg_id * 0.1)))
            if linh_thach < lt_cost:
                return await ctx.send(
                    f"⚠️ Không đủ **{lt_cost:,} Linh Thạch** để mở cổng!"
                )

            await db.execute(
                "UPDATE players SET the_luc = max(0, the_luc - 10), linh_thach = max(0, linh_thach - ?) WHERE user_id = ?",
                (lt_cost, user_id),
            )

            msg = await ctx.send(
                f"🌌 {ctx.author.mention} Đang thám hiểm bí cảnh vô tận..."
            )
            await asyncio.sleep(1.5)

            event = self._roll_event()
            result_text = ""
            grade_emojis = {1: "⬜", 2: "🟢", 3: "🔵", 4: "🟣", 5: "🟡"}

            if event == "treasure":
                count = random.randint(1, 7)
                loot_list = []
                for _ in range(count):
                    gd = self._roll_grade(cg_id)
                    item_c = await db.execute(
                        "SELECT item_id, ten_vat_pham FROM item_master WHERE pham_cap = ? ORDER BY RANDOM() LIMIT 1",
                        (gd,),
                    )
                    item = await item_c.fetchone()
                    if item:
                        it_id, it_name = item
                        await db.execute(
                            "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                            (user_id, it_id),
                        )
                        loot_list.append(f"{grade_emojis[gd]} `{it_name}`")

                if loot_list:
                    result_text = (
                        f"🎁 **KHO BÁU GACHA!** (Đã rơi **{len(loot_list)}** món)\n"
                        + "\n".join(loot_list)
                    )
                else:
                    result_text = "🏜️ Bí cảnh trống rỗng, không tìm thấy bảo vật."

            elif event == "big_fortune":
                # Cơ duyên lớn: 1 món cực phẩm + Buff chỉ số mạnh
                gd = min(5, self._roll_grade(cg_id) + 1)
                item_c = await db.execute(
                    "SELECT item_id, ten_vat_pham FROM item_master WHERE pham_cap = ? ORDER BY RANDOM() LIMIT 1",
                    (gd,),
                )
                item = await item_c.fetchone()
                b_tv = int(tu_vi * 0.1)
                b_cs = random.randint(100, 300)
                await db.execute(
                    "UPDATE players SET tu_vi = tu_vi + ?, luc_chien_goc = luc_chien_goc + ? WHERE user_id = ?",
                    (b_tv, b_cs, user_id),
                )
                result_text = (
                    f"🌟 **CƠ DUYÊN LỚN!**\n✨ +**{b_tv:,} TV** | ⚔️ +**{b_cs:,} CP**\n"
                )
                if item:
                    await db.execute(
                        "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                        (user_id, item[0]),
                    )
                    result_text += (
                        f"🎁 Nhận pháp bảo: {grade_emojis[gd]} **[{item[1]}]**"
                    )

            elif event == "trap_tv":
                loss = int(tu_vi * 0.1)
                await db.execute(
                    "UPDATE players SET tu_vi = max(0, tu_vi - ?) WHERE user_id = ?",
                    (loss, user_id),
                )
                result_text = (
                    f"🪤 **BẪY TRẬN!** Đạo hữu bị tiêu tán **-{loss:,} Tu Vi**"
                )

            elif event == "trap_cs":
                loss = int(luc_chien * 0.05)
                await db.execute(
                    "UPDATE players SET luc_chien_goc = max(10, luc_chien_goc - ?) WHERE user_id = ?",
                    (loss, user_id),
                )
                result_text = f"👹 **YÊU KHÍ!** Kinh mạch bị tổn thương, mất **-{loss:,} Lực Chiến**"

            elif event == "npc":
                lt_gain = lt_cost * 5
                await db.execute(
                    "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                    (lt_gain, user_id),
                )
                result_text = f"🧙 **TIÊN NHÂN CHỈ LỘ!** Đạo hữu nhận được **+{lt_gain:,} Linh Thạch**"

            else:
                result_text = "🏜️ Bí cảnh hoang vu, công dã tràng..."

            await db.commit()

        await self.bot.update_quest_progress(user_id, "bicanh", ctx)
        embed = discord.Embed(
            description=f"{ctx.author.mention}\n{result_text}",
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"💎 Chi phí: 10 Thể Lực + {lt_cost:,} Linh Thạch")
        await msg.edit(content=None, embed=embed)


async def setup(bot):
    await bot.add_cog(BiCanh(bot))
