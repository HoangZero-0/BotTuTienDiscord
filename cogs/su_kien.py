import discord
from discord.ext import commands, tasks
import aiosqlite
import random
import asyncio
from datetime import datetime
from utils import get_db


class SuKien(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"
        self.world_boss = {
            "name": None,
            "hp": 0,
            "max_hp": 0,
            "reward": 0,
            "damage_log": {},  # {user_id: damage}
        }
        self.spawn_boss.start()
        self.co_duyen.start()
        self.random_drop.start()

    def cog_unload(self):
        self.spawn_boss.cancel()
        self.co_duyen.cancel()
        self.random_drop.cancel()

    # --- HELPER: HP BAR ---
    def get_hp_bar(self, current, max_hp):
        if max_hp <= 0:
            return "[⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜]"
        percent = max(0, min(100, (current / max_hp) * 100))
        filled = int(percent / 10)
        bar = "🟥" * filled + "⬜" * (10 - filled)
        return f"[{bar}] {percent:.1f}%"

    # ==================== WORLD BOSS (2H/LẦN) ====================
    @tasks.loop(hours=2)
    async def spawn_boss(self):
        """Sản sinh Boss Thế Giới"""
        if self.world_boss["name"] and self.world_boss["hp"] > 0:
            old_name = self.world_boss["name"]
            await self.broadcast_event(
                f"💨 **THÔNG BÁO**: Boss **{old_name}** đã biến mất vào hư không!"
            )

        boss_names = [
            "Cự Long Thái Cổ",
            "Thiên Ma Ngoại Đạo",
            "Lão Tổ Sát Lục",
            "Yêu Phượng Bất Tử",
            "Minh Vương Huyết Hải",
        ]
        self.world_boss["name"] = random.choice(boss_names)
        self.world_boss["max_hp"] = random.randint(3000000, 10000000)
        self.world_boss["hp"] = self.world_boss["max_hp"]
        self.world_boss["reward"] = random.randint(20000, 50000)  # Quỹ thưởng chung
        self.world_boss["damage_log"] = {}

        embed = discord.Embed(
            title="🚨 CẢNH BÁO THẾ GIỚI 🚨", color=discord.Color.red()
        )
        embed.description = (
            f"⚔️ **{self.world_boss['name']}** vừa giáng thế tàn phá nhân gian!\n\n"
            f"🩸 Máu: **{self.world_boss['hp']:,}**\n"
            f"💰 Quỹ thưởng: **{self.world_boss['reward']:,} LT** (Chia theo dame)\n"
            f"🎁 Thưởng kết liễu: **5,000 LT**\n"
            f"👉 Gõ `!chemboss` để trấn áp!"
        )
        embed.set_image(
            url=(
                "https://media.discordapp.net/attachments/111/world_boss_spawn.gif"
                if False
                else None
            )
        )  # Placeholder
        await self.broadcast_event(embed=embed)

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def chemboss(self, ctx):
        """Tấn công Boss thế giới"""
        if not self.world_boss["name"] or self.world_boss["hp"] <= 0:
            return await ctx.send(
                "🏜️ Hiện tại sơn hà bình lặng, không có Boss thế giới."
            )

        user_id = str(ctx.author.id)

        async with get_db(self.db_path) as db:
            # Lấy lực chiến tổng
            c = await db.execute(
                """
                SELECT p.luc_chien_goc + (SELECT IFNULL(SUM(im.chi_so_buff), 0) FROM inventory i JOIN item_master im ON i.item_id = im.item_id WHERE i.user_id = p.user_id AND i.trang_thai = 'dang_trang_bi') 
                FROM players p WHERE user_id = ?
                """,
                (user_id,),
            )
            res = await c.fetchone()
            if not res:
                return await ctx.send("❌ Đạo hữu chưa tu luyện!")

            damage = int(res[0] * random.uniform(0.7, 1.3))
            damage = max(1, damage)

            # Giảm máu boss
            actual_dame = min(self.world_boss["hp"], damage)
            self.world_boss["hp"] -= actual_dame
            self.world_boss["damage_log"][user_id] = (
                self.world_boss["damage_log"].get(user_id, 0) + actual_dame
            )

            killed = self.world_boss["hp"] <= 0
            hp_bar = self.get_hp_bar(self.world_boss["hp"], self.world_boss["max_hp"])

            if killed:
                # --- CHIA THƯỞNG TOP DAMAGE ---
                bonus_last_hit = 5000
                total_pool = self.world_boss["reward"]

                # Sắp xếp top dame
                sorted_dame = sorted(
                    self.world_boss["damage_log"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )

                result_text = f"🌈 **CHIẾN THẮNG**: **{self.world_boss['name']}** đã bị trảm sát!\n\n"
                result_text += (
                    f"🗡️ **Kết liễu:** {ctx.author.mention} (+{bonus_last_hit:,} LT)\n\n"
                )
                result_text += "🏆 **BẢNG VÀNG SÁT THƯƠNG:**\n"

                # Thưởng Top 1 (40%), Top 2 (25%), Top 3 (15%), Còn lại chia đều 20%?
                # Thôi chia theo tỉ lệ sát thương thực tế cho công bằng nhất nhưng có bonus Top 3.

                top_medals = {0: "🥇", 1: "🥈", 2: "🥉"}
                for i, (uid, d) in enumerate(sorted_dame[:5]):
                    medal = top_medals.get(i, f"#{i+1}")
                    # Thưởng = (dame / max_hp) * total_pool
                    share = int((d / self.world_boss["max_hp"]) * total_pool)
                    if i == 0:
                        share += int(total_pool * 0.1)  # Thưởng thêm 10% cho MVP

                    await db.execute(
                        "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                        (share, uid),
                    )
                    result_text += (
                        f"{medal} <@{uid}>: **{d:,}** dame -> Nhận **{share:,} LT**\n"
                    )

                # Bonus kết liễu
                await db.execute(
                    "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                    (bonus_last_hit, user_id),
                )
                await db.commit()

                self.world_boss["name"] = None
                await self.broadcast_event(result_text)
                await self.bot.update_quest_progress(user_id, "worldboss", ctx)
            else:
                await ctx.send(
                    f"💥 {ctx.author.mention} gây **{damage:,}** ST!\n🩸 Boss: `{hp_bar}`"
                )

    # ==================== CƠ DUYÊN (30P/LẦN) ====================
    @tasks.loop(minutes=30)
    async def co_duyen(self):
        """Ban Cơ Duyên ngẫu nhiên"""
        print("🌈 [Sự Kiện] Đang tìm kiếm đạo hữu hữu duyên...")
        async with get_db(self.db_path) as db:
            c = await db.execute("SELECT user_id, canh_gioi_id, tu_vi FROM players")
            users = await c.fetchall()
            if not users:
                return

            winner_id, winner_cg, winner_tv = random.choice(users)

            # Lựa chọn kịch bản ngẫu nhiên
            scenarios = [
                {
                    "t": "Vô tình nhặt được túi trữ vật của một tán tu quá cố...",
                    "gift": "lt",
                    "val": random.randint(1000, 5000),
                },
                {
                    "t": "Được một lão tiền bối xoa đầu truyền thụ công lực...",
                    "gift": "tv",
                    "val": random.randint(500, 2000),
                },
                {
                    "t": "Nhặt được một gốc linh thảo nghìn năm bên vách núi...",
                    "gift": "item",
                    "val": None,
                },
                {
                    "t": "Ngộ ra chân lý trong lúc ngắm nhìn thác nước chảy ngược...",
                    "gift": "tv",
                    "val": random.randint(1000, 3000),
                },
            ]
            scr = random.choice(scenarios)

            msg = f"🌈 **CƠ DUYÊN**: Đạo hữu <@{winner_id}> {scr['t']}\n"

            if scr["gift"] == "lt":
                await db.execute(
                    "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                    (scr["val"], winner_id),
                )
                msg += f"💰 Nhận được: **{scr['val']:,} Linh Thạch**!"
            elif scr["gift"] == "tv":
                # Check tv_max
                mc = await db.execute(
                    "SELECT tu_vi_can_thiet FROM realms_master WHERE canh_gioi_id = ?",
                    (winner_cg + 1,),
                )
                row = await mc.fetchone()
                tv_max = row[0] if row and row[0] is not None else 999999999
                new_tv = min(tv_max, winner_tv + scr["val"])
                await db.execute(
                    "UPDATE players SET tu_vi = ? WHERE user_id = ?",
                    (new_tv, winner_id),
                )
                msg += f"✨ Tăng thêm: **{scr['val']:,} Tu Vi**!"
            elif scr["gift"] == "item":
                target_pham = min(5, (winner_cg // 4) + 1)
                ic = await db.execute(
                    "SELECT item_id, ten_vat_pham FROM item_master WHERE pham_cap <= ? ORDER BY RANDOM() LIMIT 1",
                    (target_pham,),
                )
                item = await ic.fetchone()
                if item:
                    await db.execute(
                        "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                        (winner_id, item[0]),
                    )
                    msg += f"🎁 Nhận được: **{item[1]}** (ID: `{item[0]}`)"

            await db.commit()
            await self.broadcast_event(msg)

    # ==================== LINH THẠCH RƠI VÃI (1H/LẦN) ====================
    async def _handle_guild_drop(self, ch, amount):
        msg = await ch.send(
            f"💎 **LINH THẠCH RƠI VÃI**: Đạo hữu nào nhanh tay gõ `!nhat` để lấy **{amount:,} Linh Thạch**!"
        )

        def check(m):
            return m.content == "!nhat" and m.channel == ch and not m.author.bot

        try:
            m = await self.bot.wait_for("message", check=check, timeout=60.0)
            uid = str(m.author.id)
            async with get_db(self.db_path) as db:
                await db.execute(
                    "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                    (amount, uid),
                )
                await db.commit()
            await ch.send(
                f"✅ {m.author.mention} đã nhanh tay nhặt được **{amount:,} Linh Thạch**!"
            )
        except asyncio.TimeoutError:
            await msg.edit(
                content="🏜️ Linh thạch đã bị gió cuốn trôi, không ai nhặt được."
            )

    @tasks.loop(hours=1)
    async def random_drop(self):
        """Rơi Linh Thạch ngẫu nhiên vào kênh - Ai nhặt nhanh thì được"""
        if random.random() < 0.4:  # 40% tỉ lệ mỗi giờ
            amount = random.randint(500, 2000)
            for guild in self.bot.guilds:
                ch = self.get_event_channel(guild)
                if ch:
                    asyncio.create_task(self._handle_guild_drop(ch, amount))

    # --- BROADCAST UTILS ---
    async def broadcast_event(self, content):
        for guild in self.bot.guilds:
            ch = self.get_event_channel(guild)
            if ch:
                if isinstance(content, discord.Embed):
                    await ch.send(embed=content)
                else:
                    await ch.send(content)

    def get_event_channel(self, guild):
        # CHỈ tìm kênh có tên 'Thế Giới Tu Chân'
        channel = discord.utils.get(guild.text_channels, name="thế-giới-tu-chân")

        # Nếu không tìm thấy kênh theo slug, thử tìm theo tên hiển thị
        if not channel:
            channel = next(
                (
                    x
                    for x in guild.text_channels
                    if x.name.replace("-", " ").lower() == "thế giới tu chân"
                ),
                None,
            )

        if channel and channel.permissions_for(guild.me).send_messages:
            return channel
        return None


async def setup(bot):
    await bot.add_cog(SuKien(bot))
