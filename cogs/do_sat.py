import discord
from discord.ext import commands
import random
import asyncio
from utils import get_db, update_player_stats


# Cấu hình cân bằng
ESCAPE_BASE = 0.05
MAX_ROUNDS = 15  # Chặn vòng lặp vô tận


def get_hp_bar(current, mx):
    perc = min(100, (current / max(1, mx)) * 100)
    filled = int(perc / 10)
    return "🟥" * filled + "⬜" * (10 - filled)


class DoSat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"
        self.active_fights = set()  # Tránh 2 lệnh dosat cùng lúc

    @commands.command(name="dosat")
    @commands.cooldown(1, 600, commands.BucketType.user)  # 10 phút/lần
    async def dosat(self, ctx, target: discord.Member = None):
        if not target:
            return await ctx.send("❌ Đạo hữu muốn sát hại ai? Vui lòng tag @Người_đó!")
        if target == ctx.author:
            return await ctx.send("❌ Tự sát bị cấm trong giới tu tiên!")
        if target.bot:
            return await ctx.send("❌ Không thể đồ sát thực thể thiên đạo (Bot)!")

        attacker_id = str(ctx.author.id)
        target_id = str(target.id)

        fight_key = frozenset([attacker_id, target_id])
        if fight_key in self.active_fights:
            return await ctx.send("⚔️ Trận chiến này đang diễn ra, hãy chờ kết quả!")
        self.active_fights.add(fight_key)

        try:
            # 1. Kiểm tra trạng thái Kẻ Tấn Công
            res_a = await update_player_stats(self.db_path, attacker_id)
            if not res_a:
                return await ctx.send("❌ Đạo hữu chưa bước vào con đường tu tiên!")
            a_tl, a_sl, a_max_tl, a_max_sl = res_a

            if a_tl < 10:
                return await ctx.send("⚠️ Không đủ **10 Thể Lực** để đồ sát!")
            if a_sl <= 0:
                return await ctx.send(
                    "💀 Ngài đang trọng thương, hãy an phận dưỡng thương!"
                )

            # 2. Kiểm tra trạng thái Nạn Nhân
            res_t = await update_player_stats(self.db_path, target_id)
            if not res_t:
                return await ctx.send("❌ Kẻ đó chỉ là phàm nhân, tha cho hắn đi!")
            t_tl, t_sl, t_max_tl, t_max_sl = res_t

            if t_sl <= 0:
                return await ctx.send("💀 Kẻ đó đã trọng thương gục ngã rồi!")

            async with get_db(self.db_path) as db:
                # 3. Lấy thông tin chi tiết & Kỹ năng (V4 GOLD)
                ca = await db.execute(
                    """
                    SELECT p.tu_vi, p.linh_thach, p.tong_mon_id,
                           p.luc_chien_goc + COALESCE(SUM(im.chi_so_buff), 0)
                    FROM players p
                    LEFT JOIN inventory i ON p.user_id = i.user_id AND i.trang_thai = 'dang_trang_bi'
                    LEFT JOIN item_master im ON i.item_id = im.item_id
                    WHERE p.user_id = ?
                    """,
                    (attacker_id,),
                )
                ra = await ca.fetchone()

                ct = await db.execute(
                    """
                    SELECT p.tu_vi, p.linh_thach, p.tong_mon_id,
                           p.luc_chien_goc + COALESCE(SUM(im.chi_so_buff), 0)
                    FROM players p
                    LEFT JOIN inventory i ON p.user_id = i.user_id AND i.trang_thai = 'dang_trang_bi'
                    LEFT JOIN item_master im ON i.item_id = im.item_id
                    WHERE p.user_id = ?
                    """,
                    (target_id,),
                )
                rt = await ct.fetchone()

                if not ra or not rt:
                    return await ctx.send("❌ Có lỗi khi tra cứu sổ Sinh Tử!")

                a_tv, a_lt, a_tm_id, a_cp = ra
                t_tv, t_lt, t_tm_id, t_cp = rt

                # Lấy kỹ năng trang bị
                async def get_skills(uid):
                    c = await db.execute(
                        "SELECT sm.name, sm.base_multiplier FROM player_equipped_skills eq JOIN skills_master sm ON eq.skill_id = sm.skill_id WHERE eq.user_id = ?",
                        (uid,),
                    )
                    return await c.fetchall()

                a_skills = await get_skills(attacker_id)
                t_skills = await get_skills(target_id)

                if a_tm_id and t_tm_id and a_tm_id == t_tm_id:
                    return await ctx.send(
                        "❌ Pháp tắc: **Không thể tàn sát đồng môn!**"
                    )

                await db.execute(
                    "UPDATE players SET the_luc = max(0, the_luc - 10) WHERE user_id = ?",
                    (attacker_id,),
                )
                await db.commit()

            # ===== 4. CHIẾN ĐẤU (TURN-BASED WITH SKILLS) =====
            cur_a_sl, cur_t_sl = a_sl, t_sl
            round_logs = []
            winner, escaped = None, None
            ratio = a_cp / max(1, t_cp)

            for rnd in range(1, MAX_ROUNDS + 1):
                # Kẻ tấn công ra chiêu
                a_skill_name = "Đòn đánh thường"
                a_skill_mult = 1.0
                if a_skills and random.random() < 0.7:  # 70% dùng kỹ năng
                    s = random.choice(a_skills)
                    a_skill_name, a_skill_mult = s

                dmg_at = int((a_cp * 0.10) * a_skill_mult * random.uniform(0.8, 1.2))
                dmg_at = max(1, dmg_at)
                cur_t_sl -= dmg_at

                dmg_ta = 0
                t_skill_name = "Phản kích"
                if cur_t_sl > 0:
                    # Nạn nhân phản công
                    t_skill_mult = 1.0
                    if t_skills and random.random() < 0.6:  # 60% phản công bằng kỹ năng
                        s = random.choice(t_skills)
                        t_skill_name, t_skill_mult = s

                    dmg_ta = int(
                        (t_cp * 0.10) * t_skill_mult * random.uniform(0.8, 1.2)
                    )
                    dmg_ta = max(1, dmg_ta)
                    cur_a_sl -= dmg_ta

                bar_a = get_hp_bar(max(0, cur_a_sl), a_max_sl)
                bar_t = get_hp_bar(max(0, cur_t_sl), t_max_sl)

                round_logs.append(
                    f"**Hiệp {rnd}:**\n"
                    f"⚔️ **{a_skill_name}**: -{dmg_at:,}\n"
                    f"🛡️ **{t_skill_name}**: -{dmg_ta:,}\n"
                    f"🔴 {bar_a} `{max(0,cur_a_sl):,}/{a_max_sl:,}`\n"
                    f"🔵 {bar_t} `{max(0,cur_t_sl):,}/{t_max_sl:,}`"
                )

                if cur_a_sl <= 0 or cur_t_sl <= 0:
                    if cur_a_sl <= 0 and cur_t_sl <= 0:
                        winner = "draw"
                    elif cur_a_sl <= 0:
                        winner = "target"
                    else:
                        winner = "attacker"
                    break

                # Xác suất bỏ trốn: Kẻ yếu hơn khó thoát hơn
                # ratio = a_cp / t_cp. Nếu a mạnh hơn (ratio > 1), target_escape giảm.
                attacker_escape_p = ESCAPE_BASE * ratio
                target_escape_p = ESCAPE_BASE / ratio

                if random.random() < attacker_escape_p:
                    escaped = "attacker"
                    break
                if random.random() < target_escape_p:
                    escaped = "target"
                    break

            # ===== 5. KẾT QUẢ & LOOT =====
            async with get_db(self.db_path) as db:
                embed = discord.Embed(
                    title="⚔️ HUYẾT ÁN TU CHÂN", color=discord.Color.dark_red()
                )
                shown_logs = round_logs[-3:] if len(round_logs) > 3 else round_logs
                embed.description = "\n\n".join(shown_logs) + "\n\n──────────────\n"

                async def steal_item(winner_id, loser_id):
                    res = await db.execute(
                        "SELECT item_id FROM inventory WHERE user_id = ? AND so_luong > 0 AND trang_thai != 'dang_trang_bi' ORDER BY RANDOM() LIMIT 1",
                        (loser_id,),
                    )
                    item = await res.fetchone()
                    if item:
                        it_id = item[0]
                        await db.execute(
                            "UPDATE inventory SET so_luong = so_luong - 1 WHERE user_id = ? AND item_id = ?",
                            (loser_id, it_id),
                        )
                        await db.execute(
                            "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                            (winner_id, it_id),
                        )
                        await db.execute("DELETE FROM inventory WHERE so_luong <= 0")
                        n_res = await db.execute(
                            "SELECT ten_vat_pham FROM item_master WHERE item_id = ?",
                            (it_id,),
                        )
                        n_row = await n_res.fetchone()
                        return n_row[0] if n_row else "Vật phẩm lạ"
                    return None

                if winner == "attacker":
                    s_tv, s_lt = int(t_tv * 0.10), int(t_lt * 0.10)
                    s_item = await steal_item(attacker_id, target_id)
                    await db.execute(
                        "UPDATE players SET sinh_luc = 0, tu_vi = max(0,tu_vi-?), linh_thach = max(0,linh_thach-?) WHERE user_id = ?",
                        (s_tv, s_lt, target_id),
                    )
                    await db.execute(
                        "UPDATE players SET sinh_luc = ?, tu_vi = tu_vi+?, linh_thach = linh_thach+? WHERE user_id = ?",
                        (max(1, cur_a_sl), s_tv, s_lt, attacker_id),
                    )
                    embed.description += f"☠️ **{target.mention}** ngã xuống!\n💰 **{ctx.author.mention}** đoạt được:\n🔹 **{s_tv:,} TV** | **{s_lt:,} LT**\n"
                    if s_item:
                        embed.description += f"📦 Vật phẩm cướp được: **[{s_item}]**"
                    embed.color = discord.Color.dark_red()

                elif winner == "target":
                    s_tv, s_lt = int(a_tv * 0.05), int(a_lt * 0.05)
                    s_item = await steal_item(target_id, attacker_id)
                    await db.execute(
                        "UPDATE players SET sinh_luc = 0, tu_vi = max(0,tu_vi-?), linh_thach = max(0,linh_thach-?) WHERE user_id = ?",
                        (s_tv, s_lt, attacker_id),
                    )
                    await db.execute(
                        "UPDATE players SET sinh_luc = ?, tu_vi = tu_vi+?, linh_thach = linh_thach+? WHERE user_id = ?",
                        (max(1, cur_t_sl), s_tv, s_lt, target_id),
                    )
                    embed.description += f"💀 **{ctx.author.mention}** bị phản sát!\n🛡️ **{target.mention}** thu giữ:\n🔹 **{s_tv:,} TV** | **{s_lt:,} LT**\n"
                    if s_item:
                        embed.description += f"📦 Vật phẩm thu giữ: **[{s_item}]**"
                    embed.color = discord.Color.blue()

                elif winner == "draw":
                    await db.execute(
                        "UPDATE players SET sinh_luc = 0 WHERE user_id IN (?,?)",
                        (attacker_id, target_id),
                    )
                    embed.description += (
                        "💥 **Đồng quy vu tận!** Cả hai cùng lâm vào trọng thương."
                    )

                elif escaped:
                    await db.execute(
                        "UPDATE players SET sinh_luc = ? WHERE user_id = ?",
                        (max(1, cur_a_sl), attacker_id),
                    )
                    await db.execute(
                        "UPDATE players SET sinh_luc = ? WHERE user_id = ?",
                        (max(1, cur_t_sl), target_id),
                    )
                    flee_name = (
                        ctx.author.mention if escaped == "attacker" else target.mention
                    )
                    embed.description += (
                        f"💨 {flee_name} đã vận pháp thân đào thoát khỏi trận chiến!"
                    )
                    embed.color = discord.Color.orange()

                else:  # Timeout
                    await db.execute(
                        "UPDATE players SET sinh_luc = ? WHERE user_id = ?",
                        (max(1, cur_a_sl), attacker_id),
                    )
                    await db.execute(
                        "UPDATE players SET sinh_luc = ? WHERE user_id = ?",
                        (max(1, cur_t_sl), target_id),
                    )
                    embed.description += (
                        "⏱️ Trận chiến kéo dài không dứt, hai bên đều kiệt sức lui quân."
                    )

                await db.commit()

            embed.set_footer(text=f"🏆 Lượt: {len(round_logs)}/{MAX_ROUNDS}")
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"🆘 Lỗi tàn sát: `{e}`")
        finally:
            self.active_fights.discard(fight_key)


async def setup(bot):
    await bot.add_cog(DoSat(bot))
