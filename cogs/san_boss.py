import discord
from discord.ext import commands
from utils import get_db
import asyncio
import random
import json


class SanBoss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    def _weighted_boss_select(self, bosses, player_cg):
        """Chọn boss theo trọng số: Cùng cảnh giới = cao nhất, xa hơn = thấp dần."""
        weighted = []
        for b in bosses:
            b_cg = b[2]  # canh_gioi_yeu_cau
            diff = b_cg - player_cg
            if diff == 0:
                weight = 50  # Cùng cảnh giới: trọng số cao nhất
            elif diff > 0:
                # Boss cao hơn: tỉ lệ giảm mạnh theo khoảng cách
                weight = max(1, 30 - (diff * 10))
            else:
                # Boss thấp hơn: tỉ lệ tăng dần khi gần, giảm khi xa
                weight = max(1, 25 - (abs(diff) * 8))
            weighted.append((b, weight))

        total = sum(w for _, w in weighted)
        roll = random.uniform(0, total)
        cumulative = 0
        for boss, w in weighted:
            cumulative += w
            if roll <= cumulative:
                return boss
        return weighted[-1][0]

    def _roll_buffs(self):
        """Roll ngẫu nhiên buff cho 1 bên (người chơi hoặc boss)."""
        buffs = {}
        # Mỗi buff có 20% cơ hội xuất hiện
        if random.random() < 0.20:
            buffs["critical"] = random.uniform(1.5, 2.0)  # x1.5 ~ x2 sát thương
        if random.random() < 0.20:
            buffs["dodge"] = random.uniform(0.3, 0.6)  # 30-60% né 1 đòn
        if random.random() < 0.15:
            buffs["counter"] = random.uniform(
                0.2, 0.4
            )  # Phản đòn 20-40% sát thương nhận
        if random.random() < 0.15:
            buffs["absorb"] = random.uniform(
                0.1, 0.25
            )  # Hấp thụ 10-25% sát thương thành HP
        if random.random() < 0.10:
            buffs["accuracy"] = random.uniform(
                1.1, 1.3
            )  # Tăng 10-30% sát thương chuẩn xác
        return buffs

    def _buff_text(self, buffs, is_player=True):
        """Hiển thị buff đã roll."""
        prefix = "🟢" if is_player else "🔴"
        texts = []
        names = {
            "critical": "Chí Mạng",
            "dodge": "Né Tránh",
            "counter": "Phản Đòn",
            "absorb": "Hấp Thụ",
            "accuracy": "Chính Xác",
        }
        for k, v in buffs.items():
            if k == "critical":
                texts.append(f"{prefix} {names[k]} x{v:.1f}")
            elif k == "dodge":
                texts.append(f"{prefix} {names[k]} {int(v*100)}%")
            elif k == "counter":
                texts.append(f"{prefix} {names[k]} {int(v*100)}%")
            elif k == "absorb":
                texts.append(f"{prefix} {names[k]} {int(v*100)}%")
            elif k == "accuracy":
                texts.append(f"{prefix} {names[k]} +{int((v-1)*100)}%")
        return " | ".join(texts) if texts else f"{prefix} Không có buff"

    def _roll_loot(self, loot_table_json, player_cg, boss_cg):
        """Parse loot_table JSON và roll đồ dựa theo realm gap."""
        try:
            loot_table = (
                json.loads(loot_table_json) if isinstance(loot_table_json, str) else {}
            )
        except (json.JSONDecodeError, TypeError):
            return None

        if not loot_table:
            return None

        cg_diff = boss_cg - player_cg  # Âm = boss yếu hơn, Dương = boss mạnh hơn

        for item_id_str, base_rate in loot_table.items():
            # Điều chỉnh tỉ lệ theo chênh lệch cảnh giới
            if cg_diff <= 0:
                # Boss cùng/thấp hơn: tỉ lệ gốc hoặc cao hơn
                adjusted_rate = min(100, base_rate + abs(cg_diff) * 3)
            else:
                # Boss cao hơn: tỉ lệ giảm dần theo khoảng cách
                adjusted_rate = max(1, base_rate - cg_diff * 5)

            if random.randint(1, 100) <= adjusted_rate:
                return int(item_id_str)

        return None

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def sanboss(self, ctx):
        user_id = str(ctx.author.id)
        win = False

        # 1. Cập nhật và lấy chỉ số (HP/TL)
        res = await update_player_stats(self.db_path, user_id)
        if not res:
            return await ctx.send("❌ Đạo hữu chưa tu luyện!")
        tl, sl, max_tl, max_sl = res

        async with get_db(self.db_path) as db:
            # Lấy thông tin người chơi
            p = await db.execute(
                """
                SELECT p.canh_gioi_id, p.luc_chien_goc + COALESCE(SUM(im.chi_so_buff), 0) as cp
                FROM players p
                LEFT JOIN inventory i ON p.user_id = i.user_id AND i.trang_thai = 'dang_trang_bi'
                LEFT JOIN item_master im ON i.item_id = im.item_id
                WHERE p.user_id = ?
                """,
                (user_id,),
            )
            player_row = await p.fetchone()
            if not player_row:
                return

            cg_id, cp = player_row

            if tl < 3:
                return await ctx.send(
                    "⚠️ Thể lực quá yếu, ngài cần ít nhất **3 Thể Lực** để mạo hiểm!"
                )

            # V3: Lấy tất cả boss trong khoảng cảnh giới hợp lý (±3 cảnh)
            min_cg = max(1, cg_id - 3)
            max_cg = min(66, cg_id + 3)
            cursor = await db.execute(
                "SELECT * FROM boss_monster_master WHERE canh_gioi_yeu_cau BETWEEN ? AND ?",
                (min_cg, max_cg),
            )
            all_bosses = await cursor.fetchall()

            if not all_bosses:
                await ctx.send(
                    "🏔️ Vùng đất này yên bình lạ thường, không thấy yêu thú nào."
                )
                return

            boss = self._weighted_boss_select(all_bosses, cg_id)
            b_id, b_ten, b_req, b_min_cp, b_max_cp, b_loot = boss
            boss_cp = random.randint(b_min_cp, b_max_cp)

            # --- ROLL BUFF CHO CẢ HAI BÊN ---
            p_buffs = self._roll_buffs()
            b_buffs = self._roll_buffs()

            intro = f"⚔️ **SỰ KIỆN**: {ctx.author.mention} chạm trán **[{b_ten}]** (LC: {boss_cp:,})!\n"
            intro += f"👤 Buff: {self._buff_text(p_buffs, True)}\n"
            intro += f"👹 Buff: {self._buff_text(b_buffs, False)}"
            await ctx.send(intro)
            await asyncio.sleep(2)

            # --- LOGIC CHIẾN ĐẤU ĐA HIỆP V3 ---
            boss_hp = boss_cp
            player_hp = cp
            battle_log = f"⚔️ **{ctx.author.name}** vs **[{b_ten}]**\n\n"

            msg = await ctx.send(battle_log + "🔄 *Đang khởi động trận chiến...*")
            await asyncio.sleep(1.5)

            for round_num in range(1, 4):
                # Sát thương cơ bản
                p_dmg = int(cp * random.uniform(0.20, 0.40))
                # Boss damage: avg ~23.3% per round -> ~70% total over 3 rounds
                b_dmg = int(boss_cp * random.uniform(0.13, 0.34))

                round_notes_p = ""
                round_notes_b = ""

                # --- ÁP DỤNG BUFF NGƯỜI CHƠI ---
                if "accuracy" in p_buffs:
                    p_dmg = int(p_dmg * p_buffs["accuracy"])
                    round_notes_p += "🎯"

                if "critical" in p_buffs and random.random() < 0.30:
                    p_dmg = int(p_dmg * p_buffs["critical"])
                    round_notes_p += "💥CHÍ MẠNG!"

                if "dodge" in p_buffs and random.random() < p_buffs["dodge"]:
                    b_dmg = 0
                    round_notes_p += "💨NÉ!"

                if "counter" in p_buffs and b_dmg > 0:
                    counter_dmg = int(b_dmg * p_buffs["counter"])
                    boss_hp -= counter_dmg
                    round_notes_p += f"↩️+{counter_dmg:,}"

                if "absorb" in p_buffs and p_dmg > 0:
                    heal = int(p_dmg * p_buffs["absorb"])
                    player_hp += heal
                    round_notes_p += f"💚+{heal:,}"

                # --- ÁP DỤNG BUFF BOSS ---
                if "accuracy" in b_buffs:
                    b_dmg = int(b_dmg * b_buffs["accuracy"])
                    round_notes_b += "🎯"

                if "critical" in b_buffs and random.random() < 0.30:
                    b_dmg = int(b_dmg * b_buffs["critical"])
                    round_notes_b += "💥"

                if "dodge" in b_buffs and random.random() < b_buffs["dodge"]:
                    p_dmg = 0
                    round_notes_b += "💨NÉ!"

                if "counter" in b_buffs and p_dmg > 0:
                    counter_dmg = int(p_dmg * b_buffs["counter"])
                    player_hp -= counter_dmg
                    round_notes_b += f"↩️"

                if "absorb" in b_buffs and b_dmg > 0:
                    heal = int(b_dmg * b_buffs["absorb"])
                    boss_hp += heal
                    round_notes_b += f"💚"

                boss_hp -= p_dmg
                player_hp -= b_dmg

                battle_log += f"🔹 **Hiệp {round_num}**: "
                battle_log += f"Ngài chém **-{p_dmg:,}** {round_notes_p} | Boss tát **-{b_dmg:,}** {round_notes_b}\n"
                await msg.edit(content=battle_log)
                await asyncio.sleep(1)

            if player_hp >= boss_hp:
                win = True
                gold = int(boss_cp / 5)
                received = ""

                # V3: Parse loot_table của boss
                loot_item_id = self._roll_loot(b_loot, cg_id, b_req)
                if loot_item_id:
                    c = await db.execute(
                        "SELECT ten_vat_pham FROM item_master WHERE item_id = ?",
                        (loot_item_id,),
                    )
                    res = await c.fetchone()
                    item_name = res[0] if res else "Vật phẩm bí ẩn"

                    await db.execute(
                        "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                        (user_id, loot_item_id),
                    )
                    received = f"\n🎁 Nhận thêm: **{item_name}**"

                await db.execute(
                    "UPDATE players SET linh_thach = linh_thach + ?, the_luc = max(0, the_luc - 3) WHERE user_id = ?",
                    (gold, user_id),
                )
                await db.commit()
                battle_log += f"\n🏆 **THẮNG!** {b_ten} đã trở về cát bụi!\n💰 Nhận: **{gold:,} Linh Thạch**\n🔋 Tiêu hao: **-3 Thể Lực**{received}"
            else:
                win = False
                # V3: Trừ Linh Thạch + Trừ % Thể Lực + 10% rơi đồ
                lost_gold = int(boss_cp / 10)
                hp_penalty_pct = random.uniform(0.10, 0.50)
                hp_lost = int(the_luc * hp_penalty_pct)

                await db.execute(
                    "UPDATE players SET linh_thach = max(0, linh_thach - ?), the_luc = max(0, the_luc - ?) WHERE user_id = ?",
                    (lost_gold, hp_lost, user_id),
                )

                penalty_text = f"\n💀 **THẤT BẠI!** Ngài bị đánh trọng thương!\n"
                penalty_text += f"💰 Mất: **{lost_gold:,} Linh Thạch**\n"
                penalty_text += f"❤️‍🩹 Tổn thương: **-{hp_lost} Thể Lực** ({int(hp_penalty_pct*100)}%) — Sẽ hồi phục từ từ.\n"

                # 10% rơi đồ ngẫu nhiên khi thua
                if random.random() < 0.10:
                    # Kiểm tra inventory có đồ không
                    inv_c = await db.execute(
                        "SELECT item_id, so_luong FROM inventory WHERE user_id = ? AND so_luong > 0 AND trang_thai != 'dang_trang_bi' ORDER BY RANDOM() LIMIT 1",
                        (user_id,),
                    )
                    dropped = await inv_c.fetchone()
                    if dropped:
                        drop_id, drop_qty = dropped
                        name_c = await db.execute(
                            "SELECT ten_vat_pham FROM item_master WHERE item_id = ?",
                            (drop_id,),
                        )
                        name_r = await name_c.fetchone()
                        drop_name = name_r[0] if name_r else "Vật phẩm"

                        await db.execute(
                            "UPDATE inventory SET so_luong = so_luong - 1 WHERE user_id = ? AND item_id = ?",
                            (user_id, drop_id),
                        )
                        await db.execute("DELETE FROM inventory WHERE so_luong <= 0")
                        penalty_text += f"📦 Rơi mất: **{drop_name}** x1"

                await db.commit()
                battle_log += penalty_text

            await msg.edit(content=battle_log)

        # Cập nhật nhiệm vụ hàng ngày - Ngoài async with
        if win:
            await self.bot.update_quest_progress(user_id, "sanboss", ctx)


async def setup(bot):
    await bot.add_cog(SanBoss(bot))
