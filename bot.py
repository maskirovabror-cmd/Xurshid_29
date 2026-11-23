import os
import time
import telebot
from telebot import types
from supabase import create_client, Client

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = "https://tatzcsmrhxtppwosufsf.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

user_state = {}


def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📥 Kirim (Xom sabzi)", "📤 Sotuv (Korzinka/Bozor)")
    markup.row("💸 Xarajat / Ish haqi", "📊 Hisobot")
    return markup


@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_state.pop(message.chat.id, None)
    bot.send_message(
        message.chat.id,
        "🥕 *Sabzi Eco* boshqaruv botiga xush kelibsiz!\nKerakli bo‘limni tanlang:",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


@bot.message_handler(func=lambda m: m.text == "📥 Kirim (Xom sabzi)")
def ask_kirim(message):
    user_state[message.chat.id] = "kirim"
    bot.send_message(
        message.chat.id,
        "📥 *Xom sabzi kirimi*\nMiqdor (kg) va summani probel bilan kiriting.\nMasalan: `100 250000`",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: m.text == "📤 Sotuv (Korzinka/Bozor)")
def ask_sotuv(message):
    user_state[message.chat.id] = "sotuv"
    bot.send_message(
        message.chat.id,
        "📤 *Sabzi sotuvi*\nMiqdor (kg) va summani probel bilan kiriting.\nMasalan: `80 400000`",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: m.text == "💸 Xarajat / Ish haqi")
def ask_xarajat(message):
    user_state[message.chat.id] = "xarajat"
    bot.send_message(
        message.chat.id,
        "💸 *Xarajat yoki ish haqi*\nSumma va izohni kiriting.\nMasalan: `150000 Ishchilar haqi`",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: m.text == "📊 Hisobot")
def show_report(message):
    try:
        kirim_rows = supabase.table("kirimlar").select("*").execute().data or []
        sotuv_rows = supabase.table("sotuvlar").select("*").execute().data or []
        xarajat_rows = supabase.table("xarajatlar").select("*").execute().data or []

        def pick_num(row, keys):
            for k in keys:
                if k in row and row[k] is not None:
                    try:
                        return float(row[k])
                    except (ValueError, TypeError):
                        pass
            return 0.0

        kirim_kg = sum(pick_num(r, ["kg", "miqdor", "weight", "quantity"]) for r in kirim_rows)
        kirim_sum = sum(pick_num(r, ["summa", "amount", "price", "narx"]) for r in kirim_rows)

        sotuv_kg = sum(pick_num(r, ["kg", "miqdor", "weight", "quantity"]) for r in sotuv_rows)
        sotuv_sum = sum(pick_num(r, ["summa", "amount", "price", "narx"]) for r in sotuv_rows)

        xarajat_sum = sum(pick_num(r, ["summa", "amount", "price", "narx"]) for r in xarajat_rows)
        foyda = sotuv_sum - (kirim_sum + xarajat_sum)

        report_text = (
            "📊 *Sabzi Eco — Umumiy Hisobot*\n\n"
            f"📥 *Kirim:* {kirim_kg:g} kg | {kirim_sum:,.0f} so‘m\n"
            f"📤 *Sotuv:* {sotuv_kg:g} kg | {sotuv_sum:,.0f} so‘m\n"
            f"💸 *Xarajat:* {xarajat_sum:,.0f} so‘m\n"
            f"💰 *Sof foyda:* {foyda:,.0f} so‘m"
        )
        bot.send_message(message.chat.id, report_text, parse_mode="Markdown", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Hisobot olishda xatolik: `{e}`", parse_mode="Markdown")


def insert_flexible(table_name, payload_candidates):
    last_err = None
    for data in payload_candidates:
        try:
            supabase.table(table_name).insert(data).execute()
            return True, None
        except Exception as e:
            last_err = e
    return False, last_err


@bot.message_handler(func=lambda m: True)
def handle_input(message):
    state = user_state.get(message.chat.id)
    text = (message.text or "").strip()

    if not state:
        bot.send_message(message.chat.id, "Pastdagi menyudan bo‘limni tanlang:", reply_markup=main_menu())
        return

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Iltimos, ma'lumotni to‘g‘ri formatda kiriting.")
        return

    try:
        if state in ("kirim", "sotuv"):
            kg = float(parts[0].replace(",", "."))
            summa = float(parts[1].replace(" ", "").replace(",", "."))
            table = "kirimlar" if state == "kirim" else "sotuvlar"
            candidates = [
                {"kg": kg, "summa": summa},
                {"miqdor": kg, "summa": summa},
                {"kg": kg, "narx": summa},
            ]
            ok, err = insert_flexible(table, candidates)
            if ok:
                user_state.pop(message.chat.id, None)
                label = "Kirim" if state == "kirim" else "Sotuv"
                bot.send_message(message.chat.id, f"✅ {label} bazaga saqlandi!", reply_markup=main_menu())
            else:
                bot.send_message(message.chat.id, f"⚠️ Bazaga yozishda xatolik: `{err}`", parse_mode="Markdown")

        elif state == "xarajat":
            summa = float(parts[0].replace(" ", "").replace(",", "."))
            izoh = parts[1].strip()
            candidates = [
                {"summa": summa, "izoh": izoh},
                {"summa": summa, "tavsif": izoh},
                {"summa": summa, "nomi": izoh},
                {"summa": summa},
            ]
            ok, err = insert_flexible("xarajatlar", candidates)
            if ok:
                user_state.pop(message.chat.id, None)
                bot.send_message(message.chat.id, "✅ Xarajat bazaga saqlandi!", reply_markup=main_menu())
            else:
                bot.send_message(message.chat.id, f"⚠️ Bazaga yozishda xatolik: `{err}`", parse_mode="Markdown")

    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Raqamlarni to‘g‘ri kiriting. Masalan: `100 250000`", parse_mode="Markdown")


if __name__ == "__main__":
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=20)
        except Exception as e:
            print("Polling error:", e)
            time.sleep(20)
            
