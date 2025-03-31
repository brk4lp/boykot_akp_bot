import csv
import logging
import difflib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Loglama ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_products_from_csv(file_path):
    """CSV'den ürünleri ve boykot sebeplerini yükler"""
    products = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)  # Başlıkları otomatik algılar
            for row in reader:
                if row:
                    products.append({
                        'name': row['name'].lower().strip(),
                        'reason': row.get('reason', 'Sebep belirtilmemiş')
                    })
        logger.info(f"{len(products)} ürün başarıyla yüklendi.")
    except Exception as e:
        logger.error(f"CSV okuma hatası: {str(e)}")
    return products

async def show_product_info(update: Update, product):
    """Ürün bilgisini gösterir"""
    message = (
        f"⚠️ *BOYKOT UYARISI* ⚠️\n"
        f"*Ürün:* {product['name']}\n"
        f"*Sebep:* {product['reason']}\n\n"
        f"❌ Lütfen satın almayın!"
    )
    if isinstance(update, Update):
        await update.message.reply_text(message, parse_mode='Markdown')
    else:  # CallbackQuery
        await update.edit_message_text(message, parse_mode='Markdown')

async def check_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ürün aramasını işler"""
    query = update.message.text.strip().lower()
    products = context.bot_data["products"]
    
    # 1. Tam eşleşme kontrolü
    exact_matches = [p for p in products if p['name'] == query]
    if exact_matches:
        await show_product_info(update, exact_matches[0])
        return
    
    # 2. Kısmi eşleşme kontrolü
    partial_matches = [p for p in products if query in p['name']][:5]
    if partial_matches:
        keyboard = [
            [InlineKeyboardButton(p['name'], callback_data=p['name'])]
            for p in partial_matches
        ]
        await update.message.reply_text(
            "🔍 Şu ürünler bulundu:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # 3. Benzer ürün önerisi
    similar_matches = difflib.get_close_matches(
        query, [p['name'] for p in products], n=3, cutoff=0.5
    )
    if similar_matches:
        matched_products = [p for p in products if p['name'] in similar_matches]
        keyboard = [
            [InlineKeyboardButton(p['name'], callback_data=p['name'])]
            for p in matched_products
        ]
        await update.message.reply_text(
            "🤔 Bunlardan birini mi kastettiniz?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("✅ Bu ürün boykot listesinde yok")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buton yanıtlarını işler"""
    query = update.callback_query
    product_name = query.data
    products = context.bot_data["products"]
    
    product = next((p for p in products if p['name'] == product_name), None)
    if product:
        await show_product_info(query, product)
    else:
        await query.answer("Ürün bulunamadı")

def main():
    TOKEN = "TELEGRAM_TOKEN"
    CSV_FILE_PATH = "boykot_listesi.csv"  # reason sütunu olan CSV
    
    products = load_products_from_csv(CSV_FILE_PATH)
    if not products:
        logger.error("Ürün yüklenemedi! Bot kapatılıyor...")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.bot_data["products"] = products
    
    # Handler'lar
    app.add_handler(CommandHandler("start", 
        lambda u,c: u.message.reply_text("Ürün adı yazın, boykot bilgisini verelim")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_product))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Bot başlatıldı 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()