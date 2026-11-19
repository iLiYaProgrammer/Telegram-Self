import os, json, asyncio, random
from datetime import datetime as dt
from urllib.parse import quote
from collections import OrderedDict
import pytz
from pathlib import Path

from telethon import TelegramClient, events
from telethon.tl.custom import Button
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, SendReactionRequest
from telethon.tl.functions.channels import JoinChannelRequest, GetFullChannelRequest
from telethon.tl.types import (
    ReactionEmoji, MessageMediaPhoto, MessageMediaDocument, Channel
)
from telethon.errors import FloodWaitError, UserNotParticipantError

import requests
import yt_dlp
import qrcode
from gtts import gTTS
from persiantools.jdatetime import JalaliDate
from PIL import Image, ImageDraw, ImageFont
from deep_translator import GoogleTranslator

# =========================================
# تنظیمات اولیه
# =========================================
api_id = 12345678
api_hash = "you_api_hash"
BOT_TOKEN = "You_bot_token"
BOT_USERNAME = "TornadoHelper_bot"

os.makedirs("sessions", exist_ok=True)
os.makedirs("downloads", exist_ok=True)
os.makedirs("saved_media", exist_ok=True)
os.makedirs("profiles", exist_ok=True)

SESSION_DIR = Path("sessions")
session_files = sorted([f for f in SESSION_DIR.glob("myacc*.session")])

accounts = []
for sf in session_files:
    c = TelegramClient(str(SESSION_DIR / sf.stem), api_id, api_hash)
    accounts.append(c)

if not accounts:
    print("❌ No valid 'myacc' session files found in 'sessions' folder!")
    exit()

client = accounts[0]
bot = TelegramClient("sessions/mybot", api_id, api_hash)
manager = TelegramClient("sessions/manager", api_id, api_hash)

DATA_FILE = "data2.json"
default_data = {
    "self_on": True, "enemy": [], "silent": [], "friend_enemy": [], "friend_enemy_count": {},
    "clock_on": False, "clock_font": "1", "timers": {}, "fast_replies": {},
    "last_target_id": None, "save_timed_on": False, "save_msg_on": False,
    "secretary_on": False, "secretary_text": "من فعلا آفلاین عشقم وقتی آنلاین شم جوابتو میدم ✅",
    "text_mode": None, "action_on": False, "locks": [], "auto_seen_on": False,
    "reactions": {}, "first_comment_on": False, "first_comment_targets": [],
    "first_comment_text": "کامنت اول 🤣", "force_join_on": False,
    "force_join_channel": None, "force_join_text": "عشق داداش تو چنل جوین نیستی اول جوین شو تا بتونی پیام بدی",
    "default_profile": None,
}

if os.path.exists(DATA_FILE):
    data = json.load(open(DATA_FILE, "r", encoding="utf-8"))
    for key, val in default_data.items():
        if key not in data: data[key] = val
else: data = default_data

