import discord
from discord.ext import commands
from utils import get_db
from datetime import date


class NhiemVu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    @commands.command(name="nhiemvu")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def list_quests(self, ctx):
        user_id = str(ctx.author.id)
        today = str(date.today())

        async with get_db(self.db_path) as db:
            # Lấy tất cả nhiệm vụ
            cursor = await db.execute(
                "SELECT quest_id, description, goal_value, reward_lt, reward_tv FROM daily_quests"
            )
            all_quests = await cursor.fetchall()

            embed = discord.Embed(
                title="📜 NHIỆM VỤ HÀNG NGÀY",
                color=discord.Color.blue(),
                description=f"Ngày: `{today}`",
            )

            for q_id, desc, goal, r_lt, r_tv in all_quests:
                # Lấy tiến độ của người chơi
                cursor = await db.execute(
                    "SELECT current_progress, last_completed_date FROM player_quests WHERE user_id = ? AND quest_id = ?",
                    (user_id, q_id),
                )
                row = await cursor.fetchone()

                progress = 0
                status = "🔄 Đang làm"
                if row:
                    if row[1] == today:
                        progress = row[0]
                        if progress >= goal:
                            status = "✅ Hoàn thành"
                            # Tự động nhận thưởng nếu vừa xong? Hoặc chỉ hiện status. Ở đây tạm để hiện status.
                    else:
                        # Ngày cũ, reset hiển thị
                        progress = 0

                # Kiểm tra nếu vừa hoàn thành thì cộng thưởng (nếu chưa cộng)
                # Logic này có thể tối ưu hơn, nhưng tạm để đơn giản:
                # Nếu progress == goal và chưa được đánh dấu là "đã nhận thưởng" trong ngày.
                # Tuy nhiên để tránh phức tạp, ta sẽ cộng thưởng ngay khi update_quest_progress đạt goal.

                # Tạo thanh tiến độ (10 blocks)
                if goal > 0:
                    filled = int((progress / goal) * 10)
                    bar = "🟦" * filled + "⬜" * (10 - filled)
                else:
                    bar = "⬜" * 10

                embed.add_field(
                    name=f"{status} | {desc}",
                    value=f"Tiến độ: `[{bar}]` **{progress}/{goal}**\nThưởng: `{r_lt:,}` LT, `{r_tv:,}` TV",
                    inline=False,
                )

            embed.set_footer(text="Nhiệm vụ sẽ tự động reset mỗi ngày!")
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(NhiemVu(bot))
