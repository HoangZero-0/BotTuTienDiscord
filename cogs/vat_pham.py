import discord
from discord.ext import commands
import asyncio
from utils import CleanID, get_db


class VatPham(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"
        self.MAX_EQUIP_SLOTS = 5

    # ==================== !use <id> ====================
    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def use(self, ctx, item_id: CleanID):
        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT i.so_luong, im.ten_vat_pham, im.loai_vat_pham, im.chi_so_buff, i.trang_thai
                FROM inventory i JOIN item_master im ON i.item_id = im.item_id 
                WHERE i.user_id = ? AND i.item_id = ?""",
                (user_id, item_id),
            )
            item = await cursor.fetchone()

            if not item or item[0] <= 0:
                return await ctx.send("❌ Đạo hữu không sở hữu vật phẩm này!")

            qty, name, category, buff, trang_thai = item

            # ======= ĐAN DƯỢC =======
            if category == "dan_duoc":
                status_msg = await ctx.send(
                    f"💊 {ctx.author.mention} đang cắn viên **{name}**..."
                )
                await asyncio.sleep(1.0)

                embed = discord.Embed(color=discord.Color.green())

                if item_id == 101:
                    # Huyết Khí Đan: Hồi Thể Lực
                    await db.execute(
                        "UPDATE players SET the_luc = min(100, the_luc + ?) WHERE user_id = ?",
                        (buff, user_id),
                    )
                    embed.description = f"🍵 {ctx.author.mention} dùng **{name}**, hồi phục **+{buff} Thể Lực**!"
                    await self._consume_item(db, user_id, item_id, qty)

                elif item_id in [102, 104, 106, 108]:
                    # Nhóm tăng Tu Vi: Chặn trần tv_max
                    c = await db.execute(
                        "SELECT p.tu_vi, r.tu_vi_can_thiet FROM players p JOIN realms_master r ON p.canh_gioi_id = r.canh_gioi_id WHERE p.user_id = ?",
                        (user_id,),
                    )
                    tv_row = await c.fetchone()
                    current_tv, tv_max = tv_row
                    actual_gain = min(buff, tv_max - current_tv)
                    actual_gain = max(0, actual_gain)

                    await db.execute(
                        "UPDATE players SET tu_vi = min(?, tu_vi + ?) WHERE user_id = ?",
                        (tv_max, buff, user_id),
                    )
                    embed.description = f"💊 {ctx.author.mention} cắn **{name}**, tăng **+{actual_gain} Tu Vi**!"
                    if current_tv + buff >= tv_max:
                        embed.description += (
                            "\n🌟 **BÌNH CẢNH!** Linh khí đã đầy, hãy gõ `!dotpha`!"
                        )
                    await self._consume_item(db, user_id, item_id, qty)

                elif item_id in [103, 105, 107, 109]:
                    # V3: Đan hỗ trợ Đột Phá — Thực sự kích hoạt Đột Phá!
                    c = await db.execute(
                        "SELECT p.tu_vi, p.canh_gioi_id, r.tu_vi_can_thiet FROM players p JOIN realms_master r ON p.canh_gioi_id = r.canh_gioi_id WHERE p.user_id = ?",
                        (user_id,),
                    )
                    tv_row = await c.fetchone()
                    current_tv, cg_id, tv_max = tv_row

                    if current_tv >= tv_max:
                        # Đủ Tu Vi → Cưỡng chế Đột Phá!
                        await db.execute(
                            "UPDATE players SET canh_gioi_id = canh_gioi_id + 1, tu_vi = 0, luc_chien_goc = CAST(luc_chien_goc * 1.1 AS INTEGER) WHERE user_id = ?",
                            (user_id,),
                        )
                        await self._consume_item(db, user_id, item_id, qty)

                        # Lấy tên cảnh giới mới
                        c2 = await db.execute(
                            "SELECT ten_canh_gioi FROM realms_master WHERE canh_gioi_id = ?",
                            (cg_id + 1,),
                        )
                        new_realm = await c2.fetchone()
                        new_name = new_realm[0] if new_realm else "???"

                        embed.color = discord.Color.gold()
                        embed.description = (
                            f"🌟 **ĐỘT PHÁ THẦN TỐC!** {ctx.author.mention} dùng **{name}** cưỡng chế đột phá!\n"
                            f"🎊 Thăng cấp lên **{new_name}**! Lực chiến gốc +10%!"
                        )
                    else:
                        # Chưa đủ Tu Vi → Chỉ hiển thị thông tin
                        embed.color = discord.Color.orange()
                        embed.description = (
                            f"ℹ️ **{name}** cần Tu Vi đạt Bình Cảnh ({current_tv}/{tv_max}) mới có thể kích hoạt.\n"
                            f"💡 Hãy tu luyện cho đầy rồi dùng đan này để cưỡng chế đột phá!"
                        )

                elif item_id == 110:
                    # Cửu Chuyển Hoàn Hồn Đan: Chỉ thông báo, KHÔNG trừ số lượng
                    embed.color = discord.Color.purple()
                    embed.description = (
                        f"🛡️ **{name}** sẽ tự động bảo vệ ngài nếu `!dotpha` thất bại.\n"
                        f"Đừng lo lắng, viên đan này nằm yên trong túi chờ thời cơ!"
                    )
                else:
                    embed.description = (
                        f"❓ Đan dược **{name}** chưa có bí tịch ghi chép."
                    )
                    await self._consume_item(db, user_id, item_id, qty)

                await db.commit()
                await status_msg.edit(content=None, embed=embed)

            # ======= PHÁP BẢO =======
            elif category == "phap_bao":
                if trang_thai == "dang_trang_bi":
                    return await ctx.send(f"⚔️ **{name}** đã đang được trang bị rồi!")

                # Đếm số pháp bảo đang mặc
                c_count = await db.execute(
                    "SELECT COUNT(*) FROM inventory WHERE user_id = ? AND trang_thai = 'dang_trang_bi' AND item_id IN (SELECT item_id FROM item_master WHERE loai_vat_pham = 'phap_bao')",
                    (user_id,),
                )
                count_row = await c_count.fetchone()
                equipped_count = count_row[0] if count_row else 0

                if equipped_count >= self.MAX_EQUIP_SLOTS:
                    return await ctx.send(
                        f"❌ Đạo hữu đã trang bị tối đa **{self.MAX_EQUIP_SLOTS}** pháp bảo! Hãy gỡ bớt bằng `!thao <id>`."
                    )

                await db.execute(
                    "UPDATE inventory SET trang_thai = 'dang_trang_bi' WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id),
                )
                await db.commit()

                embed = discord.Embed(
                    description=f"⚔️ {ctx.author.mention} trang bị **{name}**! Lực chiến +**{buff:,}**\n📊 Slot: {equipped_count + 1}/{self.MAX_EQUIP_SLOTS}",
                    color=discord.Color.green(),
                )
                await ctx.send(embed=embed)

            # ======= NGUYÊN LIỆU =======
            else:
                await ctx.send(
                    "📦 Đây là nguyên liệu, không thể sử dụng trực tiếp. Dùng để chế tạo (`!luyendan`)."
                )

    # ==================== !thao <id> ====================
    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def thao(self, ctx, item_id: CleanID):
        """Gỡ pháp bảo đang trang bị."""
        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT im.ten_vat_pham, im.chi_so_buff, i.trang_thai
                FROM inventory i JOIN item_master im ON i.item_id = im.item_id
                WHERE i.user_id = ? AND i.item_id = ? AND im.loai_vat_pham = 'phap_bao'""",
                (user_id, item_id),
            )
            row = await cursor.fetchone()

            if not row:
                return await ctx.send("❌ Không tìm thấy pháp bảo này trong túi đồ!")

            name, buff, status = row
            if status != "dang_trang_bi":
                return await ctx.send(
                    f"ℹ️ **{name}** đang nằm trong túi, không cần tháo."
                )

            await db.execute(
                "UPDATE inventory SET trang_thai = 'trong_tui' WHERE user_id = ? AND item_id = ?",
                (user_id, item_id),
            )
            await db.commit()

            embed = discord.Embed(
                description=f"🔓 {ctx.author.mention} đã gỡ **{name}** ra khỏi người. Lực chiến giảm **-{buff:,}**.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)

    # ==================== !tuido ====================
    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def tuido(self, ctx):
        """Hiển thị danh sách vật phẩm trong túi đồ."""
        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT im.item_id, im.ten_vat_pham, im.loai_vat_pham, im.chi_so_buff, i.so_luong, i.trang_thai
                FROM inventory i JOIN item_master im ON i.item_id = im.item_id
                WHERE i.user_id = ? AND i.so_luong > 0
                ORDER BY im.loai_vat_pham, im.pham_cap DESC""",
                (user_id,),
            )
            items = await cursor.fetchall()

        if not items:
            return await ctx.send(
                "🎒 Túi đồ trống trơn, đạo hữu chưa sở hữu vật phẩm nào!"
            )

        embed = discord.Embed(
            title=f"🎒 Túi Đồ — {ctx.author.name}",
            color=discord.Color.dark_teal(),
        )

        categories = {
            "phap_bao": ("⚔️ Pháp Bảo", []),
            "dan_duoc": ("💊 Đan Dược", []),
            "nguyen_lieu": ("🧱 Nguyên Liệu", []),
        }

        for i_id, name, cat, buff, qty, status in items:
            equip_tag = " 🟢" if status == "dang_trang_bi" else ""
            buff_text = f" (+{buff:,})" if buff and buff > 0 else ""
            line = f"`{i_id}` **{name}**{buff_text} x{qty}{equip_tag}"
            if cat in categories:
                categories[cat][1].append(line)
            else:
                categories.setdefault("other", ("📦 Khác", []))
                categories["other"][1].append(line)

        for cat_key, (cat_name, lines) in categories.items():
            if lines:
                embed.add_field(name=cat_name, value="\n".join(lines), inline=False)

        embed.set_footer(
            text="🟢 = Đang trang bị | Dùng !use <ID> để sử dụng | !thao <ID> để gỡ pháp bảo"
        )
        await ctx.send(embed=embed)

    # ==================== Helper ====================
    async def _consume_item(self, db, user_id, item_id, current_qty):
        """Trừ 1 số lượng vật phẩm hoặc xóa nếu hết."""
        if current_qty > 1:
            await db.execute(
                "UPDATE inventory SET so_luong = so_luong - 1 WHERE user_id = ? AND item_id = ?",
                (user_id, item_id),
            )
        else:
            await db.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id),
            )


async def setup(bot):
    await bot.add_cog(VatPham(bot))
