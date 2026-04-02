import asyncio
import sqlite3
import unittest
import time
import re
from unittest.mock import MagicMock, AsyncMock
import discord
from discord.ext import commands

# Fix Path
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import get_db, update_player_stats, CleanID, CleanInt
from cogs.tu_luyen import TuLuyen
from cogs.thong_tin import ThongTin
from cogs.vat_pham import VatPham
from cogs.dot_pha import DoKiep
from cogs.san_boss import SanBoss
from cogs.su_kien import SuKien
from cogs.giao_dich import GiaoDich
from cogs.dau_gia import DauGia
from cogs.cong_phap import CongPhap
from cogs.che_tao import CheTao
from cogs.dan_cac import DanCac
from cogs.do_sat import DoSat
from cogs.nhiem_vu import NhiemVu
from cogs.he_thong import HeThong
from cogs.bang_xep_hang import BangXepHang
from cogs.pvp import PvP


async def simulate():
    print("🚀 Bắt đầu mô phỏng kiểm thử hệ thống V4 GOLD FULL...")
    db_path = "tu_tien.db"

    # 1. Mock Bot & Context
    bot = AsyncMock(spec=commands.Bot)
    bot.db_path = db_path
    bot.update_quest_progress = AsyncMock()
    bot.guilds = []

    # Mock Authors
    author = MagicMock(spec=discord.Member)
    author.id = 123456789
    author.name = "TestTuSi"
    author.display_name = "TestTuSi"
    author.mention = "<@123456789>"
    author.display_avatar = MagicMock()
    author.display_avatar.url = "http://example.com/avatar.png"

    target = MagicMock(spec=discord.Member)
    target.id = 987654321
    target.name = "TargetTuSi"
    target.display_name = "TargetTuSi"
    target.mention = f"<@{target.id}>"
    target.bot = False

    ctx = MagicMock(spec=commands.Context)
    ctx.author = author
    ctx.bot = bot
    ctx.send = AsyncMock()
    ctx.reply = AsyncMock()
    ctx.guild = MagicMock()
    ctx.guild.get_member = MagicMock(return_value=target)
    ctx.channel = MagicMock()
    ctx.channel.send = AsyncMock()
    ctx.channel.name = "thế giới tu chân"

    # 2. Initialize Cogs
    cogs = {
        "TuLuyen": TuLuyen(bot),
        "ThongTin": ThongTin(bot),
        "VatPham": VatPham(bot),
        "DoKiep": DoKiep(bot),
        "SanBoss": SanBoss(bot),
        "GiaoDich": GiaoDich(bot),
        "CongPhap": CongPhap(bot),
        "CheTao": CheTao(bot),
        "DanCac": DanCac(bot),
        "DoSat": DoSat(bot),
        "NhiemVu": NhiemVu(bot),
        "HeThong": HeThong(bot),
        "Top": BangXepHang(bot),
        "SuKien": SuKien(bot),
        "PvP": PvP(bot),
    }

    # 3. TEST SEQUENCE
    results = []

    async def test_cmd(name, coro):
        print(f"  > Testing {name}...", end=" ", flush=True)
        try:
            await coro
            print("✅ OK")
            results.append((name, True))
        except Exception as e:
            print(f"❌ FAIL: {type(e).__name__}: {e}")
            results.append((name, False, str(e)))

    # --- RESET DB FOR TEST ---
    async with get_db(db_path) as db:
        await db.execute("DELETE FROM players")
        await db.execute(
            "INSERT INTO players (user_id, is_active, linh_thach, the_luc, sinh_luc, canh_gioi_id, luc_chien_goc) VALUES (?, 1, 1000000, 120, 100, 1, 50)",
            (str(author.id),),
        )
        await db.execute(
            "INSERT INTO players (user_id, is_active, linh_thach, the_luc, sinh_luc, canh_gioi_id, luc_chien_goc) VALUES (?, 1, 1000000, 120, 100, 1, 50)",
            (str(target.id),),
        )
        await db.commit()

    # --- EXECUTE CORE COMMANDS ---
    await test_cmd("!me", cogs["ThongTin"].profile.callback(cogs["ThongTin"], ctx))
    await test_cmd("!tuido", cogs["VatPham"].tuido.callback(cogs["VatPham"], ctx))
    await test_cmd("!tuluyen", cogs["TuLuyen"].tuluyen.callback(cogs["TuLuyen"], ctx))
    await test_cmd(
        "!doituvi", cogs["TuLuyen"].doituvi.callback(cogs["TuLuyen"], ctx, 1000)
    )
    await test_cmd("!dotpha", cogs["DoKiep"].dotpha.callback(cogs["DoKiep"], ctx))
    await test_cmd("!top", cogs["Top"].leaderboard.callback(cogs["Top"], ctx, "tuvi"))
    await test_cmd(
        "!trogiup", cogs["HeThong"].help_command.callback(cogs["HeThong"], ctx)
    )
    await test_cmd(
        "!nhiemvu", cogs["NhiemVu"].list_quests.callback(cogs["NhiemVu"], ctx)
    )

    # Trade & Market
    await test_cmd(
        "!chuyentien",
        cogs["GiaoDich"].chuyentien.callback(cogs["GiaoDich"], ctx, target, 100),
    )
    async with get_db(db_path) as db:
        await db.execute(
            "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, 101, 5)",
            (str(author.id),),
        )
        await db.commit()
    await test_cmd(
        "!ban", cogs["GiaoDich"].ban.callback(cogs["GiaoDich"], ctx, 101, 5000)
    )
    await test_cmd("!choden", cogs["GiaoDich"].choden.callback(cogs["GiaoDich"], ctx))

    # Alchemy & Shops
    await test_cmd("!danphuong", cogs["CheTao"].danphuong.callback(cogs["CheTao"], ctx))
    await test_cmd("!dancac", cogs["DanCac"].dancac.callback(cogs["DanCac"], ctx))

    # Skills
    async with get_db(db_path) as db:
        await db.execute(
            "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, 401, 1)",
            (str(author.id),),
        )
        await db.commit()
    await test_cmd(
        "!hoc", cogs["CongPhap"].hoc_cong_phap.callback(cogs["CongPhap"], ctx)
    )
    await test_cmd(
        "!congphap", cogs["CongPhap"].xem_cong_phap.callback(cogs["CongPhap"], ctx)
    )

    # Boss & PK
    await test_cmd("!sanboss", cogs["SanBoss"].sanboss.callback(cogs["SanBoss"], ctx))
    await test_cmd("!dosat", cogs["DoSat"].dosat.callback(cogs["DoSat"], ctx, target))
    await test_cmd("!chemboss", cogs["SuKien"].chemboss.callback(cogs["SuKien"], ctx))
    await test_cmd("!pvp", cogs["PvP"].invoke_pvp.callback(cogs["PvP"], ctx, target))

    # 4. FINAL REPORT
    print("\n" + "=" * 40)
    print("📊 BÁO CÁO MÔ PHỎNG V4 GOLD FULL")
    success_count = sum(1 for r in results if r[1])
    print(f"Tổng cộng kiểm tra: {len(results)} lệnh core")
    print(f"Thành công: {success_count} | Thất bại: {len(results) - success_count}")
    print("=" * 40)

    if success_count == len(results):
        print("🎉 KẾT LUẬN: HỆ THỐNG V4 GOLD FULL ĐÃ SẴN SÀNG QUYẾT CHIẾN!")
    else:
        print("⚠️ KẾT LUẬN: CẦN FIX CÁC LỖI TRÊN TRƯỚC KHI DEPLOY.")


if __name__ == "__main__":
    asyncio.run(simulate())
