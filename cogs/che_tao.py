import discord
from discord.ext import commands
import random
import asyncio
from utils import CleanID, get_db


class CheTao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

        # ĐAN PHƯƠNG TOÀN TẬP (10 công thức)
        # req = {item_id: số lượng}, money = Linh Thạch, name = Tên đan
        self.RECIPES = {
            # Phàm Phẩm (Phẩm cấp 1)
            101: {"req": {301: 3, 303: 2}, "money": 500, "name": "Huyết Khí Đan"},
            102: {"req": {303: 3, 301: 2}, "money": 800, "name": "Tụ Khí Đan"},
            # Linh Phẩm (Phẩm cấp 2)
            103: {"req": {305: 3, 308: 2}, "money": 2_000, "name": "Trúc Cơ Đan"},
            104: {"req": {303: 5, 306: 2}, "money": 1_000, "name": "Bồi Nguyên Đan"},
            # Tiên Phẩm (Phẩm cấp 3)
            105: {"req": {309: 3, 311: 2}, "money": 8_000, "name": "Kết Đan Đan"},
            106: {"req": {310: 3, 312: 2}, "money": 15_000, "name": "Đại Hoàn Đan"},
            # Thần Phẩm (Phẩm cấp 4)
            107: {"req": {313: 3, 315: 2}, "money": 50_000, "name": "Hóa Anh Đan"},
            108: {"req": {314: 3, 316: 2}, "money": 100_000, "name": "Thiên Đạo Đan"},
            # Chí Tôn Phẩm (Phẩm cấp 5)
            109: {"req": {317: 3, 319: 2}, "money": 500_000, "name": "Phá Giới Đan"},
            110: {
                "req": {318: 3, 320: 2, 317: 1},
                "money": 1_000_000,
                "name": "Cửu Chuyển Hoàn Hồn Đan",
            },
        }

    # ==================== !luyendan <id> ====================
    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def luyendan(self, ctx, item_id: CleanID):
        """Cú pháp: !luyendan <ID>. Gõ !danphuong để xem công thức."""
        if item_id not in self.RECIPES:
            return await ctx.send(
                "❌ Đan phương này không tồn tại! Gõ `!danphuong` để xem danh sách."
            )

        user_id = str(ctx.author.id)
        recipe = self.RECIPES[item_id]

        # 1. Cập nhật và lấy chỉ số (HP/TL)
        from utils import update_player_stats

        res = await update_player_stats(self.db_path, user_id)
        if not res:
            return await ctx.send("❌ Đạo hữu chưa tu luyện!")
        tl, sl, max_tl, max_sl = res

        async with get_db(self.db_path) as db:
            # Kiểm tra người chơi
            p = await db.execute(
                "SELECT linh_thach, canh_gioi_id FROM players WHERE user_id = ?",
                (user_id,),
            )
            res_p = await p.fetchone()
            if not res_p:
                return await ctx.send(
                    "❌ Đạo hữu chưa có tên trong sổ Thiên Đạo! Hãy gõ `!tuluyen` trước."
                )

            player_lt, player_cg = res_p

            if player_lt < recipe["money"]:
                return await ctx.send(
                    f"❌ Không đủ **{recipe['money']:,}** Linh Thạch để luyện đan! (Hiện có: {player_lt:,})"
                )

            if tl < 5:
                return await ctx.send("⚠️ Không đủ **5 Thể Lực** để nhóm lửa luyện đan!")

            # Kiểm tra nguyên liệu (hiển thị tên)
            for req_id, req_qty in recipe["req"].items():
                c = await db.execute(
                    "SELECT i.so_luong, im.ten_vat_pham FROM inventory i JOIN item_master im ON i.item_id = im.item_id WHERE i.user_id = ? AND i.item_id = ?",
                    (user_id, req_id),
                )
                res = await c.fetchone()
                if not res or res[0] < req_qty:
                    # Query tên vật phẩm nếu chưa có trong inventory
                    if not res:
                        nc = await db.execute(
                            "SELECT ten_vat_pham FROM item_master WHERE item_id = ?",
                            (req_id,),
                        )
                        nr = await nc.fetchone()
                        mat_name = nr[0] if nr else f"ID: {req_id}"
                        have = 0
                    else:
                        have = res[0]
                        mat_name = res[1]
                    return await ctx.send(
                        f"❌ Thiếu nguyên liệu: **{mat_name}** (Cần {req_qty}, có {have})"
                    )

            # --- ANIMATION LUYỆN ĐAN ---
            fire_msgs = [
                "🔥 Lửa Tam Muội bùng cháy, nguyên liệu bắt đầu tan chảy...",
                "🔥 Đan lô rung chuyển, linh khí cuộn cuộn hội tụ...",
                "🔥 Hỏa diễm tam trọng! Đan dược bắt đầu ngưng tụ...",
            ]
            status_msg = await ctx.send(
                f"🧪 {ctx.author.mention} {random.choice(fire_msgs)}"
            )
            await asyncio.sleep(2.0)

            # Trừ tiền & Thể lực & Nguyên liệu (LUÔN trừ dù thành công hay thất bại)
            await db.execute(
                "UPDATE players SET linh_thach = linh_thach - ?, the_luc = max(0, the_luc - 5) WHERE user_id = ?",
                (recipe["money"], user_id),
            )
            for req_id, req_qty in recipe["req"].items():
                await db.execute(
                    "UPDATE inventory SET so_luong = so_luong - ? WHERE user_id = ? AND item_id = ?",
                    (req_qty, user_id, req_id),
                )
            await db.execute("DELETE FROM inventory WHERE so_luong <= 0")

            # --- TÍNH TỈ LỆ THÀNH CÔNG THEO CẢNH GIỚI ---
            # Lấy phẩm cấp của đan
            pc = await db.execute(
                "SELECT pham_cap FROM item_master WHERE item_id = ?", (item_id,)
            )
            pc_row = await pc.fetchone()
            dan_grade = pc_row[0] if pc_row else 1

            # Cập nhật cho 66 cảnh giới: pc1=1-12, pc2=13-24, pc3=25-36, pc4=37-48, pc5=49-66
            grade_to_min_cg = {1: 1, 2: 13, 3: 25, 4: 37, 5: 49}
            target_cg = grade_to_min_cg.get(dan_grade, 1)
            cg_diff = player_cg - target_cg  # Dương = mạnh hơn, Âm = yếu hơn

            # Base 85% + 3% mỗi cảnh giới cao hơn (max 99%) hoặc -8% mỗi cảnh giới thấp hơn (min 40%)
            success_rate = (
                0.85 + (cg_diff * 0.03) if cg_diff >= 0 else 0.85 + (cg_diff * 0.08)
            )
            success_rate = max(0.40, min(0.99, success_rate))

            success = random.random() < success_rate

            if success:
                await db.execute(
                    "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                    (user_id, item_id),
                )
                await db.commit()

                embed = discord.Embed(
                    description=(
                        f"✅ {ctx.author.mention} luyện đan thành công! (Tỉ lệ: {int(success_rate*100)}%)\n"
                        f"🧪 Nhận được: **{recipe['name']}** x1\n"
                        f"💰 Chi phí: **{recipe['money']:,}** Linh Thạch"
                    ),
                    color=discord.Color.green(),
                )
            else:
                # Thất bại: 40% nhận Phế Đan (nguyên liệu phẩm cấp 1 ngẫu nhiên)
                waste_text = ""
                if random.random() < 0.40:
                    waste_id = random.choice([301, 302, 303, 304])
                    await db.execute(
                        "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                        (user_id, waste_id),
                    )
                    wc = await db.execute(
                        "SELECT ten_vat_pham FROM item_master WHERE item_id = ?",
                        (waste_id,),
                    )
                    wr = await wc.fetchone()
                    waste_name = wr[0] if wr else "Phế liệu"
                    waste_text = f"\n📦 Vớt vát được: **{waste_name}** x1"

                await db.commit()

                embed = discord.Embed(
                    description=(
                        f"💥 {ctx.author.mention} luyện đan **THẤT BẠI**! Đan lô nổ tung!\n"
                        f"📉 Mất toàn bộ nguyên liệu + **{recipe['money']:,}** Linh Thạch{waste_text}"
                    ),
                    color=discord.Color.red(),
                )

            await status_msg.edit(content=None, embed=embed)

        # Cập nhật nhiệm vụ - Ngoài async with
        if success:
            await self.bot.update_quest_progress(user_id, "luyendan", ctx)

    # ==================== !danphuong ====================
    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def danphuong(self, ctx):
        """Hiển thị danh sách đan phương có sẵn."""
        async with get_db(self.db_path) as db:
            embed = discord.Embed(
                title="📜 ĐAN PHƯƠNG TOÀN TẬP", color=discord.Color.orange()
            )
            embed.description = (
                "Tỉ lệ thành công: **85%** | Thất bại mất nguyên liệu\n\n"
            )

            grade_names = {
                1: "⬜ Phàm",
                2: "🟢 Linh",
                3: "🔵 Tiên",
                4: "🟣 Thần",
                5: "🟡 Chí Tôn",
            }
            # Group by pham_cap
            groups = {}
            for dan_id, r in self.RECIPES.items():
                # Determine grade from item_master
                c = await db.execute(
                    "SELECT pham_cap FROM item_master WHERE item_id = ?", (dan_id,)
                )
                row = await c.fetchone()
                grade = row[0] if row else 1
                if grade not in groups:
                    groups[grade] = []

                # Build material list with names
                mats = []
                for mat_id, mat_qty in r["req"].items():
                    mc = await db.execute(
                        "SELECT ten_vat_pham FROM item_master WHERE item_id = ?",
                        (mat_id,),
                    )
                    mr = await mc.fetchone()
                    mat_name = mr[0] if mr else f"#{mat_id}"
                    mats.append(f"{mat_name} x{mat_qty}")

                groups[grade].append(
                    f"`{dan_id}` **{r['name']}** — {' + '.join(mats)} — 💰{r['money']:,}"
                )

            for grade in sorted(groups.keys()):
                embed.add_field(
                    name=grade_names.get(grade, f"Cấp {grade}"),
                    value="\n".join(groups[grade]),
                    inline=False,
                )

            embed.set_footer(text="Dùng: !luyendan <ID> để bắt đầu luyện đan")
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CheTao(bot))