def save(): json.dump(data, open(DATA_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

FONTS = {"1": "0123456789", "2": "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡", "3": "⓪①②③④⑤⑥⑦⑧⑨", "4": "０１２３４５６７８９", "5": "➊➋➌➍➎➏➐➑➒⓿", "6": "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵", "7": "𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫", "8": "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"}
def font_time(t):
    src = "0123456789"; dst = FONTS.get(data.get("clock_font"), FONTS["1"])
    return "".join(dst[src.index(c)] if c in src else c for c in t)

# =========================================
# لیست فحش‌ها
# =========================================
ENEMY_TEXTS = [
    "ماشین با سرعت ۲۲۰ تا تو کس ننت", "خار کص مکانیکی", "تخمامو رو صورت ننت بمالم گریس ممبرک",
    "کیر پوگبا تو کس مادرت", "میگن گرگا قبل از اینکه بیان شیر مادرتو میخورن و گله میان",
    "تاج کیرم سنگینه مواظب باش میندازی سر مادرت گردنش نشکنه", "زیر تخت مادرت صدای گوز ضبط شده میزارم مشتریای مادرتو فراری میدم خودم صف اول شم",
    "عضو نیروی دلتای آمریکا میشم مادرتو درحال سکس با دوست پسرش با جاش میدزدم", "غیرت پدرت پینگش بالاس هی از سرور ناموست کانکت و دیسکانکت میشه",
    "آبجی کوچیکتو گاییدم", "تورک میشم به کسمادرت جفتک میزنم", "لر محلتون میشم با تمام قوا کسمادرت رو با سیمان آب بندی میکنم که دیگه حامله نشه",
    "بالا باش ناموص کیر دزد", "کیرم تو مادرت یخ زد باید اتیلن گلیکول بریزم.", "ننتو دادم ب دارکای افریقا گاییدن",
    "معترض میشم میشینم رو خیابون تا ننتو ندی بکنم پا نمیشم",
    "تو این دنیا 8,239,867,952 آدم وجود داره همونجوری که به تعداد توجه نکردی به اینکه قراره برینم دهن مادرت هم توجه نکن",
    "ناوگان بزرگی از کیر به سمت مادرت درحال حرکته.", "🛑پیام خامنه ای: کژمادرت",
    "ناوگان کشتی حامل بکن های مادرت به لنگرگاه‌ رسیده و فردا بدنبال ناموست صف می‌شوند", "خاله خارکونی خفه",
    "کیرم تو کفن مردهات بالا باش", "مرده کونی بالا باش", "ننه موس تخم نکن", "مادرت بردم پشت باغ گاییدم حاصلش تو بودی",
    "دالگ پیکنیکی", "خفه ناموص کونی ولدزنا", "ننه دولتی ", "ناموص کیردزد بالا باش",
    "کیر گروهبان آمریکا تو کص مص ننن تو کص ننت", "مادرت رو تمام اعضای خانواده قاطی میکنم و بعد میریزم تو مخزن تو قاطی میکنم",
    "از مامانت پرسیدن کیر چندتا حرف داره گفت کیر که حرف نداره", "پاهای مادرت رو مثل سگی که استخون دیده لیس میزنم",
    "مادر جنده ولد زنا ناموس کصته تو میخوای با من ابر انسان کل بندازی ننت میبرم زیر کیرم میکشم ننه خر حرومزاده",
    "من خدام مادرجنده فراریت میدم کونی ناموص", "شاشیدم رو صورت ناموصت", "بدو زجه بزن مث مامان جندت",
    "ننه مرده کونی", "دستم رو کص ناموصت", "بالا باش ناموص کونی از کص مادرت دفاع کن", "ساک بزن برام مثل مادرت",
    "شاش تو کص ننت", "و اما مادر جندت", "با تلمبه فاضلاب معده مادرتو از کصش دراوردم", "استین کوتاه تو کس ناموست",
    "مادرت بمیره فراری شو", "هورمون ترس ولاد رو از طریق نمونه های RNA کپی میکنم و به پدرت منتقل میکنم تا پدرت ترسو بشه و نتونه از مادرت دفاعی بکنه",
    "با مادرت تو کاسه توالت کمپین حمایت از گوه ها زدیم", "بدو بینم کیرم تو کصا خونتون",
    "با مسلسل گاتلینگ ۷ لول gau-8 avenger با نرخ آتش ۳۹۰۰ شلیک در دقیقه متعلق به هواپیمای پشتیبانی نزدیک a-10 thunderbolt II مواضع مادرت رو به گلوله میبندم",
    "کص مادرت رو کیرم بالا پایین میره بعدش مادرت میاد خایه هامو میخوره و مادرت با کونش خایه هامو ماساژ میده",
    "دارم از معدن کس مادرت فلز چوچولیوم استخراج میکنم", "وقتی میرفتم مادرتو زیر کیرم بگام چه حسی پیدا میکردی ؟",
    "گردن خارتو بخورم حشری شه؟", "عره برقی تو کس ننت😂", "برج میلاد تو کص ناموصت (از پهنا)", "موکت تو کس ناموست",
    "کصمادر کصممبرت", "انگشت پای چپ ملخ تو کون ننت",
    "فوری فوری فوری فوری                                     فاکس نیوز : مادرت بعد از ۸۰۰ساعت سکس مداوم با افراد نامعلوم هنوز به من کص نداده",
    "شب میام تو کابوس ناموست کیر می‌کنم تو ناموست",
    " مکش رحم مادرتو با گرون ترین جارو برقی بازار مقایسه کردم آپلود کردم یوتیوب شورت",
    "ننت تو جنده خونس برو جمش کن",
    " مامان کیر پرستت هر روز بهم اس ام اسای عاشقانه و احساسی میده ولی من با استیکر بادمجون خرش میکنم و میبرمش تو تختی که به بابات میده هر روز میکنمش",
    "ای کیرم تو کس مادرت باز افتادی به ران تو مادرجنده. تو سری خور وای ریدم خدایی تو بیناموس بی سطح. داری جلوی خودم نت افی میزنی فکر میکنی من تو رو حساب میکنم مادرجنده بیناموس تخم نداری جلوی خودم سر کیب باشی داری پشت خشاب پنهان میشی بیناموس تو سری خور اوی مادرجنده. نوچه بدو سر تکس باش تا اضلایی کس مادرت رو از بدنش جدا کنم بیناموس. توسری خور اوی کیرم تو کس مادرت سگ تو سری  خور میخوای جلوی خودم. گنده. گنده بدونی مسیح مادرتو خورد خمیر میکنم بیناموس تو سری خور یالا بدو سریع. سر تکس باش که بزنم ناموس کدنت بگام. شاش خور بیناموس کیرم تو کس نوامیس مادرت بیناموس تو سری خور اوی مادرجنده تورک خر وقتی نمیتونی جلوی خودم وایسی برای  چی داری جلوی خودم میشاخی کیرم تو کس مادرت کیرم تو کس مادرت ببناموس واسه من بخوای بشاخی میزنم ناموس کونیت میگام شاس ناموس تو سری خور اوی مادرجنده افگون بی خاسیت بدو ان شو که میخوام بزنم اون مادرت رو بگام بیناموس تو سری خور اوی بیناموس تو سری خور تو جلوی خدات هم نمیتونی  وایسی کیرم تو کس مادرت تو بخوای جلوی من پشت ران قایم شی میزنم اون ناموس کونیت میگام بیناموس تو سری خور اوی بیناموس شاشخور کجا داری از دست من فرار میکنی بیناموس تو سری خور کیرم تو کس نوامیست بیناموس سگ دالک بیناموس خارکسه مادرکسه کیرم تو کس نوامیست ببناموس خار کسه مادر قهوه کیرم تو ک مادرت ناموس کونی بیناموس کیرم تو کس نوامیست مادرسگ تو سری خور اوی بیناموس تو سری خور اوی مادرخراب بیمادر با توهم مادرجنده  بیناموس کس ننه کیرم تو کس مادرت بیناموس شاش خور اوی مادرجنده. تورک خر نمیتونی مقابل خودم وایسی داری جلوی خودم میشاخی که برسی ولی خب باز نمیرسی مادرسگ پسی خور کیرم تو کس مادرت شاش خور تو سری خور مادرت رو  گایدم بیناموس بیمادر باز کجا اف شدی کیرم تو کس نوامیس خارت باز فرار کردی نه بیناموس بدو ان شو پشت. ران اصلا قایم نشو مادرجندع. تو سریع خور اوی کیرم تو کس مادرت",
    "کوص گشاد ننت جا میشه آخه کص کش ننه جنده کیری کیر بابام تو کص خوار مادرت کبود شه بینانوس ننت روزی ۱۰ هزار بار جنده ساعتی میده کص هرزه مادر جنده لاپایی ننتو گاییدم حامله شدکص مادر جنده آیکون خوار کوصه ننت مادر جنده آیکون آیکون کوصه ننت مادر جنده برو خوار جندت رو جمع کن که هر روز برام ساک میزن اسپرم خر زدن تو ننت تا تویه بی ناموس بی آلت بدنیا اومدی که در این جا برا من کص کص کنی خوار کوصه مادر ولد زنا مادر کص گشاد کله کیری تو کوص گشاد ننت جا میشه آخه کص کش ننه جنده کیری کیر بابام تو کص خوار مادرت کبود شه بینانوس ننت روزی ۱۰ هزار بار جنده ساعتی میده کص هرزه مادر جنده لاپایی ننتو گاییدم حامله شدکص مادر جنده آیکون خوار کوصه ننت مادر جنده آیکون آیکون کوصه ننت مادر جنده برو خوار جندت رو جمع کن که هر روز برام ساک میزن اسپرم خر زدن تو ننت تا تویه بی ناموس بی آلت بدنیا اومدی که در این جا برا من کص کص کنی خوار کوصه مادر ولد زنا مادر کص گشاد کله کیری تو کوص گشاد ننت جا میشه آخه کص کش ننه جنده کیری کیر بابام تو کص خوار مادرت کبود شه بینانوس ننت روزی ۱۰ هزار بار جنده ساعتی میده کص هرزه مادر جنده لاپایی ننتو گاییدم حامله شدکص مادر جنده آیکون خوار کوصه ننت مادر جنده آیکون آیکون کوصه ننت مادر جنده برو خوار جندت رو جمع کن که هر روز برام ساک میزن اسپرم خر زدن تو ننت تا تویه بی ناموس بی آلت بدنیا اومدی که در این جا برا من کص کص کنی خوار کوصه مادر ولد زنا مادر کص گشاد کله کیری تو کوص گشاد ننت جا میشه آخه کص کش ننه جنده کیری کیر بابام تو کص خوار مادرت کبود شه بینانوس ننت روزی ۱۰ هزار بار جنده ساعتی میده کص هرزه مادر جنده لاپایی ننتو گاییدم حامله شد جنده جنده جنده ساعتماⷬد‌ر‌ جندهمًَُِّنًَُِِِِِِِِِِِّمَُُُُُُُُُُُُُُُُُُُُُُُِِِِِِِِِِِِِِِِِِِِِِِِِِِِِِِِِِّّّّّّّ ًَُِّبِیًَُِِِِِِِِِِِِِّب💀🩸:>>کص مادر جنده آیکون خوار کوصه ننت مادر جنده آیکون آیکون کوصه ننت مادر جنده برو خوار جندت رو جمع کن که هر روز برام ساک میزن اسپرم خر زدن تو ننت تا تویه بی ناموس بی آلت بدنیا اومدی که در این جا برا من کص کص کنی خوار کوصه مادر ولد زنا مادر کص گشاد کله کیری تو کوص گشاد ننت جا میشه آخه کص کش ننه جنده کیری کیر بابام تو کص خوار مادرت کبود شه بینانوس ننت روزی ۱۰ هزار بار جنده ساعتی میده کص هرزه مادر جنده لاپایی ننتو گاییدم حامله شدکص مادر جنده آیکون خوار کوصه ننت مادر جنده آیکون آیکون کوصه ننت مادر جنده برو خوار جندت رو جمع کن که هر روز برام ساک میزن اسپرم خر زدن تو ننت تا تویه بی ناموس بی آلت بدنیا اومدی که در این جا برا من کص کص کنی خوار کوصه مادر ولد زنا مادر کص گشاد کله کیری تو کوص گشاد ننت جا میشه آخه کص کش ننه جنده کیری کیر بابام تو کص خوار مادرت کبود شه بینانوس ننت روزی ۱۰ هزار بار جنده ساعتی میده کص هرزه مادر جنده لاپایی ننتو گاییدم حامله شدکص مادر جنده آیکون خوار کوصه ننت مادر جنده آیکون آیکون کوصه ننت مادر جنده برو خوار جندت رو جمع کن که هر روز برام ساک میزن اسپرم خر زدن تو ننت تا تویه بی ناموس بی آلت بدنیا اومدی که در این جا برا من کص کص کنی خوار کوصه مادر ولد زنا مادر کص گشاد کله کیری تو کوص گشاد ننت جا میشه آخه کص کش ننه جنده کیری کیر بابام تو کص خوار مادرت کبود شه بینانوس ننت روزی ۱۰ هزار بار جنده ساعتی میده کص هرزه مادر جنده لاپایی ننتو گاییدم حامله شدکص مادر جنده آیکون خوار کوصه ننت مادر جنده آیکون آیکون کوصه ننت مادر جنده برو خوار جندت رو جمع کن که هر روز برام ساک میزن اسپرم خر زدن تو ننت تا تویه بی ناموس بی آلت بدنیا اومدی که در این جا برا من کص کص کنی خوار کوصه مادر ولد زنا مادر کص گشاد کله کیری تو کوص گشاد ننت جا میشه آخه کص کش ننه جنده کیری کیر بابام تو کص خوار مادرت کبود شه بینانوس ننت روزی ۱۰ هزار بار جنده ساعتی میده کص هرزه مادر جنده لاپایی ننتو گاییدم حامله شد جنده جنده جنده ساعتماⷬد‌ر‌ جندهمًَُِّنًَُِِِِِِِِِِِّمَُُُُُُُُُُُُُُُُُُُُُُُِِِِِِِِِِِِِِِِِِِِِِِِِِِِِِِِِِّّّّّّّ ًَُِّبِیًَُِِِِِِِِِِِِِّب💀🩸:>>کص مادر جنده آیکون خوار کوصه ننت مادر جنده آیکون آیکون کوصه ننت مادر جنده برو خوار جندت رو جمع کن که هر روز برام ساک میزن اسپرم خر زدن تو ننت تا تویه بی ناموس بی آلت بدنیا اومدی که در این جا برا من کص کص کنی خوار کوصه مادر ولد زنا مادر کص گشاد کله کیری تو کوص گشاد ننت جا میشه آخه کص کش ننه جنده کیری کیر بابام تو کص خوار مادرت کبود شه بینانوس ننت روزی ۱۰ هزار بار جنده ساعتی میده کص هرزه مادر جنده لاپایی ننتو گاییدم حامله شدکص مادر جنده آیکون خوار کوصه ننت مادر جنده آیکون آیکون کوصه ننت مادر جنده برو خوار جندت رو جمع کن که هر روز برام ساک میزن اسپرم خر زدن تو ننت تا تویه بی ناموس بی آلت بدنیا اومدی که در این جا برا من کص کص کنی",
    "ننتو میدم علی آلت زاده بگاد دیگه شاخ نشی بیناموص", "کص مادرت روم ریپ کنی", "انگور خوردم چاییدم زن آقاتو گاییدم",
    "شاش تو کص ناموصت", "کص مادرت چت بدی بدون نقض ", "مامانت با کونش کیرمو ماساژ میداد بعد سکس ",
    "ننه جندتو جلو بابای بی غیرتت گاییدم", "مادرت از پکیج های هکینگ تلگرام با ابزار ترموکس  همراه با کوروش سنایی ۶۰ درصد تخفیف گوه تره",
    "اونقدر که کص مادرتو انگشت کردم این نات کوینه رو نکردم", "مادرت مثل همستره همه انگشتش میکنن",
    "ماشاالله مادرش خیلی گشاده 54 تا کیر رفته توش ولی بازم جا داره", "مادرتو زیر کیرم شهید کردم الان خانواده شهید حساب میشی برو ذوق کن",
    "تو کص نصلت سگ پدر کیرممممممم تو وجود ابجبت کص ممنط رو نگاییدم کص نسلت کص خاعرت کص هفت جدتت لاشی خشاب تو کص ننت کله کیری تخم صگ من کیرم تو کص مادر داغت قان قان پیش به سوی کص ابجیت کص خارت رسمن گاییدم کص نسلت پسرم کیرم تو کص خاندان نرمت کاری نکن بیام تو کابوست کیر بزنم ت ناموست لاشی تخم صگ  کیر  ابراهیم ته کص ننت کیرم تو کص ننه پریودت کص ننت تو دستمه کص خارت رو کیرمه کیر زعوس تو کص ننت مادر به خطا کون بچه تخم حروم بی پدر کص ننت ناموصا از سمت چپ تو کص ننت از سمت راست تو کص ننت کصکش ننه جنده جوجه شاخ کص ننت رسماکیر  ابراهیم ته کص ننت کیرم تو کص ننه پریودت کص ننت تو دستمه کص خارت رو کیرمه کیر زعوس تو کص ننت مادر به خطا کون بچه تخم حروم بی پدر کص ننت ناموصا از سمت چپ تو کص ننت از سمت راست تو کص ننت کصکش ننه جنده جوجه شاخ کص ننت رسماکص خارت رسمن گاییدم کیرم تو کص خاندان نرمت کابوص نصلت بشم ولدم؟ کاری میکنم برگردی کص ننت کص مصت چص ول وا لش صگ نصل کص خارتتتت ننه حرومییی ولدم نشاخ حرصی شدم ننتو بگام؟چص ممبر حقیر کص ممبر کص ننت عمو جانی گایید  کیر  ابراهیم ته کص ننت کیرم تو کص ننه پریودت کص ننت تو دستمه کص خارت رو کیرمه کیر زعوس تو کص ننت مادر به خطا کون بچه تخم حروم بی پدر کص ننت ناموصا از سمت چپ تو کص ننت از سمت راست تو کص ننت کصکش ننه جنده جوجه شاخ کص ننت رسماکصننت بیناموس وایب گاییدن مادرت از گوش دادن به سیگار بعد از آمیزش جنسی بهتره ، ننت اینقدری که توی پورن دیده میشه و توی مانیتور موبایل مردم میبیننش باید بهش بدم تیوی گرل (استعاره) بیناموس کونی زاده ننت از سر عبدول آباد تا ۷۲ تن جندست کونی زاده ننت رو با عرق جوین میگام کصکش ولدزنا بهترین ورزش برای تقویت اندام گاییدن مادرته . ننت عقب موندست چون واقعا از عقب ، موندست . کونی زاده چاقوی زنجان رو میکنم تو کصننت در میارم اینقدر این کار رو میکنم که انگاری کصننت جا کاردی میمونه ننه جنده کصکش ولدزنا وقتی مادرت میخواد برا خودش شلوار بدوزه بجای متر باید از گیگا متر برای اندازه گیری دور کونش استفاده کنه . ننت خندق بلا میمونه چون هم بلاعه (شیطون) هم عامل بلایا هستش (جناس) کونی زاده ننت رو از قلاب قصابی آویزون میکنم بعد همونطور که رو هوا معلقه میگامش",
    "ننه کونی زمانی که من مادرجنده هایی مثل تورو ننشونو شهید میکردم تو, تو روبیکا داشتی فیلم سوپرای ننتو میفروختی",
    "كير تو روح ناپاک خواهرت", "کاربرات چهار دهنه نصب کردم روی مادرت الان میتونه ۴ تا کیرو همزمان بخوره",
    "شاید توهم قبلا مسئول بودی اخه این حجم از مادرجندگی تو انسانای عادی بعیده",
    "مادرت مال دولته‌ باید چاپید‌ قاپید", "واسه مامانت طلسم ناموس مگس گرفتم", "ناموس شفته گوه.",
    "با ذولفقاز‌ واسه مادرت خیار پوست کندم",
    "🔴ترامپ : یا با مادرت سر پول امشبش به توافق می‌رسیم، یا مجبوریم یه کار خیلی خشن بکنیم، مثل دفعه قبل. الان یه ناوگان کامل توی کسمادرته، شاید یکی دیگه هم در راه باشه.",
    "ارامگاه‌ مادرتو با گوه تِی کشیدم", "سیندرلا کفششو جاگذاشت مامان جندت شورتشو جا گذاشت خونمون",
    "خفه خارننه کونی ننه جیندرلا", "میشه مامانتو برام تیپاکس کنی لطفا؟", "ننت تو کون شاهزاده سرین",
    "ارّه برقی تو کون ناموصت", "کمد دیواری تو کص مادرت", "استخون مردهات تو کون زندهات ناموص کونی",
    "ناموص کونی تتپتپتتت نکن", "کصناموصت بالا باش یتیمت کنم",
    "از قدیم میگن با دم شیر بازی نکن میزنت الان میگن با دم من بازی نکن کیرمو در میارم میوفتم دنبال ننت",
    "میدونی دیگه کیرم مادرتو ارضا نمیکنه تصمیم گرفتم مادرتو ببرم تو کلیسا و صلیب بزرگ مسیحی هارو از زاویه عرض جا بدم تو کس مادرت بلکه یکم مادرت حشری شه و کیر تمام جونور های زنده جهان رو باهام فرو کنم تو کس مادرت انقدر مادرت جندس که چیزی دیگه برای توصیف جندگیش ندارم که بگم اخه کیرم تو سوراخ های دماغ مادرت چرا با من یکی به دو میکنی نمیگی میزنم مادرتو با کیر فلج میکنم",
    "با دستگاه تداخل الکترو مغناطیسی انواع و اقسام بمب های موشکی رو توی سرو کله خانوادت پیاده میکنم و حتی بعد از مرگشون هم تو یه چاه پر از اسید میندازشمون که حیوانات زمینی از نجسات خانوادت در امان باشن ازم دلخور نشو خودت نگاه کن مادرت ارزش نداره واسش قبر بکنن یا چند متر کفن رو صرف تن بی ارزش مادرت بکنن ",
    "با بیل و یه کلنگ میام تو کس مادرت یه چاله مرگ برای دشمنان ایران درست میکنم و هرکی قصد نزدکی به ایران رو داشت تو تله ای که تو کس مادرت درست کردم گیر میکنه و یواش یواش میمیره و حتی موشک های زمینی رو از سوراخ مادرت شلیک میکنم از سوراخ های بدن مادرت یه پایگاه جنگی درست میکنم میدونم موافقی ",
    "چقدر هوس گاییدن خاهرت تو فکرمه میدونی خاهرت اصلا قیافه میافه نداشت همش واسه منو رفقام ساک میزد و ما هم بهش نفری 50تومن میدادیم در واقع دلمون برای خاهرت میسوخت بقران حیف 50تومن بود خلاصه نگم برات که خاهرت این پولارو جمع کرد و رفت روی لباش ژل تزریق کرد و دماغشو که سه متر زود تر از خودش می اومد عمل کرد الان خودشو مریم مقدس میدونه جنده پولی!",
    "حیوون زبون نفهم عصبیم نکن این تکسای خزوخیل چیه میدی کیرم تو کفن پدرت کاری نکن با کلاش بی جواز بیام سراغ مادرت و ۳۰ تیر رو همزمان رگباری خالی کنم تو واژن بوگندو مادرت وقتی که مامانت مرد پزشک قانونی بگه به دلیل پارگی کس گشادش مرده و تو و اون داداشای بی غیرتت از دیه محروم بشید فکر کردی میزارم از جیبم سیر شین کیرممم نمیدم بخورین کس کثیف تموم مونث های خان��ادت",
    "ببین بچه یتیم کونی یواش یواش داری رو مغزم راه میری کاری نکن فیلم و عکس های مادرتو توی کانال های پورن تلگرام پخش کنم که باعث گناه کار شدن یه اومت میشه و ابروی اون خانواده بی اصالتت با خاک یکسان میشه میخای مادرتو بگام واست یه داداش کوچولو بیارم کور خوندی کس ننت جوری گشاده که من وقتی بخام بکنمش کیرم تو کسش گم میشه بالفرض که من کردمش وقتی ابمو ریختم تو کس لجن مادرت کس مامانت سوراخه ابم میپاشه بیرون خدایی حیف نیست من بخاطر ننه جندت کیرمو کثیف کنم!  ",
    "ننه ۳تا کیر همزمان خورد هتریک کرد", "ناموص گراز راه فراری نیست اینجا خدا منم"
]

FRIEND_ENEMY_TEXTS = [
    "عمت خوردم برا ناهار", "روزی دوبار عمت بعنوان برده جنسی گاییدم", "یادته اوندفعه انقد بهم دادی از حال رفتی",
    "عمت زیر کیرم مرد", "دوتا عمت جلوم لز کردن", "جوری میگامت ک از کصت آبکص‌ بچکه",
    "عمه هاتو بعنوان فاحشه همجا همراه خودم میبرم وقتی حوصلم سر رف بگامشون", "عمت زیر پل صراط گاییدم",
    "کشتی تو کونت", "کونت گاییدم دیگه کنترل نداری رو ریدنت‌ میرینی تو شلوارت", "کیر به اندازه برج ایفل تو کون عمت",
    "عمه فاحشه بدرد نخور", "عمت خر بگاد", "از عمت ایدز گرفتم", "کص عمت زگیل داره", "عمه کون",
    "تو که کیر نداری خاله فک میکنی کیره", "کص بچه کون صلواتی", "بدبخت بیچاره روزی دوبار میگامت"
]
MAX_FRIEND_ENEMY_REPLY = 1000

EXCHANGE_GROUP_LINK = "https://t.me/+2vC0QPDXAMI5MGVk"
EXCHANGE_BOT_USERNAME = "HashTrxCheckerBot"

msg_cache = OrderedDict()
MSG_CACHE_MAX = 5000

LANG_LIST = {
    "فارسی": "fa", "انگلیسی": "en", "عربی": "ar", "ترکی": "tr", "روسی": "ru", "فرانسوی": "fr", "آلمانی": "de",
    "اسپانیایی": "es", "ایتالیایی": "it", "چینی": "zh-CN", "ژاپنی": "ja", "کره‌ای": "ko", "هندی": "hi",
    "پرتغالی": "pt", "هلندی": "nl", "سوئدی": "sv", "ارمنی": "hy", "کردی": "ku", "اردو": "ur", "عبری": "iw",
    "یونانی": "el", "دانمارکی": "da", "فنلاندی": "fi", "نروژی": "no", "لهستانی": "pl", "رومانیایی": "ro",
    "مجاری": "hu", "چکی": "cs", "بلغاری": "bg", "اوکراینی": "uk", "صربی": "sr", "کروات": "hr", "اسلواکی": "sk",
    "اندونزیایی": "id", "مالایی": "ms", "تایلندی": "th", "ویتنامی": "vi", "فیلیپینی": "tl", "بنگالی": "bn",
    "تامیل": "ta", "تلگو": "te", "افغانی (پشتو)": "ps", "سوئیسی": "de", "اتریشی": "de", "بلژیکی": "nl"
}

def translate_text(text, target_lang="fa"):
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as ex:
        return f"❌ خطا در ترجمه: {ex}"

async def search_music(query):
    try:
        r = requests.get(f"https://api.deezer.com/search?q={quote(query)}&limit=5", timeout=10)
        if r.status_code == 200:
            tracks = r.json().get("data", [])[:5]
            if tracks:
                return [{"title": tr.get("title","?"), "artist": tr.get("artist",{}).get("name","?")} for tr in tracks]
    except: pass
    try:
        r = requests.get(f"https://itunes.apple.com/search?term={quote(query)}&media=music&limit=5", timeout=10)
        if r.status_code == 200:
            tracks = r.json().get("results", [])[:5]
            if tracks:
                return [{"title": tr.get("trackName","?"), "artist": tr.get("artistName","?")} for tr in tracks]
    except: pass
    return None

async def do_broadcast(source_msg, kind):
    count = 0; failed = 0
    try:
        async for dialog in client.iter_dialogs():
            if kind == "group" and not dialog.is_group: continue
            if kind == "channel" and (not dialog.is_channel or dialog.is_group): continue
            if kind == "private" and not dialog.is_user: continue
            try:
                await source_msg.forward_to(dialog.id)
                count += 1
                await asyncio.sleep(1.0)
            except FloodWaitError as fw: await asyncio.sleep(fw.seconds + 3)
            except: failed += 1
    except Exception as ex: print(f"Broadcast error: {ex}")
    return count, failed

# =========================================
# تسک‌های پس‌زمینه
# =========================================
async def clock_loop():
    last_time = None
    while True:
        try:
            if data["clock_on"]:
                tehran_tz = pytz.timezone('Asia/Tehran')
                current_time = dt.now(tehran_tz).strftime("%H:%M")
                if current_time != last_time:
                    for acc in accounts:
                        try:
                            if await acc.is_user_authorized():
                                await acc(UpdateProfileRequest(last_name=font_time(current_time)))
                        except: pass
                    last_time = current_time
        except FloodWaitError as e: await asyncio.sleep(e.seconds)
        except: pass
        await asyncio.sleep(1)

async def timer_loop():
    while True:
        try:
            now = dt.now().timestamp()
            for timer_name, end_time in list(data["timers"].items()):
                if now >= end_time:
                    await client.send_message("me", f"⏰ **تایمر تمام شد!**\nنام: `{timer_name}`")
                    del data["timers"][timer_name]; save()
        except: pass
        await asyncio.sleep(1)

# =========================================
# پنل اصلی و تنظیمات (دکمه‌های کوچک ۳ تایی)
# =========================================
ADMIN_ID = None

def get_main_panel_buttons():
    return [
        [Button.inline("👤 پروفایل من", b"profile_menu"), Button.inline("⚙ تنظیمات", b"s_settings")],
        [Button.url("👨‍💻 سازنده", "https://t.me/iliya_fakhr")]
    ]

def get_settings_buttons():
    # دکمه‌ها را ۳ تایی چیدم تا کوچیک تر بشن
    return [
        [Button.inline("⏰ ساعت", b"s_clock"), Button.inline("⚔️ دشمن", b"s_enemy"), Button.inline("🤫 سایلنت", b"s_silent")],
        [Button.inline("👥 دوست دشمن", b"s_fe"), Button.inline("📤 اسپم", b"s_spam"), Button.inline("📟 ماشین حساب", b"s_calc")],
        [Button.inline("💾 مدیا", b"s_media"), Button.inline("ℹ️ اطلاعات", b"s_info"), Button.inline("🏓 پینگ", b"s_ping")],
        [Button.inline("🌐 ابزارها", b"s_tools"), Button.inline("📥 دانلودر", b"s_dl"), Button.inline("👥 مدیریت", b"s_manage")],
        [Button.inline("🎮 سرگرمی", b"s_fun"), Button.inline("📋 قوانین", b"s_rules"), Button.inline("💾 سیو زمان", b"s_timed")],
        [Button.inline("📝 سیو پیام", b"s_savemsg"), Button.inline("🤵 منشی", b"s_secretary"), Button.inline("🎵 سرچ آهنگ", b"s_music")],
        [Button.inline("📤 تبچی", b"s_broadcast"), Button.inline("🔤 حالت متن", b"s_textmode"), Button.inline("⚡ اکشن", b"s_action")],
        [Button.inline("🔒 قفل‌ها", b"s_locks"), Button.inline("🌍 ترجمه", b"s_translate"), Button.inline("👀 سین خودکار", b"s_autoseen")],
        [Button.inline("😂 ریکشن", b"s_reaction"), Button.inline("📸 اسکرین", b"s_screen"), Button.inline("💬 کامنت اول", b"s_firstcomment")],
        [Button.inline("🚪 عضویت اجباری", b"s_forcejoin"), Button.inline("👤 کپی پروفایل", b"s_copyprofile")],
        [Button.inline("🔙 بازگشت به پنل اصلی", b"main_menu")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.respond("📌 **پـنـل مـدیـریـت**\n\n👇 یک گزینه را انتخاب کنید:", buttons=get_main_panel_buttons())

@bot.on(events.InlineQuery)
async def inline_handler(event):
    if event.sender_id != ADMIN_ID: return
    builder = event.builder
    try:
        if event.text == "/panel":
            result = builder.article(
                title="پنل مدیریت", description="پنل مدیریت ربات",
                text="📌 **پـنـل مـدیـریـت**\n\n👇 یک گزینه را انتخاب کنید:",
                buttons=get_main_panel_buttons()
            )
            await event.answer([result], cache_time=0)
        elif event.text == "/enemy_panel":
            buttons = [[Button.inline("⚔️ دشمن", b"enemy_btn"), Button.inline("👥 دوست دشمن", b"fe_btn")]]
            result = builder.article(
                title="انتخاب لیست", description="دشمن یا دوست دشمن؟",
                text="⚔️ **کدوم لیست اضافه بشه؟**", buttons=buttons
            )
            await event.answer([result], cache_time=0)
    except Exception as err:
        print(f"⚠️ Inline Error: {err}")

@bot.on(events.CallbackQuery())
async def panel_callback(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("⛔ دسترسی ندارید", alert=True); return
    d = event.data.decode("utf-8")
    
    try:
        if d == "main_menu":
            await event.edit("📌 **پـنـل مـدیـریـت**\n\n👇 یک گزینه را انتخاب کنید:", buttons=get_main_panel_buttons())
            await event.answer(); return
            
        if d == "enemy_btn":
            target_id = data.get("last_target_id")
            if target_id and target_id not in data["enemy"]:
                data["enemy"].append(target_id); save()
                msg = f"✅ کاربر `{target_id}` به لیست دشمن اضافه شد."
            elif target_id: msg = f"⚠️ کاربر `{target_id}` قبلاً در لیست دشمن هست."
            else: msg = "❌ خطا! آیدی کاربر پیدا نشد."
            await event.edit(msg, buttons=[Button.inline("🔙 بازگشت", b"main_menu")]); return
        elif d == "fe_btn":
            target_id = data.get("last_target_id")
            if target_id and target_id not in data["friend_enemy"]:
                data["friend_enemy"].append(target_id)
                data["friend_enemy_count"][str(target_id)] = 0; save()
                msg = f"✅ کاربر `{target_id}` به لیست دوست دشمن اضافه شد."
            elif target_id: msg = f"⚠️ کاربر `{target_id}` قبلاً در لیست دوست دشمن هست."
            else: msg = "❌ خطا! آیدی کاربر پیدا نشد."
            await event.edit(msg, buttons=[Button.inline("🔙 بازگشت", b"main_menu")]); return

        if d == "profile_menu":
            me = await client.get_me()
            full_me = await client(GetFullUserRequest(me.id))
            bio = full_me.full_user.about or "ندارد"
            name = f"{me.first_name or ''} {me.last_name or ''}".strip()
            username = f"@{me.username}" if me.username else "ندارد"
            phone = me.phone or "مخفی"
            txt = (f"👤 **پروفایل شما:**\n\n• **نام:** {name}\n• **یوزرنیم:** {username}\n"
                   f"• **آیدی:** `{me.id}`\n• **شماره:** {phone}\n• **بیوگرافی:** {bio}\n\n**جهت ویرایش:**")
            btns = [
                [Button.inline("✏️ نام", b"p_name"), Button.inline("✏️ بیو", b"p_bio"), Button.inline("🖼 عکس", b"p_pic")],
                [Button.inline("🗑 حذف عکس", b"p_delpic"), Button.inline("🔙 بازگشت", b"main_menu")]
            ]
            await event.edit(txt, buttons=btns)
        elif d == "p_name": await event.edit("✏️ **دستور:**\n\n`setname [نام جدید]`", buttons=[Button.inline("🔙 بازگشت", b"profile_menu")])
        elif d == "p_bio": await event.edit("✏️ **دستور:**\n\n`setbio [متن بیو]`", buttons=[Button.inline("🔙 بازگشت", b"profile_menu")])
        elif d == "p_pic": await event.edit("🖼 **دستور:**\n\n`setpic` (با ریپلای روی عکس)", buttons=[Button.inline("🔙 بازگشت", b"profile_menu")])
        elif d == "p_delpic":
            await client(DeletePhotosRequest(await client.get_profile_photos("me")))
            await event.edit("🗑 **عکس پروفایل حذف شد.**", buttons=[Button.inline("🔙 بازگشت", b"profile_menu")])

        elif d == "s_settings":
            await event.edit("⚙ **تـنـظـیـمـات دسـتـورات**\n\nیک دسته را انتخاب کنید:", buttons=get_settings_buttons())
            
        elif d.startswith("s_"):
            BACK_SETTINGS = [Button.inline("🔙 بازگشت به تنظیمات", b"s_settings")]
            if d == "s_clock": await event.edit("⏰ **ساعت**\n\n• `ساعت روشن`\n• `ساعت خاموش`\n• `فونت ها`\n• `ست فونت [شماره]`", buttons=BACK_SETTINGS)
            elif d == "s_enemy": await event.edit("⚔️ **دشمن**\n\n• `دشمن` (با ریپلای)\n• `حذف دشمن`\n• `لیست دشمن`\n• `پاکسازی لیست دشمن`", buttons=BACK_SETTINGS)
            elif d == "s_silent": await event.edit("🤫 **سایلنت**\n\n• `سکوت` (با ریپلای)\n• `حذف سکوت`\n• `لیست سکوت`\n• `پاکسازی لیست سکوت`", buttons=BACK_SETTINGS)
            elif d == "s_fe": await event.edit("👥 **دوست دشمن**\n\n• `تنظیم دوست دشمن` (ریپلای)\n• `حذف دوست دشمن`\n• `لیست دوست دشمن`\n• `پاکسازی لیست دوست دشمن`", buttons=BACK_SETTINGS)
            elif d == "s_spam": await event.edit("📤 **اسپم**\n\n• `اسپم [عدد]` (ریپلای)\n• `حذف پیام [عدد]`\n• `حذف پیام` (ریپلای)", buttons=BACK_SETTINGS)
            elif d == "s_calc": await event.edit("📟 **ماشین حساب**\n\n• فرمول با نقطه شروع شود.\n• مثال: `.2+2`", buttons=BACK_SETTINGS)
            elif d == "s_media": await event.edit("💾 **مدیا**\n\n• `ذخیره` (ریپلای)\n• `Lmedia` (لیست)\n• `Smedia [اسم]`", buttons=BACK_SETTINGS)
            elif d == "s_info": await event.edit("ℹ️ **اطلاعات**\n\n• `اطلاعات` (ریپلای)\n• `اطلاعات [@یوزرنیم]`", buttons=BACK_SETTINGS)
            elif d == "s_ping": await event.edit("🏓 **پینگ**\n\n• `پینگ`\n• `رم`", buttons=BACK_SETTINGS)
            elif d == "s_tools": await event.edit("🌐 **ابزارها**\n\n• `تاریخ`\n• `هوا [شهر]`\n• `آیپی [IP]`\n• `نرخ ارز`\n• `سرچ اهنگ [متن]`", buttons=BACK_SETTINGS)
            elif d == "s_dl": await event.edit("📥 **دانلودر**\n\n• `یوتیوب [لینک]`\n• `دانلود فایل [لینک]`", buttons=BACK_SETTINGS)
            elif d == "s_manage": await event.edit("👥 **مدیریت**\n\n• `تگ`\n• `بن [یوزر]`\n• `ادمین` (ریپلای)\n• `عزل` (ریپلای)\n• `پاکسازی [متن]`\n• `حذف اخیر [عدد]`\n• `سین زدن همه`", buttons=BACK_SETTINGS)
            elif d == "s_fun": await event.edit("🎮 **سرگرمی**\n\n• `ویس [متن]`\n• `افکت [متن]`\n• `کیوآر` (ریپلای)\n• `تلویزیون`\n• `تایمر [نام]`\n• `لیست تایمر`", buttons=BACK_SETTINGS)
            elif d == "s_rules": await event.edit("📋 **قوانین**\n\nاین سلف جهت استفاده شخصی می‌باشد.", buttons=BACK_SETTINGS)
            elif d == "s_timed": await event.edit("💾 **سیو زمان دار**\n\n• `سیو زمان دار روشن`\n• `سیو زمان دار خاموش`", buttons=BACK_SETTINGS)
            elif d == "s_savemsg": await event.edit("📝 **سیو پیام**\n\n• `سیو پیام روشن`\n• `سیو پیام خاموش`", buttons=BACK_SETTINGS)
            elif d == "s_secretary": await event.edit("🤵 **منشی**\n\n• `حالت منشی روشن`\n• `حالت منشی خاموش`\n• `متن منشی`\n• `متن منشی [متن]`", buttons=BACK_SETTINGS)
            elif d == "s_music": await event.edit("🎵 **سرچ آهنگ**\n\n• `سرچ اهنگ [متن]`", buttons=BACK_SETTINGS)
            elif d == "s_broadcast": await event.edit("📤 **تبچی**\n\nریپلای کن و بزن:\n• `ارسال همه`\n• `ارسال گپ`\n• `ارسال چنل`\n• `ارسال پیوی`", buttons=BACK_SETTINGS)
            elif d == "s_textmode": await event.edit("🔤 **حالت متن**\n\n• `حالت متن` (منو)\n• `حالت متن خاموش`", buttons=BACK_SETTINGS)
            elif d == "s_action": await event.edit("⚡ **اکشن**\n\n• `اکشن روشن`\n• `اکشن خاموش`\n\n⚠️ حالت متن باید خاموش باشه.", buttons=BACK_SETTINGS)
            elif d == "s_locks": await event.edit("🔒 **قفل ها**\n\n• `قفل ها` (لیست)\n• `قفل همه`\n• `پاکسازی قفل ها`", buttons=BACK_SETTINGS)
            elif d == "s_translate": await event.edit("🌍 **ترجمه**\n\n• `ترجمه` (ریپلای) → فارسی\n• `ترجمه [زبان]` (ریپلای)\n• `لیست ترجمه`", buttons=BACK_SETTINGS)
            elif d == "s_autoseen": await event.edit("👀 **سین خودکار**\n\n• `سین خودکار روشن`\n• `سین خودکار خاموش`", buttons=BACK_SETTINGS)
            elif d == "s_reaction": await event.edit("😂 **ریکشن**\n\n• `ریکشن 😂` (ریپلای)\n• `لیست ریکشن`\n• `پاکسازی لیست ریکشن`", buttons=BACK_SETTINGS)
            elif d == "s_screen": await event.edit("📸 **اسکرین**\n\n• `اسکرین`", buttons=BACK_SETTINGS)
            elif d == "s_firstcomment": await event.edit("💬 **کامنت اول**\n\n• `تنظیم کامنت اول @USERNAME`\n• `کامنت اول روشن`\n• `کامنت اول خاموش`\n• `متن کامنت اول [متن]`", buttons=BACK_SETTINGS)
            elif d == "s_forcejoin": await event.edit("🚪 **عضویت اجباری**\n\n• `تنظیم عضویت اجباری @USERNAME`\n• `عضویت اجباری پیوی روشن`\n• `عضویت اجباری پیوی خاموش`\n• `متن عضویت اجباری [متن]`", buttons=BACK_SETTINGS)
            elif d == "s_copyprofile": await event.edit("👤 **کپی پروفایل**\n\n• `کپی پروفایل` (ریپلای)\n• `ذخیره پروفایل من`\n• `پروفایل پیشفرض`", buttons=BACK_SETTINGS)
        
        await event.answer()
    except Exception as err:
        pass

# =========================================
# قابلیت‌های پس‌زمینه
# =========================================
@client.on(events.NewMessage(incoming=True))
async def cache_incoming(e):
    if not data.get("save_msg_on"): return
    try:
        msg_cache[(e.chat_id, e.id)] = {
            "text": e.text or "", "sender_id": e.sender_id,
            "sender_name": (e.sender.first_name if e.sender else "?"), "chat_id": e.chat_id,
        }
        while len(msg_cache) > MSG_CACHE_MAX: msg_cache.popitem(last=False)
    except: pass

@client.on(events.NewMessage(incoming=True))
async def save_timed_media(e):
    if not data.get("save_timed_on"): return
    if not e.media: return
    ttl = getattr(e.media, 'ttl_seconds', None)
    if not ttl: return
    try:
        path = await e.download_media(file="downloads/")
        if path:
            try: await client.send_file("me", path, force_document=False, caption=f"⏰ از {e.sender_id}")
            except: await client.send_file("me", path, caption=f"⏰ از {e.sender_id}")
            try: os.remove(path)
            except: pass
    except: pass

@client.on(events.MessageEdited(incoming=True))
async def save_edited(e):
    if not data.get("save_msg_on") or not e.text: return
    try:
        sender_name = getattr(e.sender, 'first_name', '?') if e.sender else '?'
        txt = (f"<b>✏️ پیام ویرایش شده</b>\n\n<b>👤 فرستنده:</b> <code>{sender_name}</code>\n"
               f"<b>🆔 آیدی:</b> <code>{e.sender_id}</code>\n<b>💬 چت:</b> <code>{e.chat_id}</code>\n\n"
               f"<b>📝 متن جدید:</b>\n<code>{e.text}</code>")
        await client.send_message("me", txt, parse_mode="html")
    except: pass

@client.on(events.MessageDeleted())
async def save_deleted(e):
    if not data.get("save_msg_on"): return
    found = []
    if e.chat_id:
        for mid in e.deleted_ids:
            key = (e.chat_id, mid)
            if key in msg_cache: found.append(msg_cache.pop(key))
    else:
        for mid in e.deleted_ids:
            for key in list(msg_cache.keys()):
                if key[1] == mid: found.append(msg_cache.pop(key)); break
    for info in found:
        try:
            txt = (f"<b>🗑 پیام حذف شده</b>\n\n<b>👤 فرستنده:</b> <code>{info['sender_name']}</code>\n"
                   f"<b>🆔 آیدی:</b> <code>{info['sender_id']}</code>\n<b>💬 چت:</b> <code>{info['chat_id']}</code>\n\n"
                   f"<b>📝 متن:</b>\n<code>{info['text']}</code>")
            await client.send_message("me", txt, parse_mode="html")
        except: pass

@client.on(events.NewMessage(incoming=True))
async def auto_seen(e):
    if not data.get("auto_seen_on") or not e.is_private: return
    try: await client.send_read_acknowledge(e.chat_id, max_id=e.id)
    except: pass

def detect_media_type(msg):
    if not msg.media: return None
    if isinstance(msg.media, MessageMediaPhoto): return "photo"
    if isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document
        if doc is None: return None
        mime = doc.mime_type or ""
        attrs = doc.attributes or []
        if mime == "video/mp4" and any(getattr(a,'round_message',False) for a in attrs if hasattr(a,'round_message')): return "gif"
        if mime.startswith("image/gif"): return "gif"
        if mime.startswith("video/"): return "video"
        if mime.startswith("audio/"):
            if any(getattr(a, "voice", False) for a in attrs if hasattr(a, "voice")): return "voice"
            return "audio"
        if "sticker" in mime or any(a.__class__.__name__ == "DocumentAttributeSticker" for a in attrs): return "sticker"
        return "file"
    return None

@client.on(events.NewMessage(incoming=True))
async def locks_handler(e):
    if not e.is_private: return
    locked = data.get("locks", [])
    if not locked: return
    mtype = detect_media_type(e)
    if mtype and mtype in locked:
        try: await e.delete()
        except: pass

@client.on(events.NewMessage(incoming=True))
async def reaction_handler(e):
    reactions = data.get("reactions", {})
    if not reactions: return
    if str(e.sender_id) in reactions:
        emoji = reactions[str(e.sender_id)]
        try:
            await client(SendReactionRequest(
                peer=e.chat_id, msg_id=e.id,
                reaction=[ReactionEmoji(emoticon=emoji)]
            ))
        except: pass

async def check_force_join(user_id):
    channel = data.get("force_join_channel")
    if not channel: return True, None
    try:
        channel_entity = await client.get_entity(channel)
        try:
            await client.get_permissions(channel_entity, user_id)
            return True, channel_entity
        except UserNotParticipantError:
            return False, channel_entity
        except Exception:
            return False, channel_entity
    except Exception as ex:
        return True, None

@client.on(events.NewMessage(incoming=True))
async def force_join_handler(e):
    if not data.get("force_join_on"): return
    if not e.is_private: return
    if e.out: return
    me = await client.get_me()
    if e.sender_id == me.id: return
    ok, channel_entity = await check_force_join(e.sender_id)
    if not ok and channel_entity:
        try:
            username = getattr(channel_entity, 'username', None)
            link = f"https://t.me/{username}" if username else "لینک در دسترس نیست"
            await e.reply(f"{data['force_join_text']}\n\n{link}")
        except: pass

@client.on(events.NewMessage(incoming=True))
async def first_comment_handler(e):
    if not data.get("first_comment_on"): return
    targets = data.get("first_comment_targets", [])
    if not targets: return
    try:
        chat = await e.get_chat()
        if not isinstance(chat, Channel): return
        if chat.id not in targets and not (chat.username and chat.username in targets): return
        if not e.post: return
        try:
            await client.send_message(e.chat_id, data["first_comment_text"], reply_to=e.id)
        except Exception:
            try:
                discussion = (await client(GetFullChannelRequest(e.chat_id))).full_chat.linked_chat_id
                if discussion:
                    await client.send_message(discussion, data["first_comment_text"], reply_to=e.id)
            except: pass
    except: pass

async def action_animate(chat_id, text):
    try:
        sent = await client.send_message(chat_id, "…")
        current = ""
        for ch in text:
            current += ch
            try: await sent.edit(current)
            except: pass
            await asyncio.sleep(0.3)
        return sent
    except: return None

# =========================================
# دستورات سلف
# =========================================
@client.on(events.NewMessage(outgoing=True))
async def commands(e):
    t = e.raw_text
    if not t: return

    if t == "پنل":
        try:
            await asyncio.sleep(0.3)
            result = await client.inline_query(BOT_USERNAME, "/panel")
            if result:
                await result[0].click(e.chat_id)
                await e.delete()
        except: pass
        return

    if t.startswith("setname "):
        new_name = t.split(" ", 1)[1]
        await client(UpdateProfileRequest(first_name=new_name))
        await e.edit(f"✅ **نام شما به `{new_name}` تغییر کرد.**"); return

    if t.startswith("setbio "):
        new_bio = t.split(" ", 1)[1]
        await client(UpdateProfileRequest(about=new_bio))
        await e.edit(f"✅ **بیو شما تغییر کرد.**"); return

    if t == "setpic" and e.is_reply:
        r = await e.get_reply_message()
        if r.photo:
            path = await r.download_media()
            await client(UploadProfilePhotoRequest(file=await client.upload_file(path)))
            await e.edit("✅ **عکس پروفایل تغییر کرد.**")
            os.remove(path)
        else: await e.edit("❌ **پیام ریپلای شده عکس نیست.**")
        return

    if t == "پینگ":
        s = dt.now(); await client.get_me()
        await e.edit(f"🏓 **Ping:** `{(dt.now() - s).total_seconds():.3f}s`"); return

    if t == "رم":
        try:
            with open('/proc/meminfo') as f: l = f.readlines()
            tot, free = int(l[0].split()[1]), int(l[1].split()[1])
            await e.edit(f"💻 **رم:** `{((tot-free)/tot)*100:.1f}%` (آزاد: {free//1024} MB)")
        except: await e.edit("❌ خطا در خواندن رم")
        return

    if t == "ساعت روشن":
        data["clock_on"] = True; save()
        tehran_tz = pytz.timezone('Asia/Tehran')
        await client(UpdateProfileRequest(last_name=font_time(dt.now(tehran_tz).strftime("%H:%M"))))
        await e.edit("⏰ **ساعت روشن شد (به وقت تهران)**"); return

    if t == "ساعت خاموش":
        data["clock_on"] = False; save()
        await client(UpdateProfileRequest(last_name=""))
        await e.edit("⛔ **ساعت خاموش شد**"); return

    if t == "فونت ها":
        txt = "🔢 **فونت ها**\n\n"
        for k in FONTS: txt += f"**{k}** ➜ {''.join(FONTS[k][int(c)] if c.isdigit() else c for c in '12:34')}\n"
        await e.edit(txt); return
    if t.startswith("ست فونت"):
        try: data["clock_font"] = t.split()[2]; save(); await e.edit("✅ فونت ست شد")
        except: await e.edit("❌ مثال: `ست فونت 2`")
        return

    if t == "سیو زمان دار روشن": data["save_timed_on"] = True; save(); await e.edit("✅ **سیو زمان‌دار روشن شد**"); return
    if t == "سیو زمان دار خاموش": data["save_timed_on"] = False; save(); await e.edit("❌ **سیو زمان‌دار خاموش شد**"); return
    if t == "سیو پیام روشن": data["save_msg_on"] = True; save(); await e.edit("✅ **سیو پیام روشن شد**"); return
    if t == "سیو پیام خاموش": data["save_msg_on"] = False; save(); await e.edit("❌ **سیو پیام خاموش شد**"); return

    if t == "حالت منشی روشن":
        data["secretary_on"] = True; save()
        await e.edit(f"✅ **حالت منشی روشن شد**\n\n📝 متن:\n`{data['secretary_text']}`"); return
    if t == "حالت منشی خاموش":
        data["secretary_on"] = False; save()
        await e.edit("❌ **حالت منشی خاموش شد**"); return
    if t == "متن منشی":
        await e.edit(f"📝 **متن فعلی:**\n\n`{data['secretary_text']}`\n\n**تغییر:**\n`متن منشی [متن جدید]`"); return
    if t.startswith("متن منشی "):
        new_text = t.split(" ", 2)[2]
        data["secretary_text"] = new_text; save()
        await e.edit(f"✅ **متن منشی ست شد:**\n\n`{new_text}`"); return

    if t.startswith("سرچ اهنگ "):
        query = t.split(" ", 2)[2]
        await e.edit("🔍 در حال جستجو...")
        results = await search_music(query)
        if results:
            txt = f"🎵 **نتایج Spotify:** `{query}`\n\n"
            for i, r in enumerate(results, 1):
                sq = quote(f"{r['title']} {r['artist']}")
                txt += f"{i}. [{r['title']} - {r['artist']}](https://open.spotify.com/search/{sq})\n"
            await e.edit(txt, link_preview=False)
        else: await e.edit("❌ نتیجه‌ای یافت نشد")
        return

    if t in ["ارسال همه", "ارسال گپ", "ارسال چنل", "ارسال پیوی"] and e.is_reply:
        kind_map = {"ارسال همه": "all", "ارسال گپ": "group", "ارسال چنل": "channel", "ارسال پیوی": "private"}
        r = await e.get_reply_message()
        await e.edit("📤 در حال ارسال...")
        count, failed = await do_broadcast(r, kind_map[t])
        await e.edit(f"✅ **ارسال شد به {count} چت**\n❌ خطا: {failed}")
        return

    if t == "حالت متن":
        txt = ("🔤 **حالت‌های متن**\n\n"
               "• `حالت متن بولد` → **متن بولد**\n"
               "• `حالت متن ایتالیک` → *متن ایتالیک*\n"
               "• `حالت متن اسپویلر` → ||اسپویلر||\n"
               "• `حالت متن زیرخط` → __متن__\n"
               "• `حالت متن خط‌خورده` → ~~متن~~\n"
               "• `حالت متن کد` → `متن`\n"
               "• `حالت متن خاموش`\n\n"
               "⚠️ وقتی روشنه، پیام‌هات خودکار ادیت می‌شن.")
        await e.edit(txt, link_preview=False); return
    if t == "حالت متن بولد": data["text_mode"]="bold"; save(); await e.edit("✅ **حالت متن: بولد**"); return
    if t == "حالت متن ایتالیک": data["text_mode"]="italic"; save(); await e.edit("✅ **حالت متن: ایتالیک**"); return
    if t == "حالت متن اسپویلر": data["text_mode"]="spoiler"; save(); await e.edit("✅ **حالت متن: اسپویلر**"); return
    if t == "حالت متن زیرخط": data["text_mode"]="underline"; save(); await e.edit("✅ **حالت متن: زیرخط**"); return
    if t == "حالت متن خط‌خورده": data["text_mode"]="strike"; save(); await e.edit("✅ **حالت متن: خط‌خورده**"); return
    if t == "حالت متن کد": data["text_mode"]="code"; save(); await e.edit("✅ **حالت متن: کد**"); return
    if t == "حالت متن خاموش": data["text_mode"]=None; save(); await e.edit("❌ **حالت متن خاموش شد**"); return

    if t == "اکشن روشن":
        if data.get("text_mode"):
            await e.edit("⚠️ **اول حالت متن رو خاموش کن** (`حالت متن خاموش`)")
            return
        data["action_on"] = True; save()
        await e.edit("✅ **اکشن روشن شد** — پیام‌هات حروف به حروف تایپ می‌شن."); return
    if t == "اکشن خاموش":
        data["action_on"] = False; save()
        await e.edit("❌ **اکشن خاموش شد**"); return

    if t == "قفل ها":
        locks = data.get("locks", [])
        txt = "🔒 **قفل‌های فعلی:**\n"
        if not locks: txt += "\n_هیچ قفلی فعال نیست._"
        else:
            for lk in locks: txt += f"• `{lk}`\n"
        txt += "\n\n**فعال‌سازی:**\n`قفل پیام روشن`\n`قفل گیف روشن`\n`قفل استیکر روشن`\n`قفل اهنگ روشن`\n`قفل عکس روشن`\n`قفل ویدیو روشن`\n`قفل ویس روشن`\n`قفل فایل روشن`\n`قفل همه`\n`پاکسازی قفل ها`"
        await e.edit(txt, link_preview=False); return
    lock_map = {
        "قفل پیام": "text", "قفل گیف": "gif", "قفل استیکر": "sticker",
        "قفل اهنگ": "audio", "قفل عکس": "photo", "قفل ویدیو": "video",
        "قفل ویس": "voice", "قفل فایل": "file",
    }
    for prefix, lk in lock_map.items():
        if t == f"{prefix} روشن":
            if lk not in data["locks"]: data["locks"].append(lk)
            save(); await e.edit(f"🔒 **{prefix} روشن شد**"); return
        if t == f"{prefix} خاموش":
            if lk in data["locks"]: data["locks"].remove(lk)
            save(); await e.edit(f"🔓 **{prefix} خاموش شد**"); return
    if t == "قفل همه":
        data["locks"] = ["text","gif","sticker","audio","photo","video","voice","file"]; save()
        await e.edit("🔒 **همه قفل‌ها فعال شد**"); return
    if t == "پاکسازی قفل ها":
        data["locks"] = []; save()
        await e.edit("🔓 **همه قفل‌ها پاک شد**"); return

    if t == "لیست ترجمه":
        txt = "🌍 **زبان‌های موجود:**\n\n"
        for name, code in LANG_LIST.items():
            txt += f"• `{name}` ({code})\n"
        txt += "\n**مثال:** `ترجمه اسپانیایی`"
        await e.edit(txt, link_preview=False); return
    if t.startswith("ترجمه") and e.is_reply:
        r = await e.get_reply_message()
        if not r or not r.text:
            await e.edit("❌ پیام متنی نیست"); return
        parts = t.split(" ", 1)
        target_lang = "fa"
        if len(parts) > 1:
            lang_name = parts[1].strip()
            if lang_name in LANG_LIST:
                target_lang = LANG_LIST[lang_name]
            else:
                await e.edit(f"❌ زبان `{lang_name}` پشتیبانی نمی‌شه. `لیست ترجمه` رو بزن."); return
        await e.edit("🌍 در حال ترجمه...")
        translated = translate_text(r.text, target_lang)
        await e.edit(f"🌍 **ترجمه ({LANG_LIST.get(target_lang, target_lang)}):**\n\n`{translated}`"); return

    if t == "سین خودکار روشن": data["auto_seen_on"] = True; save(); await e.edit("✅ **سین خودکار روشن شد**"); return
    if t == "سین خودکار خاموش": data["auto_seen_on"] = False; save(); await e.edit("❌ **سین خودکار خاموش شد**"); return

    if t.startswith("ریکشن ") and e.is_reply:
        emoji = t.split(" ", 1)[1].strip()
        r = await e.get_reply_message()
        uid = r.sender_id
        data["reactions"][str(uid)] = emoji; save()
        await e.edit(f"✅ **ریکشن `{emoji}` برای `{uid}` ثبت شد.**"); return
    if t == "لیست ریکشن":
        reactions = data.get("reactions", {})
        if not reactions: await e.edit("📭 لیست خالی")
        else:
            txt = "😂 **لیست ریکشن:**\n"
            for uid, em in reactions.items(): txt += f"• `{uid}` → `{em}`\n"
            await e.edit(txt)
        return
    if t == "پاکسازی لیست ریکشن":
        data["reactions"] = {}; save()
        await e.edit("🗑 **لیست ریکشن پاک شد**"); return

    if t == "اسکرین":
        await e.edit("📸 در حال گرفتن اسکرین...")
        try:
            msgs = await client.get_messages(e.chat_id, limit=20)
            img = Image.new("RGB", (1000, 100 + len(msgs)*40), color=(30,30,30))
            draw = ImageDraw.Draw(img)
            try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            except: font = ImageFont.load_default()
            y = 30
            draw.text((30, 10), f"Chat: {e.chat_id}", fill=(200,200,200), font=font)
            for m in reversed(msgs):
                sender = getattr(m.sender, 'first_name', str(m.sender_id)) if m.sender else "?"
                text = (m.text or "[media]")[:80]
                draw.text((30, y), f"{sender}: {text}", fill=(255,255,255), font=font)
                y += 40
            path = f"downloads/screen_{int(dt.now().timestamp())}.png"
            img.save(path)
            await client.send_file(e.chat_id, path)
            await e.delete(); os.remove(path)
        except Exception as ex: await e.edit(f"❌ خطا: {ex}")
        return

    if t.startswith("تنظیم کامنت اول "):
        raw = t.split(" ", 3)[3].strip().lstrip("@")
        try:
            entity = await client.get_entity(raw)
            if entity.id not in data["first_comment_targets"]:
                data["first_comment_targets"].append(entity.id); save()
            await e.edit(f"✅ **کانال `{raw}` به کامنت اول اضافه شد.**")
        except Exception as ex: await e.edit(f"❌ خطا: {ex}")
        return
    if t == "کامنت اول روشن": data["first_comment_on"] = True; save(); await e.edit("✅ **کامنت اول روشن شد**"); return
    if t == "کامنت اول خاموش": data["first_comment_on"] = False; save(); await e.edit("❌ **کامنت اول خاموش شد**"); return
    if t == "متن کامنت اول":
        await e.edit(f"💬 **متن فعلی:**\n\n`{data['first_comment_text']}`\n\n**تغییر:**\n`متن کامنت اول [متن]`"); return
    if t.startswith("متن کامنت اول "):
        new_text = t.split(" ", 3)[3]
        data["first_comment_text"] = new_text; save()
        await e.edit(f"✅ **متن کامنت اول ست شد:**\n\n`{new_text}`"); return

    if t.startswith("تنظیم عضویت اجباری "):
        raw = t.split(" ", 3)[3].strip().lstrip("@")
        try:
            entity = await client.get_entity(raw)
            data["force_join_channel"] = entity.id; save()
            await e.edit(f"✅ **کانال `{raw}` به عضویت اجباری اضافه شد.**")
        except Exception as ex: await e.edit(f"❌ خطا: {ex}")
        return
    if t == "عضویت اجباری پیوی روشن": data["force_join_on"] = True; save(); await e.edit("✅ **عضویت اجباری روشن شد**"); return
    if t == "عضویت اجباری پیوی خاموش": data["force_join_on"] = False; save(); await e.edit("❌ **عضویت اجباری خاموش شد**"); return
    if t == "متن عضویت اجباری":
        await e.edit(f"📝 **متن فعلی:**\n\n`{data['force_join_text']}`\n\n**تغییر:**\n`متن عضویت اجباری [متن]`"); return
    if t.startswith("متن عضویت اجباری "):
        new_text = t.split(" ", 4)[4]
        data["force_join_text"] = new_text; save()
        await e.edit(f"✅ **متن عضویت اجباری ست شد:**\n\n`{new_text}`"); return

    if t == "کپی پروفایل" and e.is_reply:
        await e.edit("👤 در حال کپی پروفایل...")
        try:
            r = await e.get_reply_message()
            user = await client.get_entity(r.sender_id)
            full = await client(GetFullUserRequest(user.id))
            bio = full.full_user.about or ""
            first_name = user.first_name or ""
            last_name = user.last_name or ""
            await client(UpdateProfileRequest(first_name=first_name, last_name=last_name, about=bio))
            photos = await client.get_profile_photos(user.id, limit=1)
            if photos:
                path = await client.download_media(photos[0])
                await client(UploadProfilePhotoRequest(file=await client.upload_file(path)))
                os.remove(path)
            await e.edit(f"✅ **پروفایل `{first_name}` کپی شد.**")
        except Exception as ex: await e.edit(f"❌ خطا: {ex}")
        return

    if t == "ذخیره پروفایل من":
        try:
            me = await client.get_me()
            full = await client(GetFullUserRequest(me.id))
            profile_data = {
                "first_name": me.first_name or "",
                "last_name": me.last_name or "",
                "bio": full.full_user.about or "",
            }
            photos = await client.get_profile_photos(me.id, limit=1)
            if photos:
                path = f"profiles/default_{me.id}.jpg"
                await client.download_media(photos[0], file=path)
                profile_data["photo_path"] = path
            data["default_profile"] = profile_data; save()
            await e.edit("✅ **پروفایل فعلی ذخیره شد** (`پروفایل پیشفرض` برای بازگردانی)")
        except Exception as ex: await e.edit(f"❌ خطا: {ex}")
        return

    if t == "پروفایل پیشفرض":
        try:
            prof = data.get("default_profile")
            if not prof:
                await e.edit("❌ **هیچ پروفایل ذخیره‌شده‌ای نیست.**\nاول `ذخیره پروفایل من` بزن."); return
            await client(UpdateProfileRequest(
                first_name=prof.get("first_name",""),
                last_name=prof.get("last_name",""),
                about=prof.get("bio","")
            ))
            photo_path = prof.get("photo_path")
            if photo_path and os.path.exists(photo_path):
                await client(UploadProfilePhotoRequest(file=await client.upload_file(photo_path)))
            await e.edit("✅ **پروفایل به حالت ذخیره‌شده برگشت.**")
        except Exception as ex: await e.edit(f"❌ خطا: {ex}")
        return

    if t == "دشمن" and e.is_reply:
        try:
            r = await e.get_reply_message()
            if r and r.sender_id:
                data["last_target_id"] = r.sender_id; save()
                await asyncio.sleep(0.3)
                result = await client.inline_query(BOT_USERNAME, "/enemy_panel")
                if result:
                    await result[0].click(e.chat_id)
                    await e.delete()
            else: await e.edit("❌ باید روی یک کاربر ریپلای کنی.")
        except: pass
        return

    if t == "حذف دشمن" and e.is_reply:
        uid = (await e.get_reply_message()).sender_id
        if uid in data["enemy"]: data["enemy"].remove(uid); save(); await e.edit(f"✅ `{uid}` حذف شد")
        return
    if t == "لیست دشمن":
        await e.edit("📋 **لیست دشمن:**\n" + ("\n".join([f"`{i}`" for i in data["enemy"]]) if data["enemy"] else "خالی")); return
    if t == "پاکسازی لیست دشمن":
        data["enemy"].clear(); save(); await e.edit("🗑 پاک شد"); return

    if t == "سکوت" and e.is_reply:
        uid = (await e.get_reply_message()).sender_id
        if uid not in data["silent"]: data["silent"].append(uid); save(); await e.edit(f"✅ `{uid}` سایلنت شد")
        return
    if t == "حذف سکوت" and e.is_reply:
        uid = (await e.get_reply_message()).sender_id
        if uid in data["silent"]: data["silent"].remove(uid); save(); await e.edit(f"✅ `{uid}` خارج شد")
        return
    if t == "لیست سکوت":
        await e.edit("📋 **لیست سکوت:**\n" + ("\n".join([f"`{i}`" for i in data["silent"]]) if data["silent"] else "خالی")); return
    if t == "پاکسازی لیست سکوت":
        data["silent"].clear(); save(); await e.edit("🗑 پاک شد"); return

    if t == "تنظیم دوست دشمن" and e.is_reply:
        uid = (await e.get_reply_message()).sender_id
        if uid not in data["friend_enemy"]: data["friend_enemy"].append(uid); data["friend_enemy_count"][str(uid)] = 0; save(); await e.edit(f"✅ `{uid}` اضافه شد")
        return
    if t == "حذف دوست دشمن" and e.is_reply:
        uid = (await e.get_reply_message()).sender_id
        if uid in data["friend_enemy"]: data["friend_enemy"].remove(uid); data["friend_enemy_count"].pop(str(uid), None); save(); await e.edit(f"✅ `{uid}` حذف شد")
        return
    if t == "لیست دوست دشمن":
        await e.edit("📋 **لیست دوست دشمن:**\n" + ("\n".join([f"`{i}`" for i in data["friend_enemy"]]) if data["friend_enemy"] else "خالی")); return
    if t == "پاکسازی لیست دوست دشمن":
        data["friend_enemy"].clear(); data["friend_enemy_count"].clear(); save(); await e.edit("🗑 پاک شد"); return

    if t.startswith("اسپم") and e.is_reply:
        try:
            n = int(t.split()[1]); r = await e.get_reply_message()
            for _ in range(n): await r.forward_to(e.chat_id)
            await e.edit(f"✅ {n} بار اسپم شد")
        except: await e.edit("❌ مثال: `اسپم 5`")
        return
    if t.startswith("حذف پیام"):
        try:
            c = int(t.split()[2]); msgs = await client.get_messages(e.chat_id, limit=c)
            await client.delete_messages(e.chat_id, [m.id for m in msgs])
            await e.edit(f"✅ {c} پیام حذف شد")
        except: await e.edit("❌ مثال: `حذف پیام 10`")
        return

    if t.startswith("."):
        try: await e.edit(f"`{t[1:]}` = **{eval(t[1:])}**")
        except: await e.edit(".")
        return

    if t == "ذخیره" and e.is_reply:
        r = await e.get_reply_message()
        if r.media:
            path = await r.download_media(file="saved_media/")
            await e.edit(f"✅ **ذخیره شد:** `{os.path.basename(path)}`")
        else: await e.edit("❌ مدیا نیست")
        return
    if t == "Lmedia":
        files = os.listdir("saved_media")
        await e.edit("📂 **لیست مدیا:**\n" + ("\n".join(files) if files else "خالی")); return
    if t.startswith("Smedia "):
        fname = t.split(" ", 1)[1]
        if os.path.exists(f"saved_media/{fname}"):
            await client.send_file(e.chat_id, f"saved_media/{fname}")
            await e.delete()
        return

    if t.startswith("اطلاعات"):
        try:
            user = await client.get_entity((await e.get_reply_message()).sender_id) if e.is_reply else await client.get_entity(t.split(" ", 1)[1])
            txt = f"👤 **نام:** {getattr(user, 'first_name', '')}\n👤 **فامیل:** {getattr(user, 'last_name', '')}\n🆔 **آیدی:** `{user.id}`\n🔗 **یوزرنیم:** @{getattr(user, 'username', 'ندارد')}"
            if hasattr(user, "title"): txt = f"🏷️ **نام:** {user.title}\n🆔 **آیدی:** `{user.id}`\n🔗 **یوزرنیم:** @{getattr(user, 'username', 'ندارد')}"
            await e.edit(txt)
        except: await e.edit("❌ پیدا نشد")
        return

    if t == "تاریخ":
        await e.edit(f"📅 **تاریخ شمسی:** `{JalaliDate.today().strftime('%Y/%m/%d')}`"); return

    if t.startswith("هوا "):
        await e.edit("🌤 در حال دریافت...")
        city = t.split(" ", 1)[1]
        try:
            weather = requests.get(f"https://wttr.in/{city}?format=3").text
            await e.edit(f"🌍 **آب و هوا:**\n`{weather}`")
        except: await e.edit("❌ خطا")
        return

    if t.startswith("آیپی "):
        await e.edit("🌐 در حال دریافت...")
        ip = t.split(" ", 1)[1]
        try:
            r = requests.get(f"http://ip-api.com/json/{ip}").json()
            await e.edit(f"🌐 **{ip}:**\nکشور: `{r['country']}`\nشهر: `{r['city']}`\nISP: `{r['isp']}`")
        except: await e.edit("❌ خطا")
        return

    if t.startswith("یوتیوب "):
        await e.edit("📥 در حال دانلود از یوتیوب...")
        try:
            ydl_opts = {'outtmpl': 'downloads/%(title)s.%(ext)s', 'format': 'best'}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(t.split(" ", 1)[1], download=True)
                file_path = ydl.prepare_filename(info)
            await client.send_file(e.chat_id, file_path)
            await e.delete(); os.remove(file_path)
        except Exception as ex: await e.edit(f"❌ خطا: {ex}")
        return

    if t == "نرخ ارز":
        try:
            msg_wait = await e.reply("⏳ در حال دریافت نرخ ارز...")
            link = EXCHANGE_GROUP_LINK
            if "t.me/+" in link:
                invite_hash = link.split("t.me/+", 1)[1].split("?", 1)[0]
                try: await client(ImportChatInviteRequest(invite_hash))
                except: pass
            target_chat = None
            async for dialog in client.iter_dialogs():
                if "نرخ ارز" in getattr(dialog.entity, "title", ""):
                    target_chat = dialog.entity; break
            if not target_chat:
                await msg_wait.edit("❌ گروه نرخ ارز پیدا نشد."); return
            await client.send_message(target_chat.id, "ارز")
            await asyncio.sleep(5)
            reply = None
            async for m in client.iter_messages(target_chat.id, limit=10):
                if m.sender_id and getattr(m.sender, "username", "") and m.sender.username.lower() == EXCHANGE_BOT_USERNAME.lower():
                    reply = m; break
            if reply:
                try: await msg_wait.edit(f"📊 **نرخ ارز:**\n\n{reply.text}")
                except: await e.reply(f"📊 **نرخ ارز:**\n\n{reply.text}")
            else:
                try: await msg_wait.edit("❌ ربات پاسخ نداد.")
                except: await e.reply("❌ ربات پاسخ نداد.")
        except Exception as ex: pass
        return

    if t == "تگ" and e.is_group:
        await e.edit("🏷 در حال تگ...")
        try:
            users = await client.get_participants(e.chat_id)
            tags = [f"[{u.first_name}](tg://user?id={u.id})" for u in users if not u.bot]
            await e.edit("📢 **تگ همه:**\n\n" + " ".join(tags))
        except: await e.edit("❌ خطا")
        return

    if t.startswith("بن ") and e.is_group:
        try:
            user = await client.get_entity(t.split(" ", 1)[1] if not t.split(" ", 1)[1].isdigit() else int(t.split(" ", 1)[1]))
            await client.kick_participant(e.chat_id, user)
            await e.edit(f"✅ `{user.first_name}` اخراج شد.")
        except: await e.edit("❌ خطا")
        return

    if t == "ادمین" and e.is_reply and e.is_group:
        uid = (await e.get_reply_message()).sender_id
        await client.edit_admin(e.chat_id, uid, is_admin=True)
        await e.edit("✅ ادمین شد."); return

    if t == "عزل" and e.is_reply and e.is_group:
        uid = (await e.get_reply_message()).sender_id
        await client.edit_admin(e.chat_id, uid, is_admin=False)
        await e.edit("✅ عزل شد."); return

    if t.startswith("پاکسازی ") and e.is_group:
        await e.edit("🗑 در حال پاکسازی...")
        msgs = await client.get_messages(e.chat_id, limit=100)
        to_del = [m.id for m in msgs if m.text and t.split(" ", 1)[1] in m.text]
        if to_del: await client.delete_messages(e.chat_id, to_del)
        await e.edit(f"✅ {len(to_del)} پیام پاک شد.")
        return

    if t.startswith("حذف اخیر "):
        try:
            c = int(t.split(" ", 1)[1]); msgs = await client.get_messages(e.chat_id, limit=c+1)
            await client.delete_messages(e.chat_id, [m.id for m in msgs])
            await e.edit(f"✅ {c} پیام پاک شد.")
        except: await e.edit("❌ خطا")
        return

    if t in ["سین زدن همه", "سین همه"]:
        await e.edit("👀 در حال سین...")
        try:
            async for dialog in client.iter_dialogs():
                await client.send_read_acknowledge(dialog.id)
            await e.edit("✅ پیام‌ها خوانده شدند.")
        except: await e.edit("❌ خطا")
        return

    if t.startswith("ویس "):
        await e.edit("🎙 در حال ساخت ویس...")
        try:
            tts = gTTS(text=t.split(" ", 1)[1], lang='en'); fname = "downloads/voice.mp3"
            tts.save(fname)
            await client.send_file(e.chat_id, fname, voice_note=True)
            await e.delete(); os.remove(fname)
        except: await e.edit("❌ خطا")
        return

    if t.startswith("افکت "):
        msg = await e.edit("⏳"); final = ""
        for char in t.split(" ", 1)[1]: final += char; await msg.edit(final); await asyncio.sleep(0.1)
        return

    if t == "کیوآر" and e.is_reply:
        r = await e.get_reply_message()
        if r.text:
            qrcode.make(r.text).save("downloads/qr.png")
            await client.send_file(e.chat_id, "downloads/qr.png")
            await e.delete(); os.remove("downloads/qr.png")
        return

    if t == "تلویزیون":
        await e.edit("📺 **لینک‌های TV:**\n[Persian TV](https://t.me/persiantv)\n[Manoto](https://t.me/manototv)", link_preview=False)
        return

    if t.startswith("تایمر "):
        data["timers"][t.split(" ", 1)[1]] = dt.now().timestamp() + 3600; save()
        await e.edit(f"⏰ تایمر `{t.split(' ', 1)[1]}` برای ۱ ساعت تنظیم شد.")
        return

    if t == "لیست تایمر":
        if not data["timers"]: await e.edit("📭 تایمری نیست.")
        else:
            txt = "⏰ **تایمرها:**\n"
            for n, time_end in data["timers"].items(): txt += f"• `{n}` (باقیمانده: {int(time_end - dt.now().timestamp())} ثانیه)\n"
            await e.edit(txt)
        return

    mode = data.get("text_mode")
    action = data.get("action_on")
    if mode or action:
        skip_words = ["پنل", "setname", "setbio", "setpic", "پینگ", "رم", "ساعت", "فونت",
                      "ست فونت", "سیو", "حالت منشی", "متن منشی", "سرچ اهنگ", "ارسال",
                      "حالت متن", "اکشن", "قفل", "ترجمه", "سین", "ریکشن", "لیست", "پاکسازی",
                      "اسکرین", "تنظیم", "کامنت اول", "متن کامنت", "عضویت", "متن عضویت",
                      "کپی پروفایل", "ذخیره پروفایل", "پروفایل پیشفرض", "دشمن", "سکوت",
                      "تنظیم دوست دشمن", "حذف دوست دشمن", "اسپم", "حذف پیام", "ذخیره",
                      "Lmedia", "Smedia", "اطلاعات", "تاریخ", "هوا", "آیپی", "یوتیوب",
                      "نرخ ارز", "تگ", "بن", "ادمین", "عزل", "حذف اخیر", "ویس", "افکت",
                      "کیوآر", "تلویزیون", "تایمر"]
        if not any(t.startswith(w) for w in skip_words):
            if action:
                try:
                    await e.delete()
                    await action_animate(e.chat_id, t)
                except: pass
                return
            if mode == "bold":
                try: await e.edit(f"**{t}**")
                except: pass
                return
            if mode == "italic":
                try: await e.edit(f"__{t}__")
                except: pass
                return
            if mode == "spoiler":
                try: await e.edit(f"||{t}||")
                except: pass
                return
            if mode == "underline":
                try: await e.edit(f"__{t}__")
                except: pass
                return
            if mode == "strike":
                try: await e.edit(f"~~{t}~~")
                except: pass
                return
            if mode == "code":
                try: await e.edit(f"`{t}`")
                except: pass
                return

@client.on(events.NewMessage(incoming=True))
async def auto_reply(e):
    if not e.is_private: return
    sid = e.sender_id
    if data.get("force_join_on"):
        ok, ch = await check_force_join(sid)
        if not ok and ch:
            try:
                username = getattr(ch, 'username', None)
                link = f"https://t.me/{username}" if username else "لینک در دسترس نیست"
                await e.reply(f"{data['force_join_text']}\n\n{link}")
            except: pass
            return
    if sid in data["enemy"]:
        try: await e.reply(random.choice(ENEMY_TEXTS))
        except: pass
    elif sid in data["silent"]:
        try: await e.delete()
        except: pass
    elif sid in data["friend_enemy"]:
        try:
            sid_str = str(sid)
            c = data["friend_enemy_count"].get(sid_str, 0)
            if c < MAX_FRIEND_ENEMY_REPLY:
                await e.reply(random.choice(FRIEND_ENEMY_TEXTS))
                data["friend_enemy_count"][sid_str] = c + 1
                save()
        except: pass
    elif data.get("secretary_on"):
        try:
            await asyncio.sleep(2)
            await e.reply(data["secretary_text"])
        except: pass

async def main():
    global ADMIN_ID
    try:
        for i, acc in enumerate(accounts, 1):
            try:
                await acc.start()
                me = await acc.get_me()
                print(f"✅ Account {i} ({acc.session.filename}) | Logged in as {me.id}")
            except Exception as e:
                print(f"❌ Account {i} | Error: {e}")

        await bot.start(bot_token=BOT_TOKEN)
        me = await accounts[0].get_me()
        ADMIN_ID = me.id

        asyncio.create_task(clock_loop())
        asyncio.create_task(timer_loop())

        print(f"\n🚀 SELF BOT RUNNING WITH {len(accounts)} ACCOUNTS")
        print(f"🔒 BOT LOCKED TO ID: {ADMIN_ID}")

        await asyncio.gather(
            *[acc.run_until_disconnected() for acc in accounts],
            bot.run_until_disconnected()
        )
    except Exception as err:
        print(f"Main error: {err}")

if __name__ == "__main__":
    asyncio.run(main())
