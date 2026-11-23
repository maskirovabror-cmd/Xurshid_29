import os
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
def start_cmd(message):
    bot.send_message(
        message.chat.id,
        "🥕 Sabzi Eco boshqaruv botiga xush kelibsiz!\nKerakli bo‘limni tanlang:",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "📥 Kirim (Xom sabzi)")
def kirim_start(message):
    user_state[message.chat.id] = {"action": "kirim"}
    bot.send_message(
        message.chat.id,
        "Xom sabzi kirimi ma'lumotini kiriting.\nMasalan: `500 1200000` (kg va summa):"
    )

@bot.message_handler(func=lambda m: m.text == "📤 Sotuv (Korzinka/Bozor)")
def sotuv_start(message):
    user_state[message.chat.id] = {"action": "sotuv"}
    bot.send_message(
        message.chat.id,
        "Sotuv ma'lumotini kiriting.\nMasalan: `Korzinka 300 1800000` (mijoz, kg, summa):"
    )

@bot.message_handler(func=lambda m: m.text == "💸 Xarajat / Ish haqi")
def xarajat_start(message):
    user_state[message.chat.id] = {"action": "xarajat"}
    bot.send_message(
        message.chat.id,
        "Xarajat yoki ish haqini kiriting.\nMasalan: `Ishchi_oylik 450000` (turi va summa):"
    )

@bot.message_handler(func=lambda m: m.text == "📊 Hisobot")
def hisobot_cmd(message):
    try:
        kirim_rows = supabase.table("kirimlar").select("*").execute().data or []
        sotuv_rows = supabase.table("sotuvlar").select("*").execute().data or []
        xarajat_rows = supabase.table("xarajatlar").select("*").execute().data or []

        kirim_sum = sum(float(r.get("summa", 0) or 0) for r in kirim_rows)
        sotuv_sum = sum(float(r.get("summa", 0) or 0) for r in sotuv_rows)
        xarajat_sum = sum(float(r.get("summa", 0) or 0) for r in xarajat_rows)
        sof_foyda = sotuv_sum - (kirim_sum + xarajat_sum)

        text = (
            "📊 *Sabzi Eco — Umumiy Hisobot*\n\n"
            f"📥 Xom sabzi xarid summasi: *{kirim_sum:,.0f}* so‘m\n"
            f"📤 Jami sotuv: *{sotuv_sum:,.0f}* so‘m\n"
            f"💸 Xarajat va ish haqi: *{xarajat_sum:,.0f}* so‘m\n"
            f"💰 Sof foyda: *{sof_foyda:,.0f}* so‘m"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Hisobot olishda xatolik: {e}", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_input(message):
    chat_id = message.chat.id
    state = user_state.get(chat_id)

    if not state:
        bot.send_message(chat_id, "Pastdagi menyudan bo‘limni tanlang:", reply_markup=main_menu())
        return

    action = state.get("action")
    parts = message.text.strip().split()

    try:
        if action == "kirim" and len(parts) >= 2:
            kg = float(parts[0])
            summa = float(parts[1])
            supabase.table("kirimlar").insert({"kg": kg, "summa": summa}).execute()
            user_state.pop(chat_id, None)
            bot.send_message(chat_id, "✅ Kirim bazaga saqlandi!", reply_markup=main_menu())

        elif action == "sotuv" and len(parts) >= 3:
            mijoz = parts[0]
            kg = float(parts[1])
            summa = float(parts[2])
            supabase.table("sotuvlar").insert({"mijoz": mijoz, "kg": kg, "summa": summa}).execute()
            user_state.pop(chat_id, None)
            bot.send_message(chat_id, "✅ Sotuv bazaga saqlandi!", reply_markup=main_menu())

        elif action == "xarajat" and len(parts) >= 2:
            turi = parts[0]
            summa = float(parts[1])
            supabase.table("xarajatlar").insert({"turi": turi, "summa": summa}).execute()
            user_state.pop(chat_id, None)
            bot.send_message(chat_id, "✅ Xarajat bazaga saqlandi!", reply_markup=main_menu())

        else:
            bot.send_message(chat_id, "⚠️ Ma'lumot formati noto‘g‘ri. Qaytadan kiriting.")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Bazaga yozishda xatolik: {e}")

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
                         
