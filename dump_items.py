import asyncio
import aiosqlite


async def dump_items():
    db_path = "tu_tien.db"
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT item_id, ten_vat_pham, loai_vat_pham, chi_so_buff FROM item_master WHERE loai_vat_pham = 'dan_duoc';"
        )
        rows = await cursor.fetchall()
        for row in rows:
            print(f"ID={row[0]} | NAME={row[1]} | TYPE={row[2]} | BUFF={row[3]}")


if __name__ == "__main__":
    asyncio.run(dump_items())
